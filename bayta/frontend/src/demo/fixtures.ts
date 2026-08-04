/* In-memory family dataset for the demo build. Dates are generated relative
   to "today" so the calendar always looks alive. Mirrors seed_demo.py. */

import { addDays, format, startOfDay } from "date-fns";

export interface Store {
  profiles: { id: number; name: string; color: string; sort_order: number }[];
  occurrences: OccRecord[];
  nextEventId: number;
  chores: ChoreRecord[];
  nextChoreId: number;
  completions: { chore_id: number; date: string; profile_id: number | null; points: number }[];
  rewards: { id: number; title: string; icon: string | null; cost_points: number; active: boolean }[];
  nextRewardId: number;
  claims: { reward_id: number; profile_id: number; points_spent: number; claimed_at: string }[];
  lists: ListRecord[];
  nextListId: number;
  nextItemId: number;
  meals: MealRecord[];
  nextMealId: number;
  plan: { date: string; slot: string; meal_id: number | null; custom_text: string | null }[];
  photos: { id: number; url: string }[];
  settings: Record<string, unknown>;
}

export interface OccRecord {
  event_id: number;
  summary: string;
  location: string | null;
  start: string;
  end: string;
  all_day: boolean;
  is_recurring: boolean;
  profile_id: number | null;
  color: string;
  profile_name: string | null;
}

export interface ChoreRecord {
  id: number;
  title: string;
  icon: string | null;
  points: number;
  rrule: string;
  profile_ids: number[];
  active: boolean;
}

interface ListRecord {
  id: number;
  name: string;
  kind: string;
  icon: string | null;
  items: { id: number; text: string; done: boolean }[];
}

interface MealRecord {
  id: number;
  name: string;
  icon: string | null;
  is_favorite: boolean;
  ingredients: string[];
  notes: string | null;
  recipe_url: string | null;
  tags: string | null;
}

const MOM = 1, DAD = 2, LAINEY = 3, CHARLEE = 4, SUNNIE = 5;

const COLORS: Record<number, [string, string]> = {
  [MOM]: ["Mom", "pink"],
  [DAD]: ["Dad", "blue"],
  [LAINEY]: ["Lainey", "purple"],
  [CHARLEE]: ["Charlee", "green"],
  [SUNNIE]: ["Sunnie", "yellow"],
};

