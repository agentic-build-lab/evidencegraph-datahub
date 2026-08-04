"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import contextSnapshot from "../public/evidence/flagship/context-snapshot.live.sanitized.json";
import flagshipLedger from "../public/evidence/flagship/evidence-ledger.live.sanitized.json";
import validationReceipts from "../public/evidence/flagship/validation-receipts.json";
import writebackReceipts from "../public/evidence/flagship/writeback-receipts.json";
import writebackRetryReceipts from "../public/evidence/flagship/writeback-retry-receipts.json";
import closureReceipt from "../public/evidence/closure/closure-receipt.json";
import refusalLedger from "../public/evidence/refusal/incomplete-lineage-ledger.json";

type Workspace = "graph" | "migration" | "evidence" | "writeback";
type GraphMode = "complete" | "incomplete";

type AssetNode = {
  id: string;
  assetUrn: string;
  claimId?: string;
  short: string;
  name: string;
  kind: string;
  owner: string;
  field: string;
  risk: "source" | "blocker" | "critical" | "high";
  score: number;
  claim: string;
  evidence: string[];
  x: number;
  y: number;
  repository?: boolean;
  revealAt: number;
};

const runStages = [
  { label: "Observe", title: "Read schema and contract", tool: "DataHub MCP", receipt: "schema + active Tier 1 contract", evidenceMode: "LIVE MCP READ" },
  { label: "Resolve", title: "Join ownership, docs, and ML context", tool: "DataHub SDK", receipt: "owners + RFC-42 + modeled gaps", evidenceMode: "LIVE DATAHUB READ" },
  { label: "Traverse", title: "Exhaust paginated lineage", tool: "DataHub MCP", receipt: "7 consumers · frontier exhausted", evidenceMode: "LIVE MCP READ" },
  { label: "Compile", title: "Generate migration bundle", tool: "EvidenceGraph", receipt: `${flagshipLedger.artifacts.length} artifacts · 7 impact claim bindings`, evidenceMode: "FROZEN RUN OUTPUT" },
  { label: "Validate", title: "Run deterministic and native gates", tool: "DuckDB · dbt · Airflow", receipt: `${validationReceipts.filter((item) => item.status === "passed").length} / ${validationReceipts.length} passed`, evidenceMode: "RECORDED RECEIPTS" },
  { label: "Write back", title: "Apply governed graph updates", tool: "DataHub MCP", receipt: `${writebackReceipts.filter((item) => item.status === "applied_verified").length} / ${writebackReceipts.length} applied and read back`, evidenceMode: "SEPARATE APPROVED RUN" },
  { label: "Close", title: "Verify a fresh context graph", tool: "EvidenceGraph", receipt: `${closureReceipt.remaining_impact_urns.length} old-field consumers`, evidenceMode: "DETERMINISTIC REPLAY" },
] as const;

const completeClaims = new Map(flagshipLedger.claims.map((claim) => [claim.claim_id, claim]));
const incompleteClaims = new Map(refusalLedger.claims.map((claim) => [claim.claim_id, claim]));

function ownerFor(assetUrn: string) {
  const ownerUrn = contextSnapshot.assets.find((asset) => asset.urn === assetUrn)?.owners[0];
  return ownerUrn?.split(":").at(-1) ?? "unassigned";
}

function claimFor(claimId: string, graphMode: GraphMode) {
  return (graphMode === "complete" ? completeClaims : incompleteClaims).get(claimId);
}

