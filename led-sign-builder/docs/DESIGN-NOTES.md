# UI Design Notes — "Console SF-1"

## Seeded direction (deliberately off-default)

The user asked for a 1950s industrial look chosen by a random seed that
overrides my defaults. Drawn with `secrets.randbelow(10**6)`:

- **SEED: 582035**
- Palette: **bakelite-and-brass** — dark bakelite browns (`#3B3630` panels,
  `#332F29` recesses), warm cream ink (`#EDE4D3`), brass accent (`#C99B3F`),
  verdigris secondary (`#7FA3A1`), amber glow (`#E0B25A`).
  (My unforced default would have been the cream/mint enamel diner look —
  the seed explicitly rejected it.)
- Type: **Bungee** for display (bundled OFL font, served locally via
  @font-face) + system **monospace** for spec labels.
- Ornament: **toggle switches + spec plates**, **chevron tape edges +
  stencil stamps**. Ornament lives in borders, labels, and controls — never
  in reading surfaces. Rivets at panel corners via radial gradients.

The metaphor: a 1957 machine-shop control console — engraved plates,
brass toggle levers, hazard-chevron trim, model plates ("MODEL SF-1").

## UX audit (of the v0.1 UI) → all addressed in this rewrite

1. No account surface → login/register card, header account chip, logout.
2. No queue visibility → QUEUE panel: position, status chips, cancel,
   per-job links + thumbnail after completion.
3. Build failures buried in a log → status chips + error strips.
4. Catalog gaps → plaque shape, palette, texture-target toggles, support-rib
   switch, custom bed fields, letter-spacing control.
5. Advanced JSON errors silent → live VALID/ERROR stamp on the editor.
6. No loading/empty states → preview shimmer text, queue empty-state copy.
7. File inputs gave no feedback → filename chips + clear buttons.
8. No mobile handling → panels stack under 920px.
9. No identity → inline-SVG favicon (brass bolt), MODEL SF-1 spec plate,
   tier stamp (FREE/PREMIUM/OPEN) in the header.
10. Free-tier limits invisible until a 403 → limits printed on the account
    chip and surfaced in build errors verbatim.
