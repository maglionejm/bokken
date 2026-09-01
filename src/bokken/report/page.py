"""HTML renderer: the run as a chaptered, human-consumable report.

Layout: a fixed left rail with the numbered table of contents and the
verdict; the content column tells the story in chapters (executive summary,
run anatomy, then one chapter per stage, verdict, negative space, model ops,
appendix). Presentation only - every fact still comes from the Journal.
"""

from __future__ import annotations

import re
from html import escape

from bokken.report.context import ReportContext, split_losers

_CSS = """
:root{--ink:#1f2430;--ink2:#3a4152;--gray:#6b7280;--line:#e6e2d8;--paper:#f7f4ee;
--card:#ffffff;--accent:#c73e3a;--accent-dark:#8a2b28;--green:#2f6f4e;--amber:#b3762d;
--mono:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,sans-serif}
*{box-sizing:border-box;margin:0}
html{scroll-behavior:smooth;scroll-padding-top:24px}
body{font-family:var(--sans);color:var(--ink);background:var(--paper);line-height:1.6}
#prog{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0;z-index:99}
a{color:var(--accent-dark)}
/* ---- shell: rail + content ---- */
.shell{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}
.rail{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--ink);color:#cfc9bd;
padding:28px 20px;display:flex;flex-direction:column;gap:4px}
.rail .brand{font-family:var(--mono);font-size:12px;letter-spacing:.18em;color:var(--paper);
text-transform:uppercase;margin-bottom:6px}
.rail .brand b{color:var(--accent)}
.rail .session{font-size:12px;color:#8b8577;margin-bottom:14px;word-break:break-all}
.rail .verdict-chip{font-family:var(--mono);font-size:11px;text-transform:uppercase;
letter-spacing:.1em;border:1px solid var(--accent);color:var(--paper);border-radius:99px;
padding:5px 12px;margin-bottom:20px;align-self:flex-start}
.rail a.toc{display:flex;gap:10px;align-items:baseline;color:#a9a396;text-decoration:none;
font-size:13px;padding:7px 10px;border-radius:6px;border-left:2px solid transparent}
.rail a.toc .n{font-family:var(--mono);font-size:10.5px;color:#6d6759;min-width:18px}
.rail a.toc.on{background:rgba(255,255,255,.06);color:var(--paper);border-left-color:var(--accent)}
.rail a.toc.on .n{color:var(--accent)}
.rail .foot{margin-top:auto;font-size:11px;color:#6d6759;padding-top:20px}
main{padding:0 clamp(24px,5vw,72px) 80px;max-width:980px}
@media(max-width:900px){.shell{grid-template-columns:1fr}
.rail{position:relative;height:auto;flex-direction:row;flex-wrap:wrap;align-items:center;gap:8px}
.rail a.toc{padding:4px 8px}.rail .foot{display:none}.rail .session{margin:0}}
/* ---- hero ---- */
.hero{background:var(--ink);color:var(--paper);border-radius:0 0 18px 18px;
padding:clamp(32px,6vw,64px);margin:0 0 8px;position:relative;overflow:hidden}
.hero .kicker{color:var(--accent)}
.hero .outcome{font-family:var(--mono);font-size:clamp(34px,6vw,58px);font-weight:700;
text-transform:uppercase;letter-spacing:.04em;line-height:1.05;margin:.25em 0 .15em}
.hero .outcome.iterate{color:var(--amber)}.hero .outcome.proceed{color:#7fb597}
.hero .outcome.kill{color:var(--accent)}
.hero h1{font-size:clamp(19px,2.6vw,26px);font-weight:600;max-width:36ch;color:#e8e4da}
.hero .meta{color:#8b8577;font-size:13.5px;margin-top:14px;font-family:var(--mono)}
.hero .stats{display:flex;flex-wrap:wrap;gap:28px;margin-top:30px}
.hero .stat .num{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums}
.hero .stat small{display:block;font-size:11.5px;color:#8b8577;max-width:19ch}
.banner{border:1px solid var(--accent);background:rgba(199,62,58,.16);color:var(--paper);
padding:12px 16px;border-radius:8px;margin-top:26px;font-size:13.5px;max-width:78ch}
/* ---- chapters ---- */
.kicker{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;
color:var(--accent-dark)}
section.ch{padding:60px 0 30px;border-bottom:1px solid var(--line);position:relative}
section.ch>.chno{position:absolute;top:34px;right:0;font-family:var(--mono);font-weight:700;
font-size:clamp(48px,7vw,84px);color:rgba(31,36,48,.07);line-height:1;user-select:none}
section.ch h2{font-size:clamp(22px,3vw,30px);margin:8px 0 6px;letter-spacing:-.01em}
section.ch .lede{color:var(--gray);max-width:72ch;font-size:15.5px;margin-bottom:26px}
h3{font-size:15px;margin:26px 0 10px}
/* ---- components ---- */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}
.card h4{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;
color:var(--gray);margin-bottom:8px}
.apo{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:0;
border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card);margin:0 0 28px}
.apo .blk{padding:16px 18px;border-left:1px solid var(--line)}
.apo .blk:first-child{border-left:none}
.apo h4{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
color:var(--accent-dark);margin-bottom:8px}
.apo p{font-size:13px;color:var(--ink2)}
.apo .who{font-family:var(--mono);font-size:11.5px;color:var(--ink)}
.quote{border-left:3px solid var(--accent);background:var(--card);border-radius:0 10px 10px 0;
padding:14px 18px;margin:14px 0;font-size:15px}
.quote .who{font-family:var(--mono);font-size:11.5px;color:var(--gray);margin-top:8px}
.tag{display:inline-block;font-family:var(--mono);font-size:10px;text-transform:uppercase;
letter-spacing:.08em;padding:2px 9px;border-radius:99px;margin-left:8px;color:#fff}
.tag.simulated{background:var(--gray)}.tag.observed{background:var(--green)}
.tag.reported{background:var(--amber)}.tag.loop{background:var(--accent)}
/* timeline */
.tl{list-style:none;margin:10px 0 0;padding:0;position:relative}
.tl::before{content:'';position:absolute;left:9px;top:6px;bottom:6px;width:2px;background:var(--line)}
.tl li{position:relative;padding:0 0 22px 38px;font-size:14.5px}
.tl li::before{content:'';position:absolute;left:3px;top:4px;width:14px;height:14px;
border-radius:50%;background:var(--paper);border:3px solid var(--ink)}
.tl li.loop::before{border-color:var(--accent)}
.tl li b{font-family:var(--mono);font-size:13px}
.tl li .cond{display:block;color:var(--gray);font-size:13px;margin-top:2px;max-width:78ch}
/* cast */
.cast{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:14px}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;
display:flex;gap:12px;align-items:center}
.pcard .av{width:38px;height:38px;border-radius:50%;background:var(--ink);color:var(--paper);
display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:13px;flex:none}
.pcard.test .av{background:var(--accent-dark)}
.pcard b{display:block;font-size:13.5px;line-height:1.25}
.pcard .role{font-family:var(--mono);font-size:10px;color:var(--accent-dark);text-transform:uppercase;letter-spacing:.08em}
.pcard .seg{font-size:11.5px;color:var(--gray)}
/* register */
.reg{display:grid;grid-template-columns:minmax(0,1fr) 130px;gap:8px 14px;align-items:center;margin-top:16px}
.reg .stmt{font-size:14px}
.bar{height:22px;border-radius:5px;color:#fff;font-family:var(--mono);font-size:10px;
display:flex;align-items:center;justify-content:center;letter-spacing:.08em;
transform:scaleX(0);transform-origin:left;transition:transform .6s ease}
.seen .bar{transform:scaleX(1)}
.bar.supported{background:var(--green)}.bar.contradicted{background:var(--accent)}.bar.untested{background:var(--gray)}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 18px;margin:10px 0}
summary{cursor:pointer;font-weight:600;font-size:14px}
details .why{color:var(--gray);font-size:13.5px;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:12px;background:var(--card);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
th{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;
color:var(--gray);background:var(--paper)}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums}
code,.path{font-family:var(--mono);font-size:12px;color:var(--accent-dark);word-break:break-all}
.debt{font-size:14px;padding:9px 0 9px 16px;border-left:2px solid var(--line);margin:2px 0}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:18px;margin:16px 0;max-width:880px}
.chartbox h4{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;
letter-spacing:.1em;color:var(--gray);margin-bottom:10px}
.verdict-panel{background:var(--ink);color:var(--paper);border-radius:14px;padding:34px;
display:grid;grid-template-columns:1fr 1fr;gap:26px;align-items:center}
@media(max-width:760px){.verdict-panel{grid-template-columns:1fr}}
.verdict-panel .word{font-family:var(--mono);font-size:clamp(36px,5vw,54px);font-weight:700;
text-transform:uppercase}
.verdict-panel .word.iterate{color:var(--amber)}.verdict-panel .word.proceed{color:#7fb597}
.verdict-panel .word.kill{color:var(--accent)}
.verdict-panel p{font-size:14px;color:#cfc9bd}
.shot{max-width:100%;border:1px solid var(--line);border-radius:10px;margin:10px 0;box-shadow:0 6px 24px rgba(31,36,48,.08)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 18px}
.chips span{font-family:var(--mono);font-size:11px;background:var(--card);
border:1px solid var(--line);border-radius:99px;padding:4px 12px;color:var(--ink2)}
.chips span b{color:var(--accent-dark)}
.fcard{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:12px 0;display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:16px}
@media(max-width:760px){.fcard{grid-template-columns:1fr}}
.fcard .steps{font-family:var(--mono);font-size:11.5px;color:var(--ink2);margin-top:8px;
padding-left:14px;border-left:2px solid var(--line)}
.fcard img{width:100%;border:1px solid var(--line);border-radius:8px}
.vote{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--ink);
border-radius:0 10px 10px 0;padding:13px 16px;margin:10px 0;font-size:13.5px}
.vote .lens{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;
letter-spacing:.1em;color:var(--accent-dark)}
.actions{counter-reset:act;list-style:none;padding:0;margin:14px 0}
.actions li{counter-increment:act;background:var(--card);border:1px solid var(--line);
border-radius:10px;padding:13px 16px 13px 52px;margin:8px 0;position:relative;font-size:14px}
.actions li::before{content:counter(act);position:absolute;left:16px;top:11px;width:24px;height:24px;
border-radius:50%;background:var(--accent);color:#fff;font-family:var(--mono);font-size:12px;
display:flex;align-items:center;justify-content:center}
.reveal{opacity:0;transform:translateY(12px);transition:opacity .55s ease,transform .55s ease}
.reveal.seen{opacity:1;transform:none}
@media print{.rail{display:none}.shell{display:block}#prog{display:none}}
"""