const nodes: AssetNode[] = [
  {
    id: "source",
    assetUrn: "urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)",
    short: "PG",
    name: "commerce.raw_orders",
    kind: "PostgreSQL dataset",
    owner: ownerFor("urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)"),
    field: "customer_tier",
    risk: "source",
    score: 0,
    claim: "The proposed drop targets a required field on the producer contract.",
    evidence: ["SchemaMetadata", "DataContract", "RFC-42"],
    x: 4,
    y: 43,
    repository: true,
    revealAt: 0,
  },
  {
    id: "stg",
    assetUrn: "urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.stg_orders,PROD)",
    claimId: "CLM-006",
    short: "dbt",
    name: "analytics.stg_orders",
    kind: "dbt model",
    owner: ownerFor("urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.stg_orders,PROD)"),
    field: "customer_tier",
    risk: "critical",
    score: 75,
    claim: completeClaims.get("CLM-006")?.statement ?? "The staging model is downstream of the producer field.",
    evidence: completeClaims.get("CLM-006")?.source_observation_ids ?? [],
    x: 25,
    y: 43,
    repository: true,
    revealAt: 1,
  },
  {
    id: "fct",
    assetUrn: "urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.fct_customer_value,PROD)",
    claimId: "CLM-002",
    short: "dbt",
    name: "analytics.fct_customer_value",
    kind: "dbt model",
    owner: ownerFor("urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.fct_customer_value,PROD)"),
    field: "customer_tier",
    risk: "blocker",
    score: 90,
    claim: completeClaims.get("CLM-002")?.statement ?? "The customer-value model is transitively downstream.",
    evidence: completeClaims.get("CLM-002")?.source_observation_ids ?? [],
    x: 47,
    y: 14,
    repository: true,
    revealAt: 1,
  },
  {
    id: "airflow",
    assetUrn: "urn:li:dataJob:(urn:li:dataFlow:(airflow,daily_customer_value,prod),build_customer_value)",
    claimId: "CLM-007",
    short: "AF",
    name: "build_customer_value",
    kind: "Airflow data job",
    owner: ownerFor("urn:li:dataJob:(urn:li:dataFlow:(airflow,daily_customer_value,prod),build_customer_value)"),
    field: "table dependency",
    risk: "high",
    score: 60,
    claim: completeClaims.get("CLM-007")?.statement ?? "The production data job is downstream.",
    evidence: completeClaims.get("CLM-007")?.source_observation_ids ?? [],
    x: 47,
    y: 43,
    repository: true,
    revealAt: 1,
  },
  {
    id: "feature",
    assetUrn: "urn:li:mlFeature:(customer_profile,customer_tier_signal)",
    claimId: "CLM-001",
    short: "ML",
    name: "customer_tier_signal",
    kind: "ML feature",
    owner: ownerFor("urn:li:mlFeature:(customer_profile,customer_tier_signal)"),
    field: "customer_tier_signal",
    risk: "blocker",
    score: 100,
    claim: completeClaims.get("CLM-001")?.statement ?? "The production feature is downstream.",
    evidence: completeClaims.get("CLM-001")?.source_observation_ids ?? [],
    x: 47,
    y: 72,
    revealAt: 2,
  },
  {
    id: "dashboard",
    assetUrn: "urn:li:dashboard:(looker,executive_revenue_watch)",
    claimId: "CLM-005",
    short: "BI",
    name: "Executive Revenue Watch",
    kind: "Looker dashboard",
    owner: ownerFor("urn:li:dashboard:(looker,executive_revenue_watch)"),
    field: "table dependency",
    risk: "critical",
    score: 80,
    claim: completeClaims.get("CLM-005")?.statement ?? "The executive dashboard is downstream.",
    evidence: completeClaims.get("CLM-005")?.source_observation_ids ?? [],
    x: 72,
    y: 14,
    revealAt: 2,
  },
  {
    id: "model",
    assetUrn: "urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)",
    claimId: "CLM-004",
    short: "ML",
    name: "churn_propensity_v4",
    kind: "ML model",
    owner: ownerFor("urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)"),
    field: "customer_tier_signal",
    risk: "critical",
    score: 85,
    claim: completeClaims.get("CLM-004")?.statement ?? "The model is downstream of the impacted feature.",
    evidence: completeClaims.get("CLM-004")?.source_observation_ids ?? [],
    x: 72,
    y: 58,
    revealAt: 2,
  },
  {
    id: "api",
    assetUrn: "urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,churn_api_prod,PROD)",
    claimId: "CLM-003",
    short: "API",
    name: "churn-api-prod",
    kind: "ML deployment",
    owner: ownerFor("urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,churn_api_prod,PROD)"),
    field: "customer_tier_signal",
    risk: "blocker",
    score: 90,
    claim: completeClaims.get("CLM-003")?.statement ?? "The production deployment is downstream.",
    evidence: completeClaims.get("CLM-003")?.source_observation_ids ?? [],
    x: 76,
    y: 76,
    revealAt: 2,
  },
];

const edges = [
  { from: "source", to: "stg", left: 15, top: 49, width: 12, rotate: 0, revealAt: 1 },
  { from: "stg", to: "fct", left: 36, top: 48, width: 15, rotate: -30, revealAt: 1 },
  { from: "stg", to: "airflow", left: 36, top: 49, width: 12, rotate: 0, revealAt: 1 },
  { from: "stg", to: "feature", left: 36, top: 51, width: 15, rotate: 30, revealAt: 2 },
  { from: "fct", to: "dashboard", left: 58, top: 21, width: 15, rotate: 0, revealAt: 2 },
  { from: "feature", to: "model", left: 58, top: 77, width: 16, rotate: -18, revealAt: 2 },
  { from: "model", to: "api", left: 82, top: 67, width: 9, rotate: 31, revealAt: 2 },
] as const;

