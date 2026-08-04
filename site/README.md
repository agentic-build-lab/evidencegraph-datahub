# EvidenceGraph public replay

This directory contains the read-only EvidenceGraph public demo. It presents
the measured flagship result and serves the frozen, synthetic evidence package
under `/evidence/` for judge inspection.

The deployment has no database binding, authentication surface, or write API.
All visible results are immutable build artifacts; DataHub write-back is
demonstrated by the readback-verified receipts in the evidence package and can
be reproduced against a disposable DataHub OSS instance from the repository.

## Local verification

Requires Node.js 22.13 or newer.

```bash
npm ci
npm run lint
npm test
npm audit
```

`npm test` performs a production build and verifies the rendered HTML and
evidence links. Deployment metadata in `.openai/hosting.json` identifies the
single existing Sites project; do not create a second project.
