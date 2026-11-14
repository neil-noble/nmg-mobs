"""The public dashboard: one HTML page, Power BI style, drawn in the browser from embedded data.

Python decides every fact (who is booked, cleared or not, which item is in which state); the
page's script only counts, filters and draws. Names reach the page as JSON and are inserted with
textContent, never as markup.
"""
import json
from datetime import datetime, timedelta
from html import escape

import config as C
from render import fmt_day

#: model state -> the short code the page uses
STATE_CODE = {C.OK: "ok", C.MISSING: "missing", C.EXPIRED: "expired",
              C.NO_DOCUMENT: "nodoc", C.NOT_ON_ROLE: "norole"}


def data(workforce):
    """Everything the page draws, as plain JSON-able values: every worker, booked or not."""
    wf, people = workforce, []

    def booking(bookings):
        if not bookings:
            return {"d": None, "b": "", "m": 0, "w": False}
        first = bookings[0]
        return {"d": first.day.isoformat(), "b": f"{first.kind}: {first.detail}", "m": len(bookings) - 1,
                "w": first.day <= wf.end}

    for w in wf.workers:
        p = w.person
        row = {"n": p.name, "e": p.employer or "(no employer)", "s": w.status}
        row.update(booking(w.bookings))
        if w.status in ("c", "n"):
            states = p.item_states()
            row["st"] = [STATE_CODE[states[i]] for i in C.ITEMS]
        else:
            row["st"] = None
        people.append(row)
    for u in wf.unmatched:
        row = {"n": u.name, "e": u.employer or "(no employer)", "s": "u", "st": None}
        row.update(booking(u.bookings))
        people.append(row)
    days = [(wf.today + timedelta(days=i)).isoformat() for i in range((wf.end - wf.today).days + 1)]
    return {"items": list(C.ITEMS), "days": days, "people": people}



def _json_for_script(value):
    # "<" can never close the <script> block or open a comment once escaped.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def page(workforce, generated: datetime):
    horizon = f"{workforce.horizon:%d %b %Y}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="900"><meta name="robots" content="noindex">'
        # Montserrat stands in for the style guide's Proxima Nova, which has no free web font.
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap">'
        f"<title>{escape(C.TITLE)}</title><style>{CSS}</style></head><body>"
        f'<header><div class="bar"><div><h1>{escape(C.TITLE)}</h1>'
        f"<p>Every Crown Prince worker in PeopleTray against the five mobilisation items: medical, D&amp;A screen, "
        f"police clearance, driver's licence and site induction. Next bookings are read up to {horizon}.</p></div>"
        f'<p class="stamp">Updated {generated:%a %d %b %Y, %H:%M} AWST</p></div></header>'
        f"{BODY}"
        f'<script id="mobs-data" type="application/json">{_json_for_script(data(workforce))}</script>'
        f"<script>{JS}</script></body></html>"
    )


