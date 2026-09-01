"""HTML renderer: the same story as the deck in one self-contained page."""

from __future__ import annotations

import re
from html import escape

from bokken.report.context import ReportContext, split_losers

_CSS = """
:root{--ink:#1f2430;--gray:#6b7280;--line:#e5e1d8;--paper:#faf7f2;--card:#ffffff;
--accent:#c73e3a;--accent-dark:#8a2b28;--green:#2f6f4e;
--mono:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,sans-serif}
*{box-sizing:border-box;margin:0}
body{font-family:var(--sans);color:var(--ink);background:var(--paper);line-height:1.55}
header.hero{background:var(--ink);color:var(--paper);padding:72px 24px 56px}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
.kicker{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
header.hero h1{font-size:clamp(28px,4.5vw,44px);margin:.35em 0 .3em;max-width:22ch}
header.hero .meta{color:#b9b3a8;font-size:14px}
.banner{border:1px solid var(--accent);color:var(--paper);background:rgba(199,62,58,.14);
padding:12px 16px;border-radius:6px;margin-top:24px;font-size:14px;max-width:72ch}
nav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--line);z-index:9}
nav .wrap{display:flex;gap:4px;overflow-x:auto;padding:0 24px}
nav a{font-family:var(--mono);font-size:12px;color:var(--gray);text-decoration:none;
padding:12px 10px;border-bottom:2px solid transparent;white-space:nowrap}
nav a.on{color:var(--accent-dark);border-bottom-color:var(--accent)}
section{padding:52px 0;border-bottom:1px solid var(--line)}
section h2{font-size:24px;margin:6px 0 4px}
section .lede{color:var(--gray);max-width:70ch;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:18px}
.card h3{font-size:13px;font-family:var(--mono);text-transform:uppercase;letter-spacing:.08em;
color:var(--accent-dark);margin-bottom:10px}
.num{font-size:30px;font-weight:700}
.num small{font-size:13px;color:var(--gray);font-weight:400;display:block}
.quote{border-left:3px solid var(--accent);padding:8px 14px;margin:14px 0;background:var(--card);border-radius:0 6px 6px 0}
.quote .who{font-family:var(--mono);font-size:12px;color:var(--gray);margin-top:6px}
.tag{display:inline-block;font-family:var(--mono);font-size:11px;padding:1px 8px;border-radius:99px;
border:1px solid var(--line);color:var(--gray);margin-left:6px}
.reg{display:grid;grid-template-columns:1fr 130px;gap:8px 14px;align-items:center;margin-top:14px}
.reg .stmt{font-size:14px}
.bar{height:22px;border-radius:4px;color:#fff;font-family:var(--mono);font-size:10.5px;
display:flex;align-items:center;justify-content:center;letter-spacing:.08em;
transform:scaleX(0);transform-origin:left;transition:transform .6s ease}
.seen .bar{transform:scaleX(1)}
.bar.supported{background:var(--green)}.bar.contradicted{background:var(--accent)}.bar.untested{background:var(--gray)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:10px 0}
summary{cursor:pointer;font-weight:600;font-size:14px}
details .why{color:var(--gray);font-size:13.5px;margin-top:8px}
ol.arc{list-style:none;counter-reset:step;margin-top:14px}
ol.arc li{counter-increment:step;padding:9px 0 9px 44px;position:relative;border-bottom:1px dashed var(--line);font-size:14px}
ol.arc li::before{content:counter(step,decimal-leading-zero);position:absolute;left:0;top:9px;
font-family:var(--mono);font-size:12px;color:var(--accent-dark)}
ol.arc li.loop{color:var(--accent-dark);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:12px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--gray)}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums}
code,.path{font-family:var(--mono);font-size:12.5px;color:var(--accent-dark);word-break:break-all}
.debt{font-size:14px;padding:8px 0 8px 16px;border-left:2px solid var(--line)}
footer{padding:40px 24px;color:var(--gray);font-size:13px}
.reveal{opacity:0;transform:translateY(10px);transition:opacity .5s ease,transform .5s ease}
.reveal.seen{opacity:1;transform:none}
#prog{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0;z-index:99;transition:width .1s linear}
.apo{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:18px 0 26px}
.apo .blk{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:14px 16px}
.apo .blk h4{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent-dark);margin-bottom:8px}
.apo .blk p,.apo .blk li{font-size:13.5px;color:var(--ink)}
.apo .blk .who{font-family:var(--mono);font-size:12px}
.cast{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;margin-top:16px}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px}
.pcard b{display:block;font-size:15px}
.pcard .role{font-family:var(--mono);font-size:11px;color:var(--accent-dark);text-transform:uppercase;letter-spacing:.08em}
.pcard .seg{font-size:12.5px;color:var(--gray);margin-top:4px}
.seq{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.seq span{font-family:var(--mono);font-size:12px;background:var(--ink);color:var(--paper);padding:6px 12px;border-radius:99px}
.seq span.loopb{background:var(--accent)}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:18px;margin:16px 0;max-width:860px}
.chartbox h4{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--gray);margin-bottom:10px}
"""