const artifacts = [
  { id: "sql", name: "customer_tier_compatibility.sql", type: "SQL", gate: "DuckDB parity", path: "migration/sql/customer_tier_compatibility.sql", href: "/evidence/flagship/migration/sql/customer_tier_compatibility.sql" },
  { id: "dbt", name: "stg_orders.sql", type: "dbt", gate: "dbt build", path: "migration/dbt/models/staging/stg_orders.sql", href: "/evidence/flagship/migration/dbt/models/staging/stg_orders.sql" },
  { id: "airflow", name: "evidencegraph_change_gate.py", type: "Airflow", gate: "DAG import", path: "migration/orchestration/evidencegraph_change_gate.py", href: "/evidence/flagship/migration/orchestration/evidencegraph_change_gate.py" },
  { id: "ml", name: "customer_tier_feature_v2.yml", type: "ML contract", gate: "0.0% mismatch", path: "migration/ml/customer_tier_feature_v2.yml", href: "/evidence/flagship/migration/ml/customer_tier_feature_v2.yml" },
] as const;

const codeByArtifact: Record<string, string> = {
  sql: `-- EvidenceGraph change EG-042 · Source: DataHub RFC-42
CREATE OR REPLACE VIEW stg_orders_compat AS
SELECT
  order_id,
  customer_id,
  amount_usd,
  CASE segment_code
    WHEN 'B' THEN 'bronze'
    WHEN 'G' THEN 'gold'
    WHEN 'S' THEN 'silver'
    ELSE NULL
  END AS customer_tier,
  ordered_at
FROM raw_orders_next;`,
  dbt: `{{ config(materialized='view', contract={'enforced': true}) }}

SELECT
  order_id,
  customer_id,
  amount_usd,
  CASE segment_code
    WHEN 'B' THEN 'bronze'
    WHEN 'G' THEN 'gold'
    WHEN 'S' THEN 'silver'
  END AS customer_tier,
  ordered_at
FROM {{ source('commerce', 'raw_orders_next') }}`,
  airflow: `def require_validated_evidence() -> str:
    ledger = json.loads(ledger_path.read_text())
    validation_ids = [item["validation_id"] for item in ledger["validations"]]
    if set(validation_ids) != EXPECTED_VALIDATION_IDS:
        raise RuntimeError("EvidenceGraph rejected the bundle")
    return ledger["run_id"]

validate_change >> publish_customer_value`,
  ml: `apiVersion: evidencegraph.io/v1
kind: MLFeatureMigration
metadata:
  name: customer-tier-signal-v2
  changeId: EG-042
spec:
  sourceField: segment_code
  outputFeature: customer_tier_signal_v2
  unknownValuePolicy: reject
  parity:
    required: true
    minimumRows: 4
    maximumMismatchRate: 0.0`,
};

const claims = nodes
  .filter((node) => node.claimId)
  .sort((left, right) => (left.claimId ?? "").localeCompare(right.claimId ?? ""));

const writebacks = writebackReceipts.map((receipt) => ({
  tool: receipt.tool,
  target: receipt.tool === "save_document" ? "RFC-42 evidence ledger" : "commerce.raw_orders",
  result: receipt.status,
  hash: `${receipt.response_sha256.slice(0, 8)}…${receipt.response_sha256.slice(-6)}`,
}));

