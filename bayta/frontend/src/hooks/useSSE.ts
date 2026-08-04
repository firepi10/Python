import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const TOPIC_KEYS: Record<string, string[]> = {
  calendar: ["occurrences", "calendars"],
  profiles: ["profiles"],
  photos: ["photos", "slideshow"],
  meals: ["meals", "mealplan"],
  chores: ["chores"],
  lists: ["lists"],
  countdowns: ["countdowns"],
  weather: ["weather"],
  settings: ["settings"],
};

/** Live refresh: any change published by the backend invalidates the matching
 *  query slices, on the wall and on every phone at once. */
export function useSSE() {
  const queryClient = useQueryClient();
  useEffect(() => {
    const source = new EventSource("/api/stream");
    source.onmessage = (msg) => {
      try {
        const { topic } = JSON.parse(msg.data) as { topic: string };
        if (topic === "reload") {
          window.location.reload();
          return;
        }
        for (const key of TOPIC_KEYS[topic] ?? []) {
          queryClient.invalidateQueries({ queryKey: [key] });
        }
      } catch {
        /* keepalive */
      }
    };
    return () => source.close();
  }, [queryClient]);
}
