// Headless screenshot harness: boots the real backend (serving frontend/dist),
// captures every registered route in kiosk landscape, kiosk portrait and phone
// viewports, in light and dark themes, into bayta/artifacts/.
import { spawn } from "node:child_process";
import { mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// playwright lives in frontend/node_modules regardless of where this script is invoked from
const { chromium } = createRequire(path.join(root, "frontend", "package.json"))("playwright");
const artifacts = path.join(root, "artifacts");
mkdirSync(artifacts, { recursive: true });

const PORT = 8777;
const BASE = `http://127.0.0.1:${PORT}`;

const PAGES = [
  { name: "calendar", path: "/calendar" },
  { name: "meals", path: "/meals" },
  { name: "chores", path: "/chores" },
  { name: "lists", path: "/lists" },
  { name: "photos", path: "/photos" },
  { name: "settings", path: "/settings" },
  { name: "screensaver", path: "/screensaver" },
  { name: "gallery", path: "/dev/gallery" },
];

const VIEWPORTS = [
  { name: "landscape", width: 1920, height: 1080 },
  { name: "portrait", width: 1080, height: 1920 },
  { name: "phone", width: 390, height: 844 },
];

async function waitForHealth(timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await fetch(`${BASE}/api/health`);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("backend did not become healthy");
}

const server = spawn(
  path.join(root, "backend", ".venv", "bin", "uvicorn"),
  ["app.main:app", "--port", String(PORT)],
  { cwd: path.join(root, "backend"), stdio: "inherit" },
);

try {
  await waitForHealth();
  const exePath = process.env.BAYTA_CHROMIUM;
  const browser = await chromium.launch(
    exePath || (existsSync("/opt/pw-browsers/chromium") && { executablePath: "/opt/pw-browsers/chromium" })
      ? { executablePath: exePath || "/opt/pw-browsers/chromium" }
      : {},
  );
  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await ctx.newPage();
    for (const p of PAGES) {
      for (const theme of ["light", "dark"]) {
        await page.goto(`${BASE}${p.path}`, { waitUntil: "networkidle" });
        await page.evaluate((t) => {
          document.documentElement.dataset.theme = t;
        }, theme);
        await page.waitForTimeout(400);
        const file = path.join(artifacts, `${p.name}-${vp.name}-${theme}.png`);
        await page.screenshot({ path: file });
        console.log("captured", path.relative(root, file));
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`done: screenshots in ${path.relative(process.cwd(), artifacts)}`);
} finally {
  server.kill("SIGTERM");
}
