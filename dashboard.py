"""The public dashboard: one HTML page, drawn in the browser from embedded data.

Python decides every fact (who is booked, cleared or not, which item is in which state); the
page's script only counts, filters and draws. Names reach the page as JSON and are inserted with
textContent, never as markup.

Design (Neil, 2026-11-16): NMG style guide (A9799 stylesheet) throughout. A navy stage in the
guide's Navy->River gradient carries the masthead, filters and headline numbers on bright frosted
glass; the working lists sit on frosted glass over a light Cool Grey field. The design log is
docs/design/dashboard-2026-11-16/.
"""
import json
from datetime import datetime, timedelta
from html import escape

import config as C
from model import induction_state

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
        row["ls"] = w.last_on_site.isoformat() if w.last_on_site else None
        row["os"] = w.on_site
        row["ind"] = STATE_CODE[induction_state(p)]
        people.append(row)
    for u in wf.unmatched:
        row = {"n": u.name, "e": u.employer or "(no employer)", "s": "u", "st": None, "ls": None, "os": False,
               "ind": None}
        row.update(booking(u.bookings))
        people.append(row)
    days = [(wf.today + timedelta(days=i)).isoformat() for i in range((wf.end - wf.today).days + 1)]
    return {"items": list(C.ITEMS), "days": days, "people": people}


def _json_for_script(value):
    # "<" can never close the <script> block or open a comment once escaped.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def page(workforce, generated: datetime):
    return html(data(workforce), f"{workforce.horizon:%d %b %Y}", generated)


def html(d, horizon: str, generated: datetime):
    """The page from already-built data (page() for a build; also lets a design be previewed on live data)."""
    stamp = f"{generated:%a} {generated.day} {generated:%b %Y} · {generated:%H:%M}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="900"><meta name="robots" content="noindex">'
        '<meta name="theme-color" content="#083045">'
        # Figtree stands in for the style guide's Proxima Nova (a licensed font): the nearest free face
        # with a true Black weight for Heading 1 and tabular figures for the numbers.
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800;900&display=swap">'
        f'<link rel="icon" href="{FAVICON}">'
        f"<title>{escape(C.TITLE)}</title><style>{CSS}</style></head><body>"
        '<main class="canvas">'
        '<header class="masthead"><p class="eyebrow">New Murchison Gold <span aria-hidden="true">·</span> Crown Prince</p>'
        '<div class="mh-row"><h1>Mobilisation compliance</h1>'
        f'<p class="stamp"><span class="dot" aria-hidden="true"></span>Updated <time>{stamp}</time> AWST</p></div>'
        "<p class=\"lede\">Every Crown Prince worker in PeopleTray against the five mobilisation items: medical, "
        "D&amp;A screen, police clearance, driver's licence and site induction.</p></header>"
        f"{BODY}"
        f'<footer class="foot"><p>Source: PeopleTray. Rebuilt every hour; this page reloads itself every 15 minutes. '
        f"Next bookings are read up to {escape(horizon)}.</p></footer></main>"
        f'<script id="mobs-data" type="application/json">{_json_for_script(d)}</script>'
        f"<script>{JS}</script></body></html>"
    )


# The NMG symbol's colours as a tab icon: navy tile, gold-to-sand bars (no logo artwork is copied).
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%23083045'/%3E"
           "%3Crect x='7' y='17' width='4' height='8' rx='1' fill='%23927128'/%3E"
           "%3Crect x='14' y='12' width='4' height='13' rx='1' fill='%23B19045'/%3E"
           "%3Crect x='21' y='7' width='4' height='18' rx='1' fill='%23F1DCAA'/%3E%3C/svg%3E")

