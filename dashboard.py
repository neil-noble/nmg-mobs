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


def data(report):
    """Everything the page draws, as plain JSON-able values."""
    people = []

    def add(booked, status):
        p = booked.person
        states = p.item_states()
        people.append({
            "n": p.name, "e": p.employer or "(no employer)", "s": status,
            "d": booked.first.day.isoformat(), "b": f"{booked.first.kind}: {booked.first.detail}",
            "m": len(booked.bookings) - 1,
            "st": [STATE_CODE[states[i]] for i in C.ITEMS] if status in ("c", "n") else None,
        })

    for b in report.cleared:
        add(b, "c")
    for b in report.not_cleared:
        add(b, "n")
    for b in report.no_role:
        add(b, "r")
    for u in report.unmatched:
        first = u.bookings[0]
        people.append({"n": u.name, "e": u.employer or "(no employer)", "s": "u", "d": first.day.isoformat(),
                       "b": f"{first.kind}: {first.detail}", "m": len(u.bookings) - 1, "st": None})
    days = [(report.today + timedelta(days=i)).isoformat() for i in range((report.end - report.today).days + 1)]
    return {"items": list(C.ITEMS), "days": days, "people": people}


def _json_for_script(value):
    # "<" can never close the <script> block or open a comment once escaped.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def page(report, generated: datetime):
    window = f"{fmt_day(report.today)} to {fmt_day(report.end)}"
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
        f"<p>Flight and room bookings {window} &middot; Medical, D&amp;A screen, police clearance, "
        f"driver's licence and induction &middot; updated {generated:%a %d %b %Y %H:%M} AWST from PeopleTray</p>"
        "</div></div></header>"
        f"{BODY}"
        f'<script id="mobs-data" type="application/json">{_json_for_script(data(report))}</script>'
        f"<script>{JS}</script></body></html>"
    )


