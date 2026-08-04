"""Thin WebDAV/CalDAV request helpers (httpx).

Discovery uses the `caldav` library (it knows iCloud's principal redirect
dance); the sync loop itself uses these primitives for exact control over
etags, If-Match conflict detection, and multiget batching. Works against
iCloud and Radicale alike.
"""

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import httpx

NS = {
    "d": "DAV:",
    "c": "urn:ietf:params:xml:ns:caldav",
    "cs": "http://calendarserver.org/ns/",
}

PROPFIND_CTAG = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">'
    "<d:prop><cs:getctag/></d:prop></d:propfind>"
)

PROPFIND_ETAGS = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:">'
    "<d:prop><d:getetag/><d:resourcetype/></d:prop></d:propfind>"
)


class CalDAVAuthError(Exception):
    pass


class CalDAVConflict(Exception):
    """412 Precondition Failed — the server copy changed under us."""


@dataclass
class RemoteObject:
    href: str
    etag: str | None
    data: str | None = None


def make_client(username: str, password: str) -> httpx.Client:
    return httpx.Client(
        auth=httpx.BasicAuth(username, password),
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Bayta/1.0"},
    )


def _raise_for_auth(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise CalDAVAuthError(f"{resp.status_code} from {resp.request.url}")


def get_ctag(client: httpx.Client, calendar_url: str) -> str | None:
    resp = client.request(
        "PROPFIND", calendar_url, content=PROPFIND_CTAG, headers={"Depth": "0"}
    )
    _raise_for_auth(resp)
    if resp.status_code >= 400:
        return None
    root = ET.fromstring(resp.content)
    el = root.find(".//cs:getctag", NS)
    return el.text if el is not None else None


def list_etags(client: httpx.Client, calendar_url: str) -> dict[str, str | None]:
    """href -> etag for every .ics resource in the collection."""
    resp = client.request(
        "PROPFIND", calendar_url, content=PROPFIND_ETAGS, headers={"Depth": "1"}
    )
    _raise_for_auth(resp)
    resp.raise_for_status()
    out: dict[str, str | None] = {}
    root = ET.fromstring(resp.content)
    for response in root.findall("d:response", NS):
        href_el = response.find("d:href", NS)
        if href_el is None or not href_el.text:
            continue
        href = href_el.text
        # skip the collection itself
        if href.rstrip("/") == urlparse(calendar_url).path.rstrip("/"):
            continue
        is_collection = response.find(".//d:resourcetype/d:collection", NS) is not None
        if is_collection:
            continue
        etag_el = response.find(".//d:getetag", NS)
        out[href] = etag_el.text if etag_el is not None else None
    return out


def multiget(
    client: httpx.Client, calendar_url: str, hrefs: list[str], batch: int = 50
) -> list[RemoteObject]:
    """calendar-multiget REPORT: fetch ICS payloads for specific hrefs."""
    results: list[RemoteObject] = []
    for i in range(0, len(hrefs), batch):
        chunk = hrefs[i : i + batch]
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<c:calendar-multiget xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
            + "".join(f"<d:href>{href}</d:href>" for href in chunk)
            + "</c:calendar-multiget>"
        )
        resp = client.request(
            "REPORT", calendar_url, content=body, headers={"Depth": "1"}
        )
        _raise_for_auth(resp)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for response in root.findall("d:response", NS):
            href_el = response.find("d:href", NS)
            data_el = response.find(".//c:calendar-data", NS)
            etag_el = response.find(".//d:getetag", NS)
            if href_el is None or not href_el.text:
                continue
            results.append(
                RemoteObject(
                    href=href_el.text,
                    etag=etag_el.text if etag_el is not None else None,
                    data=data_el.text if data_el is not None else None,
                )
            )
    return results


def absolute(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def put_event(
    client: httpx.Client,
    url: str,
    ics: str,
    *,
    etag: str | None = None,
    is_new: bool = False,
) -> str | None:
    """PUT an event. If-None-Match guards creates; If-Match guards updates
    when we hold an etag. Returns the new etag when the server sends one."""
    headers = {"Content-Type": "text/calendar; charset=utf-8"}
    if is_new:
        headers["If-None-Match"] = "*"
    elif etag:
        headers["If-Match"] = etag
    resp = client.put(url, content=ics.encode(), headers=headers)
    _raise_for_auth(resp)
    if resp.status_code == 412:
        raise CalDAVConflict(url)
    resp.raise_for_status()
    return resp.headers.get("ETag")


def delete_event(client: httpx.Client, url: str, *, etag: str | None = None) -> None:
    headers = {"If-Match": etag} if etag else {}
    resp = client.delete(url, headers=headers)
    _raise_for_auth(resp)
    if resp.status_code == 412:
        raise CalDAVConflict(url)
    # 404/410: already gone — that is success for a delete
    if resp.status_code not in (404, 410):
        resp.raise_for_status()
