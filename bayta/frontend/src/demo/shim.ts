/* Demo-build fetch interceptor: serves the whole /api/* surface from the
   in-memory fixture store so the published demo is fully interactive.
   State lives for the page's lifetime and resets on reload. */

import { format, startOfDay } from "date-fns";
import { createStore, type OccRecord, type Store } from "./fixtures";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function weekdayCode(dateISO: string): string {
  return ["SU", "MO", "TU", "WE", "TH", "FR", "SA"][new Date(`${dateISO}T12:00:00`).getDay()];
}

function choreDueOn(rrule: string, dateISO: string): boolean {
  if (rrule.includes("FREQ=DAILY")) return true;
  const byday = /BYDAY=([A-Z,]+)/.exec(rrule)?.[1];
  if (rrule.includes("FREQ=WEEKLY")) {
    return byday ? byday.split(",").includes(weekdayCode(dateISO)) : true;
  }
  return false;
}

function balances(store: Store) {
  return store.profiles.map((p) => {
    const earned = store.completions
      .filter((c) => c.profile_id === p.id)
      .reduce((sum, c) => sum + c.points, 0);
    const spent = store.claims
      .filter((c) => c.profile_id === p.id)
      .reduce((sum, c) => sum + c.points_spent, 0);
    return { profile_id: p.id, earned, spent, balance: earned - spent };
  });
}

async function bodyOf(init?: RequestInit): Promise<Record<string, unknown>> {
  if (!init?.body) return {};
  try {
    return JSON.parse(String(init.body));
  } catch {
    return {};
  }
}

