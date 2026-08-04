import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
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

  const html = await response.text();
  assert.match(html, /<title>EvidenceGraph[^<]*DataHub-native change assurance<\/title>/i);
  assert.match(html, /Repository view [^<]* 3 consumers/i);
  assert.match(html, /DataHub-grounded recall/i);
  assert.match(html, /7\/7/);
  assert.match(html, /14\/14 native gates/);
  assert.match(html, /3\/3 verified receipts/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/i);
  assert.doesNotMatch(html, /C:[\\/]+Users|datahub_agent_hackathon|New project 8/i);
});

test("uses repository-owned fonts and ships inspectable public evidence", async () => {
  const [layout, css, manifest, ledger, validations, writebacks, sansFont, monoFont] = await Promise.all([
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/manifest.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/evidence-ledger.live.sanitized.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/validation-receipts.json", import.meta.url), "utf8"),
    readFile(new URL("../public/evidence/flagship/writeback-receipts.json", import.meta.url), "utf8"),
    readFile(new URL("../public/fonts/Geist-Variable.woff2", import.meta.url)),
    readFile(new URL("../public/fonts/GeistMono-Regular.woff2", import.meta.url)),
  ]);

  assert.doesNotMatch(layout, /next\/font/);
  assert.match(css, /url\("\/fonts\/Geist-Variable\.woff2"\)/);
  assert.match(css, /url\("\/fonts\/GeistMono-Regular\.woff2"\)/);
  assert.ok(sansFont.byteLength > 60_000);
  assert.ok(monoFont.byteLength > 40_000);

  assert.equal(JSON.parse(manifest).flagship_run_id, "EG-6385813884D5");
  assert.equal(JSON.parse(ledger).impacts.length, 7);
  assert.equal(JSON.parse(validations).length, 14);
  assert.equal(JSON.parse(writebacks).length, 3);
});
