import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Star, Trash2 } from "lucide-react";
import { profileColorVar, type ProfileDTO } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { useToast } from "../../components/Toast";

export interface RewardDTO {
  id: number;
  title: string;
  icon: string | null;
  cost_points: number;
}

export interface BalanceDTO {
  profile_id: number;
  earned: number;
  spent: number;
  balance: number;
}

export async function fetchRewards(): Promise<{ rewards: RewardDTO[]; balances: BalanceDTO[] }> {
  const r = await fetch("/api/rewards");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

const field: React.CSSProperties = {
  border: "1px solid var(--surface-border)",
  background: "var(--bg)",
  color: "var(--text)",
  borderRadius: "var(--radius-sm)",
  padding: "10px 12px",
  fontSize: 15,
  fontFamily: "inherit",
};

export function RewardsSheet({
  open,
  onClose,
  profiles,
}: {
  open: boolean;
  onClose: () => void;
  profiles: ProfileDTO[];
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [shopperId, setShopperId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [icon, setIcon] = useState("");
  const [cost, setCost] = useState(10);

  const { data } = useQuery({ queryKey: ["rewards"], queryFn: fetchRewards, enabled: open });
  const balances = new Map((data?.balances ?? []).map((b) => [b.profile_id, b.balance]));
  const kids = profiles.filter((p) => balances.has(p.id));
  const shopper = shopperId ?? kids[0]?.id ?? null;
  const shopperBalance = shopper != null ? (balances.get(shopper) ?? 0) : 0;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["rewards"] });
    queryClient.invalidateQueries({ queryKey: ["chores"] });
  };

  const claim = useMutation({
    mutationFn: async (reward: RewardDTO) => {
      const r = await fetch(`/api/rewards/${reward.id}/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: shopper }),
      });
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail ?? "Couldn't claim");
      return { ...body, title: reward.title };
    },
    onSuccess: (result) => {
      invalidate();
      const name = profiles.find((p) => p.id === shopper)?.name ?? "Someone";
      toast(`🎉 ${name} claimed ${result.title}!`);
    },
    onError: (e: Error) => toast(e.message),
  });

  const createReward = useMutation({
    mutationFn: () =>
      fetch("/api/rewards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), icon: icon.trim() || null, cost_points: cost }),
      }),
    onSuccess: () => {
      invalidate();
      setTitle("");
      setIcon("");
      setAdding(false);
    },
  });
  const removeReward = useMutation({
    mutationFn: (id: number) => fetch(`/api/rewards/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });

  return (
    <Sheet open={open} onClose={onClose} title="Star rewards">
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* who's shopping */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
          {kids.map((p) => {
            const selected = shopper === p.id;
            return (
              <button
                key={p.id}
                className="touch-btn"
                onClick={() => setShopperId(p.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  border: selected
                    ? `2px solid ${profileColorVar(p.color)}`
                    : "2px solid transparent",
                  background: selected
                    ? `color-mix(in srgb, ${profileColorVar(p.color)} 12%, transparent)`
                    : "var(--bg)",
                  borderRadius: 999,
                  padding: "6px 14px 6px 6px",
                  fontFamily: "inherit",
                  fontSize: 15,
                  fontWeight: 700,
                  color: "var(--text)",
                  transition: `transform var(--dur-fast) var(--ease-spring)`,
                }}
              >
                <Avatar name={p.name} color={profileColorVar(p.color)} size={30} />
                {p.name}
                <span style={{ display: "inline-flex", alignItems: "center", gap: 3, color: "var(--text-secondary)" }}>
                  <Star size={14} fill="var(--profile-yellow)" color="var(--profile-yellow)" />
                  {balances.get(p.id) ?? 0}
                </span>
              </button>
            );
          })}
        </div>

        {/* reward cards with progress toward each */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 320, overflowY: "auto" }}>
          {data?.rewards.map((reward) => {
            const progress = Math.min(1, shopperBalance / reward.cost_points);
            const affordable = shopperBalance >= reward.cost_points;
            return (
              <div
                key={reward.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-solid)",
                  borderRadius: "var(--radius-md)",
                  padding: "12px 14px",
                }}
              >
                <span style={{ fontSize: 26, width: 34, textAlign: "center" }}>
                  {reward.icon ?? "🎁"}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 15.5 }}>{reward.title}</span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 13, fontWeight: 700, color: "var(--text-secondary)" }}>
                      <Star size={12} fill="var(--profile-yellow)" color="var(--profile-yellow)" />
                      {reward.cost_points}
                    </span>
                  </div>
                  <div
                    aria-hidden
                    style={{
                      marginTop: 7,
                      height: 6,
                      borderRadius: 3,
                      background: "var(--accent-soft)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: "100%",
                        height: "100%",
                        borderRadius: 3,
                        background: affordable ? "var(--profile-green)" : "var(--accent)",
                        transform: `scaleX(${progress})`,
                        transformOrigin: "left",
                        transition: `transform var(--dur-med) var(--ease-spring)`,
                      }}
                    />
                  </div>
                  {!affordable && shopper != null && (
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                      {reward.cost_points - shopperBalance} more stars to go
                    </div>
                  )}
                </div>
                <TouchButton
                  variant={affordable ? "primary" : "secondary"}
                  size="sm"
                  disabled={!affordable || shopper == null || claim.isPending}
                  onClick={() => claim.mutate(reward)}
                >
                  Claim
                </TouchButton>
                <button
                  onClick={() => removeReward.mutate(reward.id)}
                  aria-label={`Remove ${reward.title}`}
                  style={{ border: "none", background: "none", color: "var(--text-tertiary)", padding: 4 }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            );
          })}
          {(!data || data.rewards.length === 0) && (
            <div style={{ color: "var(--text-secondary)", textAlign: "center", fontSize: 14, padding: "16px 0" }}>
              No rewards yet — add the first one below (e.g. 🎬 Movie night pick, 10 stars).
            </div>
          )}
        </div>

        {/* parent controls */}
        {adding ? (
          <div style={{ display: "grid", gridTemplateColumns: "52px 1fr 84px auto", gap: 8 }}>
            <input style={field} placeholder="🎬" value={icon} onChange={(e) => setIcon(e.target.value)} />
            <input
              style={field}
              placeholder="Reward (e.g. Ice cream trip)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <input
              style={field}
              type="number"
              min={1}
              value={cost}
              onChange={(e) => setCost(Math.max(1, Number(e.target.value) || 1))}
            />
            <TouchButton variant="primary" size="sm" disabled={!title.trim()} onClick={() => createReward.mutate()}>
              Add
            </TouchButton>
          </div>
        ) : (
          <TouchButton variant="ghost" onClick={() => setAdding(true)}>
            <Plus size={16} style={{ display: "inline", verticalAlign: -3 }} /> Add a reward
          </TouchButton>
        )}
      </div>
    </Sheet>
  );
}
