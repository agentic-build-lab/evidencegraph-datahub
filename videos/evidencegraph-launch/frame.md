---
version: 2
name: EvidenceGraph Assurance Control Room
description: "A premium, evidence-dense product film for DataHub operators. Dark ink canvas, mint proof states, orange unresolved-risk states, Geist typography, crisp source identifiers, and restrained cinematic depth."
unit: "1920x1080 frame"
principle: "Evidence changes both scope and authority"

colors:
  bg: "#0C1B22"
  panel: "#122A33"
  panel-elevated: "#173641"
  primary: "#40E0C0"
  primary-soft: "rgba(64, 224, 192, 0.12)"
  text: "#E7EEEB"
  text-muted: "#9CB0AA"
  text-light: "#6F8580"
  risk: "#FF7048"
  risk-soft: "rgba(255, 112, 72, 0.12)"
  border: "rgba(121, 184, 171, 0.22)"
  positive: "#40E0C0"

typography:
  display: { fontFamily: "Geist", weight: 720, lineHeight: 0.98, tracking: "-0.045em" }
  heading: { fontFamily: "Geist", weight: 650, lineHeight: 1.08, tracking: "-0.03em" }
  body: { fontFamily: "Geist", weight: 450, lineHeight: 1.42, tracking: "-0.01em" }
  mono: { fontFamily: "Geist Mono", weight: 400, lineHeight: 1.35, tracking: "0" }

radii:
  panel: "24px"
  card: "16px"
  chip: "999px"

spacing:
  safe-x: "86px"
  safe-top: "62px"
  caption-cutoff: "896px"
  grid: "24px"

motion:
  entrance: "power3.out"
  settle: "power2.out"
  switch: "power3.inOut"
  micro: "0.18s"
  standard: "0.55s"
  camera: "1.1s"
---

# EvidenceGraph Assurance Control Room

## Brand truth

The film should look like a modern operational product used by senior data and AI platform teams: precise, alive, and calm under pressure. It is not a generic cyberpunk dashboard and not a consulting slide deck. Every visible surface must help prove a claim, reveal provenance, or show a change in policy authority.

Use the shipped font files only:

- `assets/fonts/Geist-Variable.woff2` for display, headings, and body.
- `assets/fonts/GeistMono-Regular.woff2` for field names, URNs, checksums, code, receipts, and run labels.

Every frame must declare its own matching `@font-face` rules. Do not use network imports or system-font names.

## Visual hierarchy

- One dominant proof per frame: a field diff, `3 / 7`, the DataHub hub, `7 / 7`, `9 FILES`, `14 / 14`, `3 / 3`, or the evidence-ledger CTA.
- Primary proof numbers use 96–154px Geist, bright off-white or mint.
- Frame headings use 54–72px Geist. Eyebrows and provenance labels use 15–19px Geist Mono with generous tracking.
- Supporting copy stays short and between 22–30px. Real identifiers and code may be 18–24px but must remain legible at 1080p.
- Reserve the bottom 184px for the root caption track. No consequential content may extend below y=896.

## Surfaces

- Canvas: #0C1B22 with a very subtle radial mint lift around the active evidence, never a generic blue-purple gradient.
- Primary panels: translucent #122A33 to #173641 with a 1px mint-neutral border and soft 24px radius.
- Depth comes from overlapping operational layers, controlled blur, inner highlights, and low soft shadows. Avoid thick borders, glassmorphism glare, or excessive bloom.
- Use the captured Assurance Studio image when a frame showcases the full product. Do not rebuild the full website. Overlay only the moving proof component required by the storyboard.

## Semantic color law

- Mint means grounded, verified, complete, eligible, or readback-confirmed.
- Orange means unresolved, quarantined, refused, blocked, or missing evidence.
- Off-white carries titles and neutral totals.
- Muted gray-green carries secondary metadata.
- Never use orange as decoration and never use mint for an unsupported claim.

## Motion language

- The main subject is visible by 0.5 seconds.
- Reveal evidence on the narration cue across the entire frame duration; do not front-load the complete interface.
- Prefer direct-to-slot motion, drawn lineage paths, count-up state changes, camera push-throughs, and explicit policy-state flips.
- Use one macro camera move per frame. Micro motion should stop when a proof state settles.
- No bouncing UI, fake cursor wandering, looping ambient movement, breathing cards, or independent screensaver motion.
- Every animation must be seek-safe and owned by the single paused GSAP timeline.

## Components

### Proof rail

A horizontal row of typed evidence cells with a large grounded/total counter. Incomplete cells use low-opacity borders; grounded cells fill with mint-soft and gain a small source tick.

### Evidence card

Contains object type, short name, owner, severity, and one source pointer. Use mono for the pointer. Keep the card compact enough to show an array without looking like a table dump.

### Provenance chip

Persistent small mono labels such as `SANITIZED MCP OBSERVATION TRACE`, `FROZEN RUN`, `RECORDED VALIDATION RECEIPTS`, `RECORDED APPROVED WRITE-BACK`, and `DETERMINISTIC CLOSURE REPLAY`. These are factual state boundaries, not decoration.

### Policy card

Pairs evidence completeness with the exact authority state. Examples: `PROPOSAL ALLOWED`, `9 DRAFTS QUARANTINED`, `0 WRITEBACK PROPOSALS`, `MUTATION BLOCKED`. Never display `MERGE ALLOWED`.

### Receipt row

Action key, status, readback state, and stable proposal ID. Mint is reserved for verified readback; no-op retries stay neutral-mint and retain `duplicates 0`.

### Code surface

Realistic mono code with restrained syntax color. Use short excerpts only and label them `EXCERPT` when not showing the complete frozen artifact.

## Composition rules

- Fill the top 83% with one coherent operating surface and supporting evidence; avoid a small card floating in empty space.
- Use asymmetry for investigation frames and centered symmetry only for the opening question, the authority split, and the final CTA.
- Keep public claims exact: repository-only `3/7`; DataHub `7/7`; nine artifacts; fourteen gates broken into `1 integrity + 8 parse + 5 native/integration`; three scoped writebacks; three verified retry no-ops; zero old-field consumers in the labeled closure replay.
- Keep provenance boundaries visible whenever live evidence, frozen evidence, historical receipts, and deterministic fixtures share the same frame.
- All content must be professional English.
