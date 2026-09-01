"""Per-feature functional UI testing: exercise the product, not just inventory it.

A bounded agentic loop per feature: the model sees a digest of the page's
interactive elements and chooses each step (click, fill with demo values,
navigate, or conclude); the tester executes it in a real browser and reports
what happened. Destructive controls never enter the digest. Every step and
its observed result are journaled as observed evidence; each feature ends in
a verdict with an end-state screenshot.
"""

from __future__ import annotations

import contextlib
import json
import re
from typing import Protocol

from bokken.journal import Actor
from bokken.journal.schema import content_hash
from bokken.stages.base import FACILITATOR, structured
from bokken.stages.schemas import FeatureInventory, UIAction

TESTER_ACTOR = Actor(kind="agent", name="ui-tester", model="claude-fable-5")
MAX_FEATURES = 8
MAX_STEPS = 4
DESTRUCTIVE = re.compile(
    r"delete|remove|borrar|eliminar|logout|cerrar sesi|sign out|reset|wipe|drop|purge",
    re.IGNORECASE,
)


class FeatureTester(Protocol):
    def start(self, app_url: str) -> None: ...
    def goto(self, url: str) -> None: ...
    def digest(self) -> str: ...
    def act(self, action: UIAction) -> str: ...
    def screenshot(self) -> bytes | None: ...
    def close(self) -> None: ...


class TesterUnavailable(RuntimeError):
    pass


