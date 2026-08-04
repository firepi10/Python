import { useMemo, useState } from "react";
import { format, startOfWeek } from "date-fns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ClipboardCheck, Gift, Plus, Star, Users } from "lucide-react";
import { api, profileColorVar, type ProfileDTO } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { EmptyState } from "../../components/EmptyState";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { fetchRewards, RewardsSheet } from "./RewardsSheet";

interface ChoreDTO {
  id: number;
  title: string;
  icon: string | null;
  profile_id: number | null;
  points: number;
  completed: boolean;
  /** true when the chore is shared: it shows in every assignee's column and
   *  each person checks off their own copy */
  shared: boolean;
}

const WEEKDAYS = [
  ["MO", "M"],
  ["TU", "T"],
  ["WE", "W"],
  ["TH", "T"],
  ["FR", "F"],
  ["SA", "S"],
  ["SU", "S"],
] as const;

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function ChoresView() {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [rewardsOpen, setRewardsOpen] = useState(false);
  const today = format(new Date(), "yyyy-MM-dd");
  const weekStart = format(startOfWeek(new Date()), "yyyy-MM-dd");

  const { data: profiles } = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });
  const { data: chores } = useQuery({
    queryKey: ["chores", today],
    queryFn: () => getJSON<ChoreDTO[]>(`/api/chores?day=${today}`),
  });
  const { data: stars } = useQuery({
    queryKey: ["chores", "stars", weekStart],
    queryFn: () => getJSON<{ profile_id: number; points: number }[]>(`/api/chores/stars?since=${weekStart}`),
  });
  const { data: rewardsData } = useQuery({ queryKey: ["rewards"], queryFn: fetchRewards });
  const balances = new Map((rewardsData?.balances ?? []).map((b) => [b.profile_id, b.balance]));

  const toggle = useMutation({
    mutationFn: (vars: { choreId: number; profileId: number | null }) =>
      fetch(`/api/chores/${vars.choreId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: today, profile_id: vars.profileId }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chores"] }),
  });

  const byProfile = useMemo(() => {
    const groups = new Map<number | null, ChoreDTO[]>();
    for (const chore of chores ?? []) {
      const key = chore.profile_id;
      groups.set(key, [...(groups.get(key) ?? []), chore]);
    }
    return groups;
  }, [chores]);

  const starsFor = (pid: number) => stars?.find((s) => s.profile_id === pid)?.points ?? 0;

  const columns: (ProfileDTO | null)[] = [
    ...(profiles ?? []).filter((p) => byProfile.has(p.id)),
    ...(byProfile.has(null) ? [null] : []),
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, flex: 1 }}>
          Chores{" "}
          <span style={{ color: "var(--text-tertiary)", fontWeight: 500, fontSize: 18 }}>
            {format(new Date(), "EEEE")}
          </span>
        </h1>
        <TouchButton variant="secondary" size="sm" onClick={() => setRewardsOpen(true)}>
          <Gift size={15} style={{ display: "inline", verticalAlign: -2 }} /> Rewards
        </TouchButton>
        <TouchButton variant="primary" size="sm" onClick={() => setAddOpen(true)}>
          <Plus size={16} style={{ display: "inline", verticalAlign: -3 }} /> Add chore
        </TouchButton>
      </div>

      {columns.length === 0 && (
        <EmptyState
          icon={ClipboardCheck}
          title="No chores today"
          hint="Add recurring chores and let the kids collect stars for finishing them."
        />
      )}

      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: `repeat(${Math.max(columns.length, 1)}, 1fr)`,
          gap: 14,
          overflowY: "auto",
          alignContent: "start",
        }}
      >
        {columns.map((profile) => {
          const list = byProfile.get(profile?.id ?? null) ?? [];
          const color = profile ? profileColorVar(profile.color) : "var(--accent)";
          return (
            <div key={profile?.id ?? "everyone"} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {profile ? (
                  <Avatar name={profile.name} color={color} size={38} />
                ) : (
                  <Avatar name="All" color="var(--accent)" size={38} />
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: 17 }}>{profile?.name ?? "Everyone"}</div>
                  {profile && (
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
                      <Star size={13} fill="var(--profile-yellow)" color="var(--profile-yellow)" />
                      <b>{balances.get(profile.id) ?? 0}</b>
                      <span style={{ color: "var(--text-tertiary)" }}>
                        · {starsFor(profile.id)} this week
                      </span>
                    </div>
                  )}
                </div>
              </div>
              {list.map((chore) => (
                <button
                  key={`${chore.id}-${chore.profile_id ?? "all"}`}
                  className="touch-btn"
                  onClick={() => toggle.mutate({ choreId: chore.id, profileId: chore.profile_id })}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    border: "1px solid var(--surface-border)",
                    background: chore.completed
                      ? `color-mix(in srgb, ${color} 14%, var(--surface-solid))`
                      : "var(--surface-solid)",
                    boxShadow: "var(--shadow-card)",
                    borderRadius: "var(--radius-md)",
                    padding: "14px 16px",
                    fontFamily: "inherit",
                    color: "var(--text)",
                    textAlign: "left",
                    transition: `transform var(--dur-fast) var(--ease-spring)`,
                  }}
                >
                  <span
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: "50%",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: chore.completed ? "none" : `2px solid ${color}`,
                      background: chore.completed ? color : "transparent",
                      color: "#fff",
                      transition: `transform var(--dur-fast) var(--ease-spring)`,
                    }}
                  >
                    {chore.completed && <Check size={18} strokeWidth={3} />}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      fontSize: 16,
                      fontWeight: 600,
                      textDecoration: chore.completed ? "line-through" : "none",
                      opacity: chore.completed ? 0.55 : 1,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {chore.icon && `${chore.icon} `}
                    {chore.title}
                    {chore.shared && (
                      <Users size={14} color="var(--text-tertiary)" aria-label="Shared chore" />
                    )}
                  </span>
                  {chore.points > 0 && (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 3,
                        fontSize: 13,
                        fontWeight: 700,
                        color: "var(--text-secondary)",
                      }}
                    >
                      <Star size={13} fill="var(--profile-yellow)" color="var(--profile-yellow)" />
                      {chore.points}
                    </span>
                  )}
                </button>
              ))}
            </div>
          );
        })}
      </div>

      <AddChoreSheet open={addOpen} onClose={() => setAddOpen(false)} profiles={profiles ?? []} />
      <RewardsSheet open={rewardsOpen} onClose={() => setRewardsOpen(false)} profiles={profiles ?? []} />
    </div>
  );
}

function AddChoreSheet({
  open,
  onClose,
  profiles,
}: {
  open: boolean;
  onClose: () => void;
  profiles: ProfileDTO[];
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [profileIds, setProfileIds] = useState<number[]>([]);
  const [mode, setMode] = useState<"daily" | "days">("daily");
  const [days, setDays] = useState<string[]>(["MO"]);
  const [points, setPoints] = useState(1);

  const create = useMutation({
    mutationFn: () =>
      fetch("/api/chores", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          profile_ids: profileIds,
          points,
          rrule: mode === "daily" ? "FREQ=DAILY" : `FREQ=WEEKLY;BYDAY=${days.join(",")}`,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chores"] });
      setTitle("");
      setProfileIds([]);
      onClose();
    },
  });

  return (
    <Sheet open={open} onClose={onClose} title="New chore">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <input
          style={{
            border: "1px solid var(--surface-border)",
            background: "var(--bg)",
            color: "var(--text)",
            borderRadius: "var(--radius-sm)",
            padding: "12px 14px",
            fontSize: 17,
            fontFamily: "inherit",
          }}
          placeholder="Chore (e.g. Make your bed)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {profiles.map((p) => (
              <TouchButton
                key={p.id}
                variant={profileIds.includes(p.id) ? "primary" : "secondary"}
                size="sm"
                onClick={() =>
                  setProfileIds((ids) =>
                    ids.includes(p.id) ? ids.filter((x) => x !== p.id) : [...ids, p.id],
                  )
                }
              >
                {p.name}
              </TouchButton>
            ))}
          </div>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {profileIds.length > 1
              ? "Shared chore — it shows up for each of them, and each checks off their own."
              : profileIds.length === 0
                ? "No one picked — it becomes a family chore with a single checkbox."
                : "Pick more than one person to make it a shared chore."}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <TouchButton
            variant={mode === "daily" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setMode("daily")}
          >
            Every day
          </TouchButton>
          <TouchButton
            variant={mode === "days" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setMode("days")}
          >
            Certain days
          </TouchButton>
          {mode === "days" &&
            WEEKDAYS.map(([code, letter]) => (
              <button
                key={code}
                onClick={() =>
                  setDays((d) => (d.includes(code) ? d.filter((x) => x !== code) : [...d, code]))
                }
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: "50%",
                  border: "none",
                  fontFamily: "inherit",
                  fontWeight: 700,
                  background: days.includes(code) ? "var(--accent)" : "var(--accent-soft)",
                  color: days.includes(code) ? "#fff" : "var(--text)",
                }}
              >
                {letter}
              </button>
            ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontWeight: 600 }}>Stars</span>
          <TouchButton variant="secondary" size="sm" onClick={() => setPoints(Math.max(0, points - 1))}>
            −
          </TouchButton>
          <span className="tnum" style={{ fontWeight: 800, fontSize: 18, width: 24, textAlign: "center" }}>
            {points}
          </span>
          <TouchButton variant="secondary" size="sm" onClick={() => setPoints(Math.min(10, points + 1))}>
            +
          </TouchButton>
          <div style={{ flex: 1 }} />
          <TouchButton
            variant="primary"
            disabled={!title.trim() || (mode === "days" && days.length === 0)}
            onClick={() => create.mutate()}
          >
            Add chore
          </TouchButton>
        </div>
      </div>
    </Sheet>
  );
}