CSS = """
:root{--navy:#083045;--river:#55848A;--pale-gold:#B19045;--river-tint:#AAC2C5;
--ink:#333334;--ink2:#4f4f50;--muted:#6b6b6c;--line:#DBDBD3;--grid:#EDEDE9;--canvas:#EDEDE9;--card:#fff;
/* status: green cleared, red not cleared (Neil, 2026-10-24); River tint no work role, Black 50% not matched */
--c:#1e6b2e;--n:#e5625c;--r:#AAC2C5;--u:#99999A}
*{box-sizing:border-box}
body{margin:0;background:var(--canvas);color:var(--ink);
font-family:"Proxima Nova",Montserrat,Aptos,"Segoe UI",system-ui,sans-serif;font-size:13px;line-height:1.4}
header{background:var(--navy);color:#fff;border-bottom:3px solid var(--pale-gold)}
header .bar{max-width:1440px;margin:0 auto;padding:10px 16px}
header h1{margin:0;font-size:20px;font-weight:700;line-height:1.15}
header p{margin:2px 0 0;font-size:12px;color:var(--river-tint)}
.canvas{max-width:1440px;margin:0 auto;padding:10px 16px 18px;display:grid;
grid-template-columns:repeat(12,minmax(0,1fr));gap:10px}
.v{grid-column:span var(--span,12);background:var(--card);border:1px solid var(--line);border-radius:4px;
padding:10px 12px 12px;box-shadow:0 1px 2px rgba(0,0,0,.05);min-width:0}
.v>h2{margin:0 0 2px;font-size:13px;font-weight:700}
.v>.sub{margin:0 0 10px;font-size:11.5px;color:var(--muted)}
.note{color:var(--muted);font-size:11.5px;margin:8px 0 0}
.empty{color:var(--muted);font-style:italic;margin:6px 0}
/* slicers */
.slicers{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px 12px;align-items:end}
.slicer{display:flex;flex-direction:column;gap:3px;min-width:200px;flex:0 1 280px}
.slicer label{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700}
.slicer select,.slicer input{font:inherit;padding:6px 8px;border:1px solid #99999A;border-radius:3px;background:#fff;
color:var(--ink);width:100%}
.slicer select:focus,.slicer input:focus,button:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--navy);
outline-offset:1px}
.clear{font:inherit;padding:6px 12px;border:1px solid var(--navy);background:#fff;color:var(--navy);border-radius:3px;
cursor:pointer;font-weight:600}
.clear[hidden]{display:none}
.chip{font-size:12px;color:var(--ink2);padding:6px 0}
/* stat tiles */
.kpis{grid-column:1/-1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.kpis>.v{grid-column:auto}
.kpi{border-top:3px solid var(--navy);display:flex;flex-direction:column;gap:2px}
.kpi .lab{font-size:12px;color:var(--ink2)}
.kpi .val{font-size:30px;font-weight:700;line-height:1.1}
.kpi .val small{font-size:13px;font-weight:600;color:var(--muted);margin-left:4px}
.meter{height:6px;border-radius:3px;background:#EDEDE9;overflow:hidden;margin-top:6px}
.meter i{display:block;height:100%;background:var(--c);border-radius:3px}
/* legend */
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11.5px;color:var(--ink2);margin:0 0 10px}
.legend span{display:inline-flex;align-items:center;gap:5px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.15)}
/* donut */
.donut{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.donut svg{width:180px;height:180px;flex:none}
.donut .seg{cursor:default;transition:opacity .15s}
.donut .seg:hover{opacity:.82}
.donut ul{list-style:none;margin:0;padding:0;flex:1;min-width:150px}
.donut li{display:grid;grid-template-columns:12px 1fr auto auto;gap:6px;align-items:center;padding:5px 0;
border-bottom:1px solid var(--grid);font-size:12.5px}
.donut li b{font-variant-numeric:tabular-nums;text-align:right}
.donut li em{font-style:normal;color:var(--muted);width:38px;text-align:right;font-variant-numeric:tabular-nums}
.donut .big{font-size:22px;font-weight:700;fill:var(--ink)}
.donut .cap{font-size:9px;fill:var(--muted)}
/* horizontal bars */
.hb{display:grid;grid-template-columns:minmax(90px,34%) 1fr;gap:4px 10px;align-items:center}
.hb .lab{font-size:12px;text-align:right;color:var(--ink);background:none;border:0;padding:3px 0;font:inherit;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}
.hb .lab.static{cursor:default;color:var(--ink2)}
.hb .lab:hover:not(.static){text-decoration:underline}
.hb .lab.on{font-weight:700}
.track{display:flex;align-items:center;gap:6px;min-width:0}
.sbar{display:flex;gap:2px;height:16px;flex:0 0 auto;cursor:pointer}
.sbar.static{cursor:default}
.sbar i,.stack i{box-shadow:inset 0 0 0 1px rgba(0,0,0,.08)}  /* keeps Sand and the tints visible on white */
.sbar i{display:block;height:100%;min-width:2px}
.sbar i:last-child{border-radius:0 4px 4px 0}
.track .val{font-size:11.5px;color:var(--ink2);white-space:nowrap;font-variant-numeric:tabular-nums}
.track .val b{color:var(--ink)}
.dim{opacity:.32}
/* columns */
.cols{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);align-items:end;height:200px;
border-bottom:1px solid #99999A;gap:2px;padding-top:16px}
.col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0}
.col .tot{font-size:11px;color:var(--ink2);font-variant-numeric:tabular-nums;margin-bottom:2px}
.stack{display:flex;flex-direction:column-reverse;gap:2px;width:min(24px,80%)}
.stack i{display:block;width:100%}
.stack i:last-child{border-radius:4px 4px 0 0}
.xl{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:2px;margin-top:4px}
.xl span{font-size:10.5px;color:var(--muted);text-align:center;line-height:1.2;font-variant-numeric:tabular-nums}
.xl span.today{color:var(--ink);font-weight:700}
/* tables */
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
thead th{font-weight:700;border-bottom:2px solid var(--navy);white-space:nowrap}
tbody tr:nth-child(even){background:#F6F6F3}
tbody tr:hover{background:#F8EED5}
td.when{white-space:nowrap;font-variant-numeric:tabular-nums}
td.st,th.st{text-align:center;white-space:nowrap}
.more{color:var(--muted);font-size:11.5px}
.pill{display:inline-flex;align-items:center;gap:5px;padding:1px 8px 1px 6px;border-radius:9px;font-size:11.5px;
font-weight:600;color:var(--ink)}
.pill i{width:8px;height:8px;border-radius:50%;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.2)}
.tick{color:#1e6b2e;font-weight:700}
details>summary{cursor:pointer;font-weight:700;font-size:13px}
/* tooltip */
.tip{position:fixed;z-index:10;display:none;pointer-events:none;background:#fff;border:1px solid var(--line);
border-radius:4px;box-shadow:0 4px 14px rgba(0,0,0,.14);padding:7px 9px;font-size:12px;min-width:140px;max-width:260px}
.tip .tt{font-weight:700;margin-bottom:4px;color:var(--ink)}
.tip .tr{display:grid;grid-template-columns:12px auto 1fr;gap:6px;align-items:center}
.tip .tr i{display:block;width:12px;height:2px}
.tip .tr b{font-variant-numeric:tabular-nums}
.tip .tr span{color:var(--ink2)}
.canvas>.v{align-self:stretch}
.canvas>.v.top{align-self:start}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.canvas>.v{grid-column:1/-1}
.kpi:last-child{grid-column:1/-1}.hb{grid-template-columns:minmax(80px,38%) 1fr}}
"""