_JS = """
const obs=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('seen')}),{threshold:.15});
document.querySelectorAll('.reveal,.reg').forEach(el=>obs.observe(el));
const links=[...document.querySelectorAll('nav a')];
const spy=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){
links.forEach(l=>l.classList.toggle('on',l.hash==='#'+e.target.id))}}),{rootMargin:'-30% 0px -60% 0px'});
document.querySelectorAll('section[id]').forEach(s=>spy.observe(s));
window.addEventListener('scroll',()=>{const h=document.documentElement;
document.getElementById('prog').style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%'});
document.querySelectorAll('.num[data-n]').forEach(el=>{const end=parseFloat(el.dataset.n);const pre=el.dataset.pre||'';let t0=null;
const step=ts=>{if(!t0)t0=ts;const k=Math.min((ts-t0)/900,1);el.firstChild.textContent=pre+(end%1?(end*k).toFixed(2):Math.round(end*k));if(k<1)requestAnimationFrame(step)};
new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){requestAnimationFrame(step)}}),{threshold:.4}).observe(el)});
function drawCharts(){if(typeof Chart==='undefined')return;const D=window.__bokken;const ink='#1f2430',gray='#6b7280',acc='#c73e3a',green='#2f6f4e';
const hbar=(id,labels,data,colors)=>{const el=document.getElementById(id);if(!el||!labels.length)return;
new Chart(el,{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors}]},
options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{ticks:{autoSkip:false,font:{size:11}}}},animation:{duration:800}}})};
hbar('c-reg',['supported','contradicted','untested'],D.register,[green,acc,gray]);
hbar('c-opp',D.oppLabels,D.oppScores,D.oppScores.map(v=>v>=15?acc:v>=12?'#b3762d':gray));
hbar('c-cost',D.costLabels,D.costValues,D.costLabels.map(()=>ink));}
if(document.readyState==='complete')drawCharts();else window.addEventListener('load',drawCharts);
"""


def _e(text: str) -> str:
    return escape(str(text), quote=False)


def _apo(c: ReportContext, stage: str, output_line: str) -> str:
    d = c.stage_digest.get(stage, {})
    who = list(d.get("personas", []))[:6] + list(d.get("systems", []))
    calls = d.get("calls", {})
    calls_txt = ", ".join(f"{v} {k}" for k, v in sorted(calls.items())) or "none"
    models_txt = ", ".join(d.get("models", [])) or "-"
    moves = ", ".join(d.get("moves", [])) or "none"
    return (
        "<div class='apo'>"
        f"<div class='blk'><h4>Agents &amp; activity</h4><p class='who'>{_e(', '.join(who) or 'facilitator')}</p>"
        f"<p>{_e(calls_txt)} model call(s) on {_e(models_txt)}. Kata moves: {_e(moves)}.</p></div>"
        f"<div class='blk'><h4>Process</h4><p>{_e(d.get('process', ''))}</p></div>"
        f"<div class='blk'><h4>Output</h4><p>{_e(output_line)}</p></div>"
        "</div>"
    )


