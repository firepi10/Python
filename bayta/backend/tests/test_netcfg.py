"""bayta-netcfg reads Wi-Fi settings off the FAT boot partition — the only
surface a wall-mounted Pi with no keyboard and no network exposes to its owner.
It runs unattended at boot, so its parsing has to survive whatever a text editor
on a Mac or a Windows box produces."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "os" / "net" / "bayta-netcfg.sh"


@pytest.fixture
def run_netcfg(tmp_path):
    """Run the script with nmcli/rfkill/raspi-config stubbed, returning the
    argv nmcli was called with plus the state of the config file afterwards."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = bin_dir / "nmcli-calls"

    tzcalls = bin_dir / "tz-calls"

    (bin_dir / "nmcli").write_text(
        '#!/usr/bin/env bash\n'
        f'if [ "$1" = "device" ]; then printf "%s\\n" "$*" >> "{calls}"; fi\n'
        'exit ${NMCLI_RC:-0}\n'
    )
    (bin_dir / "timedatectl").write_text(
        '#!/usr/bin/env bash\n'
        f'printf "%s\\n" "$*" >> "{tzcalls}"\n'
        'exit ${TIMEDATECTL_RC:-0}\n'
    )
    for stub in ("rfkill", "raspi-config", "systemctl"):
        (bin_dir / stub).write_text("#!/usr/bin/env bash\nexit 0\n")
    for f in bin_dir.iterdir():
        f.chmod(0o755)

    def _run(contents: str, nmcli_rc: int = 0):
        conf = tmp_path / "bayta-wifi.txt"
        conf.write_text(contents)
        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["BAYTA_WIFI_CONF"] = str(conf)
        env["NMCLI_RC"] = str(nmcli_rc)
        proc = subprocess.run(
            [shutil.which("bash"), str(SCRIPT)], env=env, capture_output=True, text=True
        )
        return {
            "rc": proc.returncode,
            "nmcli": calls.read_text().strip() if calls.exists() else "",
            "tz": tzcalls.read_text().strip() if tzcalls.exists() else "",
            "conf_exists": conf.exists(),
            "conf": conf.read_text() if conf.exists() else "",
            "stderr": proc.stderr,
        }

    return _run


def test_joins_a_wpa_network(run_netcfg):
    r = run_netcfg("ssid=CTLCS\npassword=hunter2\ncountry=US\n")
    assert "device wifi connect CTLCS password hunter2" in r["nmcli"]


def test_open_network_sends_no_password(run_netcfg):
    r = run_netcfg("ssid=EMGUEST\ncountry=US\n")
    assert "device wifi connect EMGUEST name bayta-wifi" in r["nmcli"]
    assert "password" not in r["nmcli"]


def test_password_may_contain_spaces_and_punctuation(run_netcfg):
    """Trim the line, not the value — 'correct horse battery!!' is a password."""
    r = run_netcfg("ssid = My Net \npassword = correct horse battery!! \n")
    assert "device wifi connect My Net password correct horse battery!!" in r["nmcli"]


def test_survives_windows_line_endings_and_comments(run_netcfg):
    r = run_netcfg("# my wifi\r\nssid=CTLCS\r\n\r\npassword=abc123\r\n")
    assert "device wifi connect CTLCS password abc123" in r["nmcli"]
    assert "\r" not in r["nmcli"]


def test_config_is_deleted_once_connected(run_netcfg):
    """The password must not linger on a partition any computer can read."""
    r = run_netcfg("ssid=CTLCS\npassword=hunter2\n")
    assert r["conf_exists"] is False


def test_failed_join_keeps_the_file_and_says_so(run_netcfg):
    """A typo — or a card configured at work and booted at home — has to be
    recoverable without re-flashing."""
    r = run_netcfg("ssid=Typo\npassword=nope\n", nmcli_rc=4)
    assert r["conf_exists"] is True
    assert "Could not join" in r["conf"]
    assert "out of range" in r["conf"]
    assert "ssid=Typo" in r["conf"]
    assert r["rc"] == 0, "a bad password must never wedge the boot"


def test_the_settings_survive_repeated_failures(tmp_path, run_netcfg, monkeypatch):
    """Booted out of range for days, the file must stay parseable and not grow
    a new complaint every time — it still has to work on the boot that counts."""
    r = run_netcfg("ssid=CTLCS\npassword=hunter2\n", nmcli_rc=4)
    for _ in range(3):
        r = run_netcfg(r["conf"], nmcli_rc=4)
    assert r["conf"].count("Could not join") == 1

    # and the settings still parse on the boot where the network is in range
    ok = run_netcfg(r["conf"])
    assert "device wifi connect CTLCS password hunter2" in ok["nmcli"]
    assert ok["conf_exists"] is False


def test_no_file_is_a_no_op(tmp_path, run_netcfg):
    env = dict(os.environ)
    env["BAYTA_WIFI_CONF"] = str(tmp_path / "absent.txt")
    proc = subprocess.run(
        [shutil.which("bash"), str(SCRIPT)], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_file_without_an_ssid_does_nothing(run_netcfg):
    r = run_netcfg("country=US\n# nothing useful here\n")
    assert r["nmcli"] == ""
    assert r["rc"] == 0


def test_timezone_is_applied(run_netcfg):
    r = run_netcfg("ssid=CTLCS\npassword=hunter2\ntimezone=America/Chicago\n")
    assert "set-timezone America/Chicago" in r["tz"]
    assert "device wifi connect CTLCS" in r["nmcli"]


def test_timezone_alone_needs_no_wifi(run_netcfg):
    """Fixing a card that is already on the network shouldn't require Wi-Fi
    settings you don't want to re-enter."""
    r = run_netcfg("timezone=America/Chicago\n")
    assert "set-timezone America/Chicago" in r["tz"]
    assert r["nmcli"] == ""
    assert r["conf_exists"] is False, "applied and nothing secret left behind"
    assert r["rc"] == 0


def test_a_bogus_timezone_is_refused_not_applied(run_netcfg):
    r = run_netcfg("timezone=Mars/Olympus_Mons\n")
    assert r["tz"] == ""
    assert "unknown timezone" in r["stderr"]
    assert r["conf_exists"] is True, "leave it so the typo can be corrected"
    assert r["rc"] == 0


def test_timezone_survives_a_failed_wifi_join(run_netcfg):
    """Out of range tonight, right clock anyway — and the file is kept so the
    join retries at home."""
    r = run_netcfg("ssid=CTLCS\npassword=x\ntimezone=America/Chicago\n", nmcli_rc=4)
    assert "set-timezone America/Chicago" in r["tz"]
    assert r["conf_exists"] is True
    assert "timezone=America/Chicago" in r["conf"]
