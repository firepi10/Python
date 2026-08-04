import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarHeart, CheckCircle2, Plus, RefreshCw, Trash2, TriangleAlert, UserRound } from "lucide-react";
import {
  accountsApi,
  api,
  profileColorVar,
  profilesApi,
  type AccountDTO,
  type DiscoveredCalendar,
} from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { GlassCard } from "../../components/GlassCard";
import { SegmentedControl } from "../../components/SegmentedControl";
import { Sheet } from "../../components/Sheet";
import { TouchButton } from "../../components/TouchButton";
import { useToast } from "../../components/Toast";

const PROFILE_COLORS = ["blue", "purple", "pink", "orange", "green", "teal", "yellow", "red"];

const field: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid var(--surface-border)",
  background: "var(--bg)",
  color: "var(--text)",
  borderRadius: "var(--radius-sm)",
  padding: "12px 14px",
  fontSize: 16,
  fontFamily: "inherit",
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-secondary)", margin: "0 0 10px" }}>
      {children}
    </h2>
  );
}

// ---------------------------------------------------------------- profiles

function ProfilesSection() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: profiles } = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [color, setColor] = useState("blue");

  const create = useMutation({
    mutationFn: () => profilesApi.create({ name, color, sort_order: profiles?.length ?? 0 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      setName("");
      setAdding(false);
      toast("Family member added");
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => profilesApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });

  return (
    <GlassCard>
      <SectionTitle>Family</SectionTitle>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        {profiles?.map((p) => (
          <div
            key={p.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "var(--bg)",
              borderRadius: 999,
              padding: "5px 8px 5px 6px",
            }}
          >
            <Avatar name={p.name} color={profileColorVar(p.color)} size={30} />
            <span style={{ fontWeight: 600 }}>{p.name}</span>
            <button
              onClick={() => remove.mutate(p.id)}
              aria-label={`Remove ${p.name}`}
              style={{ border: "none", background: "none", color: "var(--text-tertiary)", padding: 4 }}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        <TouchButton variant="ghost" size="sm" onClick={() => setAdding(!adding)}>
          <Plus size={16} style={{ display: "inline", verticalAlign: -3 }} /> Add person
        </TouchButton>
      </div>
      {adding && (
        <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center", flexWrap: "wrap" }}>
          <input
            style={{ ...field, width: 180 }}
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <div style={{ display: "flex", gap: 6 }}>
            {PROFILE_COLORS.map((c) => (
              <button
                key={c}
                aria-label={c}
                onClick={() => setColor(c)}
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: profileColorVar(c),
                  border: color === c ? "3px solid var(--text)" : "3px solid transparent",
                }}
              />
            ))}
          </div>
          <TouchButton variant="primary" size="sm" disabled={!name.trim()} onClick={() => create.mutate()}>
            Add
          </TouchButton>
        </div>
      )}
    </GlassCard>
  );
}

// ---------------------------------------------------------------- accounts

function AccountCard({ account }: { account: AccountDTO }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: profiles } = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["accounts"] });
  const patchCal = useMutation({
    mutationFn: (vars: { calId: number; body: Parameters<typeof accountsApi.patchCalendar>[2] }) =>
      accountsApi.patchCalendar(account.id, vars.calId, vars.body),
    onSuccess: invalidate,
  });
  const removeAccount = useMutation({
    mutationFn: () => accountsApi.remove(account.id),
    onSuccess: () => {
      invalidate();
      toast("Account removed");
    },
  });

  return (
    <div style={{ borderTop: "1px solid var(--surface-border)", paddingTop: 14, marginTop: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {account.status === "ok" ? (
          <CheckCircle2 size={20} color="var(--profile-green)" />
        ) : (
          <TriangleAlert size={20} color="var(--danger)" />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700 }}>{account.label}</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {account.apple_id}
            {account.last_sync_at &&
              ` · synced ${new Date(account.last_sync_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`}
          </div>
        </div>
        <TouchButton variant="ghost" size="sm" onClick={() => removeAccount.mutate()}>
          Remove
        </TouchButton>
      </div>
      {account.last_error && (
        <div style={{ color: "var(--danger)", fontSize: 13, marginTop: 8 }}>{account.last_error}</div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
        {account.calendars.map((cal) => (
          <div key={cal.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              type="checkbox"
              checked={cal.enabled}
              onChange={(e) => patchCal.mutate({ calId: cal.id, body: { enabled: e.target.checked } })}
              style={{ width: 18, height: 18 }}
            />
            <span style={{ flex: 1, fontWeight: 600, fontSize: 15 }}>{cal.name}</span>
            <select
              value={cal.profile_id ?? ""}
              onChange={(e) =>
                patchCal.mutate({
                  calId: cal.id,
                  body:
                    e.target.value === ""
                      ? { clear_profile: true }
                      : { profile_id: Number(e.target.value) },
                })
              }
              style={{ ...field, width: 150, padding: "6px 10px", fontSize: 14 }}
            >
              <option value="">No person</option>
              {profiles?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

function AddAccountSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: profiles } = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });

  const [appleId, setAppleId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [discovered, setDiscovered] = useState<DiscoveredCalendar[] | null>(null);
  const [picks, setPicks] = useState<Record<string, { enabled: boolean; profile_id: number | null }>>({});

  const reset = () => {
    setAppleId("");
    setPassword("");
    setDiscovered(null);
    setPicks({});
    setError(null);
  };

  const test = useMutation({
    mutationFn: () => accountsApi.test(appleId, password),
    onSuccess: (result) => {
      setError(null);
      setDiscovered(result.calendars);
      setPicks(
        Object.fromEntries(result.calendars.map((c) => [c.url, { enabled: true, profile_id: null }])),
      );
    },
    onError: (e: Error) => setError(e.message.replace(/^\d+ [^:]+: /, "")),
  });

  const save = useMutation({
    mutationFn: () =>
      accountsApi.create({
        label: "iCloud",
        apple_id: appleId,
        password,
        calendars: (discovered ?? []).map((c) => ({
          url: c.url,
          name: c.name,
          enabled: picks[c.url]?.enabled ?? true,
          profile_id: picks[c.url]?.profile_id ?? null,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      accountsApi.syncNow().then(() => queryClient.invalidateQueries({ queryKey: ["occurrences"] }));
      toast("iCloud account connected — first sync started");
      reset();
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <Sheet open={open} onClose={onClose} title="Connect iCloud calendars">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {!discovered && (
          <>
            <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Sign in with your Apple ID and an <b>app-specific password</b> (create one at
              account.apple.com → Sign-In and Security → App-Specific Passwords). Your regular
              Apple ID password will not work. The password is stored encrypted on this device
              only.
            </div>
            <input
              style={field}
              placeholder="Apple ID (email)"
              autoCapitalize="none"
              value={appleId}
              onChange={(e) => setAppleId(e.target.value)}
            />
            <input
              style={field}
              placeholder="app-specific password (xxxx-xxxx-xxxx-xxxx)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div style={{ color: "var(--danger)", fontSize: 14 }}>{error}</div>}
            <TouchButton
              variant="primary"
              disabled={!appleId || !password || test.isPending}
              onClick={() => test.mutate()}
            >
              {test.isPending ? "Checking…" : "Find my calendars"}
            </TouchButton>
          </>
        )}
        {discovered && (
          <>
            <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
              Choose which calendars appear on the wall, and whose color each one gets.
            </div>
            {discovered.map((cal) => (
              <div key={cal.url} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  checked={picks[cal.url]?.enabled ?? true}
                  onChange={(e) =>
                    setPicks((p) => ({ ...p, [cal.url]: { ...p[cal.url], enabled: e.target.checked } }))
                  }
                  style={{ width: 18, height: 18 }}
                />
                <span style={{ flex: 1, fontWeight: 600 }}>{cal.name}</span>
                <select
                  value={picks[cal.url]?.profile_id ?? ""}
                  onChange={(e) =>
                    setPicks((p) => ({
                      ...p,
                      [cal.url]: {
                        ...p[cal.url],
                        profile_id: e.target.value === "" ? null : Number(e.target.value),
                      },
                    }))
                  }
                  style={{ ...field, width: 150, padding: "6px 10px", fontSize: 14 }}
                >
                  <option value="">No person</option>
                  {profiles?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            ))}
            {error && <div style={{ color: "var(--danger)", fontSize: 14 }}>{error}</div>}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <TouchButton variant="secondary" onClick={() => setDiscovered(null)}>
                Back
              </TouchButton>
              <TouchButton variant="primary" disabled={save.isPending} onClick={() => save.mutate()}>
                Connect
              </TouchButton>
            </div>
          </>
        )}
      </div>
    </Sheet>
  );
}

function AccountsSection() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: accountsApi.list });
  const [addOpen, setAddOpen] = useState(false);

  const syncNow = useMutation({
    mutationFn: accountsApi.syncNow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["occurrences"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast("Sync complete");
    },
  });

  return (
    <GlassCard>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <SectionTitle>iCloud calendars</SectionTitle>
        <div style={{ display: "flex", gap: 8 }}>
          {accounts && accounts.length > 0 && (
            <TouchButton variant="ghost" size="sm" onClick={() => syncNow.mutate()} disabled={syncNow.isPending}>
              <RefreshCw size={15} style={{ display: "inline", verticalAlign: -2 }} />{" "}
              {syncNow.isPending ? "Syncing…" : "Sync now"}
            </TouchButton>
          )}
          <TouchButton variant="primary" size="sm" onClick={() => setAddOpen(true)}>
            <Plus size={16} style={{ display: "inline", verticalAlign: -3 }} /> Add account
          </TouchButton>
        </div>
      </div>
      {(!accounts || accounts.length === 0) && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, color: "var(--text-secondary)", padding: "10px 0" }}>
          <CalendarHeart size={22} />
          Connect each family member's iCloud account — events sync both ways, about every 5
          minutes.
        </div>
      )}
      {accounts?.map((a) => <AccountCard key={a.id} account={a} />)}
      <AddAccountSheet open={addOpen} onClose={() => setAddOpen(false)} />
    </GlassCard>
  );
}

// ------------------------------------------------------------ display/sleep

interface SleepSchedule {
  enabled: boolean;
  off: string;
  on: string;
}

interface ScreensaverCfg {
  enabled: boolean;
  interval_s: number;
  ken_burns: boolean;
}

interface WeatherCfg {
  lat: number;
  lon: number;
  unit: string;
  label: string;
}

function Row({ label: rowLabel, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, minHeight: 44 }}>
      <span style={{ flex: 1, fontWeight: 600, fontSize: 15 }}>{rowLabel}</span>
      {children}
    </div>
  );
}

function DisplaySection() {
  const queryClient = useQueryClient();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: api.settings });

  const put = useMutation({
    mutationFn: (vars: { key: string; value: unknown }) => api.putSetting(vars.key, vars.value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  if (!settings) return null;
  const sleep = settings.sleep_schedule as SleepSchedule;
  const saver = settings.screensaver as ScreensaverCfg;
  const weather = settings.weather as WeatherCfg;
  const theme = settings.theme as string;
  const idle = settings.idle_timeout_s as number;

  const smallField: React.CSSProperties = { ...field, width: 120, padding: "8px 10px", fontSize: 14 };

  return (
    <GlassCard>
      <SectionTitle>Display & sleep</SectionTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <Row label="Appearance">
          <div style={{ width: 260 }}>
            <SegmentedControl
              options={[
                { value: "auto", label: "Auto" },
                { value: "light", label: "Light" },
                { value: "dark", label: "Dark" },
              ]}
              value={theme as "auto" | "light" | "dark"}
              onChange={(v) => put.mutate({ key: "theme", value: v })}
            />
          </div>
        </Row>
        <Row label="Screen off at night">
          <TouchButton
            size="sm"
            variant={sleep.enabled ? "primary" : "secondary"}
            onClick={() => put.mutate({ key: "sleep_schedule", value: { ...sleep, enabled: !sleep.enabled } })}
          >
            {sleep.enabled ? "On" : "Off"}
          </TouchButton>
          <input
            type="time"
            style={smallField}
            value={sleep.off}
            onChange={(e) => put.mutate({ key: "sleep_schedule", value: { ...sleep, off: e.target.value } })}
          />
          <span style={{ color: "var(--text-tertiary)" }}>to</span>
          <input
            type="time"
            style={smallField}
            value={sleep.on}
            onChange={(e) => put.mutate({ key: "sleep_schedule", value: { ...sleep, on: e.target.value } })}
          />
        </Row>
        <Row label="Photos take over after">
          <select
            style={smallField}
            value={idle}
            onChange={(e) => put.mutate({ key: "idle_timeout_s", value: Number(e.target.value) })}
          >
            <option value={60}>1 minute</option>
            <option value={120}>2 minutes</option>
            <option value={300}>5 minutes</option>
            <option value={600}>10 minutes</option>
            <option value={900}>15 minutes</option>
          </select>
        </Row>
        <Row label="Each photo shows for">
          <select
            style={smallField}
            value={saver.interval_s}
            onChange={(e) =>
              put.mutate({ key: "screensaver", value: { ...saver, interval_s: Number(e.target.value) } })
            }
          >
            <option value={8}>8 seconds</option>
            <option value={12}>12 seconds</option>
            <option value={20}>20 seconds</option>
            <option value={30}>30 seconds</option>
          </select>
        </Row>
        <Row label="Reduced glass (faster on Pi)">
          <TouchButton
            size="sm"
            variant={settings.reduced_glass ? "primary" : "secondary"}
            onClick={() => put.mutate({ key: "reduced_glass", value: !settings.reduced_glass })}
          >
            {settings.reduced_glass ? "On" : "Off"}
          </TouchButton>
        </Row>
        <Row label="Weather location">
          <input
            style={{ ...smallField, width: 90 }}
            defaultValue={weather.lat}
            onBlur={(e) =>
              put.mutate({ key: "weather", value: { ...weather, lat: Number(e.target.value) || 0 } })
            }
          />
          <input
            style={{ ...smallField, width: 90 }}
            defaultValue={weather.lon}
            onBlur={(e) =>
              put.mutate({ key: "weather", value: { ...weather, lon: Number(e.target.value) || 0 } })
            }
          />
          <div style={{ width: 130 }}>
            <SegmentedControl
              options={[
                { value: "fahrenheit", label: "°F" },
                { value: "celsius", label: "°C" },
              ]}
              value={weather.unit as "fahrenheit" | "celsius"}
              onChange={(v) => put.mutate({ key: "weather", value: { ...weather, unit: v } })}
            />
          </div>
        </Row>
      </div>
    </GlassCard>
  );
}

// -------------------------------------------------------------------- view

export function SettingsView() {
  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        maxWidth: 860,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <ProfilesSection />
      <AccountsSection />
      <DisplaySection />
      <GlassCard>
        <SectionTitle>
          <UserRound size={14} style={{ display: "inline", verticalAlign: -2 }} /> Phone app
        </SectionTitle>
        <div style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.6 }}>
          On your iPhone, open this address in Safari and tap <b>Share → Add to Home Screen</b>.
          At home use <b>http://bayta.local</b>; from anywhere, install the Tailscale app and use
          your tailnet address — one icon works in both places if you add it from the tailnet URL.
        </div>
      </GlassCard>
    </div>
  );
}