CSS = """
:root{
/* NMG style guide (A9799): every colour is a guide swatch or its 50% tint */
--navy:#083045;--navy-50:#8498A2;--river:#55848A;--river-50:#AAC2C5;--gold:#927128;--gold-50:#C9B894;
--pale-gold:#B19045;--pale-gold-50:#D8C8A2;--sand:#F1DCAA;--sand-50:#F8EED5;--grey:#DBDBD3;--grey-50:#EDEDE9;
--black:#333334;--black-50:#99999A;
/* text: Black 93% body; two navy-greys for secondary text, both >= 4.5:1 on the glass */
--ink:#333334;--ink-2:#4a5357;--muted:#5f686d;--line:rgba(8,48,69,.09);--line-2:rgba(8,48,69,.16);
/* status (Neil, 2026-10-24): cleared green, not cleared red; gap types */
--ok:#0f4d1e;--bad:#e53935;--bad-ink:#b3261e;--missing:#c62f3f;--expired:#e07b12;
/* surfaces */
--glass:rgba(255,255,255,.58);--glass-hi:rgba(255,255,255,.88);--edge:rgba(255,255,255,.8);
--blur:blur(22px) saturate(160%);
--shadow:0 1px 1px rgba(8,48,69,.04),0 4px 10px -6px rgba(8,48,69,.10),0 32px 64px -40px rgba(8,48,69,.34);
--r-xl:24px;--r-lg:20px;--r-md:14px;--r-sm:10px;
/* motion */
--out:cubic-bezier(.22,1,.36,1);--spring:cubic-bezier(.34,1.45,.64,1);
--font:Figtree,"Proxima Nova",Aptos,"Segoe UI",system-ui,sans-serif}
*{box-sizing:border-box}
html{background:var(--grey-50);color-scheme:light;scroll-behavior:smooth}
body{margin:0;overflow-x:clip;color:var(--ink);font-family:var(--font);font-size:14px;line-height:1.5;
-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
button,input,select{font:inherit;color:inherit}
h1,h2,h3,p{margin:0}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
/* the light field: soft colour fields in the guide palette for the glass to pick up (Neil, 2026-11-15: no
lines or patterns). A fixed-size tile, every field fading inside it, so a tall Wix iframe repeats it cleanly. */
body::before{content:"";position:fixed;inset:0;z-index:-3;background-color:var(--grey-50);background-image:
radial-gradient(circle 560px at 84% 34%,rgba(241,220,170,.55),rgba(241,220,170,0) 70%),
radial-gradient(circle 620px at 8% 62%,rgba(170,194,197,.5),rgba(170,194,197,0) 68%),
radial-gradient(circle 460px at 58% 86%,rgba(216,200,162,.34),rgba(216,200,162,0) 70%),
radial-gradient(circle 420px at 30% 16%,rgba(132,152,162,.2),rgba(132,152,162,0) 70%);
background-size:1600px 1400px;background-position:top center;background-repeat:repeat-y}
.canvas{max-width:1440px;margin:0 auto;padding:0 32px}
/* ── the stage: guide gradient Navy -> River, lit from the top right, ending on a Gold -> Sand rule.
(Gold light on navy turns olive, so gold stays in the rule, the type and the section marks.) ── */
.stagebox{position:relative;margin-bottom:112px}
.stagebox::before,.stagebox::after{content:"";position:absolute;left:calc(50% - 50vw);width:100vw;top:-1400px;bottom:-56px}
.stagebox::before{z-index:-2;background:linear-gradient(160deg,#083045 0%,#0a3a52 52%,#2f6168 100%)}
.stagebox::after{z-index:-1;background:
linear-gradient(90deg,var(--gold),var(--pale-gold) 35%,var(--sand) 75%,rgba(241,220,170,.15)) left bottom/100% 2px no-repeat,
radial-gradient(circle 760px at 6% calc(100% - 40px),rgba(85,132,138,.72),rgba(85,132,138,0) 70%),
radial-gradient(circle 520px at 64% calc(100% - 10px),rgba(170,194,197,.18),rgba(170,194,197,0) 70%)}
.masthead{position:relative;padding:48px 0 28px;color:#fff}
.masthead::before{content:"";position:absolute;z-index:-1;top:-120px;right:calc(50% - 50vw);width:min(1100px,90vw);height:860px;
pointer-events:none;background:radial-gradient(circle 600px at 80% 14%,rgba(170,194,197,.32),rgba(170,194,197,.08) 50%,rgba(170,194,197,0) 74%)}
.eyebrow{font-size:13px;font-weight:600;color:var(--sand);letter-spacing:.01em}
.eyebrow span{color:var(--pale-gold);margin:0 2px}
.mh-row{display:flex;justify-content:space-between;align-items:flex-end;gap:12px 32px;flex-wrap:wrap;margin-top:12px}
h1{font-size:52px;font-weight:900;line-height:1;letter-spacing:-.03em;color:#fff;text-wrap:balance}
.stamp{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:500;color:var(--pale-gold-50);
font-variant-numeric:tabular-nums;white-space:nowrap;padding-bottom:6px}
.stamp time{color:#fff;font-weight:600}
.stamp .dot{width:7px;height:7px;border-radius:50%;background:var(--sand);box-shadow:0 0 0 4px rgba(241,220,170,.16)}
.lede{margin-top:14px;max-width:64ch;font-size:15px;color:rgba(255,255,255,.74);text-wrap:pretty}
/* filters: dark navy glass, sticky, so they read on the stage and float over the light lists */
.slicers{position:sticky;top:12px;z-index:20;display:flex;flex-wrap:wrap;align-items:flex-end;gap:10px 12px;padding:12px;
border-radius:var(--r-lg);color:#fff;background:rgba(7,42,61,.86);-webkit-backdrop-filter:blur(20px) saturate(140%);
backdrop-filter:blur(20px) saturate(140%);border:1px solid rgba(255,255,255,.1);
box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 18px 40px -24px rgba(2,20,30,.7)}
.slicer{display:flex;flex-direction:column;gap:6px;flex:0 1 280px;min-width:180px}
.slicer label{font-size:12px;font-weight:600;color:var(--river-50);padding-left:2px}
.slicer select,.slicer input{width:100%;height:42px;padding:0 38px 0 14px;border-radius:12px;border:1px solid rgba(255,255,255,.14);
background-color:rgba(255,255,255,.07);color:#fff;font-size:14px;outline:none;-webkit-appearance:none;appearance:none;
transition:background-color .14s var(--out),border-color .14s var(--out)}
.slicer select{cursor:pointer;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' fill='none' stroke='%23F1DCAA' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
background-repeat:no-repeat;background-position:right 14px center;background-size:11px 8px}
.slicer select option{color:var(--ink);background:#fff}
.slicer input{padding:0 14px 0 38px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='7' cy='7' r='5' fill='none' stroke='%23AAC2C5' stroke-width='1.6'/%3E%3Cpath d='M11 11l3.2 3.2' stroke='%23AAC2C5' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
background-repeat:no-repeat;background-position:14px center;background-size:15px}
.slicer input::placeholder{color:rgba(255,255,255,.5)}
.slicer input::-webkit-search-cancel-button{filter:invert(1) brightness(2);opacity:.6;cursor:pointer}
.slicer select:hover,.slicer input:hover{background-color:rgba(255,255,255,.11)}
.slicer select:focus-visible,.slicer input:focus-visible{border-color:var(--sand);background-color:rgba(255,255,255,.12);
box-shadow:0 0 0 3px rgba(241,220,170,.22)}
.fstate{margin-left:auto;display:flex;align-items:center;gap:12px;min-height:42px}
.chip{font-size:13px;color:var(--sand-50);font-variant-numeric:tabular-nums}
.clear{height:34px;padding:0 14px;border-radius:999px;border:1px solid rgba(241,220,170,.5);background:none;color:var(--sand);
font-size:13px;font-weight:600;cursor:pointer;transition:background-color .14s var(--out),color .14s var(--out),transform .1s var(--out)}
.clear:hover{background:var(--sand);color:var(--navy)}
.clear:active{transform:scale(.97)}
.clear[hidden]{display:none}
:focus-visible{outline:2px solid var(--navy);outline-offset:2px}
.slicers :focus-visible,.clear:focus-visible{outline-color:var(--sand)}
/* ── glass ── */
.glass{background:var(--glass);-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur);
border:1px solid var(--edge);box-shadow:var(--shadow),inset 0 1px 0 rgba(255,255,255,.7)}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){.glass{background:rgba(255,255,255,.93)}}
@media (prefers-reduced-transparency:reduce){.glass,.hero{background:#fff!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important}
.slicers{background:#062536;-webkit-backdrop-filter:none;backdrop-filter:none}}
/* ── hero: where things stand ── */
.hero{margin-top:20px;border-radius:var(--r-xl);padding:36px 40px 32px;background:var(--glass-hi);
-webkit-backdrop-filter:blur(22px) saturate(115%);backdrop-filter:blur(22px) saturate(115%);border:1px solid rgba(255,255,255,.9);
box-shadow:inset 0 1px 0 #fff,0 2px 4px rgba(2,20,30,.08),0 40px 80px -40px rgba(2,20,30,.55)}
/* the big number holds the left; the manifest and the supporting figures share the right */
.hero-grid{display:grid;grid-template-columns:minmax(280px,auto) 1fr;grid-template-areas:"lead man" "lead figs";gap:32px 64px}
.lead{grid-area:lead;display:flex;flex-direction:column;align-self:start}
.lead-n{font-size:136px;font-weight:900;line-height:.78;letter-spacing:-.05em;color:var(--bad-ink);font-variant-numeric:tabular-nums;
margin-left:-.04em}
.lead-n.zero{color:var(--ok)}
.lead-l{margin-top:20px;font-size:19px;font-weight:800;color:var(--navy);letter-spacing:-.01em}
.lead-s{margin-top:4px;font-size:14px;color:var(--muted)}
.jump{align-self:flex-start;margin-top:14px;display:inline-flex;align-items:center;gap:6px;font-size:14px;font-weight:700;
color:var(--navy);text-decoration:none;border-bottom:1.5px solid var(--gold-50);padding-bottom:1px;
transition:border-color .14s var(--out),gap .2s var(--out)}
.jump:hover{border-color:var(--gold);gap:9px}
.jump svg{width:12px;height:12px}
.figs{grid-area:figs;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-self:end}
.fig{display:flex;flex-direction:column;justify-content:flex-start;padding:2px 0 2px 28px;border-left:1px solid var(--line-2)}
.fig:first-child{border-left:0;padding-left:0}
.fig-n{font-size:52px;font-weight:800;line-height:1;letter-spacing:-.03em;color:var(--navy);font-variant-numeric:tabular-nums}
.fig-n.ok{color:var(--ok)}
.fig-l{margin-top:10px;font-size:14px;font-weight:700;color:var(--ink)}
.fig-s{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
/* the manifest: one mark per worker, in status order */
.manifest{grid-area:man;align-self:start;min-width:0;padding-top:6px}
/* marks are placed by the script on whole device pixels, so every mark is the same width at any size */
.strip{position:relative;height:48px;cursor:pointer;touch-action:pan-y}
.strip i{position:absolute;top:0;bottom:0;transform-origin:50% 100%;
transition:transform .16s var(--out),filter .16s var(--out)}
.strip i:hover{transform:scaleY(1.14);filter:brightness(1.15)}
.s-c{background:var(--ok)}.s-n{background:var(--bad)}.s-r{background:var(--river-50)}.s-u{background:var(--black-50)}
.strip.enter i{animation:rise .56s var(--spring) both;animation-delay:calc(260ms + var(--k,0) * 1.4ms)}
@keyframes rise{from{transform:scaleY(0)}}
.mlegend{display:flex;flex-wrap:wrap;align-items:center;gap:6px 22px;margin-top:14px;font-size:13px;color:var(--ink-2)}
.mlegend span{display:inline-flex;align-items:center;gap:8px}
.mlegend b{font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums}
.mlegend .hint{margin-left:auto;color:var(--muted);font-size:12.5px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;flex:none}
/* ── groups ── */
.group{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px;margin-top:72px;scroll-margin-top:120px}
.stagebox+.group{margin-top:0}
.gh{grid-column:1/-1;display:flex;flex-direction:column;gap:4px;margin-bottom:4px}
.gh::before{content:"";width:28px;height:3px;border-radius:2px;margin-bottom:12px;background:linear-gradient(90deg,var(--gold),var(--sand))}
.gh h2{font-size:26px;font-weight:800;line-height:1.15;letter-spacing:-.02em;color:var(--navy)}
.gh p{font-size:14px;color:var(--muted);max-width:80ch}
.v{grid-column:span var(--span,12);border-radius:var(--r-lg);padding:24px;min-width:0}
.v h3,.vhead h3{display:flex;align-items:center;flex-wrap:wrap;gap:8px 10px;font-size:16px;font-weight:700;color:var(--ink);letter-spacing:-.005em}
.v .sub,.vhead .sub{margin-top:3px;font-size:13px;color:var(--muted)}
.vhead{display:flex;justify-content:space-between;align-items:flex-start;gap:12px 16px;flex-wrap:wrap;margin-bottom:18px}
.v>.sub{margin-bottom:18px}
.count{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:22px;padding:0 8px;border-radius:999px;
background:rgba(8,48,69,.08);color:var(--navy);font-size:12.5px;font-weight:700;font-variant-numeric:tabular-nums}
.count.bad{background:var(--bad-ink);color:#fff}
.note{color:var(--muted);font-size:13px;margin-top:14px}
.empty{color:var(--muted);margin:4px 0}
.btn{display:inline-flex;align-items:center;gap:8px;height:38px;padding:0 16px 0 14px;border-radius:999px;border:0;
background:var(--navy);color:#fff;font-size:13.5px;font-weight:600;cursor:pointer;
box-shadow:0 1px 0 rgba(255,255,255,.12) inset,0 6px 16px -8px rgba(8,48,69,.6);
transition:background-color .14s var(--out),transform .1s var(--out),opacity .14s}
.btn svg{width:15px;height:15px}
.btn:hover:not(:disabled){background:#0d4560}
.btn:active:not(:disabled){transform:scale(.97)}
.btn:disabled{opacity:.45;cursor:default}
.where{display:inline-flex;align-items:center;gap:7px;height:24px;padding:0 10px 0 9px;border-radius:999px;font-size:12.5px;
font-weight:700;white-space:nowrap}
.where i{width:7px;height:7px;border-radius:50%}
.where.now{background:var(--bad-ink);color:#fff}.where.now i{background:#fff;box-shadow:0 0 0 3px rgba(255,255,255,.25)}
.where.past{background:rgba(8,48,69,.08);color:var(--navy)}.where.past i{background:var(--navy)}
/* ── charts ── */
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12.5px;color:var(--ink-2);margin:0 0 16px}
.legend span{display:inline-flex;align-items:center;gap:7px}
.hb{display:grid;grid-template-columns:minmax(96px,32%) 1fr;gap:8px 14px;align-items:center}
.hb .lab{font-size:13px;text-align:right;color:var(--ink);background:none;border:0;padding:2px 0;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;border-radius:4px}
.hb .lab.static{cursor:default;color:var(--ink-2)}
.hb .lab:hover:not(.static){color:var(--navy);text-decoration:underline;text-decoration-color:var(--gold-50);text-underline-offset:3px}
.hb .lab.on{font-weight:700;color:var(--navy)}
.track{display:flex;align-items:center;gap:10px;min-width:0}
.sbar{display:flex;gap:2px;height:14px;flex:0 0 auto;cursor:pointer;border-radius:7px;overflow:hidden;
transition:filter .14s var(--out)}
.sbar:hover{filter:brightness(1.08) saturate(1.1)}
.sbar.static{cursor:default}
.sbar i,.stack i{box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}
.sbar i{display:block;height:100%;min-width:3px}
.rail{flex:0 0 calc(100% - 132px);height:14px;background:rgba(8,48,69,.07);border-radius:7px;display:flex;cursor:pointer;overflow:hidden}
.rail i{display:block;height:100%;background:var(--bad);border-radius:7px}
.track .val{font-size:12.5px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.track .val b{color:var(--ink);font-weight:700}
.dim{opacity:.3}
.v.fillv{display:flex;flex-direction:column}
.fillv>#items{flex:1;display:flex;flex-direction:column}
.ibars{flex:1;display:flex;flex-direction:column;justify-content:space-between;gap:20px;margin-top:4px}
.ib-h{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px;font-size:13.5px}
.ib-h span{font-weight:600;color:var(--ink)}
.ib-h em{font-style:normal;font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.ib-h em b{color:var(--ink);font-weight:700}
.ib-track{height:14px;border-radius:7px;background:rgba(8,48,69,.06)}
.ib-track .sbar{height:100%}
/* columns by day */
.cols{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);align-items:end;height:220px;gap:6px;padding-top:18px;
border-bottom:1px solid var(--line-2)}
.col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0;border-radius:8px 8px 0 0;
transition:background-color .14s var(--out)}
.col[tabindex="0"]:hover{background:rgba(8,48,69,.04)}
.col .tot{font-size:12px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;margin-bottom:5px}
.stack{display:flex;flex-direction:column-reverse;gap:2px;width:min(30px,76%);border-radius:6px 6px 2px 2px;overflow:hidden}
.stack i{display:block;width:100%}
.xl{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:6px;margin-top:8px}
.xl span{display:flex;flex-direction:column;align-items:center;font-size:11.5px;color:var(--muted);line-height:1.25;font-variant-numeric:tabular-nums}
.xl span b{font-size:13px;color:var(--ink);font-weight:600}
.xl span.today{color:var(--navy);font-weight:700}
.xl span.today b{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:22px;margin-top:2px;border-radius:999px;
background:var(--navy);color:#fff;font-weight:700}
/* ── tables ── */
.scroll{overflow-x:auto;margin:0 -8px;padding:0 8px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:12px 12px;text-align:left;vertical-align:middle}
thead th{font-size:12.5px;font-weight:600;color:var(--muted);white-space:nowrap;border-bottom:1px solid var(--line-2);padding-top:4px}
tbody td{border-bottom:1px solid var(--line)}
tbody tr:last-child td{border-bottom:0}
tbody tr{transition:background-color .14s var(--out)}
tbody tr:hover{background:rgba(248,238,213,.6)}
tbody tr.flash{animation:flash 1.8s var(--out)}
@keyframes flash{0%,30%{background:rgba(241,220,170,.85)}}
td.nm{font-weight:600;color:var(--ink);white-space:nowrap}
td.em{color:var(--ink-2)}
td.when{white-space:nowrap;font-variant-numeric:tabular-nums}
td.bk{color:var(--ink-2)}
td.st,th.st{text-align:center;white-space:nowrap}
.more{color:var(--muted)}
.pill{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 10px 0 9px;border-radius:999px;font-size:12.5px;
font-weight:600;color:var(--ink);white-space:nowrap}
.pill i{width:7px;height:7px;border-radius:50%;flex:none}
.pill .it{display:none}
.tick{display:inline-block;width:20px;height:20px;vertical-align:middle}
/* ── accordions ── */
.fold{padding:0;overflow:hidden}
.fold>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:4px 14px;flex-wrap:wrap;
padding:18px 64px 18px 24px;position:relative;transition:background-color .14s var(--out)}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary::after{content:"";position:absolute;right:24px;top:50%;width:28px;height:28px;margin-top:-14px;border-radius:50%;
background:rgba(8,48,69,.07) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' fill='none' stroke='%23083045' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center/10px 7px no-repeat;
transition:transform .26s var(--out),background-color .14s var(--out)}
.fold[open]>summary::after{transform:rotate(180deg)}
.fold>summary:hover{background:rgba(255,255,255,.35)}
.fold>summary:hover::after{background-color:rgba(8,48,69,.12)}
.fold>summary .t{display:inline-flex;align-items:center;gap:10px;font-size:16px;font-weight:700;color:var(--ink)}
.fold>summary .sub{font-size:13px;color:var(--muted)}
.fold>.body{padding:0 24px 20px}
.fold.inline{grid-column:1/-1;background:transparent;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none}
.fold.inline>summary{padding:6px 40px 6px 2px;display:inline-flex}
.fold.inline>summary::after{right:0;width:24px;height:24px;margin-top:-12px}
.fold.inline>summary:hover{background:none}
.fold.inline>summary .t{font-size:13.5px;font-weight:600;color:var(--navy)}
.fold.inline>.body{padding:0 2px 4px}
.fold.inline .note{margin:6px 0 0;max-width:110ch}
.lists{display:flex;flex-direction:column;gap:12px;grid-column:1/-1}
/* tooltip */
.tip{position:fixed;z-index:30;display:none;pointer-events:none;background:rgba(255,255,255,.9);
-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur);border:1px solid var(--edge);border-radius:12px;
box-shadow:0 16px 40px -14px rgba(8,48,69,.45),0 1px 2px rgba(8,48,69,.08);padding:10px 12px;font-size:12.5px;min-width:150px;max-width:280px}
.tip .tt{font-weight:700;color:var(--ink);font-size:13.5px}
.tip .ts{color:var(--muted);margin-bottom:6px}
.tip .tt+.tr{margin-top:6px}
.tip .tr{display:grid;grid-template-columns:10px auto 1fr;gap:8px;align-items:center;padding:1px 0}
.tip .tr i{display:block;width:10px;height:10px;border-radius:3px}
.tip .tr b{font-variant-numeric:tabular-nums;font-weight:700}
.tip .tr span{color:var(--ink-2)}
.foot{margin:72px 0 0;padding:22px 0 40px;border-top:1px solid var(--line-2);font-size:12.5px;color:var(--muted)}
.group>.v{align-self:stretch}
.group>.v.top{align-self:start}
/* ── entrance: the stage settles once per load ── */
@media (prefers-reduced-motion:no-preference){
.masthead>*,.slicers,.hero{animation:enter .7s var(--out) both}
.mh-row{animation-delay:.05s}.lede{animation-delay:.1s}.slicers{animation-delay:.14s}.hero{animation-delay:.2s}
@keyframes enter{from{opacity:0;transform:translateY(10px)}}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.strip i,.fold>summary::after,.jump{transition:none}
tbody tr.flash{animation-duration:2.4s}}
/* ── sizes ── */
@media (max-width:1180px){.hero-grid{grid-template-columns:1fr;grid-template-areas:"lead" "figs" "man";gap:32px}
.lead{flex-direction:row;flex-wrap:wrap;align-items:flex-end;gap:4px 24px}
.lead-n{font-size:112px}.lead-l,.lead-s,.jump{margin-top:0}.lead-txt{display:flex;flex-direction:column;gap:4px;padding-bottom:6px}
.manifest{padding-top:0}.group>.v{grid-column:1/-1}}
@media (min-width:1181px){.lead-txt{display:contents}}
@media (max-width:820px){
.canvas{padding:0 16px}.masthead{padding:32px 0 22px}h1{font-size:38px}.stamp{padding-bottom:0}
.slicers{position:static;padding:10px}.slicer{flex:1 1 200px}.fstate{margin-left:0;min-height:0}
.hero{padding:24px 20px 22px;border-radius:var(--r-lg)}.lead-n{font-size:96px}
.figs{gap:0}.fig{padding-left:16px}.fig-n{font-size:34px}.fig-l{font-size:13px;margin-top:8px}.fig-s{font-size:12px}
/* below 820px the manifest folds into a grid of squares, one per worker */
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(10px,1fr));height:auto;gap:3px}
.strip i{position:static;aspect-ratio:1;border-radius:2px}
.mlegend .hint{display:none}
.group{margin-top:56px}.gh h2{font-size:22px}.v{padding:18px}.vhead{margin-bottom:12px}
.hb{grid-template-columns:minmax(80px,36%) 1fr}.rail{flex-basis:calc(100% - 96px)}
.fold>summary{padding:16px 56px 16px 18px}.fold>summary::after{right:16px}.fold>.body{padding:0 18px 16px}
/* tables become one card per person */
.scroll{overflow:visible;margin:0;padding:0}
.rt thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.rt,.rt tbody{display:block}
.rt tr{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:14px 0;border-bottom:1px solid var(--line)}
.rt tr:last-child{border-bottom:0}
.rt td{display:block;padding:0;border:0}
.rt td.nm{flex:1 0 100%;font-size:15px;white-space:normal}
.rt td.em{flex:1 0 100%;margin-top:-4px;font-size:13px}
.rt td[data-label]{font-size:13px}
.rt td[data-label]::before{content:attr(data-label) " ";color:var(--muted)}
.rt td.bk{flex:1 0 100%;font-size:12.5px;margin-top:-4px}
.rt td.bk:empty,.rt td.bk.more{display:none}
.rt td.st.ok{display:none}
.rt .pill .it{display:inline}}
@media (max-width:480px){h1{font-size:32px}.lead-n{font-size:84px}.fig{padding-left:12px}.fig-n{font-size:28px}.lede{font-size:14px}}
"""

