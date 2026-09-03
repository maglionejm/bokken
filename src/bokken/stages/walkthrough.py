"""Functional UI walkthrough: observed facts about a running app, plus a review.

Walkthrough facts are `observed` evidence - a real product was really
exercised - unlike persona utterances. Discovery combines three methods: the
live DOM (every same-origin link), the code's own route definitions, and
template links; static HTML analysis (BeautifulSoup) adds structure and
accessibility facts. Bounded by design: no form submission, no auth flows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from bokken.journal import Actor
from bokken.journal.schema import content_hash
from bokken.stages.base import structured
from bokken.stages.schemas import UIReview

WALKER_ACTOR = Actor(kind="system", name="ui-walker")
MAX_PAGES = 12

# Parameterless GET routes in FastAPI/Starlette-style code.
ROUTE_DEF = re.compile(r"""@\w+\.get\(\s*["'](/[^"'{}]*)["']""")
TEMPLATE_HREF = re.compile(r"""href=["'](/[^"'#?{}]+)["']""")
_SKIP_SUFFIXES = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".svg",
    ".ico",
    ".json",
    ".xml",
    ".txt",
    ".pdf",
    ".ics",
    ".yaml",
    ".yml",
    ".csv",
)
# API/data/auth endpoints are not screens a user sees.
NON_UI_PATH = re.compile(
    r"^/(api|health|healthz|metrics|static|assets)(/|$)|callback|webhook|logout"
)


@dataclass(frozen=True)
class PageObservation:
    url: str
    title: str
    headings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)  # buttons/links a user would act on
    forms: int = 0
    unlabeled_inputs: int = 0
    images_without_alt: int = 0
    console_errors: list[str] = field(default_factory=list)
    load_ms: int = 0
    screenshot_png: bytes | None = None
    screenshot_mobile_png: bytes | None = None

    def facts(self) -> str:
        lines = [
            f"Screen: {self.title or '(untitled)'} ({self.url})",
            f"Loaded in {self.load_ms} ms. Headings: {'; '.join(self.headings) or '(none)'}.",
            f"Primary actions visible: {'; '.join(self.actions) or '(none)'}. Forms: {self.forms}.",
            f"Accessibility: {self.unlabeled_inputs} input(s) without a label, "
            f"{self.images_without_alt} image(s) without alt text.",
        ]
        if self.console_errors:
            lines.append(f"Console errors: {'; '.join(self.console_errors)}")
        else:
            lines.append("Console errors: none.")
        return "\n".join(lines)


class Walker(Protocol):
    def visit(
        self, app_url: str, *, max_pages: int, seed_paths: list[str] | None = None
    ) -> list[PageObservation]: ...


class WalkerUnavailable(RuntimeError):
    pass


def routes_from_repo(repo: str | None) -> list[str]:
    """Parameterless GET paths and template hrefs found in the declared repo."""
    if not repo:
        return []
    root = Path(repo)
    if not root.exists():
        return []
    # A subdirectory input still deserves full route discovery: scan from the VCS root.
    for parent in (root, *root.parents):
        if (parent / ".git").exists():
            root = parent
            break
    found: set[str] = set()
    for pattern, regex in (("*.py", ROUTE_DEF), ("*.html", TEMPLATE_HREF)):
        for file in list(root.rglob(pattern))[:400]:
            try:
                for path in regex.findall(file.read_text(encoding="utf-8", errors="ignore")):
                    if not path.lower().endswith(_SKIP_SUFFIXES) and "/static" not in path:
                        found.add(path)
            except OSError:
                continue
    return sorted(found)


def _static_facts(html: str) -> tuple[int, int]:
    """(unlabeled inputs, images without alt) via static analysis."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return 0, 0
    soup = BeautifulSoup(html, "html.parser")
    labeled = {label.get("for") for label in soup.find_all("label")}
    unlabeled = sum(
        1
        for node in soup.find_all("input")
        if node.get("type") not in ("hidden", "submit")
        and node.get("id") not in labeled
        and not node.get("aria-label")
    )
    no_alt = sum(1 for img in soup.find_all("img") if not img.get("alt"))
    return unlabeled, no_alt


class PlaywrightWalker:
    """Requires the optional `ui` dependency group (playwright + installed browser)."""

    def visit(
        self, app_url: str, *, max_pages: int = MAX_PAGES, seed_paths: list[str] | None = None
    ) -> list[PageObservation]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise WalkerUnavailable("playwright is not installed (uv sync --extra ui)") from exc

        import time
        from urllib.parse import urljoin, urlparse

        observations: list[PageObservation] = []
        base = urlparse(app_url)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)
            queue = [app_url] + [urljoin(app_url, p) for p in (seed_paths or [])]
            seen_paths: set[str] = set()
            while queue and len(observations) < max_pages:
                url = queue.pop(0)
                parsed = urlparse(url)
                path = parsed.path.rstrip("/") or "/"
                if parsed.netloc != base.netloc or path in seen_paths:
                    continue
                if path.lower().endswith(_SKIP_SUFFIXES) or NON_UI_PATH.search(path):
                    continue
                seen_paths.add(path)
                errors.clear()
                started = time.monotonic()
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception:
                    continue
                load_ms = int((time.monotonic() - started) * 1000)
                html = page.content()
                unlabeled, no_alt = _static_facts(html)
                mobile_png = None
                try:
                    mobile.goto(url, wait_until="networkidle", timeout=30000)
                    mobile_png = mobile.screenshot(full_page=False)
                except Exception:
                    pass
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
                        unlabeled_inputs=unlabeled,
                        images_without_alt=no_alt,
                        console_errors=list(errors),
                        load_ms=load_ms,
                        screenshot_png=page.screenshot(full_page=False),
                        screenshot_mobile_png=mobile_png,
                    )
                )
                # SPA support: activate tab-like controls, each state is an observation
                tab_selector = (
                    "[role=tab], nav button, [class*=tab] button, button[data-tab], "
                    "[data-view], .tabs button"
                )
                labels = page.eval_on_selector_all(
                    tab_selector, "els => els.map(e => e.textContent.trim()).filter(Boolean)"
                )
                for label in list(dict.fromkeys(labels))[:8]:
                    if len(observations) >= max_pages:
                        break
                    try:
                        page.locator(tab_selector, has_text=label).first.click(timeout=3000)
                        page.wait_for_timeout(600)
                    except Exception:
                        continue
                    state_html = page.content()
                    if state_html == html:
                        continue
                    unl, noa = _static_facts(state_html)
                    observations.append(
                        PageObservation(
                            url=f"{url}#tab:{label[:40]}",
                            title=f"{page.title()} - {label}",
                            headings=page.eval_on_selector_all(
                                "h1, h2",
                                "els => els.map(e => e.textContent.trim()).slice(0, 8)",
                            ),
                            actions=page.eval_on_selector_all(
                                "button, a[role=button], [type=submit]",
                                "els => els.map(e => e.textContent.trim())"
                                ".filter(Boolean).slice(0, 12)",
                            ),
                            forms=page.locator("form").count(),
                            unlabeled_inputs=unl,
                            images_without_alt=noa,
                            console_errors=list(errors),
                            load_ms=0,
                            screenshot_png=page.screenshot(full_page=False),
                        )
                    )
                # live DOM discovery: every same-origin anchor, not just nav
                for href in page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.getAttribute('href'))"
                ):
                    target = urljoin(url, href.split("#")[0].split("?")[0])
                    if urlparse(target).netloc == base.netloc:
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
    inputs = ctx.state.brief.get("inputs") or {}
    app_url = inputs.get("app_url")
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
    max_pages = ctx.state.config.get("walkthrough", {}).get("max_pages", MAX_PAGES)
    seed_paths = routes_from_repo(inputs.get("repo"))
    try:
        observations = build_walker().visit(app_url, max_pages=max_pages, seed_paths=seed_paths)
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
        for suffix, blob in (("", obs.screenshot_png), ("_mobile", obs.screenshot_mobile_png)):
            if not blob:
                continue
            shot = ui_dir / f"screen_{i:02d}{suffix}.png"
            shot.write_bytes(blob)
            ctx.store.append(
                type="artifact.generated",
                stage="empathize",
                actor=WALKER_ACTOR,
                payload={
                    "path": f"artifacts/ui/{shot.name}",
                    "kind": "ui_screenshot",
                    "content_hash": content_hash(blob),
                    "url": obs.url,
                    "viewport": "mobile" if suffix else "desktop",
                },
            )

    from bokken.stages.ui_tests import run_feature_tests

    feature_results = run_feature_tests(ctx, router, app_url=app_url, routes=seed_paths)
    feature_lines = (
        "\n".join(
            f"- {r['feature']}: {r['verdict']}"
            + (f" - {r['finding']}" if r["finding"] else "")
            + (f" (steps: {'; '.join(r['steps'])})" if r["steps"] else "")
            for r in feature_results
        )
        or "(no functional feature tests ran)"
    )

    coverage = (
        f"Visited {len(observations)} screen(s) out of a discovered candidate set of "
        f"{len(seed_paths) or 'unknown (no repo routes)'} code routes plus live links "
        f"(page budget {MAX_PAGES})."
    )
    review = structured(
        router,
        "research",
        "empathize/ui_review",
        UIReview,
        stage="empathize",
        params={
            "brief": str(ctx.state.brief.get("problem_space", "")),
            "coverage": coverage,
            "observations": "\n\n".join(facts_blocks),
            "feature_results": feature_lines,
        },
    )
    if review is None:
        return
    markdown = review.data.markdown
    content = markdown if markdown.endswith("\n") else markdown + "\n"
    path = ui_dir / "ui_review.md"
    path.write_text(content, encoding="utf-8")
    ctx.store.append(
        type="artifact.generated",
        stage="empathize",
        actor=review.actor("facilitator"),  # the reviewing call wrote this
        payload={
            "path": "artifacts/ui/ui_review.md",
            "kind": "ui_review",
            "content_hash": content_hash(content),
        },
    )
