import React from "react";

/** A wall display has no console and often no keyboard, so a crash that leaves
 *  an empty root is indistinguishable from a dead Pi — the screen just goes
 *  black and there is nothing to act on. Show the failure instead, in plain
 *  language, with the detail needed to fix it. */
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Bayta crashed:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        role="alert"
        style={{
          position: "fixed",
          inset: 0,
          // deliberately not themed: the theme is one of the things that can
          // fail, and this must be readable no matter what
          background: "#101014",
          color: "#f5f5f7",
          font: "16px/1.5 system-ui, sans-serif",
          padding: "clamp(24px, 6vw, 72px)",
          overflow: "auto",
          zIndex: 9999,
        }}
      >
        <div style={{ fontSize: 13, letterSpacing: "0.08em", opacity: 0.6 }}>BAYTA</div>
        <h1 style={{ fontSize: "clamp(24px, 4vw, 38px)", fontWeight: 600, margin: "8px 0 4px" }}>
          Something went wrong on this screen
        </h1>
        <p style={{ opacity: 0.75, marginBottom: 28, maxWidth: "60ch" }}>
          The Pi is running — the app hit an error while drawing. Tapping Reload
          usually clears it. If it comes back every time, the message below says why.
        </p>

        <button
          onClick={() => window.location.reload()}
          style={{
            appearance: "none",
            border: 0,
            borderRadius: 999,
            padding: "14px 32px",
            fontSize: 17,
            fontWeight: 600,
            color: "#fff",
            background: "#0a84ff",
            cursor: "pointer",
            marginBottom: 32,
          }}
        >
          Reload
        </button>

        <pre
          style={{
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "rgba(255,255,255,0.06)",
            borderRadius: 12,
            padding: 18,
            fontSize: 13,
            opacity: 0.9,
            margin: 0,
          }}
        >
          {error.message}
          {error.stack ? `\n\n${error.stack}` : ""}
        </pre>
      </div>
    );
  }
}