BODY = """
<main class="canvas">
<noscript><section class="v"><p>This dashboard needs JavaScript to draw its charts.</p></section></noscript>
<div class="slicers">
  <div class="slicer"><label for="f-emp">Employer</label><select id="f-emp"></select></div>
  <div class="slicer"><label for="f-q">Find a person</label><input id="f-q" type="search" placeholder="Name" autocomplete="off"></div>
  <button class="clear" id="f-clear" type="button" hidden>Clear filters</button>
  <span class="chip" id="f-chip"></span>
</div>
<div class="kpis" id="kpis"></div>
<section class="v" style="--span:4"><h2>Mobilisation status</h2><p class="sub">Everyone with a booking in the window</p>
  <div id="donut"></div></section>
<section class="v" style="--span:8"><h2>By employer</h2><p class="sub">People booked, by status &middot; most not cleared first &middot; click an employer to filter the page</p>
  <div id="emp"></div></section>
<section class="v" style="--span:5"><h2>What is missing</h2><p class="sub">People not cleared, by item and gap type &middot; one person can lack several items</p>
  <div id="items"></div></section>
<section class="v" style="--span:7"><h2>When they arrive</h2><p class="sub">People by day of first booking &middot; today includes those already on site</p>
  <div id="days"></div></section>
<section class="v top"><h2 id="h-n">Not cleared to mobilise</h2><p class="sub">Earliest booking first</p>
  <div id="tbl-n"></div>
  <p class="note"><b>Missing</b> = no document added (induction: not yet completed). <b>Expired</b> = the document or
  competency has expired. <b>No document</b> = marked competent but nothing uploaded. <b>Not on role</b> = the
  person's work role in PeopleTray does not ask for this item, so it has never been recorded; fix the work role.
  Medical = Pre Employment Medical, or a Medical Declaration for Short Term Workers.</p></section>
<section class="v top"><h2 id="h-r">No work role in PeopleTray</h2><p class="sub">Cannot be checked until a work role is set</p>
  <div id="tbl-r"></div></section>
<section class="v top" id="card-u" hidden><h2 id="h-u">Bookings not matched to a PeopleTray profile</h2>
  <p class="sub">Check the name or work email on the booking</p><div id="tbl-u"></div></section>
<section class="v top"><details><summary id="h-c">Cleared to mobilise</summary><div id="tbl-c" style="margin-top:8px"></div></details></section>
</main>
"""