function gradientPhoto(c1: string, c2: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='1000'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='${c1}'/><stop offset='1' stop-color='${c2}'/></linearGradient></defs><rect width='1600' height='1000' fill='url(#g)'/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

let eventIdCounter = 1;

function occ(
  base: Date,
  spec: {
    summary: string;
    profile?: number;
    location?: string;
    hour?: number;
    minutes?: number;
    durationMin?: number;
    allDay?: boolean;
    recurring?: boolean;
  },
): OccRecord {
  const id = eventIdCounter++;
  const [name, color] = spec.profile ? COLORS[spec.profile] : [null, "blue"];
  const start = new Date(base);
  const end = new Date(base);
  if (spec.allDay) {
    start.setUTCHours(0, 0, 0, 0);
    end.setTime(start.getTime() + 86400_000);
  } else {
    start.setHours(spec.hour ?? 9, spec.minutes ?? 0, 0, 0);
    end.setTime(start.getTime() + (spec.durationMin ?? 60) * 60_000);
  }
  return {
    event_id: id,
    summary: spec.summary,
    location: spec.location ?? null,
    start: start.toISOString(),
    end: end.toISOString(),
    all_day: spec.allDay ?? false,
    is_recurring: spec.recurring ?? false,
    profile_id: spec.profile ?? null,
    color,
    profile_name: name,
  };
}

/** Weekly recurrences share one event_id so edits behave sensibly. */
function weekly(
  weekday: number,
  spec: Parameters<typeof occ>[1],
  weeksBack = 5,
  weeksAhead = 9,
): OccRecord[] {
  const today = startOfDay(new Date());
  const out: OccRecord[] = [];
  const sharedId = eventIdCounter;
  for (let w = -weeksBack; w <= weeksAhead; w++) {
    const day = addDays(today, ((weekday - today.getDay() + 7) % 7) + w * 7);
    const record = occ(day, { ...spec, recurring: true });
    record.event_id = sharedId;
    out.push(record);
  }
  eventIdCounter = sharedId + 1;
  return out;
}

export function createStore(): Store {
  const today = startOfDay(new Date());
  const iso = (d: Date) => format(d, "yyyy-MM-dd");

  const occurrences: OccRecord[] = [
    ...weekly(1, { summary: "Soccer practice", profile: LAINEY, hour: 16, durationMin: 90, location: "Riverside fields" }),
    ...weekly(3, { summary: "Piano lesson", profile: CHARLEE, hour: 15, minutes: 30, durationMin: 45 }),
    ...weekly(4, { summary: "Trash & recycling out", profile: DAD, hour: 19, durationMin: 15 }),
    ...weekly(2, { summary: "Yoga", profile: MOM, hour: 7 }),
    ...weekly(6, { summary: "Toddler swim — Sunnie", profile: SUNNIE, hour: 9, durationMin: 45 }),
    occ(addDays(today, 2), { summary: "Dentist — Charlee", profile: CHARLEE, hour: 14, location: "Dr. Patel" }),
    occ(addDays(today, 3), { summary: "Date night", profile: MOM, hour: 19, durationMin: 180, location: "Lupa" }),
    occ(addDays(today, 5), { summary: "Grandma visits", allDay: true }),
    occ(addDays(today, 9), { summary: "School bake sale", profile: LAINEY, allDay: true }),
    occ(addDays(today, 12), { summary: "Book club", profile: MOM, hour: 19, durationMin: 120 }),
    occ(addDays(today, 20), { summary: "Sunnie's birthday 🎂", profile: SUNNIE, allDay: true }),
  ];

  const completions: Store["completions"] = [
    { chore_id: 1, date: iso(today), profile_id: LAINEY, points: 1 },
  ];
  for (let d = 1; d <= 12; d++) {
    completions.push({ chore_id: 1, date: iso(addDays(today, -d)), profile_id: LAINEY, points: 1 });
    if (d % 2 === 0) {
      completions.push({ chore_id: 1, date: iso(addDays(today, -d)), profile_id: CHARLEE, points: 1 });
    }
  }

  return {
    profiles: Object.entries(COLORS).map(([id, [name, color]], i) => ({
      id: Number(id),
      name,
      color,
      sort_order: i,
    })),
    occurrences,
    nextEventId: eventIdCounter + 1000,
    chores: [
      { id: 1, title: "Make your bed", icon: "🛏️", points: 1, rrule: "FREQ=DAILY", profile_ids: [LAINEY, CHARLEE], active: true },
      { id: 2, title: "Feed the dog", icon: "🐕", points: 1, rrule: "FREQ=DAILY", profile_ids: [CHARLEE], active: true },
      { id: 3, title: "Empty dishwasher", icon: "🍽️", points: 2, rrule: "FREQ=WEEKLY;BYDAY=MO,WE,FR", profile_ids: [LAINEY, CHARLEE], active: true },
      { id: 4, title: "Put toys in the bin", icon: "🧸", points: 1, rrule: "FREQ=DAILY", profile_ids: [SUNNIE], active: true },
      { id: 5, title: "Take out trash", icon: "🗑️", points: 3, rrule: "FREQ=WEEKLY;BYDAY=TH", profile_ids: [DAD], active: true },
    ],
    nextChoreId: 6,
    completions,
    rewards: [
      { id: 1, title: "Movie night pick", icon: "🎬", cost_points: 10, active: true },
      { id: 2, title: "Stay up 30 min late", icon: "🌙", cost_points: 15, active: true },
      { id: 3, title: "Ice cream trip", icon: "🍦", cost_points: 25, active: true },
      { id: 4, title: "New toy", icon: "🧸", cost_points: 50, active: true },
    ],
    nextRewardId: 5,
    claims: [],
    lists: [
      {
        id: 1, name: "Groceries", kind: "grocery", icon: "🛒",
        items: [
          { id: 1, text: "Milk", done: false },
          { id: 2, text: "Eggs", done: false },
          { id: 3, text: "Bananas", done: false },
          { id: 4, text: "Coffee beans", done: false },
          { id: 5, text: "Paper towels", done: true },
        ],
      },
      {
        id: 2, name: "To-Do", kind: "todo", icon: "✅",
        items: [
          { id: 6, text: "Fix the gate latch", done: false },
          { id: 7, text: "RSVP to the Nguyens", done: false },
        ],
      },
    ],
    nextListId: 3,
    nextItemId: 8,
    meals: [
      { id: 1, name: "Taco night", icon: "🌮", is_favorite: true, ingredients: ["Tortillas", "Ground beef", "Salsa", "Cheddar"], notes: null, recipe_url: null, tags: null },
      { id: 2, name: "Salmon & rice", icon: "🐟", is_favorite: true, ingredients: ["Salmon fillets", "Rice", "Broccoli"], notes: null, recipe_url: null, tags: null },
      { id: 3, name: "Pasta bolognese", icon: "🍝", is_favorite: false, ingredients: ["Spaghetti", "Ground beef", "Tomato passata"], notes: null, recipe_url: null, tags: null },
      { id: 4, name: "Pancakes", icon: "🥞", is_favorite: true, ingredients: ["Flour", "Eggs", "Maple syrup"], notes: null, recipe_url: null, tags: null },
      { id: 5, name: "Veggie stir-fry", icon: "🥦", is_favorite: false, ingredients: ["Broccoli", "Peppers", "Soy sauce", "Noodles"], notes: null, recipe_url: null, tags: null },
    ],
    nextMealId: 6,
    plan: [
      { date: iso(addDays(today, 1)), slot: "dinner", meal_id: 1, custom_text: null },
      { date: iso(addDays(today, 2)), slot: "dinner", meal_id: 2, custom_text: null },
      { date: iso(addDays(today, 3)), slot: "dinner", meal_id: 3, custom_text: null },
      { date: iso(addDays(today, 5)), slot: "breakfast", meal_id: 4, custom_text: null },
      { date: iso(addDays(today, 5)), slot: "dinner", meal_id: 5, custom_text: null },
    ],
    photos: [
      { id: 1, url: gradientPhoto("#ff9500", "#ff2d55") },
      { id: 2, url: gradientPhoto("#0a84ff", "#64d2ff") },
      { id: 3, url: gradientPhoto("#30d158", "#ffd60a") },
      { id: 4, url: gradientPhoto("#bf5af2", "#0a84ff") },
    ],
    settings: {
      sleep_schedule: { enabled: true, off: "21:30", on: "06:30" },
      idle_timeout_s: 300,
      orientation: "landscape",
      theme: "auto",
      reduced_glass: false,
      weather: { lat: 40.7128, lon: -74.006, unit: "fahrenheit", label: "Home" },
      screensaver: { enabled: false, interval_s: 12, ken_burns: true },
      admin_pin: null,
    },
  };
}
