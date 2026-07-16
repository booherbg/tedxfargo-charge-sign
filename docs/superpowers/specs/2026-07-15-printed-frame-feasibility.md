# Printed frame / back panels / legs — feasibility (2026-07-15)

**Question:** could the wood frame, back skin, and legs all be 3D printed instead?

**Verdict: possible, and physics is never the blocker — print time is.** ~84 h and ~3.3 kg of
PETG to replace ~$25 of lumber that is stiffer per gram and per dollar. **Wood remains the
plan.** Recorded so a revisit doesn't redo the analysis.

Motivation if revisited (user, 2026-07-15, priority order): (1) avoid woodworking, (2) a
fully-printed / reproducible artifact, (3) structural integration. Mounting reality: the bolt
board hangs off the **left side of the wood-framed CHARGE sign** — so no base/stand is needed.

## Numbers

Sign envelope 2067 mm (board 410 + gap 60 + word 1597). Back-skin area 0.697 m². PETG @1.27,
observed rate ~41 g/h (360 g avg piece / 8h51m), ~$22/kg.

| item | mass | print | $ |
|------|------|-------|---|
| back skin @2 mm | 1769 g | 43.5 h | $39 |
| frame @75 mm deep, ~5 m of member | 1508 g | 37.1 h | $33 |
| **added total** | **~3.3 kg** | **~84 h** | **~$72** |

Doubles project filament (3.3 kg printed → 6.7 kg). Panelization falls out exactly: back skin
needs **6 word + 2×2 board = 10 panels**, mirroring the front's 6+4 — same seams, same strap
vocabulary, nothing new to invent. Frame would need ~16 spliced joints.

## Why the section is never the problem

Every load case lands 50–200× under limits, because the word band is **295 mm deep as a beam**
over a ~2 m span:

| load case | result |
|-----------|--------|
| hanging, full 2067 mm span | 0.37 mm sag |
| word band as a 1597 mm cantilever | 0.85 mm tip deflection |
| flange stress | 0.243 MPa = **0.5% of PETG yield** |

At 0.5% of yield, **creep is a non-issue too** (needs sustained stress near yield or temps near
Tg). The intuition "a printed frame will sag over time" is not supported by the arithmetic.
Freestanding was analysed and set aside once mounting was settled; for the record, a
self-supporting version tips at **9.8°** (95 mm footprint vs 275 mm CG) and would need 200–320 mm
of outrigger plus likely ballast — stability wants mass and width, which printing is worst at.

## Fastening (if revisited)

No new vocabulary needed — reuse the seam-strap pattern that passed 43 QA checks: butt the
members, splice with a printed strap, **M4×8 button-heads into captive hex nuts** (~16 joints ≈
64 screws + nuts). Carry over the **0.12 mm/joint seam relief**; 16 unrelieved butt joints stack
±2.4 mm across the span.

## Rule the numbers support

**Print connectors, not spans or sheets.** Brackets are complex geometry where printing wins.
Long members and flat panels are where it loses to a saw — a flat sheet is the single worst
geometry for a printer (slow, warp-prone, seam-heavy), and the sag math shows the back skin
carries no bending anyway. Its real jobs are hiding wiring and blocking light.

## The one thing this changed in the wood plan

Printing the frame would eliminate the **PETG-on-wood thermal differential** via matched CTE —
the only genuine engineering argument found in favour, and still not worth 84 h. The differential
is real and is now recorded as an assembly note in `assembly-charge.md` (step 2):

| ΔT | word run grows | wood rail grows | differential | vs 0.6 mm relief |
|----|----------------|-----------------|--------------|------------------|
| 10 °C | 1.12 mm | 0.08 mm | 1.04 mm | **0.44 mm interference** |
| 20 °C | 2.24 mm | 0.16 mm | 2.08 mm | **1.48 mm interference** |

PETG ~70 µm/m/°C vs wood along grain ~5. The LEDs make this a **standing** delta — they warm the
PETG inside the plenum while the rail sits at ambient — not merely seasonal.
