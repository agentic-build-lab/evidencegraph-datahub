import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("https://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the production EvidenceGraph experience", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  assert.match(response.headers.get("content-security-policy") ?? "", /frame-ancestors 'none'/);
  assert.equal(response.headers.get("strict-transport-security"), "max-age=63072000; includeSubDomains; preload");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(response.headers.get("x-frame-options"), "DENY");
  assert.equal(response.headers.get("referrer-policy"), "strict-origin-when-cross-origin");

  const html = await response.text();
  assert.match(html, /<title>EvidenceGraph Assurance Studio[^<]*DataHub-native change assurance<\/title>/i);
  assert.match(html, /PUBLIC EVIDENCE REPLAY · LABELED SOURCES/i);
  assert.match(html, /FIELD-AWARE DOWNSTREAM LINEAGE/i);
  assert.match(html, /Repository analysis sees only three consumers/i);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/i);
  assert.doesNotMatch(html, /(?:^|[\s"'(>])[A-Za-z]:[\\/]|file:\/\/\//i);
});

test("uses repository-owned fonts and ships inspectable public evidence", async () => {
  const [layout, page, css, manifest, ledger, context, validations, writebacks, retries, refusal, closure, sansFont, monoFont] = await Promise.all([
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/manifest.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/evidence-ledger.live.sanitized.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/context-snapshot.live.sanitized.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/validation-receipts.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/writeback-receipts.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/writeback-retry-receipts.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/refusal/incomplete-lineage-ledger.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/closure/closure-receipt.json", import.meta.url), "utf8"),
    readFile(new URL("../public/fonts/Geist-Variable.woff2", import.meta.url)),
    readFile(new URL("../public/fonts/GeistMono-Regular.woff2", import.meta.url)),
  ]);

  assert.doesNotMatch(layout, /next\/font/);
  assert.match(css, /url\("\/fonts\/Geist-Variable\.woff2"\)/);
  assert.match(css, /url\("\/fonts\/GeistMono-Regular\.woff2"\)/);
  assert.match(page, /DataHub MCP/);
  assert.match(page, /DataHub SDK/);
  assert.doesNotMatch(page, /Agent Context Kit/);
  assert.match(page, /Missing lineage/);
  assert.match(page, /WRITEBACK BLOCKED — INCOMPLETE LINEAGE/);
  assert.match(page, /SEPARATE APPROVED RUN/);
  assert.match(page, /RECORDED LIVE MCP TRACE/);
  assert.match(page, /RECORDED LIVE SDK TRACE/);
  assert.match(page, /RECORDED APPROVED WRITE-BACK/);
  assert.match(page, /DETERMINISTIC CLOSURE REPLAY/);
  assert.match(page, /REPLAY ASSURANCE/);
  assert.match(page, /claimId: "CLM-006"/);
  assert.match(page, /ownerFor\(/);
  assert.match(page, /maximumMismatchRate: 0\.0/);
  assert.ok(sansFont.byteLength > 60_000);
  assert.ok(monoFont.byteLength > 40_000);

  assert.equal(JSON.parse(manifest).flagship_run_id, "EG-6385813884D5");
  const parsedLedger = JSON.parse(ledger);
  const parsedContext = JSON.parse(context);
  const parsedRefusal = JSON.parse(refusal);
  assert.equal(parsedLedger.impacts.length, 7);
  assert.equal(parsedLedger.artifacts.length, 9);
  assert.equal(parsedContext.assets.find((asset) => asset.name === "churn-api-prod").owners[0], "urn:li:corpGroup:ml-platform");
  assert.equal(JSON.parse(validations).length, 14);
  assert.equal(JSON.parse(writebacks).length, 3);
  assert.equal(JSON.parse(retries).length, 3);
  assert.equal(parsedRefusal.writeback_proposals.length, 0);
  assert.equal(parsedRefusal.safety_decision.may_generate, true);
  assert.equal(parsedRefusal.safety_decision.may_propose_writeback, false);
  assert.equal(JSON.parse(closure).status, "closed");
});