CSS = """
:root{--navy:#083045;--river:#55848A;--pale-gold:#B19045;--river-tint:#AAC2C5;
--ink:#1f2a30;--ink2:#44525a;--muted:#5d6a70;--line:rgba(8,48,69,.12);--grid:rgba(8,48,69,.07);
/* status: green cleared, red not cleared (Neil, 2026-10-24); River tint no work role, Black 50% not matched */
--c:#0f4d1e;--n:#e53935;--r:#AAC2C5;--u:#99999A;
/* frosted glass: the contour plan behind shows through, softened */
--glass:rgba(255,255,255,.5);--glass-strong:rgba(255,255,255,.72);--glass-edge:rgba(255,255,255,.75);
--blur:blur(18px) saturate(150%);--lift:0 1px 1px rgba(8,48,69,.05),0 8px 24px -12px rgba(8,48,69,.22);
--r1:14px;--r2:10px}
*{box-sizing:border-box}
html{background:#EEF2F1}
body{margin:0;background:transparent;color:var(--ink);
font-family:"Proxima Nova",Montserrat,Aptos,"Segoe UI",system-ui,sans-serif;font-size:13px;line-height:1.45;
-webkit-font-smoothing:antialiased}
/* backdrop: soft colour fields in the NMG palette for the glass to pick up (Neil, 2026-11-15: no lines).
Fixed-size tile, every field fades out inside it, so a tall Wix iframe repeats it without a seam. */
body::before{content:"";position:fixed;inset:0;z-index:-1;background-color:#EEF2F1;background-image:radial-gradient(circle 560px at 80% 30%,rgba(226,199,126,.50),rgba(226,199,126,0) 68%),radial-gradient(circle 600px at 10% 58%,rgba(85,132,138,.34),rgba(85,132,138,0) 66%),radial-gradient(circle 480px at 62% 74%,rgba(8,48,69,.13),rgba(8,48,69,0) 68%),radial-gradient(circle 420px at 30% 14%,rgba(170,194,197,.40),rgba(170,194,197,0) 68%);background-size:1600px 1400px;background-position:top center;background-repeat:repeat-y}
.glass{background:var(--glass);-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur);
border:1px solid var(--glass-edge);box-shadow:var(--lift),inset 0 1px 0 rgba(255,255,255,.6)}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){.glass{background:rgba(255,255,255,.92)}}
@media (prefers-reduced-transparency:reduce){.glass{background:#fff;-webkit-backdrop-filter:none;backdrop-filter:none}}
/* header: navy glass over the plan, gold rule from the style guide */
header{background:rgba(8,48,69,.86);-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur);color:#fff;
border-bottom:3px solid var(--pale-gold)}
header .bar{max-width:1440px;margin:0 auto;padding:18px 16px 16px;display:flex;justify-content:space-between;
align-items:flex-end;gap:8px 24px;flex-wrap:wrap}
header h1{margin:0;font-size:24px;font-weight:800;line-height:1.1;letter-spacing:-.01em}
header p{margin:6px 0 0;font-size:12.5px;color:#cfdcde;max-width:72ch}
header .stamp{margin:0;font-size:12px;color:#E2C77E;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.canvas{max-width:1440px;margin:0 auto;padding:14px 16px 40px}
/* groups: one question each, in the order a coordinator works */
.group{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px;margin-top:30px}
.gh{grid-column:1/-1;display:flex;align-items:baseline;gap:6px 14px;flex-wrap:wrap;padding:0 2px}
.gh h2{margin:0;font-size:18px;font-weight:800;color:var(--navy);letter-spacing:-.005em}
.gh p{margin:0;font-size:12.5px;color:var(--muted)}
.v{grid-column:span var(--span,12);border-radius:var(--r1);padding:14px 16px 16px;min-width:0}
.v h3,.vhead h3{margin:0 0 2px;font-size:13.5px;font-weight:700;color:var(--ink)}
.v .sub,.vhead .sub{margin:0 0 12px;font-size:11.5px;color:var(--muted)}
.vhead{display:flex;justify-content:space-between;align-items:flex-start;gap:8px 12px;flex-wrap:wrap}
.vhead .clear{margin-bottom:8px}
.clear:disabled{opacity:.5;cursor:default}
.note{color:var(--muted);font-size:11.5px;margin:8px 0 0}
.empty{color:var(--muted);font-style:italic;margin:6px 0}
/* the action list carries the page: stronger glass, navy edge */
.v.primary{background:var(--glass-strong);border-left:4px solid var(--n);padding-left:18px}
/* slicers: a frosted bar that stays in reach while scrolling */
.slicers{position:sticky;top:8px;z-index:5;display:flex;flex-wrap:wrap;gap:10px 14px;align-items:end;
padding:10px 14px;border-radius:var(--r1)}
.slicer{display:flex;flex-direction:column;gap:3px;min-width:180px;flex:0 1 260px}
.slicer label{font-size:11.5px;color:var(--ink2);font-weight:700}
.slicer select,.slicer input{font:inherit;padding:7px 9px;border:1px solid rgba(8,48,69,.28);border-radius:8px;
background:rgba(255,255,255,.8);color:var(--ink);width:100%}
.slicer select:focus,.slicer input:focus,button:focus-visible,[tabindex]:focus-visible,summary:focus-visible{
outline:2px solid var(--navy);outline-offset:2px}
.clear{font:inherit;padding:7px 14px;border:1px solid var(--navy);background:rgba(255,255,255,.7);color:var(--navy);
border-radius:8px;cursor:pointer;font-weight:600}
.clear:hover:not(:disabled){background:var(--navy);color:#fff}
.clear[hidden]{display:none}
.chip{font-size:12px;color:var(--ink2);padding:7px 0;font-variant-numeric:tabular-nums}
/* stat tiles: the not-cleared count leads, the rest support it */
.kpis{grid-column:span 7;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:auto;gap:12px}
.kpis>.v{grid-column:auto}
.kpi{display:flex;flex-direction:column;gap:2px;border-top:3px solid var(--navy);padding:12px 14px}
.kpi .lab{font-size:12px;color:var(--ink2)}
.kpi .val{font-size:28px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi .val small{font-size:13px;font-weight:600;color:var(--muted);margin-left:4px}
.kpi.hero{grid-column:1/-1;flex-direction:row;align-items:center;gap:6px 22px;flex-wrap:wrap;padding:16px 18px}
.kpi.hero .val{font-size:56px;font-weight:800;letter-spacing:-.02em}
.kpi.hero .lab{font-size:15px;font-weight:700;color:var(--ink)}
.kpi.hero .say{flex:1 1 240px;font-size:13px;color:var(--ink2);max-width:52ch}
.meter{height:6px;border-radius:3px;background:rgba(8,48,69,.1);overflow:hidden;margin-top:6px}
.meter i{display:block;height:100%;background:var(--c);border-radius:3px}
.status-donut{grid-column:span 5}
/* legend */
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11.5px;color:var(--ink2);margin:0 0 10px}
.legend span{display:inline-flex;align-items:center;gap:5px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.15)}
/* donut */
.donut{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.donut svg{width:170px;height:170px;flex:none}
.donut .seg{cursor:default;transition:opacity .15s}
.donut .seg:hover{opacity:.82}
.donut ul{list-style:none;margin:0;padding:0;flex:1;min-width:150px}
.donut li{display:grid;grid-template-columns:12px 1fr auto auto;gap:6px;align-items:center;padding:6px 0;
border-bottom:1px solid var(--grid);font-size:12.5px}
.donut li b{font-variant-numeric:tabular-nums;text-align:right}
.donut li em{font-style:normal;color:var(--muted);width:38px;text-align:right;font-variant-numeric:tabular-nums}
.donut .big{font-size:22px;font-weight:700;fill:var(--ink)}
.donut .cap{font-size:9px;fill:var(--muted)}
/* horizontal bars */
.hb{display:grid;grid-template-columns:minmax(90px,34%) 1fr;gap:5px 10px;align-items:center}
.hb .lab{font-size:12px;text-align:right;color:var(--ink);background:none;border:0;padding:3px 0;font:inherit;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}
.hb .lab.static{cursor:default;color:var(--ink2)}
.hb .lab:hover:not(.static){text-decoration:underline}
.hb .lab.on{font-weight:700}
.track{display:flex;align-items:center;gap:6px;min-width:0}
.sbar{display:flex;gap:2px;height:16px;flex:0 0 auto;cursor:pointer}
.sbar.static{cursor:default}
.sbar i,.stack i{box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)}  /* keeps Sand and the tints visible on glass */
.sbar i{display:block;height:100%;min-width:2px}
.sbar i:last-child{border-radius:0 4px 4px 0}
.rail{flex:0 0 calc(100% - 132px);height:16px;background:rgba(8,48,69,.08);border-radius:0 4px 4px 0;display:flex;cursor:pointer}
.rail i{display:block;height:100%;background:var(--n);border-radius:0 4px 4px 0}
.track .val{font-size:11.5px;color:var(--ink2);white-space:nowrap;font-variant-numeric:tabular-nums}
.track .val b{color:var(--ink)}
.dim{opacity:.32}
/* columns */
.cols{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);align-items:end;height:200px;
border-bottom:1px solid rgba(8,48,69,.35);gap:2px;padding-top:16px}
.col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0}
.col .tot{font-size:11px;color:var(--ink2);font-variant-numeric:tabular-nums;margin-bottom:2px}
.stack{display:flex;flex-direction:column-reverse;gap:2px;width:min(26px,80%)}
.stack i{display:block;width:100%}
.stack i:last-child{border-radius:4px 4px 0 0}
.xl{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:2px;margin-top:4px}
.xl span{font-size:10.5px;color:var(--muted);text-align:center;line-height:1.2;font-variant-numeric:tabular-nums}
.xl span.today{color:var(--ink);font-weight:700}
/* tables */
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
thead th{font-weight:700;border-bottom:2px solid var(--navy);white-space:nowrap}
tbody tr:nth-child(even){background:rgba(255,255,255,.4)}
tbody tr:hover{background:rgba(241,220,170,.55)}
td.when{white-space:nowrap;font-variant-numeric:tabular-nums}
td.st,th.st{text-align:center;white-space:nowrap}
.more{color:var(--muted);font-size:11.5px}
.pill{display:inline-flex;align-items:center;gap:5px;padding:1px 8px 1px 6px;border-radius:9px;font-size:11.5px;
font-weight:600;color:var(--ink)}
.pill i{width:8px;height:8px;border-radius:50%;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.2)}
.tick{color:#0f4d1e;font-weight:700}
/* accordions: reference material, folded */
.fold{padding:0;overflow:hidden}
.fold>summary{list-style:none;cursor:pointer;display:flex;align-items:baseline;gap:4px 12px;flex-wrap:wrap;
padding:13px 44px 13px 16px;position:relative}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary::after{content:"";position:absolute;right:18px;top:18px;width:8px;height:8px;
border-right:2px solid var(--navy);border-bottom:2px solid var(--navy);transform:rotate(45deg);transition:transform .2s ease}
.fold[open]>summary::after{transform:rotate(-135deg);top:21px}
.fold>summary:hover{background:rgba(255,255,255,.35)}
.fold>summary .t{font-size:13.5px;font-weight:700;color:var(--ink)}
.fold>summary .sub{margin:0;font-size:11.5px;color:var(--muted)}
.fold>.body{padding:0 16px 16px}
.fold.inline{grid-column:1/-1;background:transparent;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none}
.fold.inline>summary{padding:4px 30px 4px 2px}
.fold.inline>summary::after{right:8px;top:8px}
.fold.inline[open]>summary::after{top:11px}
.fold.inline>.body{padding:0 2px 4px}
.fold.inline .note{margin:4px 0 0;max-width:110ch}
@media (prefers-reduced-motion:reduce){.fold>summary::after{transition:none}}
/* tooltip */
.tip{position:fixed;z-index:10;display:none;pointer-events:none;background:rgba(255,255,255,.82);
-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur);border:1px solid var(--glass-edge);
border-radius:var(--r2);box-shadow:0 10px 30px -10px rgba(8,48,69,.35);padding:8px 10px;font-size:12px;min-width:140px;max-width:260px}
.tip .tt{font-weight:700;margin-bottom:4px;color:var(--ink)}
.tip .tr{display:grid;grid-template-columns:12px auto 1fr;gap:6px;align-items:center}
.tip .tr i{display:block;width:12px;height:2px}
.tip .tr b{font-variant-numeric:tabular-nums}
.tip .tr span{color:var(--ink2)}
.group>.v{align-self:stretch}
.group>.v.top{align-self:start}
@media (max-width:1100px){.kpis,.status-donut{grid-column:1/-1}}
@media (max-width:900px){.group>.v,.group>details{grid-column:1/-1}.slicers{position:static}
.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi.hero .val{font-size:44px}
.hb{grid-template-columns:minmax(80px,38%) 1fr}header .bar{padding-top:14px}}
"""

