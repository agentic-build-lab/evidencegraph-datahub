# Media inventory - 18 assets

| ID | Type | Duration | Dimensions | Path | Role |
| --- | --- | ---: | ---: | --- | --- |
| `image_001` | image | - | 1920x1080 | `assets/scroll-000.png` | Assurance Studio scroll reference (0%) |
| `image_002` | image | - | 1920x1080 | `assets/scroll-028.png` | Assurance Studio scroll reference (28%) |
| `image_003` | image | - | 1920x1080 | `assets/scroll-057.png` | Assurance Studio scroll reference (57%) |
| `image_004` | image | - | 1920x1080 | `assets/scroll-085.png` | Assurance Studio scroll reference (85%) |
| `image_005` | image | - | 1920x1080 | `assets/scroll-100.png` | Assurance Studio scroll reference (100%) |
| `product_capture_001` | video | 16.800s | 1920x1080 | `assets/evidencegraph-assurance-studio.mp4` | Silent EvidenceGraph Assurance Studio product capture |
| `voice_001` | voice | 14.000s | - | `assets/voice/01.wav` | Opening narration |
| `voice_002` | voice | 20.000s | - | `assets/voice/02.wav` | Repository blind-spot narration |
| `voice_003` | voice | 19.000s | - | `assets/voice/03.wav` | DataHub context-graph narration |
| `voice_004` | voice | 21.000s | - | `assets/voice/04.wav` | Blast-radius narration |
| `voice_005` | voice | 20.000s | - | `assets/voice/05.wav` | Artifact-generation narration |
| `voice_006_original` | voice | 22.000s | - | `assets/voice/06-original.wav` | Source narration retained for edit provenance |
| `voice_006` | voice | 20.081s | - | `assets/voice/06.wav` | Corrected deterministic-gates narration derived from `voice_006_original` |
| `voice_007` | voice | 22.000s | - | `assets/voice/07.wav` | Write-back and closure narration |
| `voice_008` | voice | 12.000s | - | `assets/voice/08.wav` | Source closing narration retained for edit provenance |
| `voice_008_trimmed` | voice | 8.220s | - | `assets/voice/08.trimmed.wav` | Public-replay close derived from `voice_008` |
| `bgm_001` | bgm | 174.720s | - | `.media/audio/bgm/bgm_001.mp3` | Licensed source: “A Little Story” by Kei Morimoto |
| `bgm_001_edit` | bgm | 130.000s | - | `.media/audio/bgm/bgm_001.edit.mp3` | Render edit derived from `bgm_001` |

Durations, dimensions, byte sizes, codecs, and SHA-256 digests in `manifest.jsonl` were measured from the local files with `ffprobe`, image inspection, and SHA-256 hashing.

## Narration provenance

Narration was generated locally at speed `1.02` through HyperFrames TTS and the MIT-licensed [`kokoro-onnx`](https://github.com/thewh1teagle/kokoro-onnx) runtime. The runtime used the release assets [`kokoro-v1.0.onnx`](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0) and `voices-v1.0.bin`; their local cache SHA-256 digests are `7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5` and `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`, respectively.

The model and source voice assets originate from the Apache-2.0-licensed [`hexgrad/Kokoro-82M`](https://huggingface.co/hexgrad/Kokoro-82M) repository. The selected voice is [`af_heart`](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/voices/af_heart.pt); its upstream source-file SHA-256 is `0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff`. The model and aggregate voice-pack binaries are not distributed by this repository.

## Music provenance

`bgm_001_edit` is rebuilt from `bgm_001` by `.hyperframes/prepare-bgm.ps1`: trim to 130 seconds, fade in for 0.8 seconds, fade out for 1.2 seconds beginning at 128.8 seconds, then encode as 256 kbps MP3. See `MUSIC_CREDITS.md` for the DOVA-SYNDROME source and license terms.
