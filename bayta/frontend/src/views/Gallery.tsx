import { useState } from "react";
import { Avatar } from "../components/Avatar";
import { Chip } from "../components/Chip";
import { GlassCard } from "../components/GlassCard";
import { SegmentedControl } from "../components/SegmentedControl";
import { Sheet } from "../components/Sheet";
import { TouchButton } from "../components/TouchButton";
import { useToast } from "../components/Toast";

const PROFILE_COLORS = [
  ["Blue", "var(--profile-blue)"],
  ["Purple", "var(--profile-purple)"],
  ["Pink", "var(--profile-pink)"],
  ["Orange", "var(--profile-orange)"],
  ["Green", "var(--profile-green)"],
  ["Teal", "var(--profile-teal)"],
] as const;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-secondary)", margin: "0 0 12px" }}>
        {title}
      </h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>{children}</div>
    </section>
  );
}

/** /dev/gallery — living spec of the design system, used by the screenshot harness. */
export function Gallery() {
  const [segment, setSegment] = useState<"month" | "week" | "day">("month");
  const [sheetOpen, setSheetOpen] = useState(false);
  const toast = useToast();

  return (
    <div
      style={{
        minHeight: "100%",
        background: "var(--bg-gradient)",
        padding: 32,
        overflowY: "auto",
      }}
    >
      <h1 style={{ fontSize: 28, fontWeight: 800, margin: "0 0 24px" }}>Bayta design system</h1>

      <Section title="Buttons">
        <TouchButton variant="primary">Add event</TouchButton>
        <TouchButton variant="secondary">Cancel</TouchButton>
        <TouchButton variant="ghost">Skip</TouchButton>
        <TouchButton variant="danger">Delete</TouchButton>
        <TouchButton variant="primary" size="sm">Small</TouchButton>
        <TouchButton variant="primary" size="lg">Large</TouchButton>
        <TouchButton variant="secondary" disabled>Disabled</TouchButton>
      </Section>

      <Section title="Segmented control">
        <div style={{ width: 320 }}>
          <SegmentedControl
            options={[
              { value: "month", label: "Month" },
              { value: "week", label: "Week" },
              { value: "day", label: "Day" },
            ]}
            value={segment}
            onChange={setSegment}
          />
        </div>
      </Section>

      <Section title="Profile chips & avatars">
        {PROFILE_COLORS.map(([name, color]) => (
          <Chip key={name} color={color}>{name}</Chip>
        ))}
        <Avatar name="Mom" color="var(--profile-pink)" />
        <Avatar name="Dad" color="var(--profile-blue)" />
        <Avatar name="Zoe K" color="var(--profile-green)" size={52} />
      </Section>

      <Section title="Cards">
        <GlassCard style={{ width: 280 }}>
          <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>Soccer practice</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>Today · 4:00–5:30 PM</div>
          <div style={{ marginTop: 12 }}>
            <Chip color="var(--profile-green)">Zoe</Chip>
          </div>
        </GlassCard>
        <GlassCard blur style={{ width: 280 }}>
          <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>Glass card</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            backdrop-blur surface — budget: one per screen
          </div>
        </GlassCard>
      </Section>

      <Section title="Overlays">
        <TouchButton variant="primary" onClick={() => setSheetOpen(true)}>Open sheet</TouchButton>
        <TouchButton variant="secondary" onClick={() => toast("Saved to iCloud")}>Show toast</TouchButton>
      </Section>

      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="New event">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, paddingBottom: 8 }}>
          <div style={{ color: "var(--text-secondary)" }}>
            Bottom sheet in the iOS style. Slides on transform only; the dim layer fades on
            opacity only.
          </div>
          <TouchButton variant="primary" onClick={() => setSheetOpen(false)}>Done</TouchButton>
        </div>
      </Sheet>
    </div>
  );
}