export default function Home() {
  const [workspace, setWorkspace] = useState<Workspace>("graph");
  const [graphMode, setGraphMode] = useState<GraphMode>("complete");
  const [runStep, setRunStep] = useState(-1);
  const [selectedNodeId, setSelectedNodeId] = useState("source");
  const [selectedArtifact, setSelectedArtifact] = useState("sql");
  const [traceExpanded, setTraceExpanded] = useState(true);

  const running = runStep >= 0 && runStep < runStages.length;
  const completed = runStep >= runStages.length;
  const blocked = completed && graphMode === "incomplete";
  const discoveryStep = completed ? runStages.length : runStep;
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? nodes[0];
  const visibleNodes = useMemo(
    () => nodes.filter((node) => node.repository || discoveryStep >= node.revealAt),
    [discoveryStep],
  );
  const progress = runStep < 0 ? 0 : Math.min(100, ((runStep + 1) / (runStages.length + 1)) * 100);

  useEffect(() => {
    if (!running) return;
    const timer = window.setTimeout(() => setRunStep((step) => step + 1), 760);
    return () => window.clearTimeout(timer);
  }, [runStep, running]);

  const decision = !completed
    ? running
      ? "ANALYZING EVIDENCE"
      : "EVIDENCE REQUIRED"
    : graphMode === "complete"
      ? "SAFE TO PROPOSE"
      : "WRITEBACK BLOCKED — INCOMPLETE LINEAGE";

  function runAssurance() {
    setWorkspace("graph");
    setSelectedNodeId("source");
    setRunStep(0);
  }

  function changeWorkspace(next: Workspace) {
    if (!completed && next !== "graph") return;
    setWorkspace(next);
  }

  return (
    <main className="app-shell">
      <aside className="rail" aria-label="Product navigation">
        <a className="rail-brand" href="#top" aria-label="EvidenceGraph home">EG</a>
        <nav>
          <RailButton label="Assurance" token="A" active />
          <RailButton label="Runs" token="R" />
          <RailButton label="Policies" token="P" />
          <RailButton label="DataHub" token="D" />
        </nav>
        <div className="rail-foot"><span className="live-dot" />OSS</div>
      </aside>

      <section className="product" id="top">
        <header className="topbar">
          <div className="product-title">
            <strong>EvidenceGraph</strong>
            <span>Assurance Studio</span>
          </div>
          <div className="run-identity">
            <span>PUBLIC EVIDENCE REPLAY · LABELED SOURCES</span>
            <code>EG-6385813884D5</code>
          </div>
          <div className="top-actions">
            <a href="/evidence/README.md">Evidence package</a>
            <a className="github-link" href="https://github.com/agentic-build-lab/evidencegraph-datahub">GitHub ↗</a>
          </div>
        </header>

        <div className="run-strip">
          <div className="change-summary">
            <div className="change-icon">Δ</div>
            <div>
              <span>CHANGE EG-042</span>
              <strong>Drop <code>customer_tier</code> from <code>commerce.raw_orders</code></strong>
            </div>
          </div>
          <div className="phase-stepper" aria-label="Assurance progress">
            {runStages.slice(0, 5).map((stage, index) => (
              <div className={blocked && index === 2 ? "phase blocked" : blocked && index > 2 ? "phase quarantined" : index < runStep || completed ? "phase done" : index === runStep ? "phase current" : "phase"} key={stage.label}>
                <i>{blocked && index === 2 ? "!" : blocked && index > 2 ? "·" : index < runStep || completed ? "✓" : index + 1}</i><span>{stage.label}</span>
              </div>
            ))}
          </div>
          <button className={running ? "primary-action running" : "primary-action"} onClick={runAssurance} disabled={running}>
            <span>{running ? "RUNNING" : completed ? "RUN AGAIN" : "RUN ASSURANCE"}</span>
            <b>{running ? `${Math.round(progress)}%` : "→"}</b>
          </button>
        </div>

        <div className="workspace-tabs" role="tablist" aria-label="EvidenceGraph workspaces">
          <div className="workspace-tab-group">
            <WorkspaceTab id="graph" label="Impact graph" badge={completed ? blocked ? "7?" : "7" : "3"} active={workspace === "graph"} onSelect={changeWorkspace} />
            <WorkspaceTab id="migration" label="Migration pack" badge={blocked ? "9*" : "9"} active={workspace === "migration"} onSelect={changeWorkspace} disabled={!completed} />
            <WorkspaceTab id="evidence" label="Evidence ledger" badge="8" active={workspace === "evidence"} onSelect={changeWorkspace} disabled={!completed} />
            <WorkspaceTab id="writeback" label="Write-back" badge={blocked ? "0" : "3"} active={workspace === "writeback"} onSelect={changeWorkspace} disabled={!completed} />
          </div>
          <div className="mode-switch" aria-label="Lineage completeness simulation">
            <button className={graphMode === "complete" ? "active" : ""} onClick={() => setGraphMode("complete")}>Complete graph</button>
            <button className={graphMode === "incomplete" ? "active danger" : ""} onClick={() => setGraphMode("incomplete")}>Missing lineage</button>
          </div>
        </div>

        <div className="console-layout">
          <ChangeProposal completed={completed} graphMode={graphMode} decision={decision} />

          <section className="canvas" aria-live="polite">
            {workspace === "graph" && (
              <GraphWorkspace
                runStep={runStep}
                completed={completed}
                graphMode={graphMode}
                visibleNodes={visibleNodes}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
              />
            )}
            {workspace === "migration" && <MigrationWorkspace selected={selectedArtifact} onSelect={setSelectedArtifact} graphMode={graphMode} />}
            {workspace === "evidence" && <EvidenceWorkspace selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} graphMode={graphMode} />}
            {workspace === "writeback" && <WritebackWorkspace graphMode={graphMode} completed={completed} />}
          </section>

          <EvidenceInspector node={selectedNode} completed={completed} graphMode={graphMode} decision={decision} />
        </div>

        <AgentTrace runStep={runStep} completed={completed} graphMode={graphMode} expanded={traceExpanded} onToggle={() => setTraceExpanded((value) => !value)} />
      </section>
    </main>
  );
}

function RailButton({ label, token, active = false }: { label: string; token: string; active?: boolean }) {
  return <button className={active ? "rail-button active" : "rail-button"} aria-label={label}><span>{token}</span></button>;
}

function WorkspaceTab({ id, label, badge, active, disabled = false, onSelect }: { id: Workspace; label: string; badge: string; active: boolean; disabled?: boolean; onSelect: (id: Workspace) => void }) {
  return <button role="tab" aria-selected={active} className={active ? "workspace-tab active" : "workspace-tab"} onClick={() => onSelect(id)} disabled={disabled}><span>{label}</span><b>{badge}</b></button>;
}

