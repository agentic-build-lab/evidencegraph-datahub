"use client";

import { useMemo, useState } from "react";

const impacts = [
  ["ML feature", "customer_tier_signal", "blocker", 100, "risk-ml"],
  ["dbt model", "analytics.fct_customer_value", "blocker", 90, "growth-analytics"],
  ["ML deployment", "churn-api-prod", "blocker", 90, "risk-ml"],
  ["ML model", "churn_propensity_v4", "critical", 85, "risk-ml"],
  ["Looker", "Executive Revenue Watch", "critical", 80, "finance-analytics"],
  ["dbt model", "analytics.stg_orders", "critical", 75, "analytics-engineering"],
  ["Airflow", "daily_customer_value.build_customer_value", "high", 60, "data-platform"],
] as const;

const validators = [
  ["SQL parity", "DuckDB", "4/4 rows"],
  ["dbt build", "dbt Core 1.12.0", "7/7 tests"],
  ["DAG gate", "Airflow 3.3.0", "official container"],
  ["ML parity", "Feature contract", "0.0% mismatch"],
  ["Patch apply", "Git", "clean apply"],
] as const;

type View = "impact" | "bundle" | "evidence" | "writeback";

export default function Home() {
  const [view, setView] = useState<View>("impact");
  const [ran, setRan] = useState(false);
  const [complete, setComplete] = useState(true);
  const decision = complete ? "PROPOSE MIGRATION" : "REFUSE & ESCALATE";
  const visibleImpacts = useMemo(
    () =>
      ran
        ? impacts
        : impacts.filter((item) =>
            [
              "analytics.stg_orders",
              "analytics.fct_customer_value",
              "daily_customer_value.build_customer_value",
            ].includes(item[1]),
          ),
    [ran],
  );

  return (
    <main>
      <nav className="nav shell" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="EvidenceGraph home">
          <span className="brand-mark">EG</span>
          <span>EvidenceGraph</span>
        </a>
        <div className="nav-links">
          <a href="#replay">Replay</a>
          <a href="#proof">Proof</a>
          <a href="#safety">Safety</a>
          <a className="nav-cta" href="/evidence/README.md">Inspect evidence</a>
        </div>
      </nav>

      <section className="hero shell" id="top">
        <div className="eyebrow"><span /> DATAHUB-NATIVE CHANGE ASSURANCE</div>
        <div className="hero-grid">
          <div>
            <h1>A schema change should not become an incident.</h1>
            <p className="lede">
              EvidenceGraph turns DataHub&apos;s context graph into a complete impact map,
              validated migration code, and an evidence-backed go/no-go decision.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#replay">Run evidence replay <b>↘</b></a>
              <a className="button ghost" href="/evidence/flagship/evidence-ledger.live.sanitized.json">
                Open the ledger
              </a>
            </div>
          </div>
          <div className="change-card" aria-label="Proposed breaking change">
            <div className="terminal-top"><span /><span /><span /><code>PROPOSAL EG-042</code></div>
            <div className="change-line"><span className="minus">−</span><code>customer_tier VARCHAR NOT NULL</code></div>
            <div className="change-line"><span className="plus">+</span><code>segment_code VARCHAR NOT NULL</code></div>
            <dl>
              <div><dt>Producer</dt><dd>commerce.raw_orders</dd></div>
              <div><dt>Revision</dt><dd>rev-842-customer-segmentation</dd></div>
              <div><dt>Contract</dt><dd><i className="dot amber" /> active · Tier 1</dd></div>
            </dl>
            <div className="scan-line" />
          </div>
        </div>

        <div className="metric-strip">
          <div><strong>3/7</strong><span>repo-only recall</span></div>
          <div className="metric-arrow">→</div>
          <div><strong className="aqua">7/7</strong><span>DataHub-grounded recall</span></div>
          <div><strong>+57.1</strong><span>percentage points</span></div>
          <div><strong>0</strong><span>false-safe decisions</span></div>
        </div>
      </section>

      <section className="graph-section" aria-label="Cross-domain context graph">
        <div className="shell">
          <div className="section-label">THE CONTEXT REPOSITORIES CANNOT SEE</div>
          <div className="graph-flow">
            <Node kind="PG" name="raw_orders" sub="PostgreSQL" active />
            <Connector label="field lineage" />
            <Node kind="dbt" name="stg_orders" sub="dbt" />
            <Connector label="transitive" />
            <div className="branch-stack">
              <Node kind="BI" name="Executive Revenue" sub="Looker · hidden" highlight />
              <Node kind="ML" name="tier_signal → model → API" sub="Production ML · hidden" highlight />
            </div>
          </div>
        </div>
      </section>

      <section className="workspace shell" id="replay">
        <div className="section-heading">
          <div>
            <div className="section-label">PUBLIC SYNTHETIC REPLAY</div>
            <h2>Make the context graph executable.</h2>
          </div>
          <button className={ran ? "run-button complete" : "run-button"} onClick={() => setRan(true)}>
            {ran ? "✓ Analysis complete" : "▶ Run EG-042"}
          </button>
        </div>

        <div className="workbench">
          <div className="tabs" role="tablist" aria-label="EvidenceGraph results">
            {(["impact", "bundle", "evidence", "writeback"] as View[]).map((item) => (
              <button key={item} role="tab" aria-selected={view === item} onClick={() => setView(item)}>
                {item === "impact" ? "01 Blast radius" : item === "bundle" ? "02 Migration pack" : item === "evidence" ? "03 Evidence ledger" : "04 Write-back"}
              </button>
            ))}
          </div>

          <div className="panel">
            {view === "impact" && <ImpactPanel impacts={visibleImpacts} ran={ran} />}
            {view === "bundle" && <BundlePanel />}
            {view === "evidence" && <EvidencePanel />}
            {view === "writeback" && <WritebackPanel />}
          </div>
        </div>
      </section>

      <section className="proof shell" id="proof">
        <div className="section-label">DETERMINISTIC RECEIPTS, NOT VIBES</div>
        <div className="proof-grid">
          <div>
            <h2>14 gates. Every one passed.</h2>
            <p>
              Generated code is parsed, executed, tested in its native runtime, hashed,
              and bound back to the DataHub observations that justify it.
            </p>
            <a className="text-link" href="/evidence/flagship/validation-receipts.json">Read all validation receipts →</a>
          </div>
          <div className="receipt-list">
            {validators.map(([name, tool, result]) => (
              <div className="receipt" key={name}>
                <span className="check">✓</span><strong>{name}</strong><span>{tool}</span><code>{result}</code>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="safety-section" id="safety">
        <div className="shell safety-grid">
          <div>
            <div className="section-label">FAIL CLOSED BY CONSTRUCTION</div>
            <h2>Uncertainty is a state,<br />not a footnote.</h2>
            <p>
              Switch off the final lineage page. EvidenceGraph keeps the evidence it has,
              marks completeness unestablished, generates no safe-to-merge verdict, and
              blocks every mutation.
            </p>
            <div className="toggle-row">
              <button onClick={() => setComplete(true)} aria-pressed={complete} className={complete ? "selected" : ""}>Complete graph</button>
              <button onClick={() => setComplete(false)} aria-pressed={!complete} className={!complete ? "selected danger" : ""}>Missing page</button>
            </div>
          </div>
          <div className={complete ? "decision-card safe" : "decision-card refused"}>
            <div className="decision-top"><span>SAFETY DECISION</span><code>{complete ? "all gates satisfied" : "lineage incomplete"}</code></div>
            <strong>{decision}</strong>
            <ul>
              <li><span>{complete ? "✓" : "!"}</span> Downstream frontier {complete ? "exhausted" : "not exhausted"}</li>
              <li><span>{complete ? "✓" : "!"}</span> Required validators {complete ? "14/14 passed" : "cannot establish closure"}</li>
              <li><span>{complete ? "✓" : "×"}</span> DataHub mutation {complete ? "proposal only" : "blocked"}</li>
            </ul>
            <a href={complete ? "/evidence/flagship/evidence-ledger.live.sanitized.json" : "/evidence/refusal/incomplete-lineage-ledger.json"}>
              Inspect machine-readable decision →
            </a>
          </div>
        </div>
      </section>

      <section className="close-loop shell">
        <div className="section-label">CLOSE THE LOOP</div>
        <h2>Context in. Verified change out.<br />Evidence back into DataHub.</h2>
        <div className="loop-steps">
          {[
            ["01", "Collect", "MCP + SDK observations"],
            ["02", "Compile", "9 migration artifacts"],
            ["03", "Validate", "14/14 native gates"],
            ["04", "Write back", "3/3 verified receipts"],
            ["05", "Close", "fresh graph, zero old-field consumers"],
          ].map(([n, title, sub]) => <div key={n}><code>{n}</code><strong>{title}</strong><span>{sub}</span></div>)}
        </div>
      </section>

      <footer className="footer shell">
        <div className="brand"><span className="brand-mark">EG</span><span>EvidenceGraph</span></div>
        <p>Built with open-source DataHub for Build with DataHub: The Agent Hackathon.</p>
        <div><a href="/evidence/README.md">Evidence</a><a href="/evidence/manifest.json">Checksums</a></div>
      </footer>
    </main>
  );
}

function Node({ kind, name, sub, active, highlight }: { kind: string; name: string; sub: string; active?: boolean; highlight?: boolean }) {
  return <div className={`graph-node ${active ? "active" : ""} ${highlight ? "highlight" : ""}`}><span>{kind}</span><div><strong>{name}</strong><small>{sub}</small></div></div>;
}

function Connector({ label }: { label: string }) {
  return <div className="connector"><span>{label}</span><i /></div>;
}

function ImpactPanel({ impacts: rows, ran }: { impacts: typeof impacts | readonly (typeof impacts)[number][]; ran: boolean }) {
  return <div><div className="panel-head"><div><span>DOWNSTREAM IMPACT</span><strong>{ran ? "7 evidenced consumers" : "Repository view · 3 consumers"}</strong></div><code>{ran ? "recall 100.0%" : "recall 42.9%"}</code></div><div className="impact-table">{rows.map(([type, name, risk, score, owner]) => <div className="impact-row" key={name}><span className={`risk ${risk}`}>{risk}</span><div><strong>{name}</strong><small>{type}</small></div><div><small>OWNER</small><code>{owner}</code></div><b>{score}</b></div>)}</div>{!ran && <button className="reveal" onClick={() => window.scrollTo({ top: document.getElementById("replay")?.offsetTop, behavior: "smooth" })}>Run the DataHub replay to recover 4 hidden consumers ↑</button>}</div>;
}

function BundlePanel() {
  const files = ["customer_tier_compatibility.sql", "stg_orders.sql + schema tests", "demo-platform.patch", "evidencegraph_change_gate.py", "customer_tier_feature_v2.yml", "validate_customer_tier.sql", "MIGRATION_PLAN.md", "evidencegraph-manifest.json", "evidence ledger binding"];
  return <div><div className="panel-head"><div><span>PR-READY OUTPUT</span><strong>9 evidence-bound artifacts</strong></div><code>sha256 verified</code></div><div className="file-grid">{files.map((file, i) => <div key={file}><span>{String(i + 1).padStart(2, "0")}</span><code>{file}</code><b>✓</b></div>)}</div><a className="panel-link" href="/evidence/flagship/migration/evidencegraph-manifest.json">Open generated manifest →</a></div>;
}

function EvidencePanel() {
  return <div><div className="panel-head"><div><span>CLAIM-LEVEL PROVENANCE</span><strong>8 claims · 18 observations</strong></div><code>frontier exhausted</code></div><div className="claim"><code>CLM-005</code><p><strong>Executive Revenue Watch</strong> is downstream of <strong>commerce.raw_orders</strong> through the documented dbt → Looker path.</p><dl><div><dt>STATUS</dt><dd>derived</dd></div><div><dt>CONFIDENCE</dt><dd>1.00</dd></div><div><dt>SOURCE</dt><dd>OBS-… DataHub MCP</dd></div><div><dt>PREDICATE</dt><dd>is_downstream_and_affected</dd></div></dl></div><a className="panel-link" href="/evidence/flagship/evidence-ledger.live.sanitized.json">Inspect every claim and observation →</a></div>;
}

function WritebackPanel() {
  return <div><div className="panel-head"><div><span>GOVERNED DATAHUB MUTATION</span><strong>3/3 applied and read back</strong></div><code>immediate retry · 3/3 no-op</code></div><div className="writeback-list">{[["add_tags", "7 scoped MCP-readable assets"], ["update_description", "producer assurance marker"], ["save_document", "durable evidence ledger"]].map(([tool, detail]) => <div key={tool}><span className="check">✓</span><code>{tool}</code><strong>{detail}</strong><em>applied_verified</em></div>)}</div><a className="panel-link" href="/evidence/flagship/writeback-retry-receipts.json">Inspect idempotent retry receipts →</a></div>;
}