BODY = """
<noscript><section class="v glass"><p>This dashboard needs JavaScript to draw its charts.</p></section></noscript>
<div class="slicers" role="search">
  <div class="slicer"><label for="f-bk">Bookings</label><select id="f-bk">
    <option value="">All workers</option><option value="w">Booked in the next 14 days</option>
    <option value="l">Booked later</option><option value="x">No booking</option></select></div>
  <div class="slicer"><label for="f-emp">Employer</label><select id="f-emp"></select></div>
  <div class="slicer"><label for="f-q">Find a person</label><input id="f-q" type="search" placeholder="Name" autocomplete="off"></div>
  <div class="fstate"><span class="chip" id="f-chip" aria-live="polite"></span>
  <button class="clear" id="f-clear" type="button" hidden>Clear filters</button></div>
</div>

<div class="stagebox">
<section class="hero" aria-labelledby="g-status"><h2 class="sr" id="g-status">Where things stand</h2>
  <div class="hero-grid"><div class="lead" id="lead"></div>
  <div class="manifest"><div class="strip" id="strip" role="img"></div><div class="mlegend" id="mlegend"></div></div>
  <div class="figs" id="figs"></div></div>
</section>
</div>

<section class="group" aria-labelledby="g-site">
  <div class="gh"><h2 id="g-site">On site without a site induction</h2><p>A room on site tonight, or a stay on site or flight into
    Meekatharra since June 2025, without a held Crown Prince Project Site Induction</p></div>
  <section class="v glass top"><div class="vhead"><div><h3 id="h-s"></h3>
    <p class="sub">On site now first, then most recently on site. The Bookings filter does not apply here.</p></div></div>
    <div id="tbl-s"></div></section>
</section>

<section class="group" id="g-chase-sec" aria-labelledby="g-chase">
  <div class="gh"><h2 id="g-chase">Who to chase</h2><p>Each person below is missing at least one item. Clear these before they travel.</p></div>
  <section class="v glass top"><div class="vhead"><div><h3 id="h-n">Not cleared to mobilise</h3>
    <p class="sub">By employer A&ndash;Z, then next booking. People with no booking come last.</p></div>
    <button class="btn" id="x-n" type="button"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8m0 0L4.5 6.5M8 10l3.5-3.5M2.5 13.5h11"
    fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Download Excel</span></button></div>
    <div id="tbl-n"></div></section>
  <details class="fold inline"><summary><span class="t">What the states mean</span></summary><div class="body">
    <p class="note"><b>Missing</b> = no document added (induction: not yet completed). <b>Expired</b> = the document or
    competency has expired. <b>No document</b> = marked competent but nothing uploaded. <b>Not on role</b> = the
    person's work role in PeopleTray does not ask for this item, so it has never been recorded; fix the work role.
    Medical = Pre Employment Medical, or a Medical Declaration for Short Term Workers.</p></div></details>
</section>

<section class="group" aria-labelledby="g-gaps">
  <div class="gh"><h2 id="g-gaps">Where the gaps are</h2><p>Which items are missing, and which employers to follow up. Click an employer to filter the page.</p></div>
  <section class="v glass fillv" style="--span:5"><h3>What is missing</h3><p class="sub">Workers not cleared, by item and gap type. One person can lack several items.</p>
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
  <div class="lists">
  <details class="v glass fold" id="card-r"><summary><span class="t" id="h-r">No work role in PeopleTray</span>
    <span class="sub">Cannot be checked until a work role is set</span></summary><div class="body" id="tbl-r"></div></details>
  <details class="v glass fold" id="card-u" hidden><summary><span class="t" id="h-u">Bookings not matched to a PeopleTray profile</span>
    <span class="sub">Check the name or work email on the booking</span></summary><div class="body" id="tbl-u"></div></details>
  <details class="v glass fold" id="card-c"><summary><span class="t" id="h-c">Cleared to mobilise</span>
    <span class="sub">Every item held</span></summary><div class="body" id="tbl-c"></div></details>
  </div>
</section>
"""

