import { useQuery } from "@tanstack/react-query";
import {
  Cloud,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Moon,
  Sun,
  type LucideIcon,
} from "lucide-react";
import { api } from "../api/client";

function iconFor(code: number, isDay: boolean): LucideIcon {
  if (code === 0) return isDay ? Sun : Moon;
  if (code <= 2) return CloudSun;
  if (code === 3) return Cloud;
  if (code === 45 || code === 48) return CloudFog;
  if (code >= 71 && code <= 77) return CloudSnow;
  if (code >= 95) return CloudLightning;
  if (code >= 51) return CloudRain;
  return Cloud;
}

export function WeatherChip() {
  const { data } = useQuery({
    queryKey: ["weather"],
    queryFn: api.weather,
    refetchInterval: 10 * 60_000,
  });
  if (!data?.available || !data.data) return null;
  const { temperature_2m, weather_code, is_day } = data.data.current;
  const Icon = iconFor(weather_code, is_day === 1);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        fontSize: 17,
        fontWeight: 600,
        color: "var(--text-secondary)",
      }}
    >
      <Icon size={20} />
      <span className="tnum">{Math.round(temperature_2m)}°</span>
    </span>
  );
}
