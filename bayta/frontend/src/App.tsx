import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { ClipboardCheck, Images, ListTodo, UtensilsCrossed } from "lucide-react";
import { EmptyState } from "./components/EmptyState";
import { ToastProvider } from "./components/Toast";
import { useSSE } from "./hooks/useSSE";
import { CalendarView } from "./views/calendar/CalendarView";
import { Gallery } from "./views/Gallery";
import { KioskShell } from "./views/KioskShell";
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
          <Route
            path="meals"
            element={<EmptyState icon={UtensilsCrossed} title="Meals" hint="Weekly planner and favorites arrive in M6." />}
          />
          <Route
            path="chores"
            element={<EmptyState icon={ClipboardCheck} title="Chores" hint="Chore chart with star rewards arrives in M6." />}
          />
          <Route
            path="lists"
            element={<EmptyState icon={ListTodo} title="Lists" hint="Shared grocery and to-do lists arrive in M6." />}
          />
          <Route
            path="photos"
            element={<EmptyState icon={Images} title="Photos" hint="iCloud Shared Album sync and screensaver arrive in M5." />}
          />
          <Route path="settings" element={<SettingsView />} />
        </Route>
        <Route path="/dev/gallery" element={<Gallery />} />
      </Routes>
    </ToastProvider>
  );
}
