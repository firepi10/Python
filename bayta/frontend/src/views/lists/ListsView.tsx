import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Plus } from "lucide-react";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";

interface ListItemDTO {
  id: number;
  text: string;
  done: boolean;
}

interface ListDTO {
  id: number;
  name: string;
  kind: string;
  icon: string | null;
  items: ListItemDTO[];
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function ListsView() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [newListOpen, setNewListOpen] = useState(false);
  const [newListName, setNewListName] = useState("");

  const { data: lists } = useQuery({
    queryKey: ["lists"],
    queryFn: () => getJSON<ListDTO[]>("/api/lists"),
  });
  const active = lists?.find((l) => l.id === activeId) ?? lists?.[0];

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["lists"] });

  const addItem = useMutation({
    mutationFn: () =>
      fetch(`/api/lists/${active!.id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: draft.trim() }),
      }),
    onSuccess: () => {
      invalidate();
      setDraft("");
    },
  });
  const toggleItem = useMutation({
    mutationFn: (item: ListItemDTO) =>
      fetch(`/api/lists/items/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ done: !item.done }),
      }),
    onSuccess: invalidate,
  });
  const clearDone = useMutation({
    mutationFn: () => fetch(`/api/lists/${active!.id}/clear-done`, { method: "POST" }),
    onSuccess: invalidate,
  });
  const createList = useMutation({
    mutationFn: () =>
      fetch("/api/lists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newListName.trim(), kind: "custom" }),
      }),
    onSuccess: () => {
      invalidate();
      setNewListOpen(false);
      setNewListName("");
    },
  });

  const doneCount = active?.items.filter((i) => i.done).length ?? 0;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12, maxWidth: 860, margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {lists?.map((l) => (
          <TouchButton
            key={l.id}
            variant={l.id === (active?.id ?? -1) ? "primary" : "secondary"}
            size="sm"
            onClick={() => setActiveId(l.id)}
          >
            {l.icon && `${l.icon} `}
            {l.name}
            {l.items.filter((i) => !i.done).length > 0 && (
              <span style={{ opacity: 0.7, marginLeft: 6 }}>
                {l.items.filter((i) => !i.done).length}
              </span>
            )}
          </TouchButton>
        ))}
        <TouchButton variant="ghost" size="sm" onClick={() => setNewListOpen(true)}>
          <Plus size={16} style={{ display: "inline", verticalAlign: -3 }} /> New list
        </TouchButton>
        <div style={{ flex: 1 }} />
        {doneCount > 0 && (
          <TouchButton variant="ghost" size="sm" onClick={() => clearDone.mutate()}>
            Clear {doneCount} done
          </TouchButton>
        )}
      </div>

      {active && (
        <>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              style={{
                flex: 1,
                border: "1px solid var(--surface-border)",
                background: "var(--surface-solid)",
                color: "var(--text)",
                borderRadius: "var(--radius-md)",
                padding: "14px 16px",
                fontSize: 17,
                fontFamily: "inherit",
                boxShadow: "var(--shadow-card)",
              }}
              placeholder={`Add to ${active.name}…`}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && draft.trim() && addItem.mutate()}
            />
            <TouchButton variant="primary" disabled={!draft.trim()} onClick={() => addItem.mutate()}>
              Add
            </TouchButton>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
            {active.items.map((item) => (
              <button
                key={item.id}
                className="touch-btn"
                onClick={() => toggleItem.mutate(item)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-solid)",
                  borderRadius: "var(--radius-md)",
                  padding: "13px 16px",
                  fontFamily: "inherit",
                  color: "var(--text)",
                  textAlign: "left",
                  transition: `transform var(--dur-fast) var(--ease-spring)`,
                }}
              >
                <span
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: "50%",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: item.done ? "none" : "2px solid var(--accent)",
                    background: item.done ? "var(--accent)" : "transparent",
                    color: "#fff",
                  }}
                >
                  {item.done && <Check size={16} strokeWidth={3} />}
                </span>
                <span
                  style={{
                    fontSize: 16.5,
                    fontWeight: 600,
                    textDecoration: item.done ? "line-through" : "none",
                    opacity: item.done ? 0.5 : 1,
                  }}
                >
                  {item.text}
                </span>
              </button>
            ))}
            {active.items.length === 0 && (
              <div style={{ color: "var(--text-tertiary)", textAlign: "center", marginTop: 40, fontSize: 15 }}>
                Nothing here yet.
              </div>
            )}
          </div>
        </>
      )}

      <Sheet open={newListOpen} onClose={() => setNewListOpen(false)} title="New list">
        <div style={{ display: "flex", gap: 10 }}>
          <input
            style={{
              flex: 1,
              border: "1px solid var(--surface-border)",
              background: "var(--bg)",
              color: "var(--text)",
              borderRadius: "var(--radius-sm)",
              padding: "12px 14px",
              fontSize: 16,
              fontFamily: "inherit",
            }}
            placeholder="List name"
            value={newListName}
            onChange={(e) => setNewListName(e.target.value)}
          />
          <TouchButton variant="primary" disabled={!newListName.trim()} onClick={() => createList.mutate()}>
            Create
          </TouchButton>
        </div>
      </Sheet>
    </div>
  );
}