def render_page(ctx: ReportContext) -> str:
    m, c = ctx.model, ctx
    parts: list[str] = []
    add = parts.append

    outcome = m.recommendation.resolution if m.recommendation else m.stage
    add(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bokken run report — {_e(m.name)}</title><style>{_CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4" defer></script></head><body><div id="prog"></div>
<header class="hero"><div class="wrap">
<div class="kicker">Bokken · design thinking run report</div>
<h1>{_e(c.headline)}</h1>
<div class="meta">Session {_e(m.name)} · mode {_e(m.mode)} · status {_e(m.status)} ·
outcome <strong>{_e(outcome)}</strong></div>""")
    if m.dojo_banner:
        add(
            '<div class="banner"><strong>Simulated run.</strong> Produced by an autonomous run '
            "against a governed synthetic persona panel; all persona contributions are simulated "
            "and evidence-bounded. Flagged decisions require validation with real users.</div>"
        )
    add("</div></header>")

    sections = [
        ("summary", "Summary"),
        ("anatomy", "How it ran"),
        ("process", "Process"),
        ("inputs", "Inputs"),
        ("empathize", "Empathize"),
        *([("ui", "UI review")] if c.ui_review else []),
        ("define", "Define"),
        ("ideate", "Ideate"),
        ("prototype", "Prototype"),
        *([("research", "Concept research")] if c.market_research else []),
        ("test", "Test"),
        ("verdict", "Verdict"),
        ("debt", "Negative space"),
        ("ops", "Model ops"),
        ("appendix", "Appendix"),
    ]
    add(
        "<nav><div class='wrap'>"
        + "".join(f"<a href='#{i}'>{t}</a>" for i, t in sections)
        + "</div></nav><main class='wrap'>"
    )

    # Summary
    counts = c.register_counts
    add(f"""<section id="summary" class="reveal"><div class="kicker">executive summary</div>
<h2>Outcome: {_e(outcome)}</h2>
<p class="lede">Every number below is derived from the append-only Journal — nothing was
written by hand.</p><div class="grid">
<div class="card"><h3>Evidence</h3><div class="num" data-n="{len(m.evidence)}">{len(m.evidence)}<small>{c.synthetic_evidence} synthetic, labeled at record level</small></div></div>
<div class="card"><h3>Options &amp; decisions</h3><div class="num">{len(m.options)} / {len(m.decisions)}<small>options generated / decisions on record</small></div></div>
<div class="card"><h3>Assumption register</h3><div class="num">{len(m.assumptions)}<small>{counts["supported"]} supported · {counts["contradicted"]} contradicted · {counts["untested"]} untested</small></div></div>
<div class="card"><h3>Cost</h3><div class="num" data-n="{c.total_cost_usd:.2f}" data-pre="$">${c.total_cost_usd:,.2f}<small>{sum(u.calls for u in c.usage)} model calls, list-price estimate</small></div></div>
</div>""")
    if m.problem_statement:
        add(
            f"<div class='quote'>{_e(m.problem_statement.resolution)}<div class='who'>problem statement · define</div></div>"
        )
    if m.concept:
        add(
            f"<div class='quote'>{_e(m.concept.resolution)}<div class='who'>concept advanced · ideate</div></div>"
        )
    add("</section>")

    # How this run worked
    add("""<section id="anatomy" class="reveal"><div class="kicker">how this run worked</div>
<h2>The sequence, the cast, the machinery</h2>
<p class="lede">Bokken executed the Design Thinking loop autonomously. Every actor below is
journaled; persona contributions are simulated and labeled as such.</p><div class="seq">""")
    for tr in m.transitions:
        cls = " class='loopb'" if tr.loopback else ""
        add(f"<span{cls}>{_e(tr.from_stage)} &rarr; {_e(tr.to_stage)}</span>")
    add("</div>")
    by_panel: dict[str, list] = {}
    for persona in m.personas:
        by_panel.setdefault(persona.panel_kind, []).append(persona)
    for panel_kind in ("interview", "ideation", "test"):
        cast = by_panel.get(panel_kind, [])
        if not cast:
            continue
        add(
            f"<h3 style='margin-top:22px'>{panel_kind.title()} panel ({len(cast)} personas"
            f"{' — firewalled from the other panels' if panel_kind == 'test' else ''})</h3><div class='cast'>"
        )
        for pc in cast:
            add(
                f"<div class='pcard'><span class='role'>{_e(pc.role)}</span><b>{_e(pc.name)}</b>"
                f"<div class='seg'>{_e(pc.segment or 'cross-segment')}</div></div>"
            )
        add("</div>")
    add(
        "<h3 style='margin-top:22px'>System agents and models</h3><table>"
        "<tr><th>Agent</th><th>Did</th><th>Model calls</th></tr>"
    )
    agent_rows = [
        (
            "facilitator",
            "ran the stage machinery: programs, clustering, selection, register, fidelity, verdicts",
        ),
        (
            "ui-walker",
            "walked the running app with a real browser; journaled observed facts and screenshots",
        ),
        (
            "convergence lenses",
            "adversarial feasibility vs the codebase, independent RICE, outcome desirability",
        ),
        ("skeptic", "mandatory on-record challenge before convergence closed"),
    ]
    for name, did in agent_rows:
        add(f"<tr><td><code>{_e(name)}</code></td><td>{_e(did)}</td><td></td></tr>")
    for u in c.usage:
        add(
            f"<tr><td><code>{_e(u.model)}</code></td><td>routing classes served</td><td class='r'>{u.calls}</td></tr>"
        )
    add("</table></section>")

    # Process
    add("""<section id="process" class="reveal"><div class="kicker">process</div>
<h2>How the run moved</h2><p class="lede">Forward transitions fire only when journaled exit
criteria hold; loop-backs are first-class and leave the trail intact.</p><ol class="arc">""")
    for t in m.transitions:
        cls = " class='loop'" if t.loopback else ""
        label = "loop-back" if t.loopback else "forward"
        add(
            f"<li{cls}>{_e(t.from_stage)} &rarr; {_e(t.to_stage)} <span class='tag'>{label}</span><br><span style='color:var(--gray);font-size:13px'>{_e(t.condition)}</span></li>"
        )
    add("</ol></section>")

    # Inputs
    brief_inputs = m.brief.get("inputs", {}) or {}
    add("""<section id="inputs" class="reveal"><div class="kicker">inputs</div>
<h2>What the run was grounded in</h2><div class="grid"><div class="card"><h3>Brief</h3><ul>""")
    for seg in m.brief.get("target_segments", []):
        add(f"<li>Segment: {_e(seg)}</li>")
    for con in m.brief.get("constraints", []):
        add(f"<li>Constraint: {_e(con)}</li>")
    add("</ul></div><div class='card'><h3>Tangible corpus</h3><ul>")
    if brief_inputs.get("repo"):
        add(f"<li>code · <span class='path'>{_e(brief_inputs['repo'])}</span></li>")
    for key, kind in (
        ("documents", "document"),
        ("metrics", "metrics"),
        ("discussions", "discussion"),
    ):
        for item in brief_inputs.get(key, []) or []:
            add(f"<li>{kind} · <span class='path'>{_e(item)}</span></li>")
    add("</ul></div></div></section>")

    # Empathize
    add("""<section id="empathize" class="reveal"><div class="kicker">intermediate output · empathize</div>
<h2>Evidence with its confidence class</h2>""")
    add(
        _apo(
            c,
            "empathize",
            f"{len(m.evidence)} evidence items, {len(m.abstentions)} abstentions, {len(c.opportunities)} ranked outcomes, UI walkthrough {'done' if c.ui_review else 'skipped'}.",
        )
    )
    for e in [e for e in m.evidence.values() if e.stage == "empathize"][:6]:
        who = e.speaker or e.source
        cites = f" · {len(e.citations)} citation(s)" if e.citations else ""
        add(
            f"<div class='quote'>{_e(e.content)}<div class='who'>{_e(who)} · {_e(e.confidence_class)}{cites}</div></div>"
        )
    if m.abstentions:
        add(
            f"<p class='lede'>{len(m.abstentions)} question(s) were honestly abstained and carried as research debt.</p>"
        )
    if c.opportunities:
        add(
            "<h3 style='margin-top:26px'>Opportunity ranking "
            "(Ulwick: Opp = Importance + max(Importance &minus; Satisfaction, 0))</h3>"
        )
        add(
            "<div class='chartbox'><h4>Opportunity score per outcome (&ge;15 severely underserved, 12&ndash;15 underserved)</h4><canvas id='c-opp' height='210'></canvas></div>"
        )
        for statement in c.opportunities[:8]:
            add(f"<div class='debt'>{_e(statement)}</div>")
    add("</section>")

    # Functional UI review
    if c.ui_review:
        add("""<section id="ui" class="reveal"><div class="kicker">observed · functional UI review</div>
<h2>The product, exercised first-hand</h2>
<p class="lede">A browser walkthrough of the running app - screenshots and facts are observed
evidence, not simulation.</p>""")
        for shot in c.ui_screenshots:
            add(
                f"<img src='../{_e(shot)}' alt='UI screenshot' style='max-width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0'>"
            )
        review_html = _e(c.ui_review).replace("\n", "<br>")
        add(f"<div class='card' style='margin-top:14px'>{review_html}</div>")
        add("</section>")

    # Define
    add("""<section id="define" class="reveal"><div class="kicker">intermediate output · define</div>
<h2>Problem statement — winner and losers</h2>""")
    add(
        _apo(
            c,
            "define",
            "One problem statement selected; losers preserved with reasons; opportunity coverage among the criteria.",
        )
    )
    if m.problem_statement:
        add(
            f"<div class='quote'>{_e(m.problem_statement.resolution)}<div class='who'>selected</div></div>"
        )
        for statement, why in split_losers(m.problem_statement.options):
            add(
                f"<details><summary>{_e(statement[:180])}</summary><div class='why'>Lost: {_e(why)}</div></details>"
            )
    reframes = [mv for mv in m.moves if mv.move_id == "hmw_reframe" and mv.executed]
    if reframes:
        add(
            f"<p class='lede'>The Kata reframed solution-shaped statements {len(reframes)} time(s) before selection.</p>"
        )
    add("</section>")

    # Ideate
    add(f"""<section id="ideate" class="reveal"><div class="kicker">intermediate output · ideate</div>
<h2>{len(m.options)} options, one concept</h2>""")
    add(
        _apo(
            c,
            "ideate",
            f"{len(m.options)} options with full lineage; one concept advanced; lens verdicts and dissent on record.",
        )
    )
    if m.concept:
        add(
            f"<div class='quote'>{_e(m.concept.resolution)}<div class='who'>advanced to prototype</div></div>"
        )
        for d in m.concept.dissent:
            if isinstance(d, dict):
                add(
                    f"<details open><summary>Dissent on record ({_e(d.get('actor', 'panel'))})</summary><div class='why'>{_e(d.get('position', ''))}</div></details>"
                )
    add("</section>")

    # Prototype
    add("""<section id="prototype" class="reveal"><div class="kicker">intermediate output · prototype</div>
<h2>Artifacts against the riskiest assumptions</h2>""")
    add(
        _apo(
            c,
            "prototype",
            f"{len(m.assumptions)} assumptions registered; {len(c.prototype_artifacts)} artifacts generated and hash-journaled.",
        )
    )
    fidelity = next(
        (d for d in m.decisions.values() if d.question.startswith("prototype fidelity")), None
    )
    if fidelity:
        add(
            f"<details><summary>Fidelity decision — why these artifacts</summary><div class='why'>{_e(fidelity.resolution)}</div></details>"
        )
    real = c.prototype_artifacts
    if real:
        add(
            "<table><tr><th>Artifact</th><th>Kind</th><th>sha256</th><th class='r'>Assumptions</th></tr>"
        )
        for a in real:
            add(
                f"<tr><td><span class='path'>{_e(a.path)}</span></td><td>{_e(a.kind)}</td><td><code>{a.content_hash[:12]}</code></td><td class='r'>{len(a.assumption_ids)}</td></tr>"
            )
        add("</table>")
    add("</section>")

    # Test
    if c.market_research:
        mr = c.market_research
        add("""<section id="research" class="reveal"><div class="kicker">reported · concept research</div>
<h2>The web, on the record</h2>
<p class="lede">Authorized deep research on the selected concept. Every signal carries its
source; findings are reported evidence, not observation.</p>""")
        if mr.get("competitors"):
            add(
                "<h3>Competitors and prior art</h3><table><tr><th>Who</th><th>What</th><th>Overlap</th></tr>"
            )
            for comp in mr["competitors"]:
                name = _e(comp.get("name", ""))
                if comp.get("url"):
                    name = f"<a href='{_e(comp['url'])}'>{name}</a>"
                add(
                    f"<tr><td>{name}</td><td>{_e(comp.get('what', ''))}</td><td>{_e(comp.get('overlap', ''))}</td></tr>"
                )
            add("</table>")
        if mr.get("market_signals"):
            add("<h3 style='margin-top:20px'>Market signals</h3>")
            for sig in mr["market_signals"]:
                add(
                    f"<div class='quote'>{_e(sig.get('stat', ''))}<div class='who'><a href='{_e(sig.get('source_url', ''))}'>{_e(sig.get('source_url', ''))}</a></div></div>"
                )
        for key, title in (
            ("regulatory", "Regulatory"),
            ("pricing_benchmarks", "Pricing benchmarks"),
            ("differentiation_risks", "Differentiation risks"),
            ("open_questions", "Open questions"),
        ):
            if mr.get(key):
                add(f"<h3 style='margin-top:20px'>{title}</h3>")
                for item in mr[key]:
                    add(f"<div class='debt'>{_e(item)}</div>")
        add("</section>")

    add("""<section id="test" class="reveal"><div class="kicker">intermediate output · test</div>
<h2>The assumption register, scored</h2>""")
    add(
        _apo(
            c,
            "test",
            f"{c.register_counts['supported']} supported, {c.register_counts['contradicted']} contradicted, {c.register_counts['untested']} untested; recommendation: "
            + (m.recommendation.resolution if m.recommendation else "-")
            + ".",
        )
    )
    add(
        "<div class='chartbox'><h4>Register outcome</h4><canvas id='c-reg' height='110'></canvas></div>"
    )
    add("""<div class="reg">""")
    for a in m.assumptions.values():
        score = a.score or "untested"
        add(
            f"<div class='stmt'>{_e(a.statement)}</div><div class='bar {score}'>{score.upper()}</div>"
        )
    add("</div></section>")

    # Verdict
    add(f"""<section id="verdict" class="reveal"><div class="kicker">final output · verdict</div>
<h2>Recommendation: {_e(outcome)}</h2>""")
    if m.recommendation and m.recommendation.requires_real_validation:
        add(
            "<p class='lede'>Flagged: the register was scored by a synthetic panel — this verdict requires real-user validation before it is acted on.</p>"
        )
    loop = next((mv for mv in m.moves if mv.move_id == "loopback_proposal" and mv.executed), None)
    if loop and loop.outcome:
        add(
            f"<details open><summary>Loop-back proposal fired at test</summary><div class='why'>{_e(loop.outcome)}</div></details>"
        )
    for moment in m.pivotal_moments:
        add(f"<div class='debt'>{_e(moment.description)}</div>")
    add("</section>")

    # Negative space
    debt = m.negative_space.research_debt
    if debt:
        add("""<section id="debt" class="reveal"><div class="kicker">negative space</div>
<h2>Open research debt</h2><p class="lede">Real-user questions the synthetic panel refused to
answer from the corpus — the honest to-do list for human research.</p>""")
        seen: set[str] = set()
        for item in debt:
            if item.question in seen:
                continue
            seen.add(item.question)
            add(f"<div class='debt'>{_e(item.question)}</div>")
        add("</section>")

    # Model ops
    add("""<section id="ops" class="reveal"><div class="kicker">final output · model operations</div>
<h2>Every call journaled</h2>
<div class='chartbox'><h4>Estimated cost by model (USD)</h4><canvas id='c-cost' height='110'></canvas></div>
<table><tr><th>Model</th><th class="r">Calls</th><th class="r">Input tok</th><th class="r">Output tok</th><th class="r">Est. cost</th></tr>""")
    for u in c.usage:
        add(
            f"<tr><td><code>{_e(u.model)}</code></td><td class='r'>{u.calls}</td><td class='r'>{u.input_tokens:,}</td><td class='r'>{u.output_tokens:,}</td><td class='r'>${u.cost_usd:,.2f}</td></tr>"
        )
    add(
        f"<tr><td><strong>Total</strong></td><td></td><td></td><td></td><td class='r'><strong>${c.total_cost_usd:,.2f}</strong></td></tr></table>"
    )
    if c.dossier_paths:
        add(
            "<p class='lede'>Companion records: "
            + " · ".join(f"<span class='path'>{_e(p)}</span>" for p in c.dossier_paths)
            + " · <span class='path'>journal.jsonl</span></p>"
        )
    add("</section>")

    # Appendix
    add("""<section id="appendix" class="reveal"><div class="kicker">appendix</div>
<h2>Specifications handed off</h2>""")
    if c.spec_entries:
        add(
            "<p class='lede'>One sentence per spec; the full requirement text lives in the linked file.</p>"
        )
        for entry in c.spec_entries:
            add(
                f"<div class='card' style='margin:10px 0'><strong>{_e(entry.capability)}</strong> — {_e(entry.sentence)}<br><span class='path'>{_e(entry.path)}</span></div>"
            )
    else:
        add(
            f"<p class='lede'>No handoff package. {_e(c.handoff_refusal or 'Handoff not generated yet.')}</p>"
        )
    add("</section></main>")

    import json as _json

    opp_pairs = []
    for statement in c.opportunities[:10]:
        match = re.search(r"^(O\d+):", statement)
        score = re.search(r"opportunity (\d+(?:\.\d+)?)", statement)
        if score:
            opp_pairs.append((match.group(1) if match else statement[:14], float(score.group(1))))
    data_json = _json.dumps(
        {
            "register": [
                c.register_counts["supported"],
                c.register_counts["contradicted"],
                c.register_counts["untested"],
            ],
            "oppLabels": [x[0] for x in opp_pairs],
            "oppScores": [x[1] for x in opp_pairs],
            "costLabels": [u.model for u in c.usage],
            "costValues": [round(u.cost_usd, 2) for u in c.usage],
        }
    )
    add(f"""<footer class="wrap">Bokken · session {_e(m.name)} — generated from the Journal,
no manual edits. Part C of the evidence graph is machine-readable in
<span class="path">dossier/dossier.json</span>.</footer>
<script>window.__bokken={data_json};</script>
<script>{_JS}</script></body></html>""")
    return "".join(parts)
