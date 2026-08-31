"""Versioned prompt registry. Every rendered prompt is hashed into the ledger."""

from __future__ import annotations

import hashlib
from typing import Any

# prompt_id -> (version, template). Bump the version whenever a template changes;
# journals keep the version each run actually used.
PROMPTS: dict[str, tuple[str, str]] = {
    "empathize/interview_program": (
        "v1",
        "You are designing a user-research interview program for the brief below.\n"
        "Brief: {brief}\n"
        "Write 2-4 open, non-leading interview questions per target segment. Ask about "
        "concrete past behavior, not hypotheticals.\n",
    ),
    "empathize/followup": (
        "v1",
        "Interview context. Question asked: {question}\nAnswer given: {answer}\n"
        "If the answer mentions a concrete difficulty or recent incident worth laddering "
        "into, produce one specific follow-up question about that instance (e.g. 'tell me "
        "about the last time...'). If not, produce no follow-up.\n",
    ),
    "empathize/persona_turn": (
        "v1",
        "You are the persona described below, answering a research interview question.\n"
        "Persona: {persona}\n"
        "Corpus (the only source you may state facts from, cite line spans):\n{context}\n"
        "Question: {question}\n"
        "Answer only from the corpus with citations; if the corpus cannot support a "
        "factual answer, abstain and say what is missing. Personal preferences may come "
        "from the persona profile and must be marked as such.\n",
    ),
    "define/cluster": (
        "v1",
        "Cluster the evidence below into insights for the problem space {problem_space}.\n"
        "Evidence items (id: content):\n{evidence}\n"
        "Each insight must list the evidence ids that support it. Do not invent evidence.\n",
    ),
    "define/candidates": (
        "v1",
        "From these insights, draft point-of-view problem-statement candidates.\n"
        "Insights (id: statement):\n{insights}\n"
        "For each candidate: the statement, the insight ids it rests on, an evidence-"
        "coverage score 0-1, whether it embeds a solution (solution_shaped), and if so a "
        "'How might we' reframe.\n",
    ),
    "define/select": (
        "v1",
        "Select the strongest problem statement.\nCandidates:\n{candidates}\n"
        "Pick one winner by evidence coverage and clarity; for every loser state briefly "
        "why it lost.\n",
    ),
    "ideate/diverge": (
        "v1",
        "Divergent ideation for: {problem_statement}\n"
        "You contribute as: {participant}\n"
        "Already on the table (do not repeat): {existing}\n"
        "Produce {quota} distinct options. Private reasoning goes in private_thought; the "
        "public contribution is the option summary.\n",
    ),
    "ideate/novelty": (
        "v1",
        "Existing option clusters:\n{clusters}\nNew option: {option}\n"
        "Classify the new option against the clusters: novel_cluster, variation, or "
        "duplicate.\n",
    ),
    "ideate/provoke": (
        "v1",
        "Ideation is stalling on: {problem_statement}\n"
        "Inject one provocation (inversion, exaggeration, or forced analogy) to open a "
        "new direction.\n",
    ),
    "ideate/converge": (
        "v1",
        "Convergence. Problem: {problem_statement}\nCriteria (frozen): {criteria}\n"
        "Options (id: summary):\n{options}\n"
        "As {participant}, score each option per criterion 0-5 and state a position.\n",
    ),
    "ideate/skeptic_challenge": (
        "v1",
        "You are the skeptic. Before convergence closes on:\n{options}\n"
        "State the strongest objection on record: what claim is weakest, what would break "
        "first. Depersonalized - challenge claims, not people.\n",
    ),
    "prototype/assumptions": (
        "v1",
        "The selected concept: {concept}\nProblem statement: {problem_statement}\n"
        "Enumerate the assumptions this concept rests on. Classify each impact and "
        "uncertainty as low/medium/high.\n",
    ),
    "prototype/fidelity": (
        "v1",
        "Assumption register (riskiest first):\n{register}\n"
        "Choose the cheapest artifact set that tests the riskiest assumption. Available "
        "kinds: concept_one_pager, landing_copy, storyboard, demo_script. Map every "
        "chosen artifact to the assumption ids it exercises and give the rationale.\n",
    ),
    "prototype/artifact": (
        "v1",
        "Generate the artifact.\nKind: {kind}\nConcept: {concept}\n"
        "Problem statement: {problem_statement}\nAssumptions it must exercise: "
        "{assumptions}\nWrite complete, plain markdown. No emojis.\n",
    ),
    "test/evaluate": (
        "v1",
        "You are the persona described below, evaluating a prototype.\n"
        "Persona: {persona}\nArtifact ({kind}):\n{artifact}\n"
        "Assumption under test: {assumption}\n"
        "React honestly from the persona's perspective: does your reaction support or "
        "contradict the assumption, or leave it untested? Explain briefly.\n",
    ),
    "test/recommend": (
        "v1",
        "Assumption register with scores:\n{register}\n"
        "Recommend kill, iterate, or proceed, with a confidence statement and the main "
        "driver. If any contradicted assumption undermines an earlier insight or the "
        "problem statement, say which.\n",
    ),
    "handoff/specify": (
        "v1",
        "Turn a validated concept into build-ready OpenSpec specifications for its MVP.\n"
        "Problem statement: {problem_statement}\n"
        "Validated concept: {concept}\n"
        "Supported assumptions (index. statement):\n{supported}\n"
        "Untested assumptions (index. statement) - these need real-world validation, do "
        "not treat them as facts:\n{untested}\n"
        "Contradicted assumptions - the MVP must NOT rely on these:\n{contradicted}\n"
        "Prototype artifacts available as reference: {artifacts}\n"
        "Produce a spec package: 1-3 kebab-case capabilities, each with a purpose and "
        "testable requirements (normative SHALL statements) with WHEN/THEN scenarios. "
        "Reference the assumption indexes each requirement rests on. Keep the MVP light: "
        "specify only what the validated concept needs.\n",
    ),
}


class UnknownPromptError(Exception):
    pass


def render_prompt(prompt_id: str, **params: Any) -> tuple[str, str, str]:
    """Return (version, rendered_text, content_hash) for a registered prompt."""
    if prompt_id not in PROMPTS:
        raise UnknownPromptError(prompt_id)
    version, template = PROMPTS[prompt_id]
    rendered = template.format(**params)
    content_hash = hashlib.sha256(rendered.encode()).hexdigest()
    return version, rendered, content_hash
