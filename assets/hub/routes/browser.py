"""Browser automation sidecar routes (Playwright)."""
from __future__ import annotations

import base64
import io
import os
import threading
import uuid
from typing import Any

_lock = threading.Lock()
_pw = None
_browser = None
_sessions: dict[str, Any] = {}

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"


def handle_get(handler, path: str, settings: dict, pack_dir: str) -> None:
    if path == "/api/browser/status":
        ready, detail = _playwright_status(settings)
        handler._json(200, {"ok": ready, "playwright": ready, "detail": detail})
        return
    handler._json(404, {"error": "not found"})


def handle_post(handler, path: str, body: dict, settings: dict, pack_dir: str) -> None:
    routes = {
        "/api/browser/navigate": _navigate,
        "/api/browser/screenshot": _screenshot,
        "/api/browser/click": _click,
        "/api/browser/fill": _fill,
        "/api/browser/a11y-audit": _a11y_audit,
        "/api/browser/metrics": _metrics,
        "/api/browser/visual-diff": _visual_diff,
        "/api/browser/accept-baseline": _accept_baseline,
        "/api/browser/pick-element": _pick_element,
    }
    fn = routes.get(path)
    if fn is None:
        handler._json(404, {"error": "not found"})
        return
    try:
        result = fn(body, settings, pack_dir)
        handler._json(200, result)
    except RuntimeError as exc:
        handler._json(503, {"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        handler._json(500, {"error": str(exc)})


def _playwright_status(settings: dict) -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False, "Playwright not installed; run setup-playwright.sh"
    browsers_path = str(settings.get("playwright_browsers_path", "") or "").strip()
    if browsers_path:
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.expanduser(browsers_path))
    try:
        with _lock:
            _ensure_browser(settings)
        return True, "chromium ready"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _ensure_browser(settings: dict) -> Any:
    global _pw, _browser
    if _browser is not None:
        return _browser
    from playwright.sync_api import sync_playwright

    browsers_path = str(settings.get("playwright_browsers_path", "") or "").strip()
    if browsers_path:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser(browsers_path)
    _pw = sync_playwright().start()
    headless = settings.get("browser_headless", True)
    if isinstance(headless, str):
        headless = headless.lower() not in ("0", "false", "no")
    _browser = _pw.chromium.launch(headless=headless)
    return _browser


def _viewport(body: dict) -> dict | None:
    vp = body.get("viewport")
    if not isinstance(vp, dict):
        return None
    w = int(vp.get("width", 1280))
    h = int(vp.get("height", 800))
    return {"width": w, "height": h}


def _new_page(settings: dict, body: dict) -> Any:
    browser = _ensure_browser(settings)
    vp = _viewport(body)
    if vp:
        context = browser.new_context(viewport=vp)
    else:
        context = browser.new_context()
    page = context.new_page()
    return page, context


def _resolve_url(body: dict) -> str:
    url = str(body.get("url", "") or "").strip()
    if not url:
        raise ValueError("missing required parameter: url")
    return url


def _get_page(body: dict, settings: dict) -> tuple[Any, Any | None, bool]:
    """Return (page, context_or_none, owns_context)."""
    session_id = str(body.get("session_id", "") or "").strip()
    if session_id:
        with _lock:
            entry = _sessions.get(session_id)
        if entry is None:
            raise ValueError(f"unknown session_id: {session_id}")
        return entry["page"], None, False

    url = _resolve_url(body)
    page, context = _new_page(settings, body)
    page.goto(url, wait_until="networkidle", timeout=60000)
    return page, context, True


def _navigate(body: dict, settings: dict, pack_dir: str) -> dict:
    url = _resolve_url(body)
    page, context = _new_page(settings, body)
    page.goto(url, wait_until="networkidle", timeout=60000)
    session_id = uuid.uuid4().hex
    with _lock:
        _sessions[session_id] = {"page": page, "context": context}
    return {"session_id": session_id, "url": page.url}


def _screenshot(body: dict, settings: dict, pack_dir: str) -> dict:
    full_page = bool(body.get("full_page", False))
    page, context, owns = _get_page(body, settings)
    try:
        png = page.screenshot(full_page=full_page, type="png")
        vp = page.viewport_size or {"width": 0, "height": 0}
        return {
            "png_b64": base64.b64encode(png).decode("ascii"),
            "width": vp.get("width", 0),
            "height": vp.get("height", 0),
            "url": page.url,
        }
    finally:
        if owns and context is not None:
            context.close()


def _click(body: dict, settings: dict, pack_dir: str) -> dict:
    selector = str(body.get("selector", "") or "").strip()
    if not selector:
        raise ValueError("missing required parameter: selector")
    session_id = str(body.get("session_id", "") or "").strip()
    if not session_id:
        raise ValueError("missing required parameter: session_id")
    with _lock:
        entry = _sessions.get(session_id)
    if entry is None:
        raise ValueError(f"unknown session_id: {session_id}")
    entry["page"].click(selector, timeout=30000)
    return {"ok": True, "url": entry["page"].url}


def _fill(body: dict, settings: dict, pack_dir: str) -> dict:
    selector = str(body.get("selector", "") or "").strip()
    value = str(body.get("value", "") or "")
    if not selector:
        raise ValueError("missing required parameter: selector")
    session_id = str(body.get("session_id", "") or "").strip()
    if not session_id:
        raise ValueError("missing required parameter: session_id")
    with _lock:
        entry = _sessions.get(session_id)
    if entry is None:
        raise ValueError(f"unknown session_id: {session_id}")
    entry["page"].fill(selector, value, timeout=30000)
    return {"ok": True}


def _a11y_audit(body: dict, settings: dict, pack_dir: str) -> dict:
    page, context, owns = _get_page(body, settings)
    try:
        page.add_script_tag(url=AXE_CDN)
        tags = body.get("tags")
        if tags and isinstance(tags, list):
            tag_expr = ",".join(repr(t) for t in tags)
            results = page.evaluate(
                f"async () => await axe.run(document, {{ runOnly: {{ type: 'tag', values: [{tag_expr}] }} }})"
            )
        else:
            results = page.evaluate("async () => await axe.run(document)")
        violations = results.get("violations", []) if isinstance(results, dict) else []
        summary = []
        for v in violations:
            nodes = v.get("nodes") or []
            summary.append(
                {
                    "id": v.get("id", ""),
                    "impact": v.get("impact", ""),
                    "description": v.get("description", ""),
                    "help": v.get("help", ""),
                    "help_url": v.get("helpUrl", ""),
                    "node_count": len(nodes),
                }
            )
        return {
            "violations": summary,
            "violation_count": len(violations),
            "passes": len(results.get("passes", [])) if isinstance(results, dict) else 0,
            "url": page.url,
        }
    finally:
        if owns and context is not None:
            context.close()


def _metrics(body: dict, settings: dict, pack_dir: str) -> dict:
    page, context, owns = _get_page(body, settings)
    try:
        data = page.evaluate(
            """() => {
              const nav = performance.getEntriesByType('navigation')[0] || {};
              const paints = performance.getEntriesByType('paint');
              const fcp = paints.find(p => p.name === 'first-contentful-paint');
              return {
                dom_nodes: document.querySelectorAll('*').length,
                dom_content_loaded_ms: nav.domContentLoadedEventEnd || 0,
                load_ms: nav.loadEventEnd || 0,
                fcp_ms: fcp ? fcp.startTime : 0,
                transfer_size: nav.transferSize || 0,
                resource_count: performance.getEntriesByType('resource').length,
              };
            }"""
        )
        if not isinstance(data, dict):
            data = {}
        return {"metrics": data, "url": page.url}
    finally:
        if owns and context is not None:
            context.close()


def _visual_diff(body: dict, settings: dict, pack_dir: str) -> dict:
    baseline_path = str(body.get("baseline_path", "") or "").strip()
    if not baseline_path:
        raise ValueError("missing required parameter: baseline_path")
    baseline_path = os.path.expanduser(baseline_path)
    if not os.path.isabs(baseline_path):
        workspace_root = str(body.get("workspace_root", "") or "").strip()
        if workspace_root:
            baseline_path = os.path.join(os.path.expanduser(workspace_root), baseline_path)

    threshold = float(body.get("threshold", 0.1))
    shot = _screenshot(body, settings, pack_dir)
    current_png = base64.b64decode(shot["png_b64"])

    if not os.path.isfile(baseline_path):
        return {
            "match_pct": 0.0,
            "baseline_exists": False,
            "baseline_path": baseline_path,
            "current_png_b64": shot["png_b64"],
            "url": shot.get("url", ""),
        }

    with open(baseline_path, "rb") as fh:
        baseline_png = fh.read()

    match_pct, diff_b64 = _compare_png(baseline_png, current_png, threshold)
    return {
        "match_pct": match_pct,
        "baseline_exists": True,
        "baseline_path": baseline_path,
        "diff_png_b64": diff_b64,
        "url": shot.get("url", ""),
    }


def _compare_png(baseline: bytes, current: bytes, threshold: float) -> tuple[float, str]:
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("Pillow not installed; run setup-playwright.sh") from exc

    img_a = Image.open(io.BytesIO(baseline)).convert("RGB")
    img_b = Image.open(io.BytesIO(current)).convert("RGB")
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(img_a, img_b)
    diff_pixels = sum(1 for px in diff.getdata() if px != (0, 0, 0))
    total = img_a.size[0] * img_a.size[1]
    match_pct = round(100.0 * (1.0 - diff_pixels / max(total, 1)), 2)

    highlight = Image.new("RGB", img_a.size)
    for x in range(img_a.size[0]):
        for y in range(img_a.size[1]):
            if diff.getpixel((x, y)) != (0, 0, 0):
                highlight.putpixel((x, y), (255, 0, 0))
            else:
                highlight.putpixel((x, y), img_b.getpixel((x, y)))

    buf = io.BytesIO()
    highlight.save(buf, format="PNG")
    return match_pct, base64.b64encode(buf.getvalue()).decode("ascii")


def _accept_baseline(body: dict, settings: dict, pack_dir: str) -> dict:
    baseline_path = str(body.get("baseline_path", "") or "").strip()
    if not baseline_path:
        raise ValueError("missing required parameter: baseline_path")
    workspace_root = str(body.get("workspace_root", "") or "").strip()
    if not workspace_root:
        raise ValueError("missing required parameter: workspace_root")
    baseline_path = os.path.expanduser(baseline_path)
    if not os.path.isabs(baseline_path):
        baseline_path = os.path.join(os.path.expanduser(workspace_root), baseline_path)
    shot = _screenshot(body, settings, pack_dir)
    png = base64.b64decode(shot["png_b64"])
    os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
    with open(baseline_path, "wb") as fh:
        fh.write(png)
    return {"ok": True, "baseline_path": baseline_path, "bytes": len(png)}


def _pick_element(body: dict, settings: dict, pack_dir: str) -> dict:
    x = body.get("x")
    y = body.get("y")
    if x is None or y is None:
        raise ValueError("missing required parameters: x, y")
    page, context, owns = _get_page(body, settings)
    try:
        result = page.evaluate(
            """([px, py]) => {
              const el = document.elementFromPoint(px, py);
              if (!el) return null;
              const cs = window.getComputedStyle(el);
              const styles = {};
              ['color','background-color','font-size','display','width','height'].forEach(k => {
                styles[k] = cs.getPropertyValue(k);
              });
              let selector = el.tagName.toLowerCase();
              if (el.id) selector = '#' + el.id;
              else if (el.className) selector = el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\\s+/).join('.');
              return {
                selector,
                outer_html: el.outerHTML.slice(0, 4000),
                tag: el.tagName.toLowerCase(),
                computed_styles: styles,
              };
            }""",
            [float(x), float(y)],
        )
        if result is None:
            raise ValueError("no element at coordinates")
        return result
    finally:
        if owns and context is not None:
            context.close()