function ChangeProposal({ completed, graphMode, decision }: { completed: boolean; graphMode: GraphMode; decision: string }) {
  const safe = completed && graphMode === "complete";
  return (
    <aside className="proposal-panel">
      <div className="panel-heading">
        <div><span>PROPOSED CHANGE</span><strong>EG-042</strong></div>
        <span className="tier-chip">TIER 1</span>
      </div>

      <div className="source-asset">
        <span className="source-token">PG</span>
        <div><strong>commerce.raw_orders</strong><small>PostgreSQL · PROD</small></div>
      </div>

      <div className="diff-card">
        <div className="diff-line removed"><span>−</span><code>customer_tier</code><small>VARCHAR · NOT NULL</small></div>
        <div className="diff-line added"><span>+</span><code>segment_code</code><small>VARCHAR · NOT NULL</small></div>
      </div>

      <dl className="proposal-meta">
        <div><dt>Revision</dt><dd>rev-842-customer-segmentation</dd></div>
        <div><dt>Requested by</dt><dd>producer-platform-bot</dd></div>
        <div><dt>Contract</dt><dd><i /> active · required field</dd></div>
      </dl>

      <div className="risk-summary">
        <div><span>{completed ? graphMode === "complete" ? "7" : "7?" : "3"}</span><small>{completed && graphMode === "incomplete" ? "observed · unproven" : "impacted"}</small></div>
        <div><span>{completed ? "3" : "2"}</span><small>blockers</small></div>
        <div><span>{completed ? "4" : "0"}</span><small>hidden by repo</small></div>
      </div>

      <div className={safe ? "decision-summary safe" : graphMode === "incomplete" && completed ? "decision-summary blocked" : "decision-summary pending"}>
        <small>ASSURANCE DECISION</small>
        <strong>{decision}</strong>
        <span>{safe ? "Human review required before merge" : graphMode === "incomplete" && completed ? "Drafts quarantined · 0 write-back proposals" : "Run the evidence traversal first"}</span>
      </div>
    </aside>
  );
}

function GraphWorkspace({ runStep, completed, graphMode, visibleNodes, selectedNodeId, onSelectNode }: { runStep: number; completed: boolean; graphMode: GraphMode; visibleNodes: AssetNode[]; selectedNodeId: string; onSelectNode: (id: string) => void }) {
  const datahubVisible = completed || runStep >= 2;
  return (
    <div className="graph-workspace">
      <div className="canvas-header">
        <div>
          <span>FIELD-AWARE DOWNSTREAM LINEAGE</span>
          <strong>{completed && graphMode === "incomplete" ? "Seven impacts observed; completeness is still unproven" : datahubVisible ? "DataHub recovered the complete operating context" : "Repository analysis sees only three consumers"}</strong>
        </div>
        <div className="graph-stats">
          <span><i className="legend blocker" />Blocker</span>
          <span><i className="legend critical" />Critical</span>
          <span><i className="legend verified" />Verified path</span>
        </div>
      </div>

      <div className={datahubVisible ? "graph-map revealed" : "graph-map"}>
        <div className="graph-grid" />
        {edges.map((edge) => {
          const visible = completed || runStep >= edge.revealAt;
          return <div className={visible ? "graph-edge visible" : "graph-edge"} key={`${edge.from}-${edge.to}`} style={{ left: `${edge.left}%`, top: `${edge.top}%`, width: `${edge.width}%`, transform: `rotate(${edge.rotate}deg)` }}><i /></div>;
        })}
        {visibleNodes.map((node) => (
          <button
            className={`asset-node ${node.risk} ${selectedNodeId === node.id ? "selected" : ""} ${!node.repository ? "datahub-only" : ""}`}
            key={node.id}
            style={{ "--x": `${node.x}%`, "--y": `${node.y}%` } as CSSProperties}
            onClick={() => onSelectNode(node.id)}
            aria-label={`Inspect ${node.name}`}
          >
            <span className="node-token">{node.short}</span>
            <span className="node-copy"><strong>{node.name}</strong><small>{node.kind}</small></span>
            {node.score > 0 && <b>{node.score}</b>}
          </button>
        ))}
        {datahubVisible && <div className="datahub-reveal-label">{completed && graphMode === "incomplete" ? "OBSERVED CONTEXT · AUTHORITY BLOCKED" : "DATAHUB-ONLY CONTEXT · 4 ASSETS"}</div>}
        {completed && graphMode === "incomplete" && (
          <div className="unknown-frontier">
            <span>?</span><div><strong>Lineage page unavailable</strong><small>Completeness cannot be established</small></div>
          </div>
        )}
        {!completed && runStep < 0 && <div className="run-prompt"><i />Run Assurance to traverse DataHub</div>}
        {runStep >= 0 && !completed && <div className="scan-frontier" style={{ left: `${Math.min(82, 20 + runStep * 11)}%` }} />}
      </div>

      <div className="canvas-footer">
        <div><span>REPOSITORY RECALL</span><strong>3 / 7</strong><small>42.9%</small></div>
        <div className="recall-lift"><span>DATAHUB IMPACT</span><strong>{datahubVisible ? completed && graphMode === "incomplete" ? "7 OBSERVED" : "7 / 7" : "—"}</strong><small>{datahubVisible ? completed && graphMode === "incomplete" ? "confidence capped · 0.65" : "+57.1 pp vs repo" : "waiting"}</small></div>
        <div><span>FRONTIER</span><strong>{completed && graphMode === "complete" ? "EXHAUSTED" : completed ? "UNKNOWN" : "PENDING"}</strong><small>{completed && graphMode === "complete" ? "all pages observed" : completed ? "fail closed" : "pagination not started"}</small></div>
      </div>
    </div>
  );
}