JS = r"""
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("mobs-data").textContent);
  D.people.forEach(function (p, i) { p.i = i; });
  var REDUCED = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var STATUS = [
    {k: "c", label: "Cleared", color: "#0f4d1e"},
    {k: "n", label: "Not cleared", color: "#e53935"},
    {k: "r", label: "No work role", color: "#AAC2C5"},
    {k: "u", label: "Not matched", color: "#99999A"}
  ];
  var STATUSBY = {};
  STATUS.forEach(function (s) { STATUSBY[s.k] = s; });
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
  F.bk = F.bk || ""; F.q = F.q || ""; F.emp = F.emp || "";
  function saveFilters() { try { sessionStorage.setItem("mobs-filters", JSON.stringify(F)); } catch (e) {} }

  function h(tag, props, kids) {
    var el = document.createElement(tag);
    if (props) Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (v == null) return;
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
  function fill(el, kids) {
    el.replaceChildren();
    kids.forEach(function (c) { if (c != null) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
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
  function count(n, cls) { return h("span", {"class": "count" + (cls ? " " + cls : ""), text: String(n)}); }

  // ── tooltip: values lead, labels follow; built with textContent only ──────────
  var tip = h("div", {"class": "tip", role: "tooltip"});
  document.body.appendChild(tip);
  var TIPS = new WeakMap();
  function drawTip(t, x, y) {
    fill(tip, [h("div", {"class": "tt", text: t.title}), t.sub ? h("div", {"class": "ts", text: t.sub}) : null]);
    t.rows.forEach(function (r) {
      tip.appendChild(h("div", {"class": "tr"}, [h("i", {style: "background:" + r.color}),
        h("b", {text: String(r.v)}), h("span", {text: r.l})]));
    });
    tip.style.display = "block";
    var w = tip.offsetWidth, ht = tip.offsetHeight;
    var left = Math.min(x + 14, window.innerWidth - w - 8);
    var top = y + 16 + ht > window.innerHeight ? y - ht - 12 : y + 16;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }
  function hideTip() { tip.style.display = "none"; }
  function withTip(el, title, rows) {
    TIPS.set(el, {title: title, rows: rows});
    el.addEventListener("pointermove", function (e) { drawTip(TIPS.get(el), e.clientX, e.clientY); });
    el.addEventListener("pointerleave", hideTip);
    el.addEventListener("focus", function () { var r = el.getBoundingClientRect(); drawTip(TIPS.get(el), r.left, r.bottom); });
    el.addEventListener("blur", hideTip);
    return el;
  }
  window.addEventListener("scroll", hideTip, {passive: true});
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

  // ── hero: the headline numbers ────────────────────────────────────────────────
  function hero(R) {
    var c = countBy(R, "s"), ok = c.c || 0, bad = c.n || 0, nr = c.r || 0, checked = ok + bad;
    var who = F.bk === "w" ? " booked in the next 14 days" : F.bk === "l" ? " booked later" : F.bk === "x" ? " with no booking" : "";
    var arrow = sv("svg", {viewBox: "0 0 12 12", "aria-hidden": "true"});
    arrow.appendChild(sv("path", {d: "M6 1.5v9m0 0L2 6.5M6 10.5l4-4", fill: "none", stroke: "currentColor", "stroke-width": "1.6",
      "stroke-linecap": "round", "stroke-linejoin": "round"}));
    fill(document.getElementById("lead"), [
      h("span", {"class": "lead-n" + (bad ? "" : " zero"), text: String(bad)}),
      h("span", {"class": "lead-txt"}, [
        h("span", {"class": "lead-l", text: "Not cleared to mobilise"}),
        h("span", {"class": "lead-s", text: !R.length ? "No workers match the filters."
          : bad ? "of " + plural(R.length, "worker", "workers") + who
          : "Everyone in this selection with a work role holds all five items."}),
        bad ? h("a", {"class": "jump", href: "#g-chase-sec"}, ["See who to chase", arrow]) : null])]);
    function fig(n, label, sub, cls) {
      return h("div", {"class": "fig"}, [h("span", {"class": "fig-n" + (cls ? " " + cls : ""), text: n}),
        h("span", {"class": "fig-l", text: label}), sub ? h("span", {"class": "fig-s", text: sub}) : null]);
    }
    fill(document.getElementById("figs"), [
      fig(String(ok), "Cleared to mobilise", null, "ok"),
      fig(pct(ok, checked), "Ready", checked ? ok + " of " + checked + " with a work role" : null),
      fig(String(nr), "No work role in PeopleTray", null)]);
    manifest(R, c);
  }

  // ── the manifest: every worker in the selection as one mark ───────────────────
  var ORDER = {c: 0, n: 1, r: 2, u: 3}, firstDraw = true;
  var stripEl = document.getElementById("strip");
  function manifest(R, c) {
    var list = R.slice().sort(function (a, b) {
      return ORDER[a.s] - ORDER[b.s] || a.e.localeCompare(b.e) || a.n.localeCompare(b.n);
    });
    stripEl.replaceChildren();
    stripEl.className = "strip" + (firstDraw && !REDUCED ? " enter" : "");
    list.forEach(function (p, k) {
      var t = h("i", {"class": "s-" + p.s, "data-i": String(p.i)});
      if (firstDraw) t.style.setProperty("--k", String(k));
      stripEl.appendChild(t);
    });
    firstDraw = false;
    layoutStrip();
    var present = presentStatuses(R).filter(function (s) { return c[s.k]; });
    stripEl.setAttribute("aria-label", "Every worker in the selection, one mark each: " +
      present.map(function (s) { return c[s.k] + " " + s.label.toLowerCase(); }).join(", "));
    fill(document.getElementById("mlegend"), present.map(function (s) {
      return h("span", null, [h("i", {"class": "sw", style: "background:" + s.color}), s.label, h("b", {text: String(c[s.k])})]);
    }).concat(R.length ? [h("span", {"class": "hint", text: "One mark per worker, in tens. Click one to find them in the lists."})] : []));
  }
  // Every mark the same whole number of device pixels wide, starting on a whole device pixel (fractional
  // widths render as an uneven 2px/3px shimmer across 250 thin marks). Marks sit in tens, like a ruler; the
  // wider gap between tens takes up the leftover pixels, so the small gaps stay identical too.
  var WAFFLE = window.matchMedia ? window.matchMedia("(max-width: 820px)") : {matches: false};
  function layoutStrip() {
    var marks = stripEl.children, N = marks.length, k;
    if (WAFFLE.matches) { for (k = 0; k < N; k++) { marks[k].style.left = ""; marks[k].style.width = ""; } return; }
    if (!N) return;
    var dpr = window.devicePixelRatio || 1, box = stripEl.getBoundingClientRect();
    var off = Math.ceil(box.left * dpr) - box.left * dpr;
    var W = Math.floor(box.width * dpr - off), g = Math.max(1, Math.round(dpr)), G = 2 * g, B = Math.floor((N - 1) / 10);
    var w = Math.floor((W - (N - 1) * g - B * G) / N);
    // too narrow for a gap between every mark: each ten closes up into one block (marks under 2 device px wide
    // with 1px gaps read as a grey hatch)
    if (w < 2) { g = 0; w = Math.floor((W - B * G) / N); }
    if (w < 1) { w = 1; G = 0; B = 0; g = N > 1 ? Math.max(0, Math.floor((W - N) / (N - 1))) : 0; }
    var capped = w > 14 * dpr;
    if (capped) w = Math.floor(14 * dpr);
    var extra = capped ? 0 : Math.max(0, W - N * w - (N - 1) * g - B * G), x = off, b = 0;
    function share(i, parts) { return Math.floor((i + 1) * extra / parts) - Math.floor(i * extra / parts); }
    for (k = 0; k < N; k++) {
      marks[k].style.left = (x / dpr) + "px";
      marks[k].style.width = (w / dpr) + "px";
      if (k === N - 1) break;
      x += w + g;
      if (B && (k + 1) % 10 === 0) { x += G + share(b, B); b++; }
      else if (!B) x += share(k, N - 1);
    }
  }
  if (window.ResizeObserver) new ResizeObserver(layoutStrip).observe(stripEl);
  else window.addEventListener("resize", layoutStrip);
  function personTip(p) {
    var s = STATUSBY[p.s], rowsOut = [{v: s.label, l: "", color: s.color}];
    if (p.st) p.st.forEach(function (code, i) {
      if (code !== "ok") rowsOut.push({v: D.items[i], l: GAPBY[code].label.toLowerCase(), color: TABLE_TONE[code] || GAPBY[code].color});
    });
    return {title: p.n, sub: p.e, rows: rowsOut};
  }
  function markAt(e) { var t = e.target; return t && t.parentNode === stripEl ? D.people[+t.getAttribute("data-i")] : null; }
  stripEl.addEventListener("pointermove", function (e) { var p = markAt(e); if (p) drawTip(personTip(p), e.clientX, e.clientY); else hideTip(); });
  stripEl.addEventListener("pointerleave", hideTip);
  stripEl.addEventListener("click", function (e) { var p = markAt(e); if (p) { hideTip(); jumpTo(p); } });
  function jumpTo(p) {
    var row = document.getElementById("p-" + p.i);
    if (!row) return;
    var fold = row.closest("details");
    if (fold && !fold.open) fold.open = true;
    row.scrollIntoView({block: "center", behavior: REDUCED ? "auto" : "smooth"});
    row.classList.remove("flash"); void row.offsetWidth; row.classList.add("flash");
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

  // ── % of each employer's people not cleared ───────────────────────────────────
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
        [h("i", {style: "width:" + Math.max(share, 2) + "%"})]);
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
    var list = h("div", {"class": "ibars"});
    rowsData.forEach(function (r) {
      var parts = GAP.map(function (g) { return {v: r.c[g.k] || 0, label: g.label, color: g.color}; })
        .filter(function (p) { return p.v; });
      var bar = h("div", {"class": "sbar static", style: "width:" + (100 * r.t / max) + "%"}, parts.map(function (p) {
        return h("i", {style: "flex:" + p.v + " 1 0;background:" + p.color});
      }));
      withTip(bar, r.item, parts.map(function (p) { return {v: p.v, l: p.label, color: p.color}; }));
      list.appendChild(h("div", {"class": "ib"}, [
        h("div", {"class": "ib-h"}, [h("span", {text: r.item}),
          h("em", null, [h("b", {text: String(r.t)}), r.t === 1 ? " person" : " people"])]),
        h("div", {"class": "ib-track"}, [bar])]));
    });
    box.appendChild(list);
  }

  // ── columns by day of first booking ───────────────────────────────────────────
  function days(R) {
    var box = document.getElementById("days");
    box.replaceChildren();
    var statuses = presentStatuses(R), by = {};
    R = R.filter(function (p) { return p.w; });
    R.forEach(function (p) { var d = by[p.d] || (by[p.d] = {t: 0}); d[p.s] = (d[p.s] || 0) + 1; d.t += 1; });
    var max = Math.max(1, Math.max.apply(null, D.days.map(function (d) { return by[d] ? by[d].t : 0; })));
    var PLOT = 176;
    box.appendChild(legend(statuses));
    var cols = h("div", {"class": "cols", role: "img", "aria-label": "People by day of first booking"});
    var xl = h("div", {"class": "xl"});
    D.days.forEach(function (d, i) {
      var v = by[d] || {t: 0};
      var stack = h("div", {"class": "stack"});
      statuses.forEach(function (s) {
        if (v[s.k]) stack.appendChild(h("i", {style: "height:" + Math.max(3, PLOT * v[s.k] / max) + "px;background:" + s.color}));
      });
      var col = h("div", {"class": "col", tabindex: v.t ? 0 : -1},
        [v.t ? h("span", {"class": "tot", text: String(v.t)}) : null, stack]);
      if (v.t) withTip(col, (i === 0 ? "Today, " : "") + fmtDay(d), statuses.filter(function (s) { return v[s.k]; })
        .map(function (s) { return {v: v[s.k], l: s.label, color: s.color}; }));
      cols.appendChild(col);
      var dd = day(d);
      xl.appendChild(h("span", {"class": i === 0 ? "today" : ""}, [i === 0 ? "Today" : dd.dow, h("b", {text: String(dd.n)})]));
    });
    box.appendChild(cols);
    box.appendChild(xl);
  }

  // ── tables (the table view of every chart) ────────────────────────────────────
  function bookingCell(p) {
    if (!p.d) return h("td", {"class": "bk more", text: "–"});
    return h("td", {"class": "bk"}, [p.b, p.m ? h("span", {"class": "more", text: " +" + p.m + " more"}) : null]);
  }
  // Neil, 2026-10-24: in the tables No document reads red like Missing (the chart keeps Sand to tell them apart).
  var TABLE_TONE = {nodoc: "#c62f3f"};
  function tick() {
    var s = sv("svg", {viewBox: "0 0 20 20", "class": "tick", role: "img", "aria-label": "Held"});
    s.appendChild(sv("circle", {cx: 10, cy: 10, r: 9, fill: "rgba(15,77,30,.1)"}));
    s.appendChild(sv("path", {d: "M6 10.4l2.6 2.6L14.2 7.4", fill: "none", stroke: "#0f4d1e", "stroke-width": "1.9",
      "stroke-linecap": "round", "stroke-linejoin": "round"}));
    return s;
  }
  function stateCell(code, item) {
    if (code === "ok") return h("td", {"class": "st ok"}, [tick()]);
    var g = GAPBY[code], color = TABLE_TONE[code] || g.color;
    return h("td", {"class": "st"}, [h("span", {"class": "pill",
      style: "background:color-mix(in srgb," + color + " 14%,#fff)"}, [h("i", {style: "background:" + color}),
        item ? h("span", {"class": "it", text: item + " · "}) : null, g.label])]);
  }
  function table(boxId, list, withItems, empty) {
    var box = document.getElementById(boxId);
    box.replaceChildren();
    if (!list.length) { box.appendChild(h("p", {"class": "empty", text: empty})); return; }
    var head = ["Name", "Employer", "Next booking", "Booking"].map(function (t) { return h("th", {text: t}); });
    if (withItems) D.items.forEach(function (t) { head.push(h("th", {"class": "st", text: t})); });
    var body = h("tbody");
    list.forEach(function (p) {
      var cells = [h("td", {"class": "nm", text: p.n}), h("td", {"class": "em", text: p.e}),
        h("td", {"class": "when", "data-label": p.d ? "Next booking" : null, text: fmtDay(p.d)}), bookingCell(p)];
      if (withItems) p.st.forEach(function (code, i) { cells.push(stateCell(code, D.items[i])); });
      body.appendChild(h("tr", {id: "p-" + p.i}, cells));
    });
    box.appendChild(h("div", {"class": "scroll"}, [h("table", {"class": "rt"}, [h("thead", null, [h("tr", null, head)]), body])]));
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
    fill(document.getElementById("h-n"), ["Not cleared to mobilise", count(n.length, n.length ? "bad" : "")]);
    fill(document.getElementById("h-r"), ["No work role in PeopleTray", count(r.length)]);
    fill(document.getElementById("h-u"), ["Bookings not matched to a PeopleTray profile", count(u.length)]);
    fill(document.getElementById("h-c"), ["Cleared to mobilise", count(c.length)]);
    document.getElementById("card-u").hidden = !u.length;
    table("tbl-n", n, true, "Nobody in this selection is missing an item.");
    table("tbl-r", r, false, "Everyone in this selection has a work role.");
    table("tbl-u", u, false, "");
    table("tbl-c", c, true, "Nobody in this selection is cleared yet.");
  }

  // ── on site (now or before) without a held site induction ────────────────────
  function siteTable() {
    var qq = F.q.trim().toLowerCase();
    var list = D.people.filter(function (p) {
      return p.ls && p.ind && p.ind !== "ok" && (!F.emp || p.e === F.emp) && (!qq || p.n.toLowerCase().indexOf(qq) >= 0);
    }).sort(function (a, b) {
      return (b.os - a.os) || b.ls.localeCompare(a.ls) || a.n.localeCompare(b.n);
    });
    var now = list.filter(function (p) { return p.os; }).length;
    fill(document.getElementById("h-s"), [plural(list.length, "person", "people"),
      now ? h("span", {"class": "where now"}, [h("i"), now + " on site now"]) : null]);
    var box = document.getElementById("tbl-s");
    box.replaceChildren();
    if (!list.length) { box.appendChild(h("p", {"class": "empty", text: "Nobody in this selection has been on site without a site induction."})); return; }
    var head = ["Name", "Employer", "On site", "Last on site", "Site induction", "Next booking"].map(function (t) {
      return h("th", {"class": t === "Site induction" ? "st" : "", text: t}); });
    var body = h("tbody");
    var year = D.days[0].slice(0, 4);
    list.forEach(function (p) {
      body.appendChild(h("tr", null, [h("td", {"class": "nm", text: p.n}), h("td", {"class": "em", text: p.e}),
        h("td", null, [h("span", {"class": "where " + (p.os ? "now" : "past")}, [h("i"), p.os ? "On site now" : "Been to site"])]),
        h("td", {"class": "when", "data-label": "Last on site", text: fmtDay(p.ls) + (p.ls.slice(0, 4) !== year ? " " + p.ls.slice(0, 4) : "")}),
        stateCell(p.ind, "Site induction"),
        h("td", {"class": "when", "data-label": p.d ? "Next booking" : null, text: fmtDay(p.d)})]));
    });
    box.appendChild(h("div", {"class": "scroll"}, [h("table", {"class": "rt"}, [h("thead", null, [h("tr", null, head)]), body])]));
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
  var xBtn = document.getElementById("x-n"), xLabel = xBtn.querySelector("span");
  function downloadExcel() {
    var list = notCleared.slice();
    if (!list.length) return;
    xBtn.disabled = true; xLabel.textContent = "Preparing…";
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
      xLabel.textContent = "Download Excel"; xBtn.disabled = !notCleared.length;
    });
  }
  xBtn.addEventListener("click", downloadExcel);

  function render() {
    hideTip();
    if (F.emp && !D.people.some(function (p) { return p.e === F.emp; })) F.emp = "";
    sel.value = F.emp; q.value = F.q; bkSel.value = F.bk;
    var active = F.emp || F.q.trim() || F.bk;
    clearBtn.hidden = !active;
    var R = rows(false);
    chip.textContent = active ? "Showing " + R.length + " of " + D.people.length : "";
    saveFilters();
    hero(R); siteTable(); employers(rows(true)); items(R); days(R); tables(R); employerShare(rows(true));
  }
  render();
})();
"""
