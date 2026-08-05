# EvidenceGraph Launch Film

This HyperFrames project produces the 130-second EvidenceGraph product demonstration for the Build with DataHub hackathon.

## Narrative proof

The film demonstrates one causal chain:

1. Repository evidence recovers only 3 of 7 known downstream consumers.
2. DataHub schema, lineage, ownership, contract, dashboard, and ML metadata recover the complete 7-of-7 blast radius.
3. EvidenceGraph compiles nine pull-request-ready migration artifacts.
4. Fourteen deterministic gates are reported by their actual composition: one integrity gate, eight parse gates, and five native/integration gates.
5. Complete evidence permits a proposal; missing lineage quarantines all drafts and blocks mutation.
6. A separately approved DataHub writeback verifies by readback, a stateless retry produces no duplicates, and a labeled deterministic replay proves closure against a newer complete graph.

The film includes a recorded interaction with the public Assurance Studio. It shows the real 3-of-7 to 7-of-7 replay, migration-pack inspection, claim-level ledger, incomplete-lineage refusal, and verified writeback state. Motion-graphics sequences are used to explain evidence and authority that would be difficult to read at normal browser scale.

## Captions

Captions are phrase-level: one complete sentence or clause appears at a time, with no word-by-word highlighting. Rebuild them with:

```powershell
node .hyperframes/build-phrase-captions.mjs .
```

The committed `caption_words.json` file is the canonical word-timing source, so
this command works from a clean clone.

## Music

The film uses “A Little Story” by Kei Morimoto from DOVA-SYNDROME. The license allows background-music use and editing, but the standalone audio file is intentionally excluded from this public repository.

Download **Track 1** from the [official track page](https://dova-s.jp/bgm/detail/19278/track/1)
and place it at `assets/A_Little_Story_Kei_Morimoto.mp3`. Then create the
130-second local edit with a 0.8-second opening fade and a 1.2-second closing
fade beginning at 128.8 seconds:

```powershell
powershell -ExecutionPolicy Bypass -File .hyperframes/prepare-bgm.ps1
```

The script requires `ffmpeg` on `PATH` and writes the ignored render input to
`.media/audio/bgm/bgm_001.edit.mp3`. The expected source SHA-256 for the track
used in the release is
`dff5eeb1f30499692e43022aebb02fe091805571f05b4820fc02e19032c3873e`.
The 130-second render edit is encoded at 256 kbps and has SHA-256
`a3ab90400ae39b79730997de0b2e1edca2ca38f9a96a3076cfb9975e25279ff0`;
its complete transformation record is stored in `.media/manifest.jsonl`.
See [MUSIC_CREDITS.md](./MUSIC_CREDITS.md). Do not redistribute the source
audio or register it with Content ID.

## Validate and preview

```powershell
npm ci
npm run check
npm run dev
```

The final MP4 is rendered only after the interactive Studio preview passes visual review.
