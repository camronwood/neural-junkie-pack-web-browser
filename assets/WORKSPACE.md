# Web browser workspace

Use the HTML browser workbench when editing `.html` files in this workspace.

## Setup (v2 — Playwright QA)

1. Enable the **Web browser** pack in **Domain packs** (⌘⇧K).
2. Run one-time setup from the pack repo:
   ```bash
   ./scripts/setup-playwright.sh
   ```
3. Confirm sidecar readiness: hub proxies `GET /api/browser/status` when the pack is enabled.

## Preview workflow

1. Open an HTML file — it opens in split editor + live preview.
2. Use **Workspace file** mode for static HTML served by the hub preview API.
3. Use **Dev server URL** mode (e.g. `http://localhost:5173`) when running Vite/Next locally.
4. Save and click **Reload preview** to refresh after edits.

## QA workflow (v2)

With the browser sidecar enabled, the workbench adds:

- **Responsive toolbar** — mobile (375×812), tablet (768×1024), desktop (1280×800)
- **A11y panel** — axe-core WCAG audit with violation list
- **Performance panel** — FCP, load time, DOM size, resource count
- **Visual diff** — compare screenshot to baseline in `.nj/browser-baselines/`
- **DOM picker** — select element in preview → copy context for chat

Ask **@WebBrowserExpert** to:

- Run `browser_screenshot` on a preview URL
- Run `browser_a11y_audit` after **@FrontendEngineer** delivers pages
- Verify forms with `browser_navigate`, `browser_click`, `browser_fill`

## SD pack handoff

After collab execution delivers HTML/CSS:

1. Open the page in the HTML browser workbench.
2. Run a11y audit at mobile + desktop breakpoints.
3. Accept visual baselines when the layout looks correct.
4. Mention `@WebBrowserExpert verify the site at mobile and desktop` in channel if agents should automate checks.
