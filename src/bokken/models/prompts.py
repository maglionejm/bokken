"""Versioned prompt registry. Every rendered prompt is hashed into the ledger."""

from __future__ import annotations

import hashlib
from typing import Any

# Prepended to every reasoning prompt. The founder reads these outputs raw:
# they must stand alone, teach as they go, and always point forward.
QUALITY_CONTRACT = (
    "Output contract (non-negotiable): you are writing for the founder of this "
    "product, who will read your output verbatim. Be constructive - every "
    "criticism comes with what to do about it. Be self-explanatory - expand "
    "every framework term and score the first time you use it; no internal "
    "jargon. Be quantitative wherever the material allows - cite counts, "
    "scores, euros, percentages, and name their source. Be specific to THIS "
    "product and corpus, never generic.\n\n"
)

# prompt_id -> (version, template). Bump the version whenever a template changes;
# journals keep the version each run actually used.
PROMPTS: dict[str, tuple[str, str]] = {
    "empathize/interview_program": (
        "v3",
        QUALITY_CONTRACT
        + "You are designing a research program for the brief below. The interviewees are "
        "personas who can only state facts found in the session's evidence corpus - they "
        "abstain on anything it cannot support.\n"
        "Brief: {brief}\n"
        "Evidence corpus available: {inputs_available}\n"
        "Write 2-4 questions per target segment, calibrated to that corpus:\n"
        "- If the corpus contains interview/discussion material, ask about concrete past "
        "behavior (laddering into specific incidents).\n"
        "- If the corpus is mostly product code, docs, or metrics, ask questions those "
        "sources CAN answer (what the product does at key moments, what its docs assume "
        "about users, what the numbers show) - phrased from the persona's perspective.\n"
        "- Include at most one behavioral question per segment that the corpus likely "
        "cannot answer; its abstention becomes explicit research debt for real users.\n",
    ),
    "empathize/followup": (
        "v2",
        "Interview context. Question asked: {question}\nAnswer given: {answer}\n"
        "If the answer mentions a concrete difficulty or recent incident worth laddering "
        "into, produce one specific follow-up question about that instance (e.g. 'tell me "
        "about the last time...'). If not, produce no follow-up.\n",
    ),
    "empathize/persona_turn": (
        "v2",
        "You are the persona described below, answering a research interview question.\n"
        "Persona: {persona}\n"
        "Corpus (the only source you may state facts from, cite line spans):\n{context}\n"
        "Question: {question}\n"
        "Answer only from the corpus with citations; quote concrete numbers, feature "
        "names, and file facts when the corpus has them. If the corpus cannot support a "
        "factual answer, abstain and say precisely what research with real users would "
        "close the gap. Personal preferences may come from the persona profile and must "
        "be marked as such.\n",
    ),
    "empathize/outcomes": (
        "v1",
        QUALITY_CONTRACT
        + "From the interview evidence below, derive the desired-outcome statements "
        "(Jobs-to-be-Done style) for the job the target segments are trying to get done.\n"
        "Brief: {brief}\n"
        "Evidence items (id: content):\n{evidence}\n"
        "Write 5-10 outcome statements in Ulwick form ('Minimize the time it takes "
        "to...', 'Increase the likelihood that...'), each naming the job step it belongs "
        "to and the evidence ids that ground it. Outcomes must be solution-free and "
        "measurable. Do not invent evidence.\n",
    ),
    "empathize/outcome_scores": (
        "v1",
        "You are the persona described below.\n"
        "Persona: {persona}\n"
        "Desired outcomes (index. statement):\n{outcomes}\n"
        "Score EVERY outcome for Importance (1-10: how much achieving it matters to you) "
        "and Satisfaction (1-10: how well your current options - including the product "
        "as described in the evidence - already serve it). Stay in character; ground "
        "satisfaction in what the evidence says the product does today. Give a one-line "
        "reason whenever you score Importance >= 8 or Satisfaction <= 3.\n",
    ),
    "empathize/feature_inventory": (
        "v1",
        QUALITY_CONTRACT
        + "Enumerate the distinct user-facing functionalities of this product so each "
        "can be functionally tested in a browser.\n"
        "Product documentation excerpt:\n{docs}\n"
        "Routes discovered in the code: {routes}\n"
        "Home page digest:\n{home}\n"
        "List up to 8 features. For each: a short name, an entry hint (path or the "
        "visible control to reach it), and the expectation - what a working version "
        "observably does. Only features reachable without authentication or destructive "
        "actions.\n",
    ),
    "empathize/ui_action": (
        "v1",
        "You are functionally testing one feature of a running product in a real "
        "browser.\nFeature: {feature}\nExpectation: {expectation}\n"
        "Steps so far:\n{log}\n"
        "Current page digest:\n{page}\n"
        "Choose exactly one next step: click an indexed element, fill an indexed field "
        "(use plausible Spanish demo values), press_enter on it, goto a path, or - if "
        "you have seen enough - done with a verdict (works: the expectation observably "
        "holds; broken: it observably fails or errors; unclear: not judgeable from the "
        "outside) and a one-line finding for the founder. Never touch destructive "
        "controls. Prefer concluding once the expectation is settled.\n",
    ),
    "empathize/ui_review": (
        "v3",
        QUALITY_CONTRACT
        + "You just walked through the running product as a first-time user. Below are "
        "the observed facts per screen (real observations, not simulations).\n"
        "Problem space: {brief}\n"
        "Coverage: {coverage}\n"
        "Observations:\n{observations}\n"
        "Per-feature functional test results:\n{feature_results}\n"
        "Open by stating the coverage so the reader knows what this review does and "
        "does not cover.\n"
        "Write a functional UI review in markdown for the founder: (1) what the "
        "product does well at first contact - be specific and generous where earned; "
        "(2) findings, each as 'screen -> observed fact -> why it matters -> concrete "
        "suggestion', quantified where the observations allow (load times, error "
        "counts, number of actions on screen); (3) the three highest-leverage "
        "improvements, ordered by expected impact. Ground every claim in an observed "
        "fact; never invent screens or numbers.\n",
    ),
    "define/cluster": (
        "v2",
        QUALITY_CONTRACT
        + "Cluster the evidence below into insights for the problem space {problem_space}.\n"
        "Evidence items (id: content):\n{evidence}\n"
        "Opportunity ranking (Ulwick: Opportunity = Importance + max(Importance - "
        "Satisfaction, 0); >=15 severely underserved, 12-15 underserved, <10 served):\n"
        "{opportunities}\n"
        "Each insight must list the evidence ids that support it, name the affected "
        "segment, and tie itself to the underserved outcomes with their scores. Do not "
        "invent evidence.\n",
    ),
    "define/candidates": (
        "v2",
        QUALITY_CONTRACT
        + "From these insights, draft point-of-view problem-statement candidates.\n"
        "Insights (id: statement):\n{insights}\n"
        "Opportunity ranking on file:\n{opportunities}\n"
        "For each candidate: the statement (naming the segment, the underserved outcomes "
        "and their opportunity scores, and the size of the gap in numbers where the "
        "evidence provides them), the insight ids it rests on, an evidence-coverage "
        "score 0-1, whether it embeds a solution (solution_shaped), and if so a 'How "
        "might we' reframe.\n",
    ),
    "define/select": (
        "v2",
        QUALITY_CONTRACT + "Select the strongest problem statement.\nCandidates:\n{candidates}\n"
        "Pick one winner by evidence coverage, opportunity coverage (does it address the "
        "highest-opportunity outcomes?), and clarity; for every loser state briefly and "
        "constructively why it lost.\n",
    ),
    "ideate/diverge": (
        "v2",
        QUALITY_CONTRACT + "Divergent ideation for: {problem_statement}\n"
        "Desired outcomes on file (index. statement - opportunity score):\n{outcomes}\n"
        "You contribute as: {participant}\n"
        "Already on the table (do not repeat): {existing}\n"
        "Produce {quota} distinct options. Every option summary must be specific enough "
        "to build from (what it does, for whom) and end by naming the outcome(s) it "
        "serves, e.g. '[serves: O2, O5]'. Private reasoning goes in private_thought; the "
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
        "v2",
        QUALITY_CONTRACT
        + "Convergence vote. Problem: {problem_statement}\nCriteria (frozen): {criteria}\n"
        "Options (id: summary):\n{options}\n"
        "You vote as {participant}.\n{lens}\n"
        "Score each option per criterion 0-5 and state a position that a founder can "
        "act on: name the strongest option and the concrete risk of the weakest.\n",
    ),
    "ideate/skeptic_challenge": (
        "v2",
        QUALITY_CONTRACT + "You are the skeptic. Before convergence closes on:\n{options}\n"
        "State the strongest objection on record: which claim is weakest, what evidence "
        "it lacks (cite what the record does and does not contain), and what would break "
        "first in practice. End with the cheapest test that would settle the objection. "
        "Depersonalized - challenge claims, not people.\n",
    ),
    "research/deep": (
        "v1",
        QUALITY_CONTRACT
        + "The team has selected a concept and you must research it on the live web - "
        "deeply, with sources.\n"
        "Problem statement: {problem_statement}\nSelected concept: {concept}\n"
        "Investigate: (1) competitors and prior art - who already does this or part of "
        "it, and how much it overlaps; (2) quantified market signals - sizes, adoption "
        "rates, prices, growth, each with its source; (3) regulatory or compliance "
        "constraints; (4) pricing benchmarks for comparable offerings; (5) risks to "
        "differentiation; (6) the open questions the web cannot settle. Cite the URL "
        "for every factual claim. Write plain structured text with those six headings.\n",
    ),
    "research/structure": (
        "v1",
        "Convert the research notes below into the structured record exactly. Keep "
        "every source URL attached to its claim; do not invent or drop findings.\n"
        "Notes:\n{notes}\n",
    ),
    "prototype/assumptions": (
        "v3",
        QUALITY_CONTRACT
        + "The selected concept: {concept}\nProblem statement: {problem_statement}\n"
        "Concept research on file (competitors, signals, risks - cite it):\n{research}\n"
        "Enumerate the assumptions this concept rests on - demand, behavior change, "
        "willingness to act, technical, and viability assumptions. Classify each impact "
        "and uncertainty as low/medium/high and phrase each so a cheap test could score "
        "it supported or contradicted.\n",
    ),
    "prototype/fidelity": (
        "v2",
        QUALITY_CONTRACT + "Assumption register (riskiest first):\n{register}\n"
        "Choose the cheapest artifact set that tests the riskiest assumption. Available "
        "kinds: concept_one_pager, landing_copy, storyboard, demo_script. Map every "
        "chosen artifact to the assumption ids it exercises and explain the rationale "
        "so the founder understands why cheaper beats higher fidelity here.\n",
    ),
    "prototype/artifact": (
        "v2",
        QUALITY_CONTRACT + "Generate the artifact.\nKind: {kind}\nConcept: {concept}\n"
        "Problem statement: {problem_statement}\nAssumptions it must exercise: "
        "{assumptions}\n"
        "If the kind is concept_one_pager, open with a Hill - three lines: WHO (the "
        "specific user), WHAT (what they can now do), WOW (the measurable differentiator) "
        "- followed by a Lean-UX hypothesis: 'We believe [outcome] for [segment], "
        "measured by [signal]'. For every kind: write complete, plain markdown a founder "
        "could hand to a designer today. Use the product's own vocabulary and real "
        "numbers from the record. No emojis.\n",
    ),
    "test/evaluate": (
        "v2",
        "You are the persona described below, evaluating a prototype.\n"
        "Persona: {persona}\nArtifact ({kind}):\n{artifact}\n"
        "Assumption under test: {assumption}\n"
        "React honestly from the persona's perspective to THIS artifact - quote the "
        "parts that trigger your reaction. Does your reaction support or contradict the "
        "assumption, or leave it untested? Be candid about problems and constructive "
        "about what would change your mind.\n",
    ),
    "test/recommend": (
        "v2",
        QUALITY_CONTRACT + "Assumption register with scores:\n{register}\n"
        "Recommend kill, iterate, or proceed. Quantify the register in your confidence "
        "statement (how many supported / contradicted / untested, and which contradiction "
        "strikes which insight or outcome). Whatever the verdict, end constructively: "
        "the single most valuable next step for the founder - on kill, name what was "
        "learned and the cheapest pivot worth exploring. If any contradicted assumption "
        "undermines an earlier insight or the problem statement, say which.\n",
    ),
    "handoff/specify": (
        "v3",
        QUALITY_CONTRACT
        + "Turn a validated concept into build-ready OpenSpec specifications for its MVP.\n"
        "Problem statement: {problem_statement}\n"
        "Validated concept: {concept}\n"
        "Supported assumptions (index. statement):\n{supported}\n"
        "Untested assumptions (index. statement) - these need real-world validation, do "
        "not treat them as facts:\n{untested}\n"
        "Contradicted assumptions - the MVP must NOT rely on these:\n{contradicted}\n"
        "Prototype artifacts available as reference: {artifacts}\n"
        "Produce a spec package: 1-3 kebab-case capabilities, each with a purpose and "
        "testable requirements (normative SHALL statements) with WHEN/THEN scenarios. "
        "Reference the assumption indexes each requirement rests on. For each capability "
        "give 1-3 slices (name, size S/M/L, what ships) and its dependencies; give a "
        "package-level sequencing list - the PR-train build order with a one-line "
        "rationale each (quick wins and enablers first, order != importance). Keep "
        "the MVP light: specify only what the validated concept needs.\n",
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