function MigrationWorkspace({ selected, onSelect, graphMode }: { selected: string; onSelect: (id: string) => void; graphMode: GraphMode }) {
  const artifact = artifacts.find((item) => item.id === selected) ?? artifacts[0];
  const quarantined = graphMode === "incomplete";
  return (
    <div className="migration-workspace">
      <div className="canvas-header">
        <div><span>{quarantined ? "QUARANTINED DRAFT · NOT AUTHORIZED" : "EVIDENCE-BOUND MIGRATION PACK"}</span><strong>{quarantined ? "Generation is useful; incomplete evidence keeps every action gated" : "Generated files are reviewable, testable, and PR-ready"}</strong></div>
        <a className="outline-action" href="/evidence/flagship/migration/evidencegraph-manifest.json">Open binding manifest ↗</a>
      </div>
      <div className="artifact-layout">
        <div className="artifact-list">
          <div className={quarantined ? "artifact-count quarantined" : "artifact-count"}><strong>{flagshipLedger.artifacts.length}</strong><span>{quarantined ? "draft artifacts" : "generated artifacts"}</span><b>{quarantined ? "NOT ACTIONABLE" : "SHA-256 VERIFIED"}</b></div>
          {artifacts.map((item) => (
            <button className={selected === item.id ? "artifact-row active" : "artifact-row"} key={item.id} onClick={() => onSelect(item.id)}>
              <span>{item.type}</span><div><strong>{item.name}</strong><small>{item.path}</small></div><b>✓</b>
            </button>
          ))}
          <div className="artifact-more">+ 5 supporting artifacts: schema tests, validation SQL, unified patch, migration plan, binding manifest</div>
        </div>
        <div className="code-review">
          <div className="code-toolbar"><div><span className="window-dot coral" /><span className="window-dot amber" /><span className="window-dot mint" /></div><code>{artifact.name}</code><a href={artifact.href}>REVIEW EXCERPT · OPEN FULL FILE ↗</a><span>{artifact.gate} · passed</span></div>
          <pre><code>{codeByArtifact[selected]}</code></pre>
          <div className="code-receipt"><span>BOUND CLAIMS</span><strong>CLM-001 — CLM-007</strong><span>NATIVE GATE</span><strong>{artifact.gate}</strong></div>
        </div>
      </div>
    </div>
  );
}

