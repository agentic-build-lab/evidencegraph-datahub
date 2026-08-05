# Third-party notices

EvidenceGraph depends on open-source packages listed in `pyproject.toml` and the
generated lockfile. Their copyright and license terms remain with their
respective authors.

The project integrates with these Apache-2.0-licensed DataHub components
without copying their source code:

- DataHub Core: <https://github.com/datahub-project/datahub>
- DataHub MCP Server: <https://github.com/acryldata/mcp-server-datahub>
- DataHub Python SDK: <https://github.com/datahub-project/datahub>

“DataHub” and associated marks belong to their respective owner. References are
descriptive and do not imply sponsorship or endorsement.

The public site and demo video embed the Geist and Geist Mono fonts from
<https://github.com/vercel/geist-font>. They are distributed under the SIL Open
Font License 1.1; the complete license text is retained at both
`site/public/fonts/OFL-Geist.txt` and
`videos/evidencegraph-launch/assets/fonts/OFL-Geist.txt`.

The demo video uses GSAP 3.14.2 under GreenSock's standard no-charge license
for this non-fee-access project; the build dependency is pinned in the video
package lock.

Voice narration was generated locally at speed `1.02` through HyperFrames TTS
and the MIT-licensed [`kokoro-onnx`](https://github.com/thewh1teagle/kokoro-onnx)
runtime. The runtime loaded `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the
[`model-files-v1.0`](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0)
release. The model and source voice assets originate from
[`hexgrad/Kokoro-82M`](https://huggingface.co/hexgrad/Kokoro-82M) and are
licensed under Apache License 2.0. The selected voice is
[`af_heart`](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/voices/af_heart.pt),
whose upstream source-file SHA-256 is
`0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff`.
The model and voice-pack binaries are not distributed by this repository. The
generated WAV narration is project-authored demo output; no voice cloning or
personal data was used. Exact local binary and output hashes, edit lineage, and
durations are recorded in
[`videos/evidencegraph-launch/.media/manifest.jsonl`](videos/evidencegraph-launch/.media/manifest.jsonl).

The demo film uses **“A Little Story” by Kei Morimoto** as secondary
background music under the DOVA-SYNDROME Audio Source Usage License. The
composer retains all rights; the track is not included in the Apache-2.0 grant.
The source and edited audio are excluded from Git and release assets. Do not
extract, redistribute, register with Content ID, or use the track as standalone
content. See
[`videos/evidencegraph-launch/MUSIC_CREDITS.md`](videos/evidencegraph-launch/MUSIC_CREDITS.md).
