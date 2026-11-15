# Dashboard redesign: NMG style guide, frosted glass (2026-11-16)

Neil's brief: use the NMG style guide (A9799 stylesheet), keep the frosted-glass theme, and make the dashboard
look high-end, modern and professional, befitting a top-tier mining company.

## Directions tried (rendered side by side on live data at 1440px)

1. **Porcelain**: all light, navy type on a Cool Grey field, gold hairlines. Clean, but it read as a tidy admin page.
2. **Night**: all dark navy with dark glass. Dramatic, but Neil's status colours (green #0f4d1e, red #e53935)
   disappear or go unreadable on navy, and changing them would undo his 2026-10-24 decision.
3. **Navy stage** (chosen): the masthead, filters and headline numbers sit on the guide's Navy -> River
   gradient, with bright frosted cards floating on it, then the working lists on frosted glass over the light
   field. It continues the navy header Neil already approved, keeps his colours legible (they sit on light glass),
   and gives the page one confident first screen.

## System (all colours are guide swatches or their 50% tints)

- Navy #083045, River #55848A, Gold #927128, Pale Gold #B19045, Sand #F1DCAA, Cool Grey #DBDBD3, Black 93% #333334,
  plus tints (Navy 50 #8498A2, River 50 #AAC2C5, Sand 50 #F8EED5, Cool Grey 50 #EDEDE9 = page field).
- Gradients from the guide: Navy -> River (the stage) and Gold -> Sand (the stage's bottom rule and the mark above
  each section heading). Gold light was tried on the stage and turns olive over navy, so gold is used only as line
  and type.
- Type: Figtree stands in for Proxima Nova (licensed): Black 900 for Heading 1, 800/700 for headings, 400 body,
  tabular figures for every number. Aptos is in the fallback stack.
- Status colours unchanged (Neil 2026-10-24): cleared green, not cleared red, Missing #c62f3f, Expired #e07b12,
  No document Sand (charts) / red (tables), Not on role Navy 50, no work role River 50.
- Radii 24/20/14/10; glass = white 58% + blur 22px; hero glass = white 88%; motion ease cubic-bezier(.22,1,.36,1).

## Signature: the manifest

One mark per worker in the selection, in status order, grouped in tens like a ruler. Pointing at a mark shows the
person and what they are missing; clicking jumps to their row (opening the list if it is folded) and flashes it.
Marks are placed by the script on whole device pixels, so every mark is identical at any width or zoom; where
marks would be under 2 device pixels, each ten closes into one block. Below 820px it folds into a grid of squares.
On load the marks rise left to right (follow-through, slow-out), once; reduced motion turns all motion off.

## Verification (2026-11-16, local preview on the live page's data)

- 360, 390, 768, 1024, 1100, 1240 (Wix embed width), 1280, 1440 px; DPR 1 and 2; no horizontal overflow;
  console clean.
- Entrance read frame by frame at 30 fps: masthead 0-200 ms, hero ~230 ms, manifest sweep 260-1000 ms; no pops.
- Interactions: tooltip, click-to-find (chase table and folded lists), employer filter, no-match state, Excel
  download (valid .xlsx), keyboard focus ring on filters, reduced motion (0 animations), empty data set.
- Tables become one card per person below 820px, showing only the missing items.

## Critique, round 1 (self-scored from the captures; no separate critic was started)

Design 7.5, Usability 8, Creativity 7, Content 8 -> weighted 7.6.
Fixed in the round: strip pixel snapping and grouping, hero composition (number left, manifest and figures right),
olive glow replaced, stage-to-section spacing (margin collapse), sticky filter bar too grey over light content,
"What is missing" layout, arrivals gridlines removed, mobile stray dash.

## Open

- The light section (tables, bar charts) is still conventional next to the stage.
- The dark green mass of the cleared marks is heavy; it is Neil's colour, so it stays unless he changes it.
- No NMG logo inside the page (the Wix page shows it above the embed); the bare Pages URL has none.
