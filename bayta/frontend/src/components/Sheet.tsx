import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  /** max width of the sheet on large screens */
  maxWidth?: number;
}

/** Bottom sheet in the iOS style: dimmed backdrop (opacity fade) + panel
 *  sliding up (translateY). This is the app's single allowed blur surface. */
export function Sheet({ open, onClose, title, children, maxWidth = 640 }: Props) {
  const [mounted, setMounted] = useState(open);
  useEffect(() => {
    if (open) setMounted(true);
    else {
      const t = setTimeout(() => setMounted(false), 350);
      return () => clearTimeout(t);
    }
  }, [open]);

  if (!mounted) return null;

  return createPortal(
    <div style={{ position: "fixed", inset: 0, zIndex: 100 }}>
      <div
        onClick={onClose}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          opacity: open ? 1 : 0,
          transition: `opacity var(--dur-med) ease`,
        }}
      />
      <div
        className="glass"
        role="dialog"
        aria-label={title}
        style={{
          position: "absolute",
          left: "50%",
          bottom: 0,
          width: "100%",
          maxWidth,
          maxHeight: "88%",
          overflowY: "auto",
          borderRadius: "var(--radius-xl) var(--radius-xl) 0 0",
          boxShadow: "var(--shadow-sheet)",
          padding: "12px 24px 32px",
          transform: `translateX(-50%) translateY(${open ? "0%" : "105%"})`,
          transition: `transform var(--dur-med) var(--ease-spring)`,
          willChange: "transform",
        }}
      >
        <div
          aria-hidden
          style={{
            width: 40,
            height: 5,
            borderRadius: 3,
            background: "var(--text-tertiary)",
            margin: "4px auto 14px",
          }}
        />
        {title && (
          <h2 style={{ margin: "0 0 16px", fontSize: 22, fontWeight: 700, textAlign: "center" }}>
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>,
    document.body,
  );
}