BODY = """
<main class="canvas">
<noscript><section class="v glass"><p>This dashboard needs JavaScript to draw its charts.</p></section></noscript>
<div class="slicers glass" role="search">
  <div class="slicer"><label for="f-bk">Bookings</label><select id="f-bk">
    <option value="">All workers</option><option value="w">Booked in the next 14 days</option>
    <option value="l">Booked later</option><option value="x">No booking</option></select></div>
  <div class="slicer"><label for="f-emp">Employer</label><select id="f-emp"></select></div>
  <div class="slicer"><label for="f-q">Find a person</label><input id="f-q" type="search" placeholder="Name" autocomplete="off"></div>
  <button class="clear" id="f-clear" type="button" hidden>Clear filters</button>
  <span class="chip" id="f-chip"></span>
</div>

<section class="group" aria-labelledby="g-status">
  <div class="gh"><h2 id="g-status">Where things stand</h2><p>Who can mobilise today, and what is holding the rest back</p></div>
  <div class="kpis" id="kpis"></div>
  <section class="v glass status-donut"><h3>Mobilisation status</h3><p class="sub">Every worker in the selection</p>
    <div id="donut"></div></section>
</section>

<section class="group" aria-labelledby="g-chase">
  <div class="gh"><h2 id="g-chase">Who to chase</h2><p>Each person below is missing at least one item. Clear these before they travel.</p></div>
  <section class="v glass primary top"><div class="vhead"><div><h3 id="h-n">Not cleared to mobilise</h3>
    <p class="sub">By employer A&ndash;Z, then next booking. People with no booking come last.</p></div>
    <button class="clear" id="x-n" type="button">Download Excel</button></div>
    <div id="tbl-n"></div></section>
  <details class="fold inline"><summary><span class="t">What the states mean</span></summary><div class="body">
    <p class="note"><b>Missing</b> = no document added (induction: not yet completed). <b>Expired</b> = the document or
    competency has expired. <b>No document</b> = marked competent but nothing uploaded. <b>Not on role</b> = the
    person's work role in PeopleTray does not ask for this item, so it has never been recorded; fix the work role.
    Medical = Pre Employment Medical, or a Medical Declaration for Short Term Workers.</p></div></details>
</section>

<section class="group" aria-labelledby="g-gaps">
  <div class="gh"><h2 id="g-gaps">Where the gaps are</h2><p>Which items are missing, and which employers to follow up. Click an employer to filter the page.</p></div>
  <section class="v glass" style="--span:5"><h3>What is missing</h3><p class="sub">Workers not cleared, by item and gap type. One person can lack several items.</p>
    <div id="items"></div></section>
  <section class="v glass" style="--span:7"><h3>Not cleared by employer</h3><p class="sub">Share of each employer's workers who
    are not cleared, highest first</p>
    <div id="emppct"></div></section>
  <section class="v glass"><h3>Workers by employer</h3><p class="sub">By status, most not cleared first</p>
    <div id="emp"></div></section>
</section>

<section class="group" aria-labelledby="g-arrive">
  <div class="gh"><h2 id="g-arrive">Who is arriving</h2><p>Next booking by day for the coming 14 days. Today includes people already on site.</p></div>
  <section class="v glass"><div id="days"></div></section>
</section>

<section class="group" aria-labelledby="g-lists">
  <div class="gh"><h2 id="g-lists">Other lists</h2><p>Open a list to see who is in it</p></div>
  <details class="v glass fold"><summary><span class="t" id="h-r">No work role in PeopleTray</span>
    <span class="sub">Cannot be checked until a work role is set</span></summary><div class="body" id="tbl-r"></div></details>
  <details class="v glass fold" id="card-u" hidden><summary><span class="t" id="h-u">Bookings not matched to a PeopleTray profile</span>
    <span class="sub">Check the name or work email on the booking</span></summary><div class="body" id="tbl-u"></div></details>
  <details class="v glass fold"><summary><span class="t" id="h-c">Cleared to mobilise</span>
    <span class="sub">Every item held</span></summary><div class="body" id="tbl-c"></div></details>
</section>
</main>
"""

