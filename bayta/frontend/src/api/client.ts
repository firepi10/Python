export interface OccurrenceDTO {
  event_id: number;
  summary: string;
  location: string | null;
  start: string;
  end: string;
  all_day: boolean;
  is_recurring: boolean;
  calendar_id: number | null;
  calendar_name: string;
  read_only: boolean;
  color: string;
  profile_id: number | null;
  profile_name: string | null;
}

export interface ProfileDTO {
  id: number;
  name: string;
  color: string;
  sort_order: number;
}

export interface EventInput {
  summary: string;
  start: string;
  end: string;
  all_day: boolean;
  location?: string | null;
  rrule?: string | null;
  calendar_id?: number | null;
  profile_id?: number | null;
}

export interface CalendarDTO {
  id: number;
  display_name: string;
  color: string | null;
  profile_id: number | null;
  enabled: boolean;
  read_only: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  occurrences: (start: string, end: string) =>
    request<OccurrenceDTO[]>(
      `/api/calendar/occurrences?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
    ),
  calendars: () => request<CalendarDTO[]>("/api/calendar/calendars"),
  createEvent: (body: EventInput) =>
    request<{ id: number }>("/api/calendar/events", { method: "POST", body: JSON.stringify(body) }),
  updateEvent: (id: number, body: EventInput) =>
    request<{ id: number }>(`/api/calendar/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteEvent: (id: number) => request<void>(`/api/calendar/events/${id}`, { method: "DELETE" }),
  profiles: () => request<ProfileDTO[]>("/api/profiles"),
  weather: () => request<{ available: boolean; data?: WeatherData }>("/api/weather"),
  settings: () => request<Record<string, unknown>>("/api/settings"),
  putSetting: (key: string, value: unknown) =>
    request<Record<string, unknown>>(`/api/settings/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
};

export interface AccountCalendarDTO {
  id: number;
  name: string;
  enabled: boolean;
  profile_id: number | null;
}

export interface AccountDTO {
  id: number;
  label: string;
  apple_id: string;
  status: "ok" | "auth_failed" | "error";
  last_sync_at: string | null;
  last_error: string | null;
  calendars: AccountCalendarDTO[];
}

export interface DiscoveredCalendar {
  url: string;
  name: string;
}

export const accountsApi = {
  list: () => request<AccountDTO[]>("/api/accounts"),
  test: (apple_id: string, password: string) =>
    request<{ principal_url: string; calendars: DiscoveredCalendar[] }>("/api/accounts/test", {
      method: "POST",
      body: JSON.stringify({ apple_id, password }),
    }),
  create: (body: {
    label: string;
    apple_id: string;
    password: string;
    calendars: { url: string; name: string; enabled: boolean; profile_id: number | null }[];
  }) => request<{ id: number }>("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
  patchCalendar: (
    accountId: number,
    calendarId: number,
    body: { enabled?: boolean; profile_id?: number | null; clear_profile?: boolean },
  ) =>
    request(`/api/accounts/${accountId}/calendars/${calendarId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (accountId: number) => request<void>(`/api/accounts/${accountId}`, { method: "DELETE" }),
  reauth: (accountId: number, apple_id: string, password: string) =>
    request(`/api/accounts/${accountId}/reauth`, {
      method: "POST",
      body: JSON.stringify({ apple_id, password }),
    }),
  syncNow: () => request<{ ok: boolean }>("/api/accounts/sync-now", { method: "POST" }),
};

export const profilesApi = {
  create: (body: { name: string; color: string; sort_order?: number }) =>
    request<ProfileDTO>("/api/profiles", { method: "POST", body: JSON.stringify(body) }),
  remove: (id: number) => request<void>(`/api/profiles/${id}`, { method: "DELETE" }),
};

export interface WeatherData {
  current: { temperature_2m: number; weather_code: number; is_day: number };
  daily: {
    time: string[];
    weather_code: number[];
    temperature_2m_max: number[];
    temperature_2m_min: number[];
  };
}

export function profileColorVar(color: string): string {
  return `var(--profile-${color}, var(--accent))`;
}
