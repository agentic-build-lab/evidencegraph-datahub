# Security Model

EvidenceGraph is designed as a bounded change-assurance agent. It analyzes and
proposes metadata changes; it does not modify production tables, pipelines,
dashboards, models, deployments, or source repositories by itself.

## Trust boundaries

- **DataHub observations** are recorded with the interface operation, source
  URN, observation time, and normalized payload hash.
- **Deterministic derivations** compute reachability, risk, artifact selection,
  and safety decisions from normalized observations.
- **Generated artifacts** remain files for human review and native validation;
  they are not applied to production systems.
- **DataHub mutations** are a separate, allowlisted metadata-only boundary.
- **Optional model assistance**, if added later, may suggest wording or
  variants but must not create facts, raise confidence, or bypass a policy
  decision.

## Default-deny write policy

Live DataHub write-back requires three independent conditions:

1. the operator requests `--apply`;
2. the process receives `EVIDENCEGRAPH_ENABLE_WRITES=true`; and
3. the official MCP server exposes its mutation tools.

The current allowlist is limited to:

- adding an EvidenceGraph review tag;
- appending a clearly marked EvidenceGraph section to a description; and
- saving an EvidenceGraph analysis document.

EvidenceGraph refuses writes when lineage completeness is unestablished,
required ownership is missing, a factual claim lacks evidence, evidence
conflicts, or any required validator fails. Human-authored descriptions are
appended to rather than silently replaced in the demonstrated path.

## Secrets and logging

- `DATAHUB_GMS_TOKEN` is read from the environment and is not accepted as a CLI
  argument.
- Token fields are excluded from configuration representations.
- MCP server logs are discarded unless an explicit diagnostic stream is
  requested.
- Sanitized evidence records payload hashes and URNs, not authorization
  headers, cookies, or credentials.
- `.env`, logs, local databases, caches, build artifacts, and generated run
  directories are excluded from version control.

Never commit a real token or use a personal production tenant for the public
demo.

## Public demo boundary

The public judge experience must:

- use only synthetic, allowlisted scenarios;
- require no credentials, payment, or private membership;
- expose no public mutation endpoint;
- label fixture or replay data visibly;
- enforce bounded input size, execution time, and request rate; and
- reveal no local path, environment value, private URL, or server diagnostic.

The included judge surface is a read-only server-rendered replay. It has no
application API, form submission, uploaded content, arbitrary scenario input,
or mutation route, so there is no public agent execution to rate-limit or time
out. The worker adds a Content Security Policy, HSTS on HTTPS, clickjacking and
MIME-sniffing defenses, a restrictive permissions policy, same-origin resource
boundaries, and a strict referrer policy to every application response. These
headers are asserted in the rendered-site test.

## Dependency and release checks

The final release gate includes linting, type checking, the full automated test
suite, dependency audit, a Gitleaks 8.30.1 scan over complete Git history, a
second scan over the clean release-tree archive, and signed-out public-link
verification. The pinned CI commands and manual publication allowlist are
documented in [`RELEASE_GATES.md`](RELEASE_GATES.md).

The release dependency audit reports one accepted upstream exception:
`setuptools 81.0.0` is affected by `PYSEC-2026-3447` / `CVE-2026-59890`
(`GHSA-h35f-9h28-mq5c`), fixed in 83.0.0. The
official `acryl-datahub==1.6.0.6` package declares `setuptools<82`, so a
non-vulnerable resolver solution does not currently exist without breaking the
official DataHub dependency contract. EvidenceGraph does not invoke setuptools
at runtime, build or publish source distributions, accept package archives, or
expose a packaging endpoint. The advisory requires a local macOS APFS/HFS+
source-distribution build with a Unicode-normalization collision in an exclusion
rule; that path is outside EvidenceGraph's supported runtime. This is a documented
upstream exception, not a claim of a clean vulnerability scan, and it should be
removed when the official DataHub constraint is relaxed.

## Current non-claims

The verified local write-back demonstrates apply and per-target read-back for three allowlisted
metadata operations plus an immediate stateless 3/3 no-op retry. The deterministic replay proves
the fresh-observation closure protocol. These results do not prove transactional rollback or
suitability for unattended production mutation. See `docs/LIMITATIONS.md`.

## Reporting a vulnerability

Do not include credentials, private tenant metadata, or exploit details in a
public issue. Use the private security-reporting mechanism at
`https://github.com/agentic-build-lab/evidencegraph-datahub/security/advisories/new` after it is configured.
