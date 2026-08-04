import { useMemo, useState } from "react";
import { addDays, addWeeks, format, isSameDay, startOfWeek } from "date-fns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ShoppingCart, Star, UtensilsCrossed } from "lucide-react";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { useToast } from "../../components/Toast";

interface MealDTO {
  id: number;
  name: string;
  icon: string | null;
  is_favorite: boolean;
  ingredients: string[];
}

interface PlanEntry {
  date: string;
  slot: string;
  meal_id: number | null;
  meal_name: string | null;
  meal_icon: string | null;
  custom_text: string | null;
}

const SLOTS = ["breakfast", "lunch", "dinner"] as const;
const SLOT_LABEL: Record<string, string> = { breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner" };

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function MealsView() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [anchor, setAnchor] = useState(() => new Date());
  const [picker, setPicker] = useState<{ date: Date; slot: string } | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [custom, setCustom] = useState("");

  const weekStart = useMemo(() => startOfWeek(anchor), [anchor]);
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);
  const startISO = format(weekStart, "yyyy-MM-dd");
  const endISO = format(addDays(weekStart, 6), "yyyy-MM-dd");

  const { data: meals } = useQuery({
    queryKey: ["meals"],
    queryFn: () => getJSON<MealDTO[]>("/api/meals"),
  });
  const { data: plan } = useQuery({
    queryKey: ["mealplan", startISO],
    queryFn: () => getJSON<PlanEntry[]>(`/api/meals/plan?start=${startISO}&end=${endISO}`),
  });

  const invalidatePlan = () => queryClient.invalidateQueries({ queryKey: ["mealplan"] });

  const putPlan = useMutation({
    mutationFn: (body: { date: string; slot: string; meal_id?: number | null; custom_text?: string | null }) =>
      fetch("/api/meals/plan", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      invalidatePlan();
      setPicker(null);
      setCustom("");
    },
  });

  const grocery = useMutation({
    mutationFn: async () => {
      const r = await fetch(`/api/meals/plan/grocery?start=${startISO}&end=${endISO}`, { method: "POST" });
      return r.json() as Promise<{ added: number }>;
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["lists"] });
      toast(
        result.added > 0
          ? `Added ${result.added} ingredient${result.added === 1 ? "" : "s"} to Groceries`
          : "Grocery list already has everything",
      );
    },
  });

  const entryFor = (day: Date, slot: string) =>
    plan?.find((e) => e.slot === slot && isSameDay(new Date(`${e.date}T12:00:00`), day));

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, flex: 1 }}>
          Meals{" "}
          <span style={{ color: "var(--text-tertiary)", fontWeight: 500, fontSize: 18 }}>
            {format(weekStart, "MMM d")} – {format(addDays(weekStart, 6), "MMM d")}
          </span>
        </h1>
        <TouchButton variant="secondary" size="sm" onClick={() => setAnchor(addWeeks(anchor, -1))}>
          <ChevronLeft size={18} style={{ display: "block" }} />
        </TouchButton>
        <TouchButton variant="secondary" size="sm" onClick={() => setAnchor(new Date())}>
          This week
        </TouchButton>
        <TouchButton variant="secondary" size="sm" onClick={() => setAnchor(addWeeks(anchor, 1))}>
          <ChevronRight size={18} style={{ display: "block" }} />
        </TouchButton>
        <TouchButton variant="secondary" size="sm" onClick={() => setLibraryOpen(true)}>
          <UtensilsCrossed size={15} style={{ display: "inline", verticalAlign: -2 }} /> Library
        </TouchButton>
        <TouchButton variant="primary" size="sm" onClick={() => grocery.mutate()} disabled={grocery.isPending}>
          <ShoppingCart size={15} style={{ display: "inline", verticalAlign: -2 }} /> Grocery list
        </TouchButton>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: "72px repeat(7, 1fr)",
          gridTemplateRows: `34px repeat(${SLOTS.length}, 1fr)`,
          gap: 6,
        }}
      >
        <div />
        {days.map((day) => {
          const today = isSameDay(day, new Date());
          return (
            <div key={day.toISOString()} style={{ textAlign: "center" }}>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: today ? "var(--accent)" : "var(--text-secondary)",
                }}
              >
                {format(day, "EEE d")}
              </span>
            </div>
          );
        })}
        {SLOTS.map((slot) => (
          <div key={`row-${slot}`} style={{ display: "contents" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                fontSize: 12,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--text-tertiary)",
              }}
            >
              {SLOT_LABEL[slot]}
            </div>
            {days.map((day) => {
              const entry = entryFor(day, slot);
              const label = entry?.meal_name ?? entry?.custom_text;
              return (
                <button
                  key={`${slot}-${day.toISOString()}`}
                  className="touch-btn"
                  onClick={() => setPicker({ date: day, slot })}
                  style={{
                    border: "1px solid var(--surface-border)",
                    background: label ? "var(--accent-soft)" : "var(--surface-solid)",
                    borderRadius: "var(--radius-sm)",
                    fontFamily: "inherit",
                    color: "var(--text)",
                    padding: 8,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 4,
                    minHeight: 0,
                    overflow: "hidden",
                    transition: `transform var(--dur-fast) var(--ease-spring)`,
                  }}
                >
                  {entry?.meal_icon && <span style={{ fontSize: 22 }}>{entry.meal_icon}</span>}
                  <span
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: label ? "var(--text)" : "var(--text-tertiary)",
                      textAlign: "center",
                    }}
                  >
                    {label ?? "+"}
                  </span>
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* slot picker */}
      <Sheet
        open={picker !== null}
        onClose={() => setPicker(null)}
        title={picker ? `${SLOT_LABEL[picker.slot]} · ${format(picker.date, "EEEE")}` : undefined}
      >
        {picker && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 8 }}>
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
                placeholder="Type anything… (Leftovers, Order pizza)"
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
              />
              <TouchButton
                variant="primary"
                disabled={!custom.trim()}
                onClick={() =>
                  putPlan.mutate({
                    date: format(picker.date, "yyyy-MM-dd"),
                    slot: picker.slot,
                    custom_text: custom.trim(),
                  })
                }
              >
                Set
              </TouchButton>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, maxHeight: 300, overflowY: "auto" }}>
              {meals?.map((m) => (
                <TouchButton
                  key={m.id}
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    putPlan.mutate({
                      date: format(picker.date, "yyyy-MM-dd"),
                      slot: picker.slot,
                      meal_id: m.id,
                    })
                  }
                >
                  {m.icon && `${m.icon} `}
                  {m.name}
                  {m.is_favorite && <Star size={12} style={{ display: "inline", verticalAlign: -1, marginLeft: 4 }} />}
                </TouchButton>
              ))}
              {(!meals || meals.length === 0) && (
                <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>
                  No saved meals yet — add favorites in the Library.
                </span>
              )}
            </div>
            <TouchButton
              variant="ghost"
              onClick={() =>
                putPlan.mutate({ date: format(picker.date, "yyyy-MM-dd"), slot: picker.slot })
              }
            >
              Clear this slot
            </TouchButton>
          </div>
        )}
      </Sheet>

      <MealLibrarySheet open={libraryOpen} onClose={() => setLibraryOpen(false)} meals={meals ?? []} />
    </div>
  );
}

