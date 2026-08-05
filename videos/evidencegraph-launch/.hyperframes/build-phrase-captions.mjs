import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const project = resolve(process.argv[2] || ".");
const request = JSON.parse(
  readFileSync(resolve(project, "audio_request.json"), "utf8"),
);
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

let words = request.lines
  .flatMap((line, index) => {
    const frame = index + 1;
    const id = String(frame).padStart(2, "0");
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
          resolve(project, `assets/voice/${id}.wav`),
        ],
        { encoding: "utf8" },
      ).trim(),
    );
    const tokens = line.text.split(/\s+/).filter(Boolean);
    const weights = tokens.map((token) => {
      const letters = token.replace(/[^A-Za-z0-9]/g, "").length;
      const punctuation = /[.!?]$/.test(token) ? 1.2 : /[,;:]$/.test(token) ? 0.5 : 0;
      return Math.max(1, letters * 0.42) + punctuation;
    });
    const totalWeight = weights.reduce((sum, value) => sum + value, 0);
    const usable = Math.max(0.1, duration - 0.18);
    let cursor = (frameStarts.get(frame) ?? 0) + 0.08;
    return tokens.map((text, wordIndex) => {
      const wordDuration = usable * (weights[wordIndex] / totalWeight);
      const start = Number(cursor.toFixed(3));
      cursor += wordDuration;
      return {
        frame,
        text,
        start,
        end: Number(Math.min((frameStarts.get(frame) ?? 0) + duration - 0.02, cursor).toFixed(3)),
      };
    });
  })
  .sort((a, b) => a.start - b.start);

const terminal = /[.!?]$/;
const clause = /[,;:]$/;
const groups = [];
let current = [];

function flush() {
  if (!current.length) return;
  const index = groups.length;
  groups.push({
    id: `phrase-${index}`,
    frame: current[0].frame,
    start: current[0].start,
    end: Number((current.at(-1).end + 0.16).toFixed(3)),
    text: current.map((word) => word.text).join(" "),
    words: current.map((word, wordIndex) => ({
      id: `phrase-${index}-word-${wordIndex}`,
      text: word.text,
      start: word.start,
      end: word.end,
    })),
  });
  current = [];
}

for (const word of words) {
  const frameChanged = current.length && current[0].frame !== word.frame;
  const projectedDuration = current.length ? word.end - current[0].start : 0;
  if (frameChanged || current.length >= 12 || projectedDuration > 4.6) flush();
  current.push(word);
  const duration = current.at(-1).end - current[0].start;
  if (
    terminal.test(word.text) ||
    (clause.test(word.text) && (current.length >= 7 || duration >= 3.2))
  ) {
    flush();
  }
}
flush();

for (let index = groups.length - 1; index > 0; index -= 1) {
  const group = groups[index];
  const previous = groups[index - 1];
  const sameFrame = group.frame === previous.frame;
  const combinedWords = previous.words.length + group.words.length;
  const combinedDuration = group.end - previous.start;
  if (
    sameFrame &&
    group.words.length <= 2 &&
    combinedWords <= 14 &&
    combinedDuration <= 5.6
  ) {
    previous.words.push(...group.words);
    previous.text = `${previous.text} ${group.text}`;
    previous.end = group.end;
    groups.splice(index, 1);
  }
}

// Keep the closure sentence in two comfortable clauses instead of ending a
// caption on "newer" or leaving a two-word tail.
const closureStart = groups.findIndex(
  (group) => group.frame === 7 && group.text.startsWith("A labeled closure replay"),
);
if (closureStart >= 0) {
  let closureEnd = closureStart;
  while (closureEnd < groups.length && groups[closureEnd].frame === 7) closureEnd += 1;
  const closureWords = groups
    .slice(closureStart, closureEnd)
    .flatMap((group) => group.words);
  const splitAt = closureWords.findIndex(
    (word, index) => word.text === "with" && index > 0 && closureWords[index - 1].text === "graph",
  );
  if (splitAt > 0) {
    const makeClause = (clauseWords) => ({
      frame: 7,
      start: clauseWords[0].start,
      end: Number((clauseWords.at(-1).end + 0.16).toFixed(3)),
      text: clauseWords.map((word) => word.text).join(" "),
      words: clauseWords,
    });
    groups.splice(
      closureStart,
      closureEnd - closureStart,
      makeClause(closureWords.slice(0, splitAt)),
      makeClause(closureWords.slice(splitAt)),
    );
  }
}

