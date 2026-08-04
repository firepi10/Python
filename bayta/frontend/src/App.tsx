import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";
import { ToastProvider } from "./components/Toast";
import { useSSE } from "./hooks/useSSE";
import { CalendarView } from "./views/calendar/CalendarView";
import { ChoresView } from "./views/chores/ChoresView";
import { Gallery } from "./views/Gallery";
import { KioskShell } from "./views/KioskShell";
import { ListsView } from "./views/lists/ListsView";
import { MealsView } from "./views/meals/MealsView";
import { PhotosView } from "./views/photos/PhotosView";
import { Screensaver } from "./views/screensaver/Screensaver";
import { SettingsView } from "./views/settings/SettingsView";

function applyTheme(mode: string) {
  let dark: boolean;
  if (mode === "light") dark = false;
  else if (mode === "dark") dark = true;
  else {
    const hour = new Date().getHours();
    dark = hour >= 19 || hour < 7;
  }
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

export default function App() {
  useSSE();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const theme = (settings?.theme as string | undefined) ?? "auto";
  const reducedGlass = Boolean(settings?.reduced_glass);

  useEffect(() => {
    applyTheme(theme);
    document.documentElement.dataset.glass = reducedGlass ? "reduced" : "full";
    const id = setInterval(() => applyTheme(theme), 60_000);
    return () => clearInterval(id);
  }, [theme, reducedGlass]);

  return (
    <ToastProvider>
      <Routes>
        <Route path="/" element={<KioskShell />}>
          <Route index element={<Navigate to="/calendar" replace />} />
          <Route path="calendar" element={<CalendarView />} />
          <Route path="meals" element={<MealsView />} />
          <Route path="chores" element={<ChoresView />} />
          <Route path="lists" element={<ListsView />} />
          <Route path="photos" element={<PhotosView />} />
          <Route path="settings" element={<SettingsView />} />
        </Route>
        <Route path="/screensaver" element={<Screensaver />} />
        <Route path="/dev/gallery" element={<Gallery />} />
      </Routes>
    </ToastProvider>
  );
}