_JS = """
const obs=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('seen')}),{threshold:.12});
document.querySelectorAll('.reveal,.reg').forEach(el=>obs.observe(el));
const links=[...document.querySelectorAll('.rail a.toc')];
const spy=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){
links.forEach(l=>l.classList.toggle('on',l.hash==='#'+e.target.id))}}),{rootMargin:'-25% 0px -65% 0px'});
document.querySelectorAll('section[id],header[id]').forEach(s=>spy.observe(s));
window.addEventListener('scroll',()=>{const h=document.documentElement;
document.getElementById('prog').style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%'});
document.querySelectorAll('.num[data-n]').forEach(el=>{const end=parseFloat(el.dataset.n);const pre=el.dataset.pre||'';let t0=null;
const step=ts=>{if(!t0)t0=ts;const k=Math.min((ts-t0)/900,1);el.firstChild.textContent=pre+(end%1?(end*k).toFixed(2):Math.round(end*k));if(k<1)requestAnimationFrame(step)};
new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){requestAnimationFrame(step)}}),{threshold:.4}).observe(el)});
function drawCharts(){if(typeof Chart==='undefined')return;const D=window.__bokken;
const ink='#1f2430',gray='#6b7280',acc='#c73e3a',green='#2f6f4e';
const hbar=(id,labels,data,colors)=>{const el=document.getElementById(id);if(!el||!labels.length)return;
new Chart(el,{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4}]},
options:{indexAxis:'y',plugins:{legend:{display:false}},
scales:{x:{grid:{display:false}},y:{ticks:{autoSkip:false,font:{size:11,family:'Menlo'}}}},animation:{duration:800}}})};
hbar('c-reg',['supported','contradicted','untested'],D.register,[green,acc,gray]);
hbar('c-opp',D.oppLabels,D.oppScores,D.oppScores.map(v=>v>=15?acc:v>=12?'#b3762d':gray));
hbar('c-cost',D.costLabels,D.costValues,D.costLabels.map(()=>ink));}
if(document.readyState==='complete')drawCharts();else window.addEventListener('load',drawCharts);
"""