// Merge tails that would otherwise flash as two-to-five-word fragments. The
// resulting phrases remain short enough for the two-line caption band.
const mergeIntoPrevious = new Set([
  "waiting to happen.",
  "the Python S D K.",
  "All fourteen pass.",
  "verdict and blocks every mutation.",
  "and verify by readback.",
]);
for (let index = groups.length - 1; index > 0; index -= 1) {
  const group = groups[index];
  const previous = groups[index - 1];
  if (group.frame === previous.frame && mergeIntoPrevious.has(group.text)) {
    previous.words.push(...group.words);
    previous.text = `${previous.text} ${group.text}`;
    previous.end = group.end;
    groups.splice(index, 1);
  }
}

function normalizeCaptionText(value) {
  return value
    .replaceAll("M C P", "MCP")
    .replaceAll("S D K", "SDK")
    .replaceAll("M L", "ML")
    .replaceAll("S Q L", "SQL")
    .replaceAll("Duck D B", "DuckDB")
    .replaceAll("forty-two point nine percent", "42.9 percent");
}

groups.forEach((group) => {
  group.text = normalizeCaptionText(group.text);
});

groups.forEach((group, groupIndex) => {
  group.id = `phrase-${groupIndex}`;
  group.words = group.words.map((word, wordIndex) => ({
    ...word,
    id: `phrase-${groupIndex}-word-${wordIndex}`,
  }));
});

for (let index = 0; index < groups.length - 1; index += 1) {
  groups[index].end = Math.min(groups[index].end, groups[index + 1].start - 0.035);
}

const payload = {
  total_duration_s: 130,
  width: 1920,
  height: 1080,
  style: "phrase-level",
  groups,
};

writeFileSync(
  resolve(project, "caption_groups.json"),
  `${JSON.stringify(payload, null, 2)}\n`,
);

const serialized = JSON.stringify(groups).replaceAll("</script", "<\\/script");
const html = `<template id="captions-template" data-composition-id="captions" data-width="1920" data-height="1080">
<style>
  @font-face { font-family: "Geist"; src: url("assets/fonts/Geist-Variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
  #captions-root { position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: hidden; pointer-events: none; }
  .caption-layer { position: absolute; inset: 0; }
  .caption-stage { position: absolute; left: 120px; right: 120px; bottom: 44px; height: 142px; display: grid; place-items: center; }
  .caption-group { position: absolute; inset: 0; display: grid; place-items: center; opacity: 0; }
  .caption-phrase { max-width: 1500px; padding: 18px 32px 19px; border: 1px solid rgba(64,224,192,.22); border-radius: 18px; background: linear-gradient(180deg, rgba(12,27,34,.78), rgba(12,27,34,.94)); box-shadow: 0 18px 70px rgba(0,0,0,.34), inset 0 1px 0 rgba(231,238,235,.08); color: #F2F7F5; font-family: "Geist"; font-size: 43px; font-weight: 590; line-height: 1.16; letter-spacing: -0.02em; text-align: center; text-wrap: balance; text-shadow: 0 2px 12px rgba(0,0,0,.6); }
</style>
<div id="captions-root" data-composition-id="captions" data-timeline-locked data-start="0" data-duration="130" data-fps="30" data-width="1920" data-height="1080">
  <div class="caption-layer" aria-hidden="true"><div id="caption-stage" class="caption-stage"></div></div>
</div>
<script>
  var PHRASES = ${serialized};
  var DURATION = 130;
  (function () {
    var stage = document.getElementById("caption-stage");
    PHRASES.forEach(function (phrase, index) {
      var group = document.createElement("div");
      group.className = "caption-group";
      group.id = "caption-phrase-" + index;
      var line = document.createElement("div");
      line.className = "caption-phrase";
      line.textContent = phrase.text;
      group.appendChild(line);
      stage.appendChild(group);
    });
    window.__timelines = window.__timelines || {};
    var tl = gsap.timeline({ paused: true });
    PHRASES.forEach(function (phrase, index) {
      var group = document.getElementById("caption-phrase-" + index);
      var start = Math.max(0, Number(phrase.start));
      var end = Math.max(start + 0.2, Number(phrase.end));
      tl.set(group, { visibility: "visible" }, start);
      tl.fromTo(group, { opacity: 0, y: 9 }, { opacity: 1, y: 0, duration: 0.14, ease: "power2.out" }, start);
      tl.to(group, { opacity: 0, y: -5, duration: 0.1, ease: "power1.in" }, Math.max(start + 0.14, end - 0.1));
      tl.set(group, { opacity: 0, visibility: "hidden" }, end);
    });
    window.__timelines["captions"] = tl;
  })();
</script>
</template>\n`;

writeFileSync(resolve(project, "compositions/captions.html"), html);
console.log(`Built ${groups.length} phrase-level caption groups.`);
