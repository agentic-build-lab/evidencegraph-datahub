---
format: 1920x1080
duration: 130s
message: "DataHub changes both the blast radius EvidenceGraph can see and the actions it is allowed to take"
arc: "Risk -> Blind spot -> Context -> Complete impact -> Migration -> Evidence authority -> Governed closure -> Inspect"
audience: data engineers, platform leaders, and hackathon judges
mode: autonomous
music: "A Little Story — Kei Morimoto / DOVA-SYNDROME"
captions: phrase-level
---

## Video direction

Build a premium assurance-control-room film, not a narrated slide deck. The story is one continuous investigation of the proposed `customer_tier` removal and its approved `segment_code` compatibility mapping. Deep ink (#0C1B22) is the operating canvas; mint (#40E0C0) means grounded evidence; off-white (#E7EEEB) carries the hierarchy; orange (#FF7048) appears only when evidence or authority is missing. Use Geist for display and body and Geist Mono for identifiers, receipts, and code.

The central proof is the authority switch: repository evidence sees 3/7 consumers and cannot authorize a safe decision; DataHub recovers 7/7, binds every impact to an object and owner, and allows a migration proposal only after deterministic gates pass. Removing one lineage page must visibly revoke that authority and quarantine all nine artifacts. Separate live DataHub writeback receipts from the deterministic closure replay. Keep captions in a dedicated lower band, one complete phrase at a time, maximum two lines. No karaoke highlighting, fake cursor motion, browser chrome, decorative dashboards, unsupported metrics, or unlabeled fixture/live state.

## Frame 1 — The change is not the incident

- scene: A contract diff enters an assurance console; “INCIDENT” is replaced by the question that drives the film.
- voiceover: "A schema change should not become an incident. Before anyone merges it, EvidenceGraph asks a harder question: what will this change actually break?"
- duration: 14s
- transition_in: cut
- status: animated
- src: compositions/frames/01-change-not-incident.html
- type: hook
- persuasion: risk prevention
- beat: tension -> control
- blueprint: kinetic-type-beats (Adapt)
- asset_candidates: assets/studio-control-room.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = supporting

narrativeRole: Establish the operational stake and turn it into an assurance question.
keyMessage: The dangerous event is an unexamined change, not the schema edit itself.

Scene 1 (0.0–2.8s): The required `customer_tier` field is removed, `segment_code` appears, and `INCIDENT` is challenged in the same visual plane.
Scene 2 (2.8–5.8s): The Assurance Studio rises behind the diff while one decisive orange stroke rejects the incident framing.
Scene 3 (5.8–9.0s): The evidence question resolves in two beats: “What will this change” and “actually break?”
Scene 4 (9.0–9.714s): The assurance state remains active through the transition into the repository-only ablation.

## Frame 2 — The 3/7 false-safe view

- scene: A repository-only scan grounds three consumers while four operational dependencies remain outside the codebase.
- voiceover: "Repository search finds three of seven downstream consumers. It misses the dashboard, the machine-learning feature, the model, and the production deployment. That is a forty-two point nine percent view — and a false-safe decision waiting to happen."
- duration: 20s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/02-repo-blind-spot.html
- type: pain_point
- persuasion: measured ablation
- beat: skepticism -> urgency
- blueprint: dataviz-countup (Adapt)
- asset_candidates: assets/studio-control-room.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = background (dim 18%)

narrativeRole: Prove why code-only reasoning cannot support a safe decision.
keyMessage: Repository evidence recovers only three of seven independently known impacts.

Scene 1 (0.0–4.0s): A seven-cell truth rail builds across the center. Only two dbt models and one orchestration job illuminate; the counter stops at `3 / 7`.
Scene 2 (4.0–10.0s): The three grounded cards dock on the left with repository paths. Four ghost cards remain on the right behind a vertical “OUTSIDE REPO” boundary.
Scene 3 (10.0–15.5s): Reveal the four missed consumers on their narrated cues: Executive Dashboard, ML Feature, Churn Model, Production Deployment. Each uses a distinct object-type glyph and muted lineage fragment.
Scene 4 (9.6–16.155s): Convert the rail to `42.9% COVERAGE`. An orange decision chip flips from “looks safe” to `FALSE-SAFE`; the independent truth manifest and decision boundary remain active through the final narration beat.

## Frame 3 — DataHub becomes executable context

- scene: Official DataHub interfaces hydrate one operational graph with the metadata needed to reason and act.
- voiceover: "EvidenceGraph reads DataHub through the official MCP server and the Python SDK. Schemas, ownership, lineage, contracts, tags, documentation, dashboards, and machine-learning metadata become one executable context graph."
- duration: 19s
- transition_in: crossfade
- status: animated
- src: compositions/frames/03-context-graph.html
- type: product_intro
- persuasion: mechanism clarity
- beat: curiosity -> clarity
- blueprint: constellation-hub (Adapt)
- asset_candidates: assets/studio-control-room.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = background (dim 22%)

narrativeRole: Introduce DataHub as the operational reasoning substrate, not a metadata search box.
keyMessage: Official interfaces supply one evidence-bound context graph.

Scene 1 (0.0–3.5s): A crisp DataHub core appears at center with two labeled ingress lanes: `OFFICIAL MCP SERVER` and `PYTHON SDK`.
Scene 2 (3.5–9.5s): Metadata packets arrive in paired beats—schema + contract, owner + docs, tags + lineage—then bind to typed graph nodes. Paths draw only after their source packet lands.
Scene 3 (9.5–15.0s): Dashboard and ML metadata complete the graph. Each node receives a source URN tick, emphasizing provenance rather than visual decoration.
Scene 4 (13.1–16.433s): The camera moves through the DataHub core into a compact decision panel labeled `EXECUTABLE CONTEXT GRAPH`; below it, three outputs resolve: `Scope`, `Plan`, `Authority`.

## Frame 4 — DataHub changes the blast radius

- scene: The 3/7 repository view expands to seven grounded impacts with owner, severity, path, and source object.
- voiceover: "Now the blast radius is complete: two dbt models, an Airflow job, an executive dashboard, an ML feature, a model, and its production deployment. Each path is routed to its owner, prioritized, and linked to the exact DataHub object that supports it."
- duration: 21s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/04-complete-blast-radius.html
- type: feature_showcase
- persuasion: graph proof
- beat: relief + control
- blueprint: grid-card-assemble (Adapt)
- asset_candidates: assets/studio-control-room.png, assets/studio-full-page.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = supporting | studio-full-page.png = background (dim 18%)

narrativeRole: Deliver the product’s core advantage and expose the evidence path behind every impact.
keyMessage: DataHub-grounded reasoning recovers all seven truth-manifest impacts with provenance.

Scene 1 (0.0–6.5s): Recorded Assurance Studio interaction runs the complete graph from `3 / 7` to `7 / 7`.
Scene 2 (6.5–10.4s): Owner, priority, and source URN populate across all seven consumers.
Scene 3 (8.7–12.5s): Dashboard and ML paths receive focused provenance traces.
Scene 4 (12.5–18.089s): The graph collapses into an ordered impact queue and resolves to `BLAST RADIUS GROUNDED — 7/7` without a static tail.

## Frame 5 — Compile a migration pack, not advice

- scene: Nine pull-request-ready files assemble, then a real patch and validation query open for inspection.
- voiceover: "EvidenceGraph does not stop at an explanation. It compiles nine concrete artifacts: SQL, dbt model and tests, validation queries, an Airflow evidence gate, an ML contract, a migration plan, and a real unified diff that Git can apply cleanly."
- duration: 20s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/05-migration-bundle.html
- type: feature_showcase
- persuasion: artifact-level proof
- beat: power + confidence
- blueprint: transcript-scroll-artifact-reveal (Adapt)
- asset_candidates: assets/studio-full-page.png
- focal: assets/studio-full-page.png
- roles: studio-full-page.png = background (dim 15%)

narrativeRole: Translate graph context into executable engineering work instead of generic recommendations.
keyMessage: The output is a nine-file migration pack ready for deterministic verification.

Scene 1 (0.0–2.8s): Recorded product interaction opens the migration pack and inspects a real artifact.
Scene 2 (2.3–13.8s): The `MIGRATION PACK / 9 FILES` manifest compiles SQL, dbt, validation, Airflow, ML, plan, manifest, and patch artifacts on their narrated cues.
Scene 3 (13.8–16.2s): The surface splits between the real unified diff and the deterministic zero-row validation query.
Scene 4 (16.2–18.492s): `git apply --check` resolves to `PASS`; checksum, run ID, and draft-only authority remain visible.

## Frame 6 — Evidence changes authority

- scene: Fourteen gates are broken into honest categories; complete evidence permits proposals, while one missing lineage page quarantines every artifact and blocks mutation.
- voiceover: "Fourteen deterministic gates: DuckDB, dbt Core, the official Airflow container, feature-parity checks, and Git patch application. All fourteen pass. Remove one lineage page, and EvidenceGraph refuses the safe-to-merge verdict and blocks every mutation."
- duration: 22s
- transition_in: squeeze
- status: animated
- src: compositions/frames/06-evidence-gates.html
- type: feature_showcase
- persuasion: authority reversal
- beat: trust -> guarded confidence
- blueprint: agent-progress-theater (Adapt)
- asset_candidates: assets/studio-control-room.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = background (dim 16%)

narrativeRole: Demonstrate that DataHub evidence determines both scope and the agent’s authority to act.
keyMessage: Passing deterministic checks allows a proposal; missing evidence revokes authority and blocks mutation.

Scene 1 (0.0–4.0s): A gate matrix appears with the honest breakdown: `1 integrity`, `8 parse`, `5 native / integration`, totaling `14`. A small line reads `Deterministic gate suite`.
Scene 2 (4.0–11.0s): Receipts resolve by category. Show concrete runtime labels only where supported: DuckDB, dbt Core, Airflow container, feature parity, Git apply. The total becomes `14 / 14 PASS`.
Scene 3 (9.7–10.6s): Complete DataHub evidence binds to `Confidence 1.00`, nine drafts eligible for proposal, and zero mutations without approval.
Scene 4 (10.35–16.25s): Recorded Assurance Studio interaction removes one lineage page, lowers confidence to `0.65`, quarantines all drafts, and blocks writeback.
Scene 5 (16.0–18.452s): The authority comparison resolves to `PROPOSAL ALLOWED` versus `MUTATION BLOCKED`.

## Frame 7 — Governed writeback, idempotent retry, deterministic closure

- scene: A separately approved live writeback verifies by readback; a stateless retry produces no duplicates; a clearly labeled replay proves closure against a newer complete graph.
- voiceover: "With explicit approval, three scoped results write back into DataHub and verify by readback. A new client retries the same plan: three verified no-ops, no duplicates. In the deterministic closure replay, EvidenceGraph requires a newer complete graph and closes only when the retired field has zero remaining consumers."
- duration: 22s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/07-writeback-closure.html
- type: benefit_highlight
- persuasion: governed operational closure
- beat: confidence -> peace of mind
- blueprint: camera-journey (Adapt)
- asset_candidates: assets/studio-full-page.png
- focal: assets/studio-full-page.png
- roles: studio-full-page.png = background (dim 14%)

narrativeRole: Complete the loop without conflating live mutation receipts and fixture-based closure proof.
keyMessage: Explicitly approved results verify by readback, retries are idempotent, and closure requires fresher complete evidence.

Scene 1 (0.0–4.5s): Establish three horizontally connected zones: `SEPARATE APPROVED RUN`, `STATELESS RETRY`, `DETERMINISTIC CLOSURE REPLAY`. Keep these provenance labels persistent.
Scene 2 (4.5–10.0s): In the approved-run zone, three scoped DataHub writes resolve to `APPLIED + READBACK VERIFIED`. Show stable proposal IDs and the source run label.
Scene 3 (10.0–14.5s): Move to the retry zone. The same three action keys resolve to `NO-OP + VERIFIED`; duplicate count stays at `0`.
Scene 4 (14.5–19.0s): Move to the replay zone. A newer complete graph timestamp overtakes the applied timestamp, then old-field consumers count down from seven to zero.
Scene 5 (19.0–22.0s): Resolve the loop to `CLOSED`, with three supporting facts: `newer graph`, `complete evidence`, `0 remaining consumers`.

## Frame 8 — Inspect, do not merely believe

- scene: A live Assurance Studio view and an evidence ledger resolve into a concise reproducibility call to action.
- voiceover: "EvidenceGraph makes DataHub's context graph operational. Inspect the public replay, audit every claim in the evidence ledger."
- duration: 12s
- transition_in: blur-crossfade
- status: animated
- src: compositions/frames/08-inspect-every-claim.html
- type: cta
- persuasion: transparent reproducibility
- beat: motivation + trust
- blueprint: titlecard-reveal (Adapt)
- asset_candidates: assets/studio-control-room.png
- focal: assets/studio-control-room.png
- roles: studio-control-room.png = background (dim 8%)

narrativeRole: Convert interest into inspection and reproducibility.
keyMessage: The interactive replay, evidence ledger, and source code are the call to action.

Scene 1 (0.0–6.9s): Recorded Assurance Studio interaction runs the assurance replay while three proof receipts dock: `7/7 grounded`, `14/14 passed`, `3/3 verified`.
Scene 2 (6.55–9.9s): The recorded evidence ledger opens and one claim is bound to its DataHub object, confidence, and receipt.
Scene 3 (9.45–13.644s): A clean-clone command runs, deterministic receipts resolve, and the public URL plus `Replay`, `Audit`, and `Run` actions remain active through the final frame.