def _img_uri(ctx: ReportContext, relative: str) -> str:
    import base64

    path = ctx.session_dir / relative
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


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
        f"<div class='blk'><h4>Agents &amp; activity</h4>"
        f"<p class='who'>{_e(', '.join(who) or 'facilitator')}</p>"
        f"<p>{_e(calls_txt)} model call(s) on {_e(models_txt)}. Kata moves: {_e(moves)}.</p></div>"
        f"<div class='blk'><h4>Process</h4><p>{_e(d.get('process', ''))}</p></div>"
        f"<div class='blk'><h4>Output</h4><p>{_e(output_line)}</p></div>"
        "</div>"
    )


def _chips(items: list[tuple[str, str]]) -> str:
    return (
        "<div class='chips'>"
        + "".join(f"<span><b>{_e(v)}</b> {_e(k)}</span>" for k, v in items if v)
        + "</div>"
    )


def render_page(ctx: ReportContext) -> str:
    m, c = ctx.model, ctx
    parts: list[str] = []
    add = parts.append
    outcome = m.recommendation.resolution if m.recommendation else m.stage

    # ---- chapter inventory (id, rail label, kicker, title) ----
    chapters: list[tuple[str, str, str, str]] = [
        ("summary", "Executive summary", "executive summary", "What this run concluded"),
        ("anatomy", "How it ran", "how this run worked", "The sequence, the cast, the machinery"),
        ("inputs", "Inputs", "inputs", "What the run was grounded in"),
        ("empathize", "Empathize", "stage · empathize", "Evidence, on the record"),
    ]
    if c.ui_review:
        chapters.append(
            (
                "ui",
                "UI review",
                "observed · functional ui review",
                "The product, exercised first-hand",
            )
        )
    chapters += [
        ("define", "Define", "stage · define", "The problem statement, and why the losers lost"),
        ("ideate", "Ideate", "stage · ideate", f"{len(m.options)} options in, one concept out"),
        (
            "prototype",
            "Prototype",
            "stage · prototype",
            "Artifacts against the riskiest assumptions",
        ),
    ]
    if c.market_research:
        chapters.append(
            (
                "research",
                "Concept research",
                "reported · concept research",
                "The web, on the record",
            )
        )
    chapters += [
        ("test", "Test", "stage · test", "The assumption register, scored"),
        (
            "deliberation",
            "Deliberation",
            "how the agents argued",
            "Votes, challenge, dissent, iteration",
        ),
        ("verdict", "Verdict", "final output", f"Recommendation: {outcome}"),
        ("debt", "Negative space", "negative space", "What this run honestly did not do"),
        ("ops", "Model ops", "model operations", "Every call journaled, every euro estimated"),
        ("actions", "Next actions", "action oriented", "What to do next, in order"),
        ("appendix", "Appendix", "appendix", "Specifications handed off"),
    ]
    numbers = {cid: f"{i + 1:02d}" for i, (cid, *_rest) in enumerate(chapters)}

    def chapter(cid: str) -> str:
        _, _, kicker, title = next(ch for ch in chapters if ch[0] == cid)
        return (
            f"<section id='{cid}' class='ch reveal'><span class='chno'>{numbers[cid]}</span>"
            f"<div class='kicker'>{_e(kicker)}</div><h2>{_e(title)}</h2>"
        )

    # ---- head + shell + rail ----
    add(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bokken run report — {_e(m.name)}</title><style>{_CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4" defer></script></head><body><div id="prog"></div>
<div class="shell"><nav class="rail"><div class="brand"><b>Bokken</b> · run report</div>
<div class="session">{_e(m.name)} · {_e(m.mode)}</div>
<div class="verdict-chip">outcome: {_e(outcome)}</div>""")
    for cid, label, *_rest in chapters:
        add(f"<a class='toc' href='#{cid}'><span class='n'>{numbers[cid]}</span>{_e(label)}</a>")
    add("""<div class="foot">Generated from the append-only Journal.<br>No manual edits.</div></nav>
<main>""")

    # ---- hero ----
    counts = c.register_counts
    add(f"""<header class="hero" id="top">
<div class="kicker">bokken · design thinking run report</div>
<div class="outcome {_e(outcome)}">{_e(outcome)}</div>
<h1>{_e(c.headline)}</h1>
<div class="meta">session {_e(m.name)} · mode {_e(m.mode)} · status {_e(m.status)}</div>
<div class="stats">
<div class="stat"><div class="num" data-n="{len(m.evidence)}">{len(m.evidence)}</div><small>evidence items ({c.synthetic_evidence} synthetic, labeled)</small></div>
<div class="stat"><div class="num" data-n="{len(m.options)}">{len(m.options)}</div><small>options generated with full lineage</small></div>
<div class="stat"><div class="num" data-n="{len(m.assumptions)}">{len(m.assumptions)}</div><small>{counts["supported"]} supported · {counts["contradicted"]} contradicted · {counts["untested"]} untested</small></div>
<div class="stat"><div class="num" data-n="{c.total_cost_usd:.2f}" data-pre="$">${c.total_cost_usd:,.2f}</div><small>{sum(u.calls for u in c.usage)} model calls, list-price estimate</small></div>
</div>""")
    if m.dojo_banner:
        add(
            '<div class="banner"><strong>Simulated run.</strong> Produced by an autonomous run '
            "against a governed synthetic persona panel; all persona contributions are simulated "
            "and evidence-bounded. Flagged decisions require validation with real users.</div>"
        )
    add("</header>")

    # ---- 01 executive summary ----
    add(chapter("summary"))
    add(
        "<p class='lede'>Every number on this page is derived from the append-only Journal — nothing was written by hand.</p>"
    )
    if m.problem_statement:
        add(
            f"<div class='quote'>{_e(m.problem_statement.resolution)}<div class='who'>problem statement · define</div></div>"
        )
    if m.concept:
        add(
            f"<div class='quote'>{_e(m.concept.resolution)}<div class='who'>concept advanced · ideate</div></div>"
        )
    if m.recommendation and m.recommendation.requires_real_validation:
        add(
            "<p class='lede'>The verdict rests on simulated evidence and requires validation with real users before it is acted on.</p>"
        )
    add("</section>")

    # ---- 02 anatomy ----
    add(chapter("anatomy"))
    add(
        "<p class='lede'>Bokken executed the Design Thinking loop autonomously. Every actor below is journaled; persona contributions are simulated and labeled as such.</p>"
    )
    add("<h3>The sequence</h3><ol class='tl'>")
    for t in m.transitions:
        loop = t.loopback
        add(
            f"<li{' class=loop' if loop else ''}><b>{_e(t.from_stage)} &rarr; {_e(t.to_stage)}</b>"
            f"{'<span class=&quot;tag loop&quot;>loop-back</span>' if loop else ''}"
            f"<span class='cond'>{_e(t.condition)}</span></li>"
        )
    add("</ol>")
    by_panel: dict[str, list] = {}
    for persona in m.personas:
        by_panel.setdefault(persona.panel_kind, []).append(persona)
    for panel_kind in ("interview", "ideation", "test"):
        cast = by_panel.get(panel_kind, [])
        if not cast:
            continue
        fw = " — firewalled from the other panels" if panel_kind == "test" else ""
        add(f"<h3>{panel_kind.title()} panel ({len(cast)} personas{fw})</h3><div class='cast'>")
        for pc in cast:
            initials = "".join(w[0] for w in pc.name.split()[:2]).upper() or "?"
            add(
                f"<div class='pcard {panel_kind}'><div class='av'>{_e(initials)}</div><div>"
                f"<span class='role'>{_e(pc.role)}</span><b>{_e(pc.name)}</b>"
                f"<div class='seg'>{_e(pc.segment or 'cross-segment')}</div></div></div>"
            )
        add("</div>")
    add(
        "<h3>System agents and models</h3><table><tr><th>Agent</th><th>Did</th><th class='r'>Model calls</th></tr>"
    )
    for name, did in (
        (
            "facilitator",
            "ran the stage machinery: programs, clustering, selection, register, fidelity, verdicts",
        ),
        (
            "ui-walker",
            "walked the running app with a real browser; journaled observed facts and screenshots",
        ),
        (
            "concept-researcher",
            "authorized deep web research on the selected concept, sources cited",
        ),
        (
            "convergence lenses",
            "adversarial feasibility vs the codebase, independent RICE, outcome desirability",
        ),
        ("skeptic", "mandatory on-record challenge before convergence closed"),
    ):
        add(f"<tr><td><code>{_e(name)}</code></td><td>{_e(did)}</td><td></td></tr>")
    for u in c.usage:
        add(
            f"<tr><td><code>{_e(u.model)}</code></td><td>routing classes served</td><td class='r'>{u.calls}</td></tr>"
        )
    add("</table></section>")

    # ---- 03 inputs ----
    brief_inputs = m.brief.get("inputs", {}) or {}
    add(chapter("inputs"))
    add("<div class='grid'><div class='card'><h4>Brief</h4><ul>")
    for seg in m.brief.get("target_segments", []):
        add(f"<li>Segment: {_e(seg)}</li>")
    for con in m.brief.get("constraints", []):
        add(f"<li>Constraint: {_e(con)}</li>")
    add("</ul></div><div class='card'><h4>Tangible corpus</h4><ul>")
    if brief_inputs.get("repo"):
        add(f"<li>code · <span class='path'>{_e(brief_inputs['repo'])}</span></li>")
    if brief_inputs.get("app_url"):
        add(f"<li>running app · <span class='path'>{_e(brief_inputs['app_url'])}</span></li>")
    for key, kind in (
        ("documents", "document"),
        ("metrics", "metrics"),
        ("discussions", "discussion"),
    ):
        for item in brief_inputs.get(key, []) or []:
            add(f"<li>{kind} · <span class='path'>{_e(item)}</span></li>")
    add("</ul></div></div></section>")

    # ---- 04 empathize ----
    add(chapter("empathize"))
    d_emp = c.stage_digest.get("empathize", {})
    add(
        _chips(
            [
                ("evidence items", str(len(m.evidence))),
                (
                    "observed",
                    str(sum(1 for e in m.evidence.values() if e.confidence_class == "observed")),
                ),
                ("ranked outcomes", str(len(c.opportunities))),
                ("research calls", str(d_emp.get("calls", {}).get("research", 0))),
                ("abstentions", str(len(m.abstentions))),
            ]
        )
    )
    add(
        _apo(
            c,
            "empathize",
            f"{len(m.evidence)} evidence items, {len(m.abstentions)} abstentions, "
            f"{len(c.opportunities)} ranked outcomes, UI walkthrough "
            f"{'done' if c.ui_review else 'skipped'}.",
        )
    )
    for e in [e for e in m.evidence.values() if e.stage == "empathize"][:6]:
        who = e.speaker or e.source
        cites = f" · {len(e.citations)} citation(s)" if e.citations else ""
        add(
            f"<div class='quote'>{_e(e.content)}<div class='who'>{_e(who)}"
            f"<span class='tag {_e(e.confidence_class)}'>{_e(e.confidence_class)}</span>{cites}</div></div>"
        )
    if m.abstentions:
        add(
            f"<p class='lede'>{len(m.abstentions)} question(s) were honestly abstained and carried as research debt.</p>"
        )
    if c.opportunities:
        add(
            "<h3>Opportunity ranking (Ulwick: Opp = Importance + max(Importance &minus; Satisfaction, 0))</h3>"
        )
        add(
            "<div class='chartbox'><h4>Opportunity score per outcome (&ge;15 severely underserved, 12&ndash;15 underserved)</h4><canvas id='c-opp' height='210'></canvas></div>"
        )
        for statement in c.opportunities[:8]:
            add(f"<div class='debt'>{_e(statement)}</div>")
    add("</section>")

    # ---- UI review ----
    if c.ui_review:
        add(chapter("ui"))
        add(
            "<p class='lede'>A browser walkthrough of the running app — screenshots and facts are observed evidence, not simulation.</p>"
        )
        if c.ui_feature_results:
            counts_v = {"works": 0, "broken": 0, "unclear": 0}
            for r in c.ui_feature_results:
                counts_v[r.get("verdict", "unclear")] = (
                    counts_v.get(r.get("verdict", "unclear"), 0) + 1
                )
            add(
                _chips(
                    [
                        ("features exercised", str(len(c.ui_feature_results))),
                        ("broken", str(counts_v["broken"])),
                        ("works", str(counts_v["works"])),
                        ("unclear", str(counts_v["unclear"])),
                    ]
                )
            )
            verdict_tag = {"works": "observed", "broken": "loop", "unclear": "simulated"}
            for r in c.ui_feature_results:
                v = r.get("verdict", "unclear")
                steps_html = (
                    "".join(f"<div>{_e(s)}</div>" for s in r.get("steps", []))
                    or "<div>(entry state only)</div>"
                )
                shot_html = ""
                if r.get("screenshot"):
                    uri = _img_uri(c, f"artifacts/ui/{r['screenshot']}")
                    if uri:
                        shot_html = f"<div><img src='{uri}' alt='end state'></div>"
                add(
                    f"<div class='fcard'><div><strong>{_e(r.get('feature', ''))}</strong>"
                    f"<span class='tag {verdict_tag.get(v, 'simulated')}'>{_e(v)}</span>"
                    + (
                        f"<p style='font-size:13.5px;margin-top:6px'>{_e(r.get('finding', ''))}</p>"
                        if r.get("finding")
                        else ""
                    )
                    + f"<div class='steps'>{steps_html}</div></div>{shot_html}</div>"
                )
        walk_shots = [s for s in c.ui_screenshots if "feature_" not in s][:4]
        for shot in walk_shots:
            uri = _img_uri(c, shot)
            if uri:
                add(f"<img class='shot' src='{uri}' alt='UI screenshot'>")
        review_html = _e(c.ui_review).replace("\n", "<br>")
        add(
            "<details style='margin-top:14px'><summary>Full heuristic review (verbatim)</summary>"
            f"<div class='why'>{review_html}</div></details></section>"
        )

    # ---- define ----
    add(chapter("define"))
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

    # ---- ideate ----
    add(chapter("ideate"))
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

    # ---- prototype ----
    add(chapter("prototype"))
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
    if c.prototype_artifacts:
        add(
            "<table><tr><th>Artifact</th><th>Kind</th><th>sha256</th><th class='r'>Assumptions</th></tr>"
        )
        for a in c.prototype_artifacts:
            add(
                f"<tr><td><span class='path'>{_e(a.path)}</span></td><td>{_e(a.kind)}</td><td><code>{a.content_hash[:12]}</code></td><td class='r'>{len(a.assumption_ids)}</td></tr>"
            )
        add("</table>")
    add("</section>")

    # ---- concept research ----
    if c.market_research:
        mr = c.market_research
        add(chapter("research"))
        add(
            "<p class='lede'>Authorized deep research on the selected concept. Every signal carries its source; findings are reported evidence, not observation.</p>"
        )
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
            add("<h3>Market signals</h3>")
            for sig in mr["market_signals"]:
                add(
                    f"<div class='quote'>{_e(sig.get('stat', ''))}<div class='who'><a href='{_e(sig.get('source_url', ''))}'>{_e(sig.get('source_url', ''))}</a><span class='tag reported'>reported</span></div></div>"
                )
        for key, title in (
            ("regulatory", "Regulatory"),
            ("pricing_benchmarks", "Pricing benchmarks"),
            ("differentiation_risks", "Differentiation risks"),
            ("open_questions", "Open questions"),
        ):
            if mr.get(key):
                add(f"<h3>{title}</h3>")
                for item in mr[key]:
                    add(f"<div class='debt'>{_e(item)}</div>")
        add("</section>")

    # ---- test ----
    add(chapter("test"))
    add(
        _apo(
            c,
            "test",
            f"{counts['supported']} supported, {counts['contradicted']} contradicted, "
            f"{counts['untested']} untested; recommendation: "
            + (m.recommendation.resolution if m.recommendation else "-")
            + ".",
        )
    )
    add(
        "<div class='chartbox'><h4>Register outcome</h4><canvas id='c-reg' height='110'></canvas></div>"
    )
    add("<div class='reg'>")
    for a in m.assumptions.values():
        score = a.score or "untested"
        add(
            f"<div class='stmt'>{_e(a.statement)}</div><div class='bar {score}'>{score.upper()}</div>"
        )
    add("</div></section>")

    # ---- deliberation ----
    add(chapter("deliberation"))
    add(
        _chips(
            [
                ("lens votes", str(len(c.lens_votes))),
                ("kata moves executed", str(sum(1 for mv in c.kata_moves if mv["executed"]))),
                ("suppressed", str(sum(1 for mv in c.kata_moves if not mv["executed"]))),
                ("dissents on record", str(len(c.dissent))),
            ]
        )
    )
    if c.lens_votes:
        add("<h3>Convergence lens votes</h3>")
        by_lens: dict[str, list[str]] = {}
        for vote in c.lens_votes:
            by_lens.setdefault(vote["lens"], []).append(vote["position"])
        for lens, positions in by_lens.items():
            add(
                f"<details{' open' if lens == 'feasibility' else ''}>"
                f"<summary>{_e(lens)} — {len(positions)} vote(s)</summary>"
            )
            for pos in positions:
                add(f"<div class='vote'><span class='lens'>{_e(lens)}</span><br>{_e(pos)}</div>")
            add("</details>")
    if c.skeptic_challenge:
        add("<h3>The skeptic, verbatim</h3>")
        add(
            f"<div class='quote'>{_e(c.skeptic_challenge)}<div class='who'>skeptic · on the record before convergence closed</div></div>"
        )
    if c.dissent:
        add("<h3>Dissent preserved on the decision</h3>")
        for d in c.dissent:
            add(
                f"<div class='quote'>{_e(d.get('reservation', ''))}<div class='who'>{_e(d.get('actor', 'panel'))}</div></div>"
            )
    if c.kata_moves:
        add("<h3>Facilitation (Kata) — every intervention journaled</h3>")
        add("<table><tr><th>Move</th><th>Stage</th><th>Fired</th><th>Trigger / note</th></tr>")
        for mv in c.kata_moves[:14]:
            fired = "yes" if mv["executed"] else "suppressed"
            note = (mv["note"] or mv["trigger"])[:110]
            add(
                f"<tr><td><code>{_e(mv['move'])}</code></td><td>{_e(mv['stage'])}</td><td>{fired}</td><td>{_e(note)}</td></tr>"
            )
        add("</table>")
    add("</section>")

    # ---- verdict ----
    add(chapter("verdict"))
    validation = (
        "Scored by a synthetic panel — requires validation with real users before acting."
        if m.recommendation and m.recommendation.requires_real_validation
        else "Scored with human participation."
    )
    add(
        f"<div class='verdict-panel'><div><div class='word {_e(outcome)}'>{_e(outcome)}</div>"
        f"<p>{_e(validation)}</p></div><div>"
        f"<p>Register: {counts['supported']} supported · {counts['contradicted']} contradicted · "
        f"{counts['untested']} untested of {len(m.assumptions)}.</p></div></div>"
    )
    loop = next((mv for mv in m.moves if mv.move_id == "loopback_proposal" and mv.executed), None)
    if loop and loop.outcome:
        add(
            f"<details open><summary>Loop-back proposal fired at test</summary><div class='why'>{_e(loop.outcome)}</div></details>"
        )
    for moment in m.pivotal_moments:
        add(f"<div class='debt'>{_e(moment.description)}</div>")
    add("</section>")

    # ---- negative space ----
    add(chapter("debt"))
    debt = m.negative_space.research_debt
    if debt:
        add(
            "<p class='lede'>Real-user questions the run refused to answer from its inputs — the honest to-do list for human research.</p>"
        )
        seen: set[str] = set()
        for item in debt:
            if item.question in seen:
                continue
            seen.add(item.question)
            add(f"<div class='debt'>{_e(item.question)}</div>")
    else:
        add("<p class='lede'>No open research debt was journaled in this run.</p>")
    add("</section>")

    # ---- model ops ----
    add(chapter("ops"))
    add(
        "<div class='chartbox'><h4>Estimated cost by model (USD)</h4><canvas id='c-cost' height='110'></canvas></div>"
    )
    add(
        "<table><tr><th>Model</th><th class='r'>Calls</th><th class='r'>Input tok</th><th class='r'>Output tok</th><th class='r'>Est. cost</th></tr>"
    )
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

    # ---- next actions ----
    add(chapter("actions"))
    if c.next_actions:
        add(
            "<p class='lede'>Derived from journaled findings: broken features first, then the verdict's next step, then the top research debt.</p>"
        )
        add("<ol class='actions'>")
        for action in c.next_actions:
            add(f"<li>{_e(action)}</li>")
        add("</ol>")
    else:
        add("<p class='lede'>No pending actions were journaled.</p>")
    add("</section>")

    # ---- appendix ----
    add(chapter("appendix"))
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
    add("</section></main></div>")

    # ---- chart data ----
    import json as _json

    opp_pairs = []
    for statement in c.opportunities[:10]:
        match = re.search(r"^(O\d+):", statement)
        score = re.search(r"opportunity (\d+(?:\.\d+)?)", statement)
        if score:
            opp_pairs.append((match.group(1) if match else statement[:14], float(score.group(1))))
    data_json = _json.dumps(
        {
            "register": [counts["supported"], counts["contradicted"], counts["untested"]],
            "oppLabels": [x[0] for x in opp_pairs],
            "oppScores": [x[1] for x in opp_pairs],
            "costLabels": [u.model for u in c.usage],
            "costValues": [round(u.cost_usd, 2) for u in c.usage],
        }
    )
    add(f"<script>window.__bokken={data_json};</script><script>{_JS}</script></body></html>")
    return "".join(parts)