function EvidenceWorkspace({ selectedNodeId, onSelectNode, graphMode }: { selectedNodeId: string; onSelectNode: (id: string) => void; graphMode: GraphMode }) {
  const active = claims.find((claim) => claim.id === selectedNodeId) ?? claims[0];
  const activeClaim = claimFor(active.claimId ?? "", graphMode);
  const completenessClaim = graphMode === "complete" ? completeClaims.get("CLM-COMPLETE") : incompleteClaims.get("CLM-INCOMPLETE");
  return (
    <div className="evidence-workspace">
      <div className="canvas-header">
        <div><span>CLAIM-LEVEL PROVENANCE</span><strong>Every decision links back to observed DataHub objects</strong></div>
        <div className="evidence-totals"><b>8</b> claims <i /> <b>{graphMode === "complete" ? flagshipLedger.observations.length : refusalLedger.observations.length}</b> observations <i /> <b>{graphMode === "complete" ? "1.00" : "0.65"}</b> impact confidence</div>
      </div>
      <div className="ledger-layout">
        <div className="claim-list">
          {claims.map((claim) => {
            const boundClaim = claimFor(claim.claimId ?? "", graphMode);
            return (
            <button className={active.id === claim.id ? "claim-row active" : "claim-row"} onClick={() => onSelectNode(claim.id)} key={claim.id}>
              <code>{claim.claimId}</code><span>{claim.name}</span><b>{claim.risk}</b><i>{boundClaim?.confidence.toFixed(2) ?? "—"}</i>
            </button>
          );})}
          <button className={graphMode === "complete" ? "claim-row" : "claim-row incomplete"}><code>{completenessClaim?.claim_id}</code><span>{graphMode === "complete" ? "Downstream frontier exhausted" : "Blast-radius completeness unproven"}</span><b>{completenessClaim?.status}</b><i>{completenessClaim?.confidence.toFixed(2)}</i></button>
        </div>
        <article className="claim-detail">
          <div className="claim-kicker"><code>{active.claimId}</code><span>{activeClaim?.status.toUpperCase()} · CONFIDENCE {activeClaim?.confidence.toFixed(2)}</span></div>
          <h2>{active.name}</h2>
          <p>{activeClaim?.statement}</p>
          <div className="derivation">
            <span>DERIVATION</span>
            <strong>Deterministic field-aware breadth-first traversal over DataHub lineage.</strong>
          </div>
          <div className="observation-stack">
            {(activeClaim?.source_observation_ids ?? []).map((item, index) => <div key={item}><span>{index + 1}</span><div><code>{item}</code><small>{index === 0 ? "DataHub observation" : "Corroborating graph evidence"}</small></div><b>VERIFIED</b></div>)}
          </div>
          <a href={graphMode === "complete" ? "/evidence/flagship/evidence-ledger.live.sanitized.json" : "/evidence/refusal/incomplete-lineage-ledger.json"}>Inspect the complete machine-readable ledger ↗</a>
        </article>
      </div>
    </div>
  );
}

function WritebackWorkspace({ graphMode, completed }: { graphMode: GraphMode; completed: boolean }) {
  const blocked = graphMode === "incomplete" || !completed;
  const verifiedCount = writebackReceipts.filter((item) => item.status === "applied_verified").length;
  const retryCount = writebackRetryReceipts.filter((item) => item.status === "skipped_idempotent_verified").length;
  return (
    <div className="writeback-workspace">
      <div className="canvas-header">
        <div><span>{blocked ? "REFUSAL FIXTURE · INCOMPLETE LINEAGE" : "RECORDED LIVE WRITE-BACK · SEPARATE APPROVED RUN"}</span><strong>{blocked ? "Draft generation remains useful; proposal and mutation authority stay closed" : "Propose, apply, read back, and prove idempotency"}</strong></div>
        <span className={blocked ? "status-pill blocked" : "status-pill verified"}>{blocked ? `${refusalLedger.writeback_proposals.length} PROPOSALS` : `${verifiedCount} / ${writebackReceipts.length} VERIFIED`}</span>
      </div>
      <div className="writeback-flow">
        <div className="writeback-before">
          <span>BEFORE</span>
          <strong>Assurance annotations are absent</strong>
          <ul><li>Migration tag absent</li><li>Producer note absent</li><li>Evidence document absent</li></ul>
        </div>
        <div className="writeback-arrow"><span>PROPOSE</span><b>→</b><small>two-key write gate</small></div>
        <div className={blocked ? "writeback-after blocked" : "writeback-after"}>
          <span>{blocked ? "REFUSED" : "AFTER · READ BACK"}</span>
          <strong>{blocked ? "Completeness not established" : "Context graph carries the decision"}</strong>
          <ul>{blocked ? <><li>No mutation attempted</li><li>Human escalation required</li><li>Evidence retained</li></> : <><li>Assurance tag visible</li><li>Producer description updated</li><li>Evidence document queryable</li></>}</ul>
        </div>
      </div>
      <div className="writeback-receipts">
        {writebacks.map((item) => <div className={blocked ? "writeback-receipt disabled" : "writeback-receipt"} key={item.tool}><span>{blocked ? "×" : "✓"}</span><div><code>{item.tool}</code><strong>{item.target}</strong></div><small>{blocked ? "not executed" : item.result}</small><code>{blocked ? "blocked" : item.hash}</code></div>)}
      </div>
      <div className="retry-proof"><span>IMMEDIATE RETRY</span><strong>{blocked ? "Not permitted" : `${retryCount} / ${writebackRetryReceipts.length} deterministic no-op`}</strong><small>{blocked ? "Missing lineage keeps both write gates closed." : "The same change does not create duplicate tags, notes, or documents."}</small></div>
    </div>
  );
}

