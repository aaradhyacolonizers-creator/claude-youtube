# Edit Sub-Skill

This sub-skill turns a folder of raw phone or camera footage into a finished, upload-ready vlog. Claude analyses every clip (speech, loudness, visuals), proposes a story-driven edit plan, gets the creator's sign-off, then renders the cut with ffmpeg — cold-open montage, section titles, music bed and all. It is built for travel and day-in-the-life vlogs but works for any footage-first format where the story is found in the edit rather than scripted up front.

> Workflow adapted from **vlog-auto-edit** v1.1.0 by nyx研究所 ([GitHub @znyupup](https://github.com/znyupup) · [Bilibili @nyx研究所](https://space.bilibili.com/4330525)).

## Inputs Required

- **Footage folder** (path): directory of source clips (`.mp4`, `.mov`, etc.)
- **Vlog topic** (string): e.g. "3 days in Harbin in winter", "first week in our new flat"
- **Target length** (optional): default is whatever the strongest material supports, typically 8-15 minutes
- **Cleanup mode** (optional): `strict` | `normal` | `loose` — default `normal`
- **Output resolution** (optional): default 1920×1080, 30 fps
- **Music** (optional): path to a BGM file, or "suggest" for a generation brief
- **Reference vlogs** (optional): 1-3 URLs of vlogs whose style the creator wants to match

Channel niche, size tier and goal are not required for this sub-skill — skip the full context-gathering protocol and ask only for the footage folder and topic if missing.

## Reference Files to Load

- `references/vlog-editing-guide.md` — required (commands, benchmarks, pitfalls)
- `references/retention-scripting-guide.md` — for cold-open and pacing decisions
- `templates/vlog-channel.md` — vlog-specific structure and benchmarks

## Prerequisites Check

Before touching footage, verify the toolchain and report what's missing with install commands. Do not install anything without telling the user.

1. `ffmpeg -version` and `ffprobe -version` — required; stop if missing.
2. ASR: `python3 -c "import whisper"`, else `python3 -c "from funasr import AutoModel"`. Prefer Whisper; suggest FunASR for Mandarin footage or when Whisper models can't download. Show the actual import error.
3. `ffmpeg -filters | grep drawtext` — if absent, check `python3 -c "from PIL import Image"` for title overlays.
4. Vision model: ask for an OpenAI-compatible endpoint, model name and API key (read the key from an environment variable; never echo or write it to disk). If none is available, fall back to Claude reading the sampled frames directly with the Read tool.

## Parallel Agents

Optional. For more than ~20 clips, split clip analysis (Step 2) across up to 4 agents, each handling a slice of the footage and writing its own partial `clip_analysis` file; merge them before Step 3. Everything else runs sequentially.

## Execution Steps

1. **Inventory the footage.** Run ffprobe across the folder and produce a clip inventory: count, total duration, resolution and orientation mix, codecs, capture-date range. Flag vertical clips in a landscape project and ask whether to drop them or save them for a Shorts cut. Confirm the output resolution now and keep it for every later step.

2. **Analyse each clip in three dimensions** and write `analysis/clip_analysis.json` (schema in the reference guide):
   - **Speech** — extract 16 kHz mono WAV, transcribe with Whisper `medium` or FunASR. For FunASR, group character timestamps into sentences, skipping punctuation when indexing timestamps.
   - **Loudness** — `volumedetect` mean/max dB. Mean below -40 dB means discard the transcript (ASR hallucination).
   - **Visuals** — sample frames per the duration rule (3 / 5 / every 15s), describe each with the vision model: content, shot size, camera movement, mood.

3. **(Optional) Study reference vlogs.** If the creator supplied reference URLs, download at 720p with yt-dlp, transcribe for narrative structure, run scenedetect for average shot length, and sample frames for shot-size mix. Otherwise use the pacing benchmarks in the reference guide. Skipping both produces a chronological slideshow — don't.

4. **Run pre-edit cleanup.**
   ```bash
   python execution/vlog_edit_tools.py preprocess --analysis analysis/clip_analysis.json --mode normal
   ```
   Merge the `suggested_range` and `skip_zones` per clip into the material you pass to planning. These are suggestions: a "here we go!" cue can be a great cold-open line.

5. **Write the edit plan** (`edit_plan.json`, schema in the Output Template). Apply the benchmarks from the reference guide:
   - Pick an angle — what is this vlog *about* beyond "where we went"? State it in `editing_notes`.
   - Structure: cold-open highlights → arrival → place-by-place or theme-by-theme sections → emotional close.
   - Average 3-4s per shot in b-roll runs; let talking moments breathe; cap silent b-roll stretches per cleanup mode.
   - Aim for the content and shot-size mix in the guide; note deliberate deviations.
   - Same clip may appear multiple times with different ranges. Prefer `suggested_range` unless there's a story reason not to.
   - Pick 6-10 cold-open shots (0.5-1s each, one per major section, landscape only).

6. **Fix speech cuts.**
   ```bash
   python execution/vlog_edit_tools.py fix-cuts --analysis analysis/clip_analysis.json \
     --plan edit_plan.json --out edit_plan_fixed.json
   ```
   Exit code 1 means cuts remain — inspect `remaining` and adjust those clips by hand. Never send a plan with mid-sentence cuts to render.

7. **Get approval.** Present the storyboard (Output Template section 2) with section runtimes, total runtime and any vertical/unused clips. If the user wants a visual review, build an HTML page with a thumbnail per planned clip and transcript snippets. **Do not render until the user approves the plan.**

8. **Render** with the recipes in the reference guide, in this order:
   1. Test the full recipe on one 5-8s clip first.
   2. Cut and normalise every segment with identical encode settings; after each, compare video vs audio stream duration (must differ by < 0.05s; pad audio if not).
   3. Build the cold-open montage (no source audio).
   4. Generate transparent title PNGs; overlay on each section's first 3s with explicit `-map`.
   5. Concat sections with the concat demuxer (never chained xfade). If joins click, use the WAV + concat-filter audio path.
   6. Mix BGM at the level for the section type (0.08-0.12 under speech); use `-t`, not `-shortest`.

9. **Verify the output.** Frame count via `ffmpeg -f null`, final A/V duration diff, last spoken line present, grab one QC frame every 30s and check them. Report anything you could not verify.

10. **Hand off.** Summarise what was cut and why, list unused strong clips (Shorts candidates), and suggest next steps.

## Output Template

````markdown
## Vlog Edit: [Title]

### 1. Footage Inventory
- **Clips**: [N] ([X] min total) · **With speech**: [N] · **Vertical**: [N] ([kept/dropped/Shorts])
- **Resolution mix**: [e.g. 38× 1920×1080, 4× 3840×2160] → output [1920×1080 @ 30fps]
- **Toolchain**: ffmpeg [ver] · ASR [Whisper medium / FunASR] · Vision [model / Claude frames]

### 2. Storyboard
**Angle**: [one sentence — what this vlog is really about]

| # | Section | Clips | Runtime | Purpose |
|---|---------|-------|---------|---------|
| 0 | Cold open | [N] shots | 0:0X | Hook — best moment from each section |
| 1 | [Section — subtitle] | [N] | X:XX | [...] |
| … | … | … | … | … |
| N | [Closing] | [N] | X:XX | Emotional payoff |

**Total runtime**: [X:XX] · **Avg shot length**: [X.Xs] · **Content mix**: food X% / scenery X% / people X% / daily X%

### 3. Edit Plan (edit_plan_fixed.json)
```json
{
  "title": "Video title",
  "structure": [
    {"section": "Section — subtitle", "description": "What this section does",
     "clips": [{"file": "clip_012.mp4", "start": 2.4, "end": 14.0,
                "note": "Shot description", "subtitle": "Kept dialogue"}]}
  ],
  "highlights": [{"file": "clip_031.mp4", "start": 5.2, "end": 5.9}],
  "bgm_suggestion": "genre / mood / instruments / tempo / bpm",
  "editing_notes": "Angle, deliberate deviations from benchmarks"
}
```

### 4. Cleanup & Validation Log
- **Cues removed**: [N] · **Retakes removed**: [N] · **Speech-cut fixes**: [N] · **Remaining issues**: 0

### 5. Render Report
- **Output**: `output/final.mp4` — [duration], [resolution], [size]
- **Frames**: [N] (expected ≈ [duration × fps]) · **A/V diff**: [X.XXs]
- **BGM**: [file / brief] at [level]
- **QC**: [pass/notes per 30s frame check]

### 6. Unused Highlights
| Clip | Range | Why it's strong | Suggested use |
|------|-------|-----------------|---------------|
````

## Quality Checks

- Plan approved by the user before any full render.
- Zero remaining speech cuts from `fix-cuts`.
- Every segment's audio/video duration within 0.05s; final audio ends with the last line intact.
- No black title cards, no xfade chains, no `shortest=1` on overlays.
- Pacing stats in the storyboard are computed from the plan, not estimated.

## Next Steps

After the edit is rendered, suggest:
- `/youtube metadata` — upload package (titles, description, chapters from the section list)
- `/youtube thumbnail` — brief built from the strongest cold-open frame
- `/youtube shorts` or `/youtube repurpose` — turn the Unused Highlights table into Shorts