JS = r"""
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("mobs-data").textContent);
  var STATUS = [
    {k: "c", label: "Cleared", color: "#1e6b2e"},
    {k: "n", label: "Not cleared", color: "#e5625c"},
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
  var F = {emp: "", q: ""};
  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var SVGNS = "http://www.w3.org/2000/svg";

  // The page reloads itself every 15 minutes; keep this viewer's filters across reloads.
  try { var saved = JSON.parse(sessionStorage.getItem("mobs-filters") || "null"); if (saved) F = saved; } catch (e) {}
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
  function fmtDay(iso) { var d = day(iso); return d.dow + " " + d.n + " " + d.mon; }
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
      return (ignoreEmployer || !F.emp || p.e === F.emp) && (!q || p.n.toLowerCase().indexOf(q) >= 0);
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
  var sel = document.getElementById("f-emp"), q = document.getElementById("f-q");
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
  clearBtn.addEventListener("click", function () { F = {emp: "", q: ""}; render(); });
  function setEmployer(e) { F.emp = F.emp === e ? "" : e; render(); }

  // ── stat tiles ────────────────────────────────────────────────────────────────
  function kpis(R) {
    var c = countBy(R, "s"), ok = c.c || 0, bad = c.n || 0, nr = c.r || 0, checked = ok + bad;
    var box = document.getElementById("kpis");
    box.replaceChildren();
    function tile(label, value, color, extra, tone) {
      // tone: the tile itself reads green / red - tinted card, coloured figure (Neil, 2026-10-24)
      var style = "border-top-color:" + color + (tone ? ";background:color-mix(in srgb," + color + " 10%,#fff)" : "");
      if (tone) value.style.color = tone;
      box.appendChild(h("div", {"class": "v kpi", style: style},
        [h("span", {"class": "lab", text: label}), value, extra || null]));
    }
    tile("People booked", h("span", {"class": "val", text: String(R.length)}), "#083045");
    tile("Cleared to mobilise", h("span", {"class": "val", text: String(ok)}), STATUS[0].color, null, "#1e6b2e");
    tile("Not cleared", h("span", {"class": "val", text: String(bad)}), STATUS[1].color, null, "#b3261e");
    tile("No work role in PeopleTray", h("span", {"class": "val", text: String(nr)}), STATUS[2].color);
    var meter = h("div", {"class": "meter", role: "img", "aria-label": "Readiness " + pct(ok, checked)},
      [h("i", {style: "width:" + (checked ? 100 * ok / checked : 0) + "%"})]);
    tile("Readiness (of people with a work role)",
      h("span", {"class": "val"}, [pct(ok, checked), h("small", {text: ok + " of " + checked})]), "#55848A", meter);
  }

  // ── donut: part-to-whole of the booked people ─────────────────────────────────
  function donut(R) {
    var box = document.getElementById("donut");
    box.replaceChildren();
    if (!R.length) { box.appendChild(h("p", {"class": "empty", text: "No bookings match the filters."})); return; }
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
      withTip(arc, s.label, [{v: c[s.k], l: pct(c[s.k], R.length) + " of " + R.length + " booked", color: s.color}]);
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
    if (!R.length) { box.appendChild(h("p", {"class": "empty", text: "No bookings match the filters."})); return; }
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
    return h("td", null, [p.b, p.m ? h("span", {"class": "more", text: " +" + p.m + " more"}) : null]);
  }
  function stateCell(code) {
    if (code === "ok") return h("td", {"class": "st"}, [h("span", {"class": "tick", text: "✓", "aria-label": "Held"})]);
    var g = GAPBY[code], color = g.color;
    return h("td", {"class": "st"}, [h("span", {"class": "pill",
      style: "background:color-mix(in srgb," + color + " 15%,#fff)"}, [h("i", {style: "background:" + color}), g.label])]);
  }
  function table(boxId, list, withItems, empty) {
    var box = document.getElementById(boxId);
    box.replaceChildren();
    if (!list.length) { box.appendChild(h("p", {"class": "empty", text: empty})); return; }
    var head = ["Name", "Employer", "First booking", "Booking"].map(function (t) { return h("th", {text: t}); });
    if (withItems) D.items.forEach(function (t) { head.push(h("th", {"class": "st", text: t})); });
    var body = h("tbody");
    list.forEach(function (p) {
      var cells = [h("td", {text: p.n}), h("td", {text: p.e}), h("td", {"class": "when", text: fmtDay(p.d)}), bookingCell(p)];
      if (withItems) p.st.forEach(function (code) { cells.push(stateCell(code)); });
      body.appendChild(h("tr", null, cells));
    });
    box.appendChild(h("div", {"class": "scroll"}, [h("table", null, [h("thead", null, [h("tr", null, head)]), body])]));
  }
  function byDayThenName(a, b) { return a.d.localeCompare(b.d) || a.n.localeCompare(b.n); }
  function tables(R) {
    function of(s) { return R.filter(function (p) { return p.s === s; }).sort(byDayThenName); }
    var n = of("n"), r = of("r"), u = of("u"), c = of("c");
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

  function render() {
    hideTip();
    if (F.emp && !D.people.some(function (p) { return p.e === F.emp; })) F.emp = "";
    sel.value = F.emp; q.value = F.q;
    var active = F.emp || F.q.trim();
    clearBtn.hidden = !active;
    var R = rows(false);
    chip.textContent = active ? "Showing " + plural(R.length, "person", "people") + " of " + D.people.length : "";
    saveFilters();
    kpis(R); donut(R); employers(rows(true)); items(R); days(R); tables(R);
  }
  render();
})();
"""