class PlaywrightFeatureTester:
    """Requires the optional `ui` dependency group."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self.page = None
        self.errors: list[str] = []
        self.app_url = ""

    def start(self, app_url: str) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise TesterUnavailable("playwright is not installed (uv sync --extra ui)") from exc
        self.app_url = app_url
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self.page = self._browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.on(
            "console",
            lambda m: self.errors.append(m.text[:160]) if m.type == "error" else None,
        )
        self.page.goto(app_url, wait_until="networkidle", timeout=30000)

    def goto(self, url: str) -> None:
        from urllib.parse import urljoin

        self.page.goto(urljoin(self.app_url, url), wait_until="networkidle", timeout=30000)

    def _elements(self):
        return self.page.eval_on_selector_all(
            "button, a[href], input:not([type=hidden]), select, textarea, "
            "[role=tab], [role=button]",
            """els => els.slice(0, 60).map((e, i) => ({
                i, tag: e.tagName.toLowerCase(),
                text: (e.textContent || e.getAttribute('placeholder')
                    || e.getAttribute('aria-label') || e.name || '').trim().slice(0, 60),
                type: e.getAttribute('type') || '', href: e.getAttribute('href') || ''
            }))""",
        )

    def digest(self) -> str:
        lines = [f"URL: {self.page.url}", f"Title: {self.page.title()}"]
        headings = self.page.eval_on_selector_all(
            "h1, h2, h3", "els => els.map(e => e.textContent.trim()).slice(0, 10)"
        )
        lines.append("Headings: " + ("; ".join(headings) or "(none)"))
        if self.errors:
            lines.append("Console errors so far: " + "; ".join(self.errors[-3:]))
        lines.append("Interactive elements (index · tag · text):")
        for el in self._elements():
            label = f"{el['text']} {el['href']}".strip()
            if DESTRUCTIVE.search(label):
                continue  # destructive controls never enter the digest
            lines.append(
                f"  [{el['i']}] {el['tag']}{'/' + el['type'] if el['type'] else ''} · {label[:80]}"
            )
        return "\n".join(lines)

    def act(self, action: UIAction) -> str:
        """Execute one step; return a short observed-result line."""
        before_url = self.page.url
        self.errors.clear()
        try:
            if action.action == "goto" and action.value:
                self.goto(action.value)
            elif action.target_index is not None:
                locator = self.page.locator(
                    "button, a[href], input:not([type=hidden]), select, textarea, "
                    "[role=tab], [role=button]"
                ).nth(action.target_index)
                if action.action == "fill":
                    locator.fill(action.value or "", timeout=4000)
                elif action.action == "press_enter":
                    locator.press("Enter", timeout=4000)
                else:
                    locator.click(timeout=4000)
            self.page.wait_for_timeout(700)
        except Exception as exc:
            return f"action failed: {str(exc)[:140]}"
        moved = f" (navigated to {self.page.url})" if self.page.url != before_url else ""
        errs = f" console errors: {'; '.join(self.errors[-2:])}" if self.errors else ""
        return f"ok{moved}{errs}"

    def screenshot(self) -> bytes | None:
        try:
            return self.page.screenshot(full_page=False)
        except Exception:
            return None

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()


def build_tester() -> FeatureTester:
    """Seam for tests: monkeypatch this to inject a fake tester."""
    return PlaywrightFeatureTester()


def _docs_excerpt(ctx) -> str:
    inputs = ctx.state.brief.get("inputs") or {}
    from pathlib import Path

    chunks = []
    for doc in (inputs.get("documents") or [])[:3]:
        path = Path(doc)
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore")[:4000])
    return "\n\n".join(chunks) or "(no documents declared)"


def run_feature_tests(ctx, router, *, app_url: str, routes: list[str]) -> list[dict]:
    """Exercise each inventoried feature; journal steps, verdicts, artifacts.

    Returns the per-feature results for the UI review prompt.
    """
    tester = build_tester()
    try:
        tester.start(app_url)
    except TesterUnavailable:
        return []
    try:
        inventory = structured(
            router,
            "research",
            "empathize/feature_inventory",
            FeatureInventory,
            stage="empathize",
            params={
                "docs": _docs_excerpt(ctx),
                "routes": ", ".join(routes) or "(none discovered)",
                "home": tester.digest(),
            },
        )
        if inventory is None:
            return []
        results: list[dict] = []
        ui_dir = ctx.store.session_dir / "artifacts" / "ui"
        ui_dir.mkdir(parents=True, exist_ok=True)
        for f_idx, feature in enumerate(inventory.features[:MAX_FEATURES], 1):
            if feature.entry_hint:
                with contextlib.suppress(Exception):
                    tester.goto(feature.entry_hint)
            steps: list[str] = []
            verdict, finding = "unclear", ""
            for _step in range(MAX_STEPS):
                # Fusion: mechanical stepping on the sidekick lane; the concluding
                # verdict escalates to the frontier below.
                action = structured(
                    router,
                    "sidekick",
                    "empathize/ui_action",
                    UIAction,
                    stage="empathize",
                    params={
                        "feature": feature.name,
                        "expectation": feature.expectation,
                        "log": "\n".join(steps) or "(no steps yet)",
                        "page": tester.digest(),
                    },
                )
                if action is None:
                    return results
                if action.action == "done":
                    confirm = structured(
                        router,
                        "research",
                        "empathize/ui_action",
                        UIAction,
                        stage="empathize",
                        params={
                            "feature": feature.name,
                            "expectation": feature.expectation,
                            "log": "\n".join(steps) or "(no steps yet)",
                            "page": tester.digest(),
                        },
                    )
                    final = confirm if confirm and confirm.action == "done" else action
                    verdict = final.verdict or action.verdict or "unclear"
                    finding = final.finding or action.finding
                    break
                observed = tester.act(action)
                steps.append(
                    f"{action.action} "
                    f"[{action.target_index if action.target_index is not None else action.value}]"
                    f" -> {observed}"
                )
            shot = tester.screenshot()
            shot_name = ""
            if shot:
                shot_name = f"feature_{f_idx:02d}.png"
                (ui_dir / shot_name).write_bytes(shot)
                ctx.store.append(
                    type="artifact.generated",
                    stage="empathize",
                    actor=TESTER_ACTOR,
                    payload={
                        "path": f"artifacts/ui/{shot_name}",
                        "kind": "ui_screenshot",
                        "content_hash": content_hash(shot),
                        "feature": feature.name,
                    },
                )
            record = {
                "feature": feature.name,
                "verdict": verdict,
                "steps": steps,
                "finding": finding,
                "screenshot": shot_name,
            }
            results.append(record)
            ctx.store.append(
                type="evidence.captured",
                stage="empathize",
                actor=TESTER_ACTOR,
                payload={
                    "content": (
                        f"Functional test - {feature.name}: {verdict}. "
                        + (f"{finding} " if finding else "")
                        + "Steps: "
                        + ("; ".join(steps) or "(entry state only)")
                    ),
                    "source": "ui_feature_test",
                    "confidence_class": "observed",
                },
            )
    finally:
        tester.close()

    if results:
        payload_json = json.dumps(results, indent=2) + "\n"
        md = ["# Functional feature tests (real browser)", ""]
        for r in results:
            md.append(f"## {r['feature']} - {r['verdict'].upper()}")
            if r["finding"]:
                md.append(r["finding"])
            md += [f"- {s}" for s in r["steps"]] + [""]
        content_md = "\n".join(md)
        for name, content in (
            ("ui_feature_tests.md", content_md),
            ("ui_feature_tests.json", payload_json),
        ):
            (ctx.store.session_dir / "artifacts" / "ui" / name).write_text(
                content, encoding="utf-8"
            )
            ctx.store.append(
                type="artifact.generated",
                stage="empathize",
                actor=FACILITATOR,
                payload={
                    "path": f"artifacts/ui/{name}",
                    "kind": "ui_feature_tests",
                    "content_hash": content_hash(content),
                },
            )
    return results
