import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
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

function applyTheme() {
  const hour = new Date().getHours();
  const dark = hour >= 19 || hour < 7;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

export default function App() {
  useSSE();
  useEffect(() => {
    applyTheme();
    const id = setInterval(applyTheme, 60_000);
    return () => clearInterval(id);
  }, []);

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