JS = r"""
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("mobs-data").textContent);
  var STATUS = [
    {k: "c", label: "Cleared", color: "#0f4d1e"},
    {k: "n", label: "Not cleared", color: "#e53935"},
    {k: "r", label: "No work role", color: "#AAC2C5"},
    {k: "u", label: "Not matched", color: "#99999A"}
  ];
  var GAP = [
    {k: "missing", label: "Missing", color: "#c62f3f"},
    {k: "expired", label: "Expired", color: "#e07b12"},
    {k: "nodoc", label: "No document", color: "#F1DCAA"},
    {k: "norole", label: "Not on role", color: "#8498A2"}
  ];
  var GAPBY = {};
  GAP.forEach(function (g) { GAPBY[g.k] = g; });
  var F = {emp: "", q: "", bk: ""};
  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var SVGNS = "http://www.w3.org/2000/svg";

  // The page reloads itself every 15 minutes; keep this viewer's filters across reloads.
  try { var saved = JSON.parse(sessionStorage.getItem("mobs-filters") || "null"); if (saved) F = saved; } catch (e) {}
  F.bk = F.bk || "";
  function saveFilters() { try { sessionStorage.setItem("mobs-filters", JSON.stringify(F)); } catch (e) {} }

  function h(tag, props, kids) {
    var el = document.createElement(tag);
    if (props) Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k === "style") el.style.cssText = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    });
    (kids || []).forEach(function (c) {
      if (c == null) return;
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  }
  function sv(tag, attrs) {
    var el = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    return el;
  }
  function day(iso) {
    var d = new Date(iso + "T00:00:00");
    return {dow: DOW[d.getDay()], n: d.getDate(), mon: MON[d.getMonth()]};
  }
  function fmtDay(iso) { if (!iso) return "No booking"; var d = day(iso); return d.dow + " " + d.n + " " + d.mon; }
  function pct(a, b) { return b ? Math.round(100 * a / b) + "%" : "–"; }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  // ── tooltip: values lead, labels follow; built with textContent only ──────────
  var tip = h("div", {"class": "tip", role: "tooltip"});
  document.body.appendChild(tip);
  var TIPS = new WeakMap();
  function showTip(el, x, y) {
    var t = TIPS.get(el);
    if (!t) return;
    tip.replaceChildren(h("div", {"class": "tt", text: t.title}));
    t.rows.forEach(function (r) {
      tip.appendChild(h("div", {"class": "tr"}, [h("i", {style: "background:" + r.color}),
        h("b", {text: String(r.v)}), h("span", {text: r.l})]));
    });
    tip.style.display = "block";
    var w = tip.offsetWidth, ht = tip.offsetHeight;
    var left = Math.min(x + 14, window.innerWidth - w - 8);
    var top = y + 14 + ht > window.innerHeight ? y - ht - 10 : y + 14;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }
  function hideTip() { tip.style.display = "none"; }
  function withTip(el, title, rows) {
    TIPS.set(el, {title: title, rows: rows});
    el.addEventListener("pointermove", function (e) { showTip(el, e.clientX, e.clientY); });
    el.addEventListener("pointerleave", hideTip);
    el.addEventListener("focus", function () { var r = el.getBoundingClientRect(); showTip(el, r.left, r.bottom); });
    el.addEventListener("blur", hideTip);
    return el;
  }
  function legend(list) {
    return h("div", {"class": "legend"}, list.map(function (s) {
      return h("span", null, [h("i", {"class": "sw", style: "background:" + s.color}), s.label]);
    }));
  }

  // ── data slices ───────────────────────────────────────────────────────────────
  function rows(ignoreEmployer) {
    var q = F.q.trim().toLowerCase();
    return D.people.filter(function (p) {
      var bk = !F.bk || (F.bk === "w" ? p.w : F.bk === "l" ? p.d && !p.w : !p.d);
      return bk && (ignoreEmployer || !F.emp || p.e === F.emp) && (!q || p.n.toLowerCase().indexOf(q) >= 0);
    });
  }
  function countBy(list, key) {
    var c = {};
    list.forEach(function (p) { c[p[key]] = (c[p[key]] || 0) + 1; });
    return c;
  }
  function presentStatuses(list) {
    var c = countBy(list, "s");
    return STATUS.filter(function (s) { return s.k !== "u" || c.u; });
  }

  // ── slicers ───────────────────────────────────────────────────────────────────
  var sel = document.getElementById("f-emp"), q = document.getElementById("f-q"), bkSel = document.getElementById("f-bk");
  var clearBtn = document.getElementById("f-clear"), chip = document.getElementById("f-chip");
  (function fillEmployers() {
    var c = countBy(D.people, "e");
    sel.appendChild(h("option", {value: "", text: "All employers (" + D.people.length + ")"}));
    Object.keys(c).sort(function (a, b) { return a.localeCompare(b); }).forEach(function (e) {
      sel.appendChild(h("option", {value: e, text: e + " (" + c[e] + ")"}));
    });
  })();
  sel.addEventListener("change", function () { F.emp = sel.value; render(); });
  q.addEventListener("input", function () { F.q = q.value; render(); });
  bkSel.addEventListener("change", function () { F.bk = bkSel.value; render(); });
  clearBtn.addEventListener("click", function () { F = {emp: "", q: "", bk: ""}; render(); });
  function setEmployer(e) { F.emp = F.emp === e ? "" : e; render(); }

  // ── stat tiles ────────────────────────────────────────────────────────────────
  function kpis(R) {
    var c = countBy(R, "s"), ok = c.c || 0, bad = c.n || 0, nr = c.r || 0, checked = ok + bad;
    var box = document.getElementById("kpis");
    box.replaceChildren();
    function tile(label, value, color, extra, tone, cls) {
      // tone: the tile itself reads green / red - tinted glass, coloured figure (Neil, 2026-10-24)
      var style = "border-top-color:" + color + (tone ? ";background:color-mix(in srgb," + color + " 9%,rgba(255,255,255,.62))" : "");
      if (tone) value.style.color = tone;
      box.appendChild(h("div", {"class": "v glass kpi" + (cls ? " " + cls : ""), style: style},
        [value, h("span", {"class": "lab", text: label}), extra || null]));
    }
    var who = F.bk === "w" ? "booked in the next 14 days" : F.bk === "l" ? "booked later" : F.bk === "x" ? "with no booking" : "";
    tile("Not cleared to mobilise", h("span", {"class": "val", text: String(bad)}), STATUS[1].color,
      h("span", {"class": "say", text: bad
        ? plural(bad, "worker", "workers") + (who ? " " + who : "") + " of " + R.length + " cannot mobilise until every item is held. The list is under Who to chase."
        : "Everyone in this selection with a work role holds all five items."}), "#b3261e", "hero");
    tile("Cleared to mobilise", h("span", {"class": "val", text: String(ok)}), STATUS[0].color, null, "#0f4d1e");
    var meter = h("div", {"class": "meter", role: "img", "aria-label": "Readiness " + pct(ok, checked)},
      [h("i", {style: "width:" + (checked ? 100 * ok / checked : 0) + "%"})]);
    tile("Ready, of workers with a work role",
      h("span", {"class": "val"}, [pct(ok, checked), h("small", {text: ok + " of " + checked})]), "#55848A", meter);
    tile("No work role in PeopleTray", h("span", {"class": "val", text: String(nr)}), STATUS[2].color);
  }

  // ── donut: part-to-whole of the booked people ─────────────────────────────────
  function donut(R) {
    var box = document.getElementById("donut");
    box.replaceChildren();
    if (!R.length) { box.appendChild(h("p", {"class": "empty", text: "No workers match the filters."})); return; }
    var c = countBy(R, "s"), segs = presentStatuses(R).filter(function (s) { return c[s.k]; });
    var r = 40, C = 2 * Math.PI * r, gap = segs.length > 1 ? 1.2 : 0, at = 0;
    var svg = sv("svg", {viewBox: "0 0 100 100", role: "img",
      "aria-label": segs.map(function (s) { return s.label + " " + c[s.k]; }).join(", ")});
    svg.appendChild(sv("circle", {cx: 50, cy: 50, r: r, fill: "none", stroke: "#EDEDE9", "stroke-width": 14}));
    segs.forEach(function (s) {
      var len = C * c[s.k] / R.length;
      var arc = sv("circle", {cx: 50, cy: 50, r: r, fill: "none", stroke: s.color, "stroke-width": 14,
        "stroke-dasharray": Math.max(0.01, len - gap) + " " + (C - Math.max(0.01, len - gap)),
        "stroke-dashoffset": -at, transform: "rotate(-90 50 50)", "class": "seg", tabindex: 0});
      withTip(arc, s.label, [{v: c[s.k], l: pct(c[s.k], R.length) + " of " + R.length + " workers", color: s.color}]);
      svg.appendChild(arc);
      at += len;
    });
    var checked = (c.c || 0) + (c.n || 0);
    var big = sv("text", {x: 50, y: 50, "text-anchor": "middle", "class": "big"});
    big.textContent = pct(c.c || 0, checked);
    var cap = sv("text", {x: 50, y: 62, "text-anchor": "middle", "class": "cap"});
    cap.textContent = "ready";
    svg.appendChild(big); svg.appendChild(cap);
    var list = h("ul", null, segs.map(function (s) {
      return h("li", null, [h("i", {"class": "sw", style: "background:" + s.color}), s.label,
        h("b", {text: String(c[s.k])}), h("em", {text: pct(c[s.k], R.length)})]);
    }));
    box.appendChild(h("div", {"class": "donut"}, [svg, list]));
  }

  // ── stacked horizontal bars ───────────────────────────────────────────────────
  var LABEL_ROOM = 132;   // px kept free after the longest bar for its value label
  function stackedBar(parts, max, isStatic, title) {
    var bar = h("div", {"class": "sbar" + (isStatic ? " static" : "")});
    var total = 0;
    parts.forEach(function (p) { total += p.v; });
    bar.style.width = "calc((100% - " + LABEL_ROOM + "px) * " + (max ? total / max : 0) + ")";
    parts.forEach(function (p) {
      if (!p.v) return;
      bar.appendChild(h("i", {style: "flex:" + p.v + " 1 0;background:" + p.color}));
    });
    withTip(bar, title, parts.filter(function (p) { return p.v; })
      .map(function (p) { return {v: p.v, l: p.label, color: p.color}; }));
    return bar;
  }

  function employers(R) {
    var box = document.getElementById("emp");
    box.replaceChildren();
    if (!R.length) { box.appendChild(h("p", {"class": "empty", text: "No workers match the filters."})); return; }
    var statuses = presentStatuses(R), by = {};
    R.forEach(function (p) {
      var e = by[p.e] || (by[p.e] = {name: p.e, t: 0});
      e[p.s] = (e[p.s] || 0) + 1; e.t += 1;
    });
    var list = Object.keys(by).map(function (k) { return by[k]; }).sort(function (a, b) {
      return (b.n || 0) - (a.n || 0) || b.t - a.t || a.name.localeCompare(b.name);
    });
    var TOP = 12, shown = list.slice(0, TOP), rest = list.slice(TOP);
    if (F.emp && shown.every(function (e) { return e.name !== F.emp; })) {
      var picked = list.filter(function (e) { return e.name === F.emp; });
      if (picked.length) { shown.push(picked[0]); rest = rest.filter(function (e) { return e.name !== F.emp; }); }
    }
    if (rest.length) {
      var other = {name: "Other (" + plural(rest.length, "employer", "employers") + ")", t: 0, other: true};
      rest.forEach(function (e) { STATUS.forEach(function (s) { other[s.k] = (other[s.k] || 0) + (e[s.k] || 0); }); other.t += e.t; });
      shown.push(other);
    }
    var max = Math.max.apply(null, shown.map(function (e) { return e.t; }));
    box.appendChild(legend(statuses));
    var grid = h("div", {"class": "hb"});
    shown.forEach(function (e) {
      var dim = F.emp && e.name !== F.emp ? " dim" : "";
      var label = e.other
        ? h("span", {"class": "lab static" + dim, text: e.name, title: e.name})
        : h("button", {"class": "lab" + (F.emp === e.name ? " on" : "") + dim, type: "button", text: e.name,
            title: e.name, "aria-pressed": String(F.emp === e.name), onclick: function () { setEmployer(e.name); }});
      var parts = statuses.map(function (s) { return {v: e[s.k] || 0, label: s.label, color: s.color}; });
      var bar = stackedBar(parts, max, e.other, e.name);
      if (!e.other) bar.addEventListener("click", function () { setEmployer(e.name); });
      var val = h("span", {"class": "val"}, [h("b", {text: String(e.n || 0)}), " not cleared of " + e.t]);
      grid.appendChild(label);
      grid.appendChild(h("div", {"class": "track" + dim}, [bar, val]));
    });
    box.appendChild(grid);
  }

  // ── % of each employer's booked people not cleared ────────────────────────────
  function employerShare(R) {
    var box = document.getElementById("emppct");
    box.replaceChildren();
    var by = {};
    R.forEach(function (p) {
      var e = by[p.e] || (by[p.e] = {name: p.e, n: 0, t: 0});
      e.t += 1; if (p.s === "n") e.n += 1;
    });
    var all = Object.keys(by).map(function (k) { return by[k]; });
    var list = all.filter(function (e) { return e.n; }).sort(function (a, b) {
      return b.n / b.t - a.n / a.t || b.n - a.n || a.name.localeCompare(b.name);
    });
    if (!list.length) { box.appendChild(h("p", {"class": "empty", text: "Nobody in this selection is not cleared."})); return; }
    var grid = h("div", {"class": "hb"});
    list.forEach(function (e) {
      var dim = F.emp && e.name !== F.emp ? " dim" : "", share = 100 * e.n / e.t;
      var rail = h("div", {"class": "rail", role: "img", "aria-label": e.name + ": " + e.n + " of " + e.t + " not cleared"},
        [h("i", {style: "width:" + Math.max(share, 1) + "%"})]);
      withTip(rail, e.name, [{v: e.n, l: "not cleared", color: STATUS[1].color},
                             {v: e.t, l: "workers", color: "#EDEDE9"},
                             {v: pct(e.n, e.t), l: "not cleared", color: STATUS[1].color}]);
      rail.addEventListener("click", function () { setEmployer(e.name); });
      grid.appendChild(h("button", {"class": "lab" + (F.emp === e.name ? " on" : "") + dim, type: "button", text: e.name,
        title: e.name, "aria-pressed": String(F.emp === e.name), onclick: function () { setEmployer(e.name); }}));
      grid.appendChild(h("div", {"class": "track" + dim}, [rail,
        h("span", {"class": "val"}, [h("b", {text: pct(e.n, e.t)}), " · " + e.n + " of " + e.t])]));
    });
    box.appendChild(grid);
    var clear = all.length - list.length;
    if (clear) box.appendChild(h("p", {"class": "note", text: plural(clear, "other employer has", "other employers have") +
      " nobody not cleared."}));
  }

  function items(R) {
    var box = document.getElementById("items");
    box.replaceChildren();
    var bad = R.filter(function (p) { return p.s === "n"; });
    if (!bad.length) { box.appendChild(h("p", {"class": "empty", text: "Nobody in this selection is missing an item."})); return; }
    var rowsData = D.items.map(function (item, i) {
      var c = {};
      bad.forEach(function (p) { var st = p.st[i]; if (st !== "ok") c[st] = (c[st] || 0) + 1; });
      var total = 0;
      GAP.forEach(function (g) { total += c[g.k] || 0; });
      return {item: item, c: c, t: total};
    });
    var max = Math.max(1, Math.max.apply(null, rowsData.map(function (r) { return r.t; })));
    box.appendChild(legend(GAP));
    var grid = h("div", {"class": "hb"});
    rowsData.forEach(function (r) {
      var parts = GAP.map(function (g) { return {v: r.c[g.k] || 0, label: g.label, color: g.color}; });
      grid.appendChild(h("span", {"class": "lab static", text: r.item}));
      grid.appendChild(h("div", {"class": "track"}, [stackedBar(parts, max, true, r.item),
        h("span", {"class": "val"}, [h("b", {text: String(r.t)}), r.t === 1 ? " person" : " people"])]));
    });
    box.appendChild(grid);
  }

  // ── columns by day of first booking ───────────────────────────────────────────
  function days(R) {
    var box = document.getElementById("days");
    box.replaceChildren();
    var statuses = presentStatuses(R), by = {};
    R = R.filter(function (p) { return p.w; });
    R.forEach(function (p) { var d = by[p.d] || (by[p.d] = {t: 0}); d[p.s] = (d[p.s] || 0) + 1; d.t += 1; });
    var max = Math.max(1, Math.max.apply(null, D.days.map(function (d) { return by[d] ? by[d].t : 0; })));
    var PLOT = 168;
    box.appendChild(legend(statuses));
    var cols = h("div", {"class": "cols", role: "img", "aria-label": "People by day of first booking"});
    var xl = h("div", {"class": "xl"});
    D.days.forEach(function (d, i) {
      var v = by[d] || {t: 0};
      var stack = h("div", {"class": "stack"});
      statuses.forEach(function (s) {
        if (v[s.k]) stack.appendChild(h("i", {style: "height:" + Math.max(2, PLOT * v[s.k] / max) + "px;background:" + s.color}));
      });
      var col = h("div", {"class": "col", tabindex: v.t ? 0 : -1},
        [v.t ? h("span", {"class": "tot", text: String(v.t)}) : null, stack]);
      if (v.t) withTip(col, (i === 0 ? "Today, " : "") + fmtDay(d), statuses.filter(function (s) { return v[s.k]; })
        .map(function (s) { return {v: v[s.k], l: s.label, color: s.color}; }));
      cols.appendChild(col);
      var dd = day(d);
      xl.appendChild(h("span", {"class": i === 0 ? "today" : ""}, [i === 0 ? "Today" : dd.dow, h("br"), String(dd.n)]));
    });
    box.appendChild(cols);
    box.appendChild(xl);
  }

  // ── tables (the table view of every chart) ────────────────────────────────────
  function bookingCell(p) {
    if (!p.d) return h("td", {"class": "more", text: "–"});
    return h("td", null, [p.b, p.m ? h("span", {"class": "more", text: " +" + p.m + " more"}) : null]);
  }
  // Neil, 2026-10-24: in the tables No document reads red like Missing (the chart keeps Sand to tell them apart).
  var TABLE_TONE = {nodoc: "#c62f3f"};
  function stateCell(code) {
    if (code === "ok") return h("td", {"class": "st"}, [h("span", {"class": "tick", text: "✓", "aria-label": "Held"})]);
    var g = GAPBY[code], color = TABLE_TONE[code] || g.color;
    return h("td", {"class": "st"}, [h("span", {"class": "pill",
      style: "background:color-mix(in srgb," + color + " 15%,#fff)"}, [h("i", {style: "background:" + color}), g.label])]);
  }
  function table(boxId, list, withItems, empty) {
    var box = document.getElementById(boxId);
    box.replaceChildren();
    if (!list.length) { box.appendChild(h("p", {"class": "empty", text: empty})); return; }
    var head = ["Name", "Employer", "Next booking", "Booking"].map(function (t) { return h("th", {text: t}); });
    if (withItems) D.items.forEach(function (t) { head.push(h("th", {"class": "st", text: t})); });
    var body = h("tbody");
    list.forEach(function (p) {
      var cells = [h("td", {text: p.n}), h("td", {text: p.e}), h("td", {"class": "when", text: fmtDay(p.d)}), bookingCell(p)];
      if (withItems) p.st.forEach(function (code) { cells.push(stateCell(code)); });
      body.appendChild(h("tr", null, cells));
    });
    box.appendChild(h("div", {"class": "scroll"}, [h("table", null, [h("thead", null, [h("tr", null, head)]), body])]));
  }
  function byDayThenName(a, b) {
    return (!a.d - !b.d) || (a.d && b.d ? a.d.localeCompare(b.d) : 0) || a.n.localeCompare(b.n);
  }
  // Neil, 2026-10-25: the not-cleared table reads by employer A-Z first.
  function byEmployer(a, b) { return a.e.localeCompare(b.e) || byDayThenName(a, b); }
  var notCleared = [];   // what the not-cleared table shows now - the Excel download writes exactly this
  function tables(R) {
    function of(s, order) { return R.filter(function (p) { return p.s === s; }).sort(order || byDayThenName); }
    var n = of("n", byEmployer), r = of("r"), u = of("u"), c = of("c");
    notCleared = n;
    document.getElementById("x-n").disabled = !n.length;
    document.getElementById("h-n").textContent = "Not cleared to mobilise (" + n.length + ")";
    document.getElementById("h-r").textContent = "No work role in PeopleTray (" + r.length + ")";
    document.getElementById("h-u").textContent = "Bookings not matched to a PeopleTray profile (" + u.length + ")";
    document.getElementById("h-c").textContent = "Cleared to mobilise (" + c.length + ")";
    document.getElementById("card-u").hidden = !u.length;
    table("tbl-n", n, true, "Nobody in this selection is missing an item.");
    table("tbl-r", r, false, "Everyone in this selection has a work role.");
    table("tbl-u", u, false, "");
    table("tbl-c", c, true, "Nobody in this selection is cleared yet.");
  }

  // ── Excel download of the not-cleared table (ExcelJS, fetched on first click) ──
  var EXCELJS = "https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.4.0/exceljs.min.js";
  var EXCELJS_SRI = "sha512-dlPw+ytv/6JyepmelABrgeYgHI0O+frEwgfnPdXDTOIZz+eDgfW07QXG02/O8COfivBdGNINy+Vex+lYmJ5rxw==";
  var excelLoad = null;
  function loadExcel() {
    if (window.ExcelJS) return Promise.resolve(window.ExcelJS);
    if (!excelLoad) excelLoad = new Promise(function (ok, fail) {
      var s = h("script", {src: EXCELJS, integrity: EXCELJS_SRI, crossorigin: "anonymous", referrerpolicy: "no-referrer"});
      s.onload = function () { ok(window.ExcelJS); };
      s.onerror = function () { excelLoad = null; fail(new Error("Could not load the Excel library")); };
      document.head.appendChild(s);
    });
    return excelLoad;
  }
  function argb(hex) { return "FF" + hex.slice(1).toUpperCase(); }
  function downloadExcel() {
    var btn = document.getElementById("x-n"), list = notCleared.slice();
    if (!list.length) return;
    btn.disabled = true; btn.textContent = "Preparing…";
    loadExcel().then(function (ExcelJS) {
      var wb = new ExcelJS.Workbook();
      var ws = wb.addWorksheet("Not cleared", {views: [{state: "frozen", ySplit: 1}]});
      ws.columns = [{header: "Name", width: 28}, {header: "Employer", width: 34},
        {header: "Next booking", width: 16, style: {numFmt: "ddd d mmm yyyy"}}, {header: "Booking", width: 42}]
        .concat(D.items.map(function (t) { return {header: t, width: 16}; }));
      list.forEach(function (p) {
        var d = p.d ? p.d.split("-").map(Number) : null;
        var row = ws.addRow([p.n, p.e, d ? new Date(Date.UTC(d[0], d[1] - 1, d[2])) : "No booking",
          p.b + (p.m ? " (+" + p.m + " more)" : "")]
          .concat(p.st.map(function (code) { return code === "ok" ? "Held" : GAPBY[code].label; })));
        p.st.forEach(function (code, i) {
          var cell = row.getCell(5 + i);
          cell.alignment = {horizontal: "center"};
          if (code === "ok") { cell.font = {color: {argb: argb("#0f4d1e")}}; return; }
          var color = TABLE_TONE[code] || GAPBY[code].color;
          cell.font = {bold: true};
          cell.fill = {type: "pattern", pattern: "solid", fgColor: {argb: argb(color)}};
          if (color === "#c62f3f") cell.font = {bold: true, color: {argb: "FFFFFFFF"}};
        });
      });
      var head = ws.getRow(1);
      head.font = {bold: true, color: {argb: "FFFFFFFF"}};
      head.fill = {type: "pattern", pattern: "solid", fgColor: {argb: argb("#083045")}};
      head.alignment = {vertical: "middle"};
      ws.autoFilter = {from: {row: 1, column: 1}, to: {row: 1, column: 4 + D.items.length}};
      return wb.xlsx.writeBuffer();
    }).then(function (buf) {
      var url = URL.createObjectURL(new Blob([buf],
        {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));
      var a = h("a", {href: url, download: "NMG not cleared to mobilise " + D.days[0] + ".xlsx"});
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    }).catch(function (e) {
      alert("The Excel download failed: " + e.message);
    }).then(function () {
      btn.textContent = "Download Excel"; btn.disabled = !notCleared.length;
    });
  }
  document.getElementById("x-n").addEventListener("click", downloadExcel);

  function render() {
    hideTip();
    if (F.emp && !D.people.some(function (p) { return p.e === F.emp; })) F.emp = "";
    sel.value = F.emp; q.value = F.q; bkSel.value = F.bk;
    var active = F.emp || F.q.trim() || F.bk;
    clearBtn.hidden = !active;
    var R = rows(false);
    chip.textContent = active ? "Showing " + plural(R.length, "person", "people") + " of " + D.people.length : "";
    saveFilters();
    kpis(R); donut(R); employers(rows(true)); items(R); days(R); tables(R); employerShare(rows(true));
  }
  render();
})();
"""
