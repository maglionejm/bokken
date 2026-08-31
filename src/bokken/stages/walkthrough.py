"""Functional UI walkthrough: observed facts about a running app, plus a review.

Walkthrough facts are `observed` evidence - a real product was really
exercised - unlike persona utterances. Bounded by design: the entry page plus
a handful of same-origin nav targets, no form submission, no auth flows.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol

from bokken.journal import Actor
from bokken.stages.base import FACILITATOR, structured
from bokken.stages.schemas import UIReview

WALKER_ACTOR = Actor(kind="system", name="ui-walker")
MAX_PAGES = 6


@dataclass(frozen=True)
class PageObservation:
    url: str
    title: str
    headings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)  # buttons/links a user would act on
    forms: int = 0
    console_errors: list[str] = field(default_factory=list)
    load_ms: int = 0
    screenshot_png: bytes | None = None

    def facts(self) -> str:
        lines = [
            f"Screen: {self.title or '(untitled)'} ({self.url})",
            f"Loaded in {self.load_ms} ms. Headings: {'; '.join(self.headings) or '(none)'}.",
            f"Primary actions visible: {'; '.join(self.actions) or '(none)'}. Forms: {self.forms}.",
        ]
        if self.console_errors:
            lines.append(f"Console errors: {'; '.join(self.console_errors)}")
        else:
            lines.append("Console errors: none.")
        return "\n".join(lines)


class Walker(Protocol):
    def visit(self, app_url: str, *, max_pages: int) -> list[PageObservation]: ...


class WalkerUnavailable(RuntimeError):
    pass


class PlaywrightWalker:
    """Requires the optional `ui` dependency group (playwright + installed browser)."""

    def visit(self, app_url: str, *, max_pages: int = MAX_PAGES) -> list[PageObservation]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise WalkerUnavailable("playwright is not installed (uv sync --extra ui)") from exc

        import time
        from urllib.parse import urljoin, urlparse

        observations: list[PageObservation] = []
        origin = urlparse(app_url).netloc
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)
            queue, seen = [app_url], set()
            while queue and len(observations) < max_pages:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                errors.clear()
                started = time.monotonic()
                page.goto(url, wait_until="networkidle", timeout=30000)
                load_ms = int((time.monotonic() - started) * 1000)
                observations.append(
                    PageObservation(
                        url=url,
                        title=page.title(),
                        headings=page.eval_on_selector_all(
                            "h1, h2", "els => els.map(e => e.textContent.trim()).slice(0, 8)"
                        ),
                        actions=page.eval_on_selector_all(
                            "button, a[role=button], [type=submit]",
                            "els => els.map(e => e.textContent.trim())"
                            ".filter(Boolean).slice(0, 12)",
                        ),
                        forms=page.locator("form").count(),
                        console_errors=list(errors),
                        load_ms=load_ms,
                        screenshot_png=page.screenshot(full_page=False),
                    )
                )
                for href in page.eval_on_selector_all(
                    "nav a[href], header a[href]", "els => els.map(e => e.getAttribute('href'))"
                ):
                    target = urljoin(url, href)
                    if urlparse(target).netloc == origin and target not in seen:
                        queue.append(target)
            browser.close()
        return observations


def build_walker() -> Walker:
    """Seam for tests: monkeypatch this to inject a fake walker."""
    return PlaywrightWalker()


def run_walkthrough(ctx, router) -> None:
    """Observe the running app (if any), journal facts + screenshots + review."""
    for event in ctx.store.events():
        if event.type == "artifact.generated" and event.payload.get("kind") == "ui_review":
            return  # already walked; loop-backs re-interview, not re-crawl
        if event.type == "evidence.abstained" and str(event.payload.get("question", "")).startswith(
            "Functional UI walkthrough"
        ):
            return
    app_url = (ctx.state.brief.get("inputs") or {}).get("app_url")
    if not app_url:
        ctx.store.append(
            type="evidence.abstained",
            stage="empathize",
            actor=WALKER_ACTOR,
            payload={
                "question": "Functional UI walkthrough of the running product",
                "gap": "no app_url declared in the brief inputs; a documented UI test "
                "needs a reachable instance",
            },
        )
        return
    try:
        observations = build_walker().visit(app_url, max_pages=MAX_PAGES)
    except WalkerUnavailable as exc:
        ctx.store.append(
            type="evidence.abstained",
            stage="empathize",
            actor=WALKER_ACTOR,
            payload={
                "question": "Functional UI walkthrough of the running product",
                "gap": f"browser runtime unavailable: {exc}",
            },
        )
        return

    ui_dir = ctx.store.session_dir / "artifacts" / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    facts_blocks: list[str] = []
    for i, obs in enumerate(observations, 1):
        ctx.store.append(
            type="evidence.captured",
            stage="empathize",
            actor=WALKER_ACTOR,
            payload={
                "content": obs.facts(),
                "source": "ui_walkthrough",
                "confidence_class": "observed",
                "url": obs.url,
            },
        )
        facts_blocks.append(f"[screen {i}]\n{obs.facts()}")
        if obs.screenshot_png:
            shot = ui_dir / f"screen_{i:02d}.png"
            shot.write_bytes(obs.screenshot_png)
            ctx.store.append(
                type="artifact.generated",
                stage="empathize",
                actor=WALKER_ACTOR,
                payload={
                    "path": f"artifacts/ui/screen_{i:02d}.png",
                    "kind": "ui_screenshot",
                    "content_hash": hashlib.sha256(obs.screenshot_png).hexdigest(),
                    "url": obs.url,
                },
            )

    review = structured(
        router,
        "research",
        "empathize/ui_review",
        UIReview,
        stage="empathize",
        params={
            "brief": str(ctx.state.brief.get("problem_space", "")),
            "observations": "\n\n".join(facts_blocks),
        },
    )
    if review is None:
        return
    content = review.markdown if review.markdown.endswith("\n") else review.markdown + "\n"
    path = ui_dir / "ui_review.md"
    path.write_text(content, encoding="utf-8")
    ctx.store.append(
        type="artifact.generated",
        stage="empathize",
        actor=FACILITATOR,
        payload={
            "path": "artifacts/ui/ui_review.md",
            "kind": "ui_review",
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        },
    )
