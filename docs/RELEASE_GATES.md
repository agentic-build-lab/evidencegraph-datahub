# Release gates

The immutable release commit is the unit of verification. A release is eligible
for publication only when the `evidencegraph-ci` workflow on that exact commit
passes every job.

## Automated gates

- Gitleaks 8.30.1 scans the complete reachable Git history with redaction.
- A clean `git archive` of the candidate commit is extracted and scanned again
  as a directory.
- Python 3.11 and 3.12 both install from `uv.lock` with `--locked`, then pass
  Ruff, strict mypy, and the full pytest suite.
- The public replay passes `npm audit --audit-level=high`, ESLint, and its test
  suite from a clean `npm ci` install.

The Gitleaks allowlist has two narrow cases: named negative-security test files
that contain deliberately synthetic credential strings, and the
`generic-api-key` rule only for an exact 64-character SHA-256
`idempotency_key` field in named sanitized write-back ledgers. The latter
requires the rule, field format, and evidence-ledger path to match together; it
does not suppress other content in examples, documentation, site assets, video
sources, or Git history.

## Publication gates

Before rendering, the release operator must verify the DOVA-SYNDROME source
hash, rebuild the ignored 130-second music edit with
`.hyperframes/prepare-bgm.ps1`, rebuild phrase captions from the committed word
timings, and pass `npm run check` from a clean `npm ci` installation. The final
Studio preview still requires explicit approval before a high-quality render.

After rendering, the release operator must:

1. verify MP4 duration, resolution, codecs, streams, and metadata with
   `ffprobe`;
2. calculate SHA-256 for every uploaded asset;
3. upload only `EvidenceGraph-v0.2.0-demo.mp4` and `SHA256SUMS.txt`;
4. reject any release asset whose name or archive contents include `.mp3`,
   `.wav`, `A_Little_Story`, or `.media/audio`;
5. download every public asset and verify its checksum; and
6. verify the repository, demo, video, release, and Devpost page without an
   authenticated session.

The standalone DOVA-SYNDROME music source and edit are never release assets.
