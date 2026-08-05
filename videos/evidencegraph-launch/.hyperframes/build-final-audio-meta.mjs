import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const frameStarts = new Map([
  [1, 0],
  [2, 9.464],
  [3, 25.119],
  [4, 41.052],
  [5, 58.641],
  [6, 76.732],
  [7, 94.784],
  [8, 116.506],
]);
const phrases = JSON.parse(readFileSync("caption_groups.json", "utf8"));

const voices = [...frameStarts.entries()].map(([frame, base]) => {
  const id = String(frame).padStart(2, "0");
  const path = `assets/voice/${id}.wav`;
  const duration = Number(
    execFileSync(
      "ffprobe",
      [
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
      ],
      { encoding: "utf8" },
    ).trim(),
  );
  const words = phrases.groups
    .filter((group) => group.frame === frame)
    .flatMap((group) => group.words)
    .map((word, index) => ({
      id: `w${index}`,
      text: word.text,
      start: Number((word.start - base).toFixed(3)),
      end: Number((word.end - base).toFixed(3)),
    }));
  return { frame, path, duration_s: Number(duration.toFixed(3)), words };
});

const metadata = {
  bgm: {
    path: ".media/audio/bgm/bgm_001.edit.mp3",
    volume: 0.085,
    title: "A Little Story",
    composer: "Kei Morimoto",
    provider: "DOVA-SYNDROME",
    source_url: "https://dova-s.jp/bgm/detail/19278/track/1",
    license_url: "https://dova-s.jp/en/contents/license",
  },
  bgm_pending: false,
  voices,
  sfx: [],
};

writeFileSync("audio_meta.json", `${JSON.stringify(metadata, null, 2)}\n`);
console.log(`audio_meta.json: ${voices.length} voices, licensed BGM at volume ${metadata.bgm.volume}`);