function EvidenceInspector({ node, completed, graphMode, decision }: { node: AssetNode; completed: boolean; graphMode: GraphMode; decision: string }) {
  const blocked = completed && graphMode === "incomplete";
  const boundClaim = node.claimId ? claimFor(node.claimId, graphMode) : undefined;
  const confidence = !completed ? null : node.id === "source" ? 1 : boundClaim?.confidence ?? 1;
  const sourceObjects = boundClaim?.source_observation_ids ?? node.evidence;
  return (
    <aside className="inspector">
      <div className="panel-heading"><div><span>EVIDENCE INSPECTOR</span><strong>{node.short} · {node.name}</strong></div><span className={`risk-chip ${node.risk}`}>{node.risk}</span></div>
      <div className="inspector-section">
        <span>FACTUAL CLAIM</span>
        <p>{boundClaim?.statement ?? node.claim}</p>
      </div>
      <div className="confidence-block">
        <div className="confidence-ring"><span>{confidence === null ? "—" : Math.round(confidence * 100)}<small>{confidence === null ? "" : "%"}</small></span></div>
        <div><span>CONFIDENCE</span><strong>{blocked && node.id !== "source" ? "Capped by incomplete frontier" : completed ? "Deterministically evidenced" : "Awaiting traversal"}</strong><small>{blocked && node.id !== "source" ? "Useful draft · not sufficient authority" : completed ? "No model judgment in risk propagation" : "Run Assurance to collect observations"}</small></div>
      </div>
      <dl className="asset-facts">
        <div><dt>Owner</dt><dd>{node.owner}</dd></div>
        <div><dt>Affected field</dt><dd><code>{node.field}</code></dd></div>
        <div><dt>Risk score</dt><dd>{node.score || "source"}</dd></div>
        <div><dt>Environment</dt><dd>PROD</dd></div>
      </dl>
      <div className="evidence-links">
        <span>SOURCE OBJECTS</span>
        {sourceObjects.map((item) => <a href={blocked ? "/evidence/refusal/incomplete-lineage-ledger.json" : "/evidence/flagship/evidence-ledger.live.sanitized.json"} key={item}><code>{item}</code><b>↗</b></a>)}
      </div>
      <div className="validation-mini">
        <span>DETERMINISTIC GATES</span>
        {["SQL parity", "dbt build", "Airflow import", "ML parity"].map((item) => <div key={item}><i>{completed ? "✓" : "·"}</i><span>{item}</span><b>{completed ? blocked ? "passed · non-authorizing" : "passed" : "pending"}</b></div>)}
      </div>
      <div className={blocked ? "inspector-decision blocked" : completed ? "inspector-decision safe" : "inspector-decision"}>
        <span>RUN DECISION</span><strong>{decision}</strong><small>{blocked ? "Drafts allowed · proposals and mutations refused" : completed ? "Proposal only · human review required" : "No unsupported action will run"}</small>
      </div>
    </aside>
  );
}

function AgentTrace({ runStep, completed, graphMode, expanded, onToggle }: { runStep: number; completed: boolean; graphMode: GraphMode; expanded: boolean; onToggle: () => void }) {
  const blocked = completed && graphMode === "incomplete";
  return (
    <section className={expanded ? "agent-trace" : "agent-trace collapsed"}>
      <button className="trace-heading" onClick={onToggle} aria-expanded={expanded}>
        <div><span className={runStep >= 0 ? "live-dot active" : "live-dot"} /><strong>Agent trace</strong><code>{blocked ? "refused · evidence preserved" : completed ? "complete · labeled multi-run proof" : runStep >= 0 ? `running · step ${runStep + 1}/${runStages.length}` : "ready"}</code></div>
        <span>{expanded ? "Collapse ↓" : "Expand ↑"}</span>
      </button>
      {expanded && <div className="trace-track">
        {runStages.map((stage, index) => {
          const done = completed || index < runStep;
          const active = index === runStep;
          const refused = blocked && (index === 2 || index >= 5);
          const quarantined = blocked && (index === 3 || index === 4);
          const blockedReceipt = index === 2
            ? "frontier incomplete · confidence capped"
            : index === 3
              ? `${refusalLedger.artifacts.length} drafts · quarantined`
              : index === 4
                ? `${refusalLedger.validations.filter((item) => item.status === "passed").length} passed · non-authorizing`
                : index === 5
                  ? `${refusalLedger.writeback_proposals.length} proposals · no mutation attempted`
                  : "not eligible for closure";
          const evidenceMode = blocked && index === 5 ? "REFUSAL FIXTURE" : blocked && index === 6 ? "NOT RUN" : stage.evidenceMode;
          return <div className={refused ? "trace-step blocked" : quarantined ? "trace-step quarantined" : done ? "trace-step done" : active ? "trace-step active" : "trace-step"} key={stage.label}>
            <div className="trace-number">{refused ? "×" : quarantined ? "!" : done ? "✓" : String(index + 1).padStart(2, "0")}</div>
            <div><span>{stage.label.toUpperCase()}</span><em>{evidenceMode}</em><strong>{stage.title}</strong><code>{stage.tool}</code><small>{blocked && index >= 2 ? blockedReceipt : done ? stage.receipt : active ? "executing…" : "queued"}</small></div>
          </div>;
        })}
      </div>}
    </section>
  );
}
