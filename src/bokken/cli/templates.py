"""Brief templates for `bokken init`: proven starting points, not blank pages."""

from __future__ import annotations

TODO = "TODO: replace with your product's reality"

TEMPLATES: dict[str, dict] = {
    "saas-retention": {
        "problem_space": "Our SaaS product ({product}) is losing established "
        "customers faster than we acquire new ones. The space to explore: what "
        "between the promise that sold them and their day-to-day reality is "
        "driving the churn.",
        "target_segments": ["power users on annual plans", "admins who bought for a team"],
        "success_criteria": ["logo churn flattens within two quarters",
                             "expansion revenue from retained accounts grows"],
        "constraints": ["current pricing model stays", "no new headcount"],
        "risk_tolerance": "medium",
    },
    "consumer-app": {
        "problem_space": "Our consumer app ({product}) gets installs but not "
        "habits: day-30 retention is a fraction of day-1. The space to "
        "explore: which moment of real life the app should own, and what "
        "breaks between intent and routine.",
        "target_segments": ["new users in their first week", "lapsed users who return occasionally"],
        "success_criteria": ["day-30 retention improves measurably",
                             "a repeat usage loop is identified and instrumented"],
        "constraints": ["no dark patterns", "works within current app-store review cycle"],
        "risk_tolerance": "medium",
    },
    "internal-tool": {
        "problem_space": "An internal tool ({product}) that a team is obliged "
        "to use but routes around: shadow spreadsheets, chat workarounds, "
        "stale data. The space to explore: which job the official tool fails "
        "at that the workarounds quietly serve.",
        "target_segments": ["daily operators of the tool", "managers consuming its reports"],
        "success_criteria": ["workaround usage drops", "data freshness in the tool improves"],
        "constraints": ["existing system of record stays", "no procurement of new vendors"],
        "risk_tolerance": "low",
    },
}


def build_brief(template: str, product: str | None = None) -> dict:
    base = TEMPLATES[template]
    name = product or TODO
    return {
        "problem_space": base["problem_space"].format(product=name),
        "target_segments": list(base["target_segments"]),
        "success_criteria": list(base["success_criteria"]),
        "constraints": list(base["constraints"]),
        "risk_tolerance": base["risk_tolerance"],
        "inputs": {},
    }
