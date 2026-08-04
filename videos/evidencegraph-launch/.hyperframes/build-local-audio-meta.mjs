import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const script = readFileSync("SCRIPT.md", "utf8");
const spoken = [...script.matchAll(/^ {4}(.+)$/gm)].map((match) => match[1].trim());

if (spoken.length !== 8) {
  throw new Error(`Expected 8 narration lines, found ${spoken.length}`);
}

const voices = spoken.map((line, index) => {
  const frame = index + 1;
  const id = String(frame).padStart(2, "0");
  const path = `assets/voice/${id}.wav`;
  const duration = Number(
    execFileSync("ffprobe", [
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=noprint_wrappers=1:nokey=1",
      path,
    ], { encoding: "utf8" }).trim(),
  );
  const speechDuration = Number(
    execFileSync("ffprobe", [
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "default=noprint_wrappers=1:nokey=1",
      `assets/voice/raw/${id}.wav`,
    ], { encoding: "utf8" }).trim(),
  );

  const tokens = line.split(/\s+/).filter(Boolean);
  const weights = tokens.map((token) => {
    const letters = token.replace(/[^A-Za-z0-9]/g, "").length;
    const punctuation = /[.!?]$/.test(token) ? 1.2 : /[,;:]$/.test(token) ? 0.5 : 0;
    return Math.max(1, letters * 0.42) + punctuation;
  });
  const totalWeight = weights.reduce((sum, value) => sum + value, 0);
  const usable = Math.max(0.1, speechDuration - 0.18);
  let cursor = 0.08;
  const words = tokens.map((text, wordIndex) => {
    const wordDuration = usable * (weights[wordIndex] / totalWeight);
    const start = Number(cursor.toFixed(3));
    cursor += wordDuration;
    const end = Number(Math.min(speechDuration - 0.02, cursor).toFixed(3));
    return { id: `w${wordIndex}`, text, start, end };
  });

  return { frame, path, duration_s: Number(duration.toFixed(3)), words };
});

writeFileSync(
  "audio_meta.json",
  `${JSON.stringify({ bgm: null, bgm_pending: false, voices, sfx: [] }, null, 2)}\n`,
);

console.log(`audio_meta.json: ${voices.length} voices, ${voices.reduce((n, v) => n + v.words.length, 0)} timed words`);
