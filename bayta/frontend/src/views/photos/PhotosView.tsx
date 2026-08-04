import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CloudDownload, Images, Plus, Upload } from "lucide-react";
import { EmptyState } from "../../components/EmptyState";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { useToast } from "../../components/Toast";

interface PhotoDTO {
  id: number;
  url: string;
  thumb: string;
  source: string;
  hidden: boolean;
}

interface AlbumDTO {
  id: number;
  name: string;
  last_sync_at: string | null;
  last_error: string | null;
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function PhotosView() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [albumSheet, setAlbumSheet] = useState(false);
  const [albumUrl, setAlbumUrl] = useState("");
  const [albumError, setAlbumError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PhotoDTO | null>(null);

  const { data: photos } = useQuery({
    queryKey: ["photos"],
    queryFn: () => getJSON<PhotoDTO[]>("/api/photos"),
  });
  const { data: albums } = useQuery({
    queryKey: ["photos", "albums"],
    queryFn: () => getJSON<AlbumDTO[]>("/api/photos/shared-albums"),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["photos"] });

  const upload = useMutation({
    mutationFn: async (files: FileList) => {
      const form = new FormData();
      for (const f of files) form.append("files", f);
      const r = await fetch("/api/photos/upload", { method: "POST", body: form });
      if (!r.ok) throw new Error(await r.text());
      return r.json() as Promise<{ added: number; duplicates: number; failed: number }>;
    },
    onSuccess: (result) => {
      invalidate();
      toast(
        result.added > 0
          ? `Added ${result.added} photo${result.added === 1 ? "" : "s"}`
          : "Those photos were already here",
      );
    },
  });

  const addAlbum = useMutation({
    mutationFn: async () => {
      const r = await fetch("/api/photos/shared-albums", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: albumUrl }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({ detail: "Something went wrong" }));
        throw new Error(body.detail);
      }
      return r.json() as Promise<{ name: string; added: number }>;
    },
    onSuccess: (result) => {
      invalidate();
      setAlbumSheet(false);
      setAlbumUrl("");
      setAlbumError(null);
      toast(`Connected “${result.name}” — ${result.added} photos synced`);
    },
    onError: (e: Error) => setAlbumError(e.message),
  });

  const patchPhoto = useMutation({
    mutationFn: (vars: { id: number; hidden: boolean }) =>
      fetch(`/api/photos/${vars.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hidden: vars.hidden }),
      }),
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
  });
  const deletePhoto = useMutation({
    mutationFn: (id: number) => fetch(`/api/photos/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      invalidate();
      setSelected(null);
      toast("Photo deleted");
    },
  });

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, flex: 1 }}>
          Photos{" "}
          <span style={{ color: "var(--text-tertiary)", fontWeight: 500, fontSize: 18 }}>
            {photos?.length ?? 0}
          </span>
        </h1>
        {albums?.map((a) => (
          <span
            key={a.id}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 600,
              color: a.last_error ? "var(--danger)" : "var(--text-secondary)",
              background: "var(--surface-solid)",
              border: "1px solid var(--surface-border)",
              borderRadius: 999,
              padding: "6px 12px",
            }}
          >
            <CloudDownload size={14} /> {a.name}
          </span>
        ))}
        <TouchButton variant="secondary" size="sm" onClick={() => setAlbumSheet(true)}>
          <Plus size={15} style={{ display: "inline", verticalAlign: -2 }} /> iCloud album
        </TouchButton>
        <TouchButton variant="primary" size="sm" onClick={() => fileInput.current?.click()}>
          <Upload size={15} style={{ display: "inline", verticalAlign: -2 }} />{" "}
          {upload.isPending ? "Uploading…" : "Upload"}
        </TouchButton>
        <input
          ref={fileInput}
          type="file"
          accept="image/*,.heic,.heif"
          multiple
          hidden
          onChange={(e) => e.target.files?.length && upload.mutate(e.target.files)}
        />
      </div>

      {(!photos || photos.length === 0) && (
        <EmptyState
          icon={Images}
          title="No photos yet"
          hint="Connect an iCloud shared album or upload from your phone — they'll appear on the wall automatically."
        />
      )}

      {photos && photos.length > 0 && (
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
            gap: 8,
            alignContent: "start",
          }}
        >
          {photos.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelected(p)}
              className="touch-btn"
              style={{
                border: "none",
                padding: 0,
                borderRadius: "var(--radius-sm)",
                overflow: "hidden",
                aspectRatio: "1",
                opacity: p.hidden ? 0.35 : 1,
                transition: `transform var(--dur-fast) var(--ease-spring)`,
                background: "var(--surface-solid)",
              }}
            >
              <img
                src={p.thumb}
                alt=""
                loading="lazy"
                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              />
            </button>
          ))}
        </div>
      )}

      <Sheet open={albumSheet} onClose={() => setAlbumSheet(false)} title="Connect an iCloud shared album">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.5 }}>
            In Apple Photos: make a <b>Shared Album</b>, turn on <b>Public Website</b>, then
            copy the icloud.com link and paste it here. Anything anyone adds to the album shows
            up on the wall within about 30 minutes — no passwords needed.
          </div>
          <input
            style={{
              border: "1px solid var(--surface-border)",
              background: "var(--bg)",
              color: "var(--text)",
              borderRadius: "var(--radius-sm)",
              padding: "12px 14px",
              fontSize: 16,
              fontFamily: "inherit",
            }}
            placeholder="https://www.icloud.com/sharedalbum/#B0…"
            value={albumUrl}
            onChange={(e) => setAlbumUrl(e.target.value)}
          />
          {albumError && <div style={{ color: "var(--danger)", fontSize: 14 }}>{albumError}</div>}
          <TouchButton
            variant="primary"
            disabled={!albumUrl.trim() || addAlbum.isPending}
            onClick={() => addAlbum.mutate()}
          >
            {addAlbum.isPending ? "Connecting…" : "Connect album"}
          </TouchButton>
        </div>
      </Sheet>

      <Sheet open={selected !== null} onClose={() => setSelected(null)} title="Photo">
        {selected && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <img
              src={selected.url}
              alt=""
              style={{ width: "100%", borderRadius: "var(--radius-md)", maxHeight: 320, objectFit: "contain" }}
            />
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <TouchButton variant="danger" onClick={() => deletePhoto.mutate(selected.id)}>
                Delete
              </TouchButton>
              <TouchButton
                variant="secondary"
                onClick={() => patchPhoto.mutate({ id: selected.id, hidden: !selected.hidden })}
              >
                {selected.hidden ? "Show on wall" : "Hide from wall"}
              </TouchButton>
              <TouchButton variant="primary" onClick={() => setSelected(null)}>
                Done
              </TouchButton>
            </div>
          </div>
        )}
      </Sheet>
    </div>
  );
}