function MealLibrarySheet({
  open,
  onClose,
  meals,
}: {
  open: boolean;
  onClose: () => void;
  meals: MealDTO[];
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [icon, setIcon] = useState("");
  const [ingredients, setIngredients] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["meals"] });
  const create = useMutation({
    mutationFn: () =>
      fetch("/api/meals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          icon: icon.trim() || null,
          is_favorite: true,
          ingredients: ingredients
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      }),
    onSuccess: () => {
      invalidate();
      setName("");
      setIcon("");
      setIngredients("");
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => fetch(`/api/meals/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });

  const field: React.CSSProperties = {
    border: "1px solid var(--surface-border)",
    background: "var(--bg)",
    color: "var(--text)",
    borderRadius: "var(--radius-sm)",
    padding: "10px 12px",
    fontSize: 15,
    fontFamily: "inherit",
  };

  return (
    <Sheet open={open} onClose={onClose} title="Meal library">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "56px 1fr auto", gap: 8 }}>
          <input style={field} placeholder="🌮" value={icon} onChange={(e) => setIcon(e.target.value)} />
          <input style={field} placeholder="Meal name" value={name} onChange={(e) => setName(e.target.value)} />
          <TouchButton variant="primary" size="sm" disabled={!name.trim()} onClick={() => create.mutate()}>
            Add
          </TouchButton>
        </div>
        <input
          style={field}
          placeholder="Ingredients, comma separated (for the grocery list)"
          value={ingredients}
          onChange={(e) => setIngredients(e.target.value)}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 320, overflowY: "auto" }}>
          {meals.map((m) => (
            <div
              key={m.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 4px",
                borderBottom: "1px solid var(--surface-border)",
              }}
            >
              <span style={{ fontSize: 20, width: 28, textAlign: "center" }}>{m.icon ?? "🍽️"}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600 }}>{m.name}</div>
                {m.ingredients.length > 0 && (
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {m.ingredients.join(", ")}
                  </div>
                )}
              </div>
              <TouchButton variant="ghost" size="sm" onClick={() => remove.mutate(m.id)}>
                Remove
              </TouchButton>
            </div>
          ))}
        </div>
      </div>
    </Sheet>
  );
}