// eslint-disable-next-line complexity
async function handle(store: Store, url: URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const path = url.pathname.replace(/^.*\/api\//, "/api/");
  const body = await bodyOf(init);
  const match = (re: RegExp) => re.exec(path);
  let m: RegExpExecArray | null;

  if (path === "/api/health") return json({ status: "ok", version: "demo", time: new Date().toISOString() });
  if (path === "/api/profiles") return json(store.profiles);
  if (path === "/api/settings" && method === "GET") return json(store.settings);
  if ((m = match(/^\/api\/settings\/(.+)$/)) && method === "PUT") {
    store.settings[m[1]] = body.value;
    return json({ [m[1]]: body.value });
  }

  // ---------------------------------------------------------------- calendar
  if (path === "/api/calendar/occurrences") {
    const start = new Date(url.searchParams.get("start")!).getTime();
    const end = new Date(url.searchParams.get("end")!).getTime();
    const rows = store.occurrences
      .filter((o) => new Date(o.start).getTime() < end && new Date(o.end).getTime() > start)
      .map((o) => ({ ...o, calendar_id: null, calendar_name: "Bayta", read_only: false }))
      .sort((a, b) => a.start.localeCompare(b.start));
    return json(rows);
  }
  if (path === "/api/calendar/calendars") return json([]);
  if (path === "/api/calendar/events" && method === "POST") {
    const id = store.nextEventId++;
    const profile = store.profiles.find((p) => p.id === body.profile_id);
    const record: OccRecord = {
      event_id: id,
      summary: String(body.summary ?? "New event"),
      location: (body.location as string) ?? null,
      start: String(body.start),
      end: String(body.end),
      all_day: Boolean(body.all_day),
      is_recurring: Boolean(body.rrule),
      profile_id: profile?.id ?? null,
      color: profile?.color ?? "blue",
      profile_name: profile?.name ?? null,
    };
    store.occurrences.push(record);
    if (body.rrule) {
      for (let w = 1; w <= 8; w++) {
        const shift = w * 7 * 86400_000;
        store.occurrences.push({
          ...record,
          start: new Date(new Date(record.start).getTime() + shift).toISOString(),
          end: new Date(new Date(record.end).getTime() + shift).toISOString(),
        });
      }
    }
    return json({ id, uid: `demo-${id}` }, 201);
  }
  if ((m = match(/^\/api\/calendar\/events\/(\d+)$/))) {
    const id = Number(m[1]);
    if (method === "DELETE") {
      store.occurrences = store.occurrences.filter((o) => o.event_id !== id);
      return new Response(null, { status: 204 });
    }
    if (method === "PATCH") {
      const profile = store.profiles.find((p) => p.id === body.profile_id);
      store.occurrences = store.occurrences.map((o) =>
        o.event_id === id
          ? {
              ...o,
              summary: String(body.summary ?? o.summary),
              location: (body.location as string) ?? null,
              start: String(body.start),
              end: String(body.end),
              all_day: Boolean(body.all_day),
              profile_id: profile?.id ?? null,
              color: profile?.color ?? "blue",
              profile_name: profile?.name ?? null,
            }
          : o,
      );
      return json({ id });
    }
  }

  // ------------------------------------------------------------------ chores
  if (path === "/api/chores" && method === "GET") {
    const day = url.searchParams.get("day") ?? format(startOfDay(new Date()), "yyyy-MM-dd");
    const out: unknown[] = [];
    for (const chore of store.chores) {
      if (!chore.active || !choreDueOn(chore.rrule, day)) continue;
      const base = {
        id: chore.id,
        title: chore.title,
        icon: chore.icon,
        points: chore.points,
        shared: chore.profile_ids.length > 1,
      };
      if (chore.profile_ids.length === 0) {
        out.push({
          ...base,
          profile_id: null,
          completed: store.completions.some(
            (c) => c.chore_id === chore.id && c.date === day && c.profile_id === null,
          ),
        });
      } else {
        for (const pid of chore.profile_ids) {
          out.push({
            ...base,
            profile_id: pid,
            completed: store.completions.some(
              (c) => c.chore_id === chore.id && c.date === day && c.profile_id === pid,
            ),
          });
        }
      }
    }
    return json(out);
  }
  if (path === "/api/chores" && method === "POST") {
    const chore = {
      id: store.nextChoreId++,
      title: String(body.title ?? "Chore"),
      icon: (body.icon as string) ?? null,
      points: Number(body.points ?? 1),
      rrule: String(body.rrule ?? "FREQ=DAILY"),
      profile_ids: (body.profile_ids as number[]) ?? [],
      active: true,
    };
    store.chores.push(chore);
    return json(chore, 201);
  }
  if ((m = match(/^\/api\/chores\/(\d+)\/complete$/)) && method === "POST") {
    const choreId = Number(m[1]);
    const date = String(body.date);
    const profileId = (body.profile_id as number | null) ?? null;
    const idx = store.completions.findIndex(
      (c) => c.chore_id === choreId && c.date === date && c.profile_id === profileId,
    );
    if (idx >= 0) {
      store.completions.splice(idx, 1);
      return json({ id: choreId, profile_id: profileId, completed: false });
    }
    const chore = store.chores.find((c) => c.id === choreId);
    store.completions.push({ chore_id: choreId, date, profile_id: profileId, points: chore?.points ?? 1 });
    return json({ id: choreId, profile_id: profileId, completed: true });
  }
  if (path === "/api/chores/stars") {
    const since = url.searchParams.get("since") ?? "1970-01-01";
    const totals = new Map<number, number>();
    for (const c of store.completions) {
      if (c.date >= since && c.profile_id != null) {
        totals.set(c.profile_id, (totals.get(c.profile_id) ?? 0) + c.points);
      }
    }
    return json([...totals].map(([profile_id, points]) => ({ profile_id, points })));
  }
  if ((m = match(/^\/api\/chores\/(\d+)$/)) && method === "DELETE") {
    store.chores = store.chores.filter((c) => c.id !== Number(m![1]));
    return new Response(null, { status: 204 });
  }

  // ----------------------------------------------------------------- rewards
  if (path === "/api/rewards" && method === "GET") {
    return json({ rewards: store.rewards.filter((r) => r.active), balances: balances(store) });
  }
  if (path === "/api/rewards" && method === "POST") {
    const reward = {
      id: store.nextRewardId++,
      title: String(body.title ?? "Reward"),
      icon: (body.icon as string) ?? null,
      cost_points: Number(body.cost_points ?? 10),
      active: true,
    };
    store.rewards.push(reward);
    return json(reward, 201);
  }
  if ((m = match(/^\/api\/rewards\/(\d+)\/claim$/)) && method === "POST") {
    const reward = store.rewards.find((r) => r.id === Number(m![1]));
    const profileId = Number(body.profile_id);
    if (!reward) return json({ detail: "reward not found" }, 404);
    const balance = balances(store).find((b) => b.profile_id === profileId)?.balance ?? 0;
    const name = store.profiles.find((p) => p.id === profileId)?.name ?? "They";
    if (balance < reward.cost_points) {
      return json({ detail: `${name} needs ${reward.cost_points - balance} more stars for that` }, 422);
    }
    store.claims.push({
      reward_id: reward.id,
      profile_id: profileId,
      points_spent: reward.cost_points,
      claimed_at: new Date().toISOString(),
    });
    return json({ claimed: true, reward: reward.title, profile_id: profileId, balance: balance - reward.cost_points });
  }
  if ((m = match(/^\/api\/rewards\/(\d+)$/)) && method === "DELETE") {
    store.rewards = store.rewards.filter((r) => r.id !== Number(m![1]));
    return new Response(null, { status: 204 });
  }
  if (path === "/api/rewards/claims") return json([]);

  // ------------------------------------------------------------------- lists
  if (path === "/api/lists" && method === "GET") return json(store.lists);
  if (path === "/api/lists" && method === "POST") {
    const lst = {
      id: store.nextListId++,
      name: String(body.name ?? "List"),
      kind: String(body.kind ?? "custom"),
      icon: (body.icon as string) ?? null,
      items: [],
    };
    store.lists.push(lst);
    return json(lst, 201);
  }
  if ((m = match(/^\/api\/lists\/(\d+)\/items$/)) && method === "POST") {
    const lst = store.lists.find((l) => l.id === Number(m![1]));
    if (!lst) return json({ detail: "not found" }, 404);
    const item = { id: store.nextItemId++, text: String(body.text ?? ""), done: false };
    lst.items.push(item);
    return json(item, 201);
  }
  if ((m = match(/^\/api\/lists\/items\/(\d+)$/)) && method === "PATCH") {
    for (const lst of store.lists) {
      const item = lst.items.find((i) => i.id === Number(m![1]));
      if (item) {
        if (body.done !== undefined) item.done = Boolean(body.done);
        if (body.text !== undefined) item.text = String(body.text);
        return json(item);
      }
    }
    return json({ detail: "not found" }, 404);
  }
  if ((m = match(/^\/api\/lists\/(\d+)\/clear-done$/)) && method === "POST") {
    const lst = store.lists.find((l) => l.id === Number(m![1]));
    if (!lst) return json({ detail: "not found" }, 404);
    const before = lst.items.length;
    lst.items = lst.items.filter((i) => !i.done);
    return json({ removed: before - lst.items.length });
  }
  if ((m = match(/^\/api\/lists\/(\d+)$/)) && method === "DELETE") {
    store.lists = store.lists.filter((l) => l.id !== Number(m![1]));
    return new Response(null, { status: 204 });
  }

  // ------------------------------------------------------------------- meals
  if (path === "/api/meals" && method === "GET") return json(store.meals);
  if (path === "/api/meals" && method === "POST") {
    const meal = {
      id: store.nextMealId++,
      name: String(body.name ?? "Meal"),
      icon: (body.icon as string) ?? null,
      is_favorite: Boolean(body.is_favorite),
      ingredients: (body.ingredients as string[]) ?? [],
      notes: null,
      recipe_url: null,
      tags: null,
    };
    store.meals.push(meal);
    return json(meal, 201);
  }
  if ((m = match(/^\/api\/meals\/(\d+)$/)) && method === "DELETE") {
    store.meals = store.meals.filter((x) => x.id !== Number(m![1]));
    return new Response(null, { status: 204 });
  }
  if (path === "/api/meals/plan" && method === "GET") {
    const start = url.searchParams.get("start")!;
    const end = url.searchParams.get("end")!;
    return json(
      store.plan
        .filter((e) => e.date >= start && e.date <= end)
        .map((e) => {
          const meal = store.meals.find((x) => x.id === e.meal_id);
          return { ...e, meal_name: meal?.name ?? null, meal_icon: meal?.icon ?? null };
        }),
    );
  }
  if (path === "/api/meals/plan" && method === "PUT") {
    const date = String(body.date);
    const slot = String(body.slot);
    store.plan = store.plan.filter((e) => !(e.date === date && e.slot === slot));
    if (body.meal_id != null || body.custom_text) {
      store.plan.push({
        date,
        slot,
        meal_id: (body.meal_id as number) ?? null,
        custom_text: (body.custom_text as string) ?? null,
      });
    }
    return json({ date, slot });
  }
  if (path === "/api/meals/plan/grocery" && method === "POST") {
    const grocery = store.lists.find((l) => l.kind === "grocery");
    if (!grocery) return json({ added: 0, list_id: 0 });
    const existing = new Set(grocery.items.map((i) => i.text.toLowerCase()));
    let added = 0;
    for (const entry of store.plan) {
      const meal = store.meals.find((x) => x.id === entry.meal_id);
      for (const ing of meal?.ingredients ?? []) {
        if (!existing.has(ing.toLowerCase())) {
          grocery.items.push({ id: store.nextItemId++, text: ing, done: false });
          existing.add(ing.toLowerCase());
          added++;
        }
      }
    }
    return json({ added, list_id: grocery.id });
  }

  // ------------------------------------------------------------------ photos
  if (path === "/api/photos" && method === "GET") {
    return json(
      store.photos.map((p) => ({
        id: p.id,
        url: p.url,
        thumb: p.url,
        width: 1600,
        height: 1000,
        source: "shared_album",
        hidden: false,
        taken_at: null,
        created_at: new Date().toISOString(),
      })),
    );
  }
  if (path === "/api/photos/slideshow") {
    return json(store.photos.map((p) => ({ url: p.url, width: 1600, height: 1000 })));
  }
  if (path === "/api/photos/shared-albums" && method === "GET") {
    return json([{ id: 1, name: "Family Wall (demo)", enabled: true, last_sync_at: new Date().toISOString(), last_error: null }]);
  }
  if (path.startsWith("/api/photos") && method !== "GET") {
    return json({ detail: "Uploads are disabled in the demo — this works on the real device." }, 501);
  }

  // ------------------------------------------------------------------ device
  if (path === "/api/device" && method === "GET") {
    return json({
      version: "demo",
      display_on: true,
      scheduled_asleep: false,
      disk_total_gb: 64,
      disk_free_gb: 51.2,
      time: new Date().toISOString(),
    });
  }
  if (path === "/api/weather") {
    return json({
      available: true,
      fetched_at: new Date().toISOString(),
      data: {
        current: { temperature_2m: 76, weather_code: 1, is_day: 1 },
        daily: { time: [], weather_code: [], temperature_2m_max: [], temperature_2m_min: [] },
      },
    });
  }
  if (path === "/api/accounts" && method === "GET") return json([]);
  if (path.startsWith("/api/accounts")) {
    return json({ detail: "iCloud sign-in is disabled in the demo — it works on the real device." }, 501);
  }

  return json({ detail: `demo: unhandled ${method} ${path}` }, 404);
}

export function installDemoShim(): void {
  const store = createStore();
  const realFetch = window.fetch.bind(window);
  window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    const raw =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (!raw.includes("/api/")) return realFetch(input as RequestInfo, init);
    // base is only for URL parsing; file:// and sandboxed origins are fine
    const url = new URL(raw, "http://bayta.demo");
    return handle(store, url, init);
  }) as typeof window.fetch;

  // SSE is meaningless without a backend; react-query handles refresh locally
  class FakeEventSource {
    onmessage: ((ev: MessageEvent) => void) | null = null;
    close(): void {}
  }
  (window as unknown as { EventSource: unknown }).EventSource = FakeEventSource;
}
