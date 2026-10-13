# Vlog Auto-Editing Guide

Commands, benchmarks, and failure modes for turning raw phone footage into a
finished vlog with ffmpeg + ASR + a vision model. Used by `sub-skills/edit.md`.

> Adapted from **vlog-auto-edit** v1.1.0 by nyx研究所
> ([GitHub @znyupup](https://github.com/znyupup) · [Bilibili](https://space.bilibili.com/4330525)).

## Toolchain

| Tool | Role | Notes |
|------|------|-------|
| ffmpeg / ffprobe | Probe, cut, encode, concat, frame grabs, loudness | Only system-level dependency |
| Whisper (`openai-whisper`) | ASR, sentence-level timestamps | `medium` is the sweet spot: `base` is weak on non-English, `large` is slow |
| FunASR (`funasr modelscope torchaudio`) | ASR alternative, best for Mandarin | ~3-5x faster on CPU; char-level timestamps; models download from ModelScope (fast in mainland China) |
| Pillow | Transparent title overlays | Needed when `ffmpeg -filters` has no `drawtext` (Homebrew builds often lack freetype) |
| Vision model API | Describe sampled frames | Any OpenAI-compatible chat endpoint with base64 `image_url` support (GPT-4o, Qwen-VL, GLM-4.6V-Flash free tier) |
| yt-dlp, scenedetect | Optional reference-vlog research | Pacing analysis only |

**Detect before installing.** Run `python3 -c "import whisper"` (and `from funasr import AutoModel`,
`from PIL import Image`) and read the real error — don't hide it with `2>/dev/null`. Don't create
a fresh venv per project: the Whisper medium model is 1.4 GB. FunASR **must** have `torchaudio`
installed explicitly or import fails.

**Avoid:** CapCut/Jianying project files (encrypted since v10.4), moviepy (adds nothing over
ffmpeg), ImageMagick (Pillow covers it).

## Footage Analysis

```bash
# Inventory: duration, resolution, codec per clip
ffprobe -v quiet -print_format json -show_format -show_streams clip.mp4
# Audio for ASR: 16 kHz mono WAV works for both engines
ffmpeg -i clip.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
# Loudness: mean < -40 dB ≈ silent; mean > -20 dB ≈ clear speech/sound
ffmpeg -i clip.mp4 -af volumedetect -f null /dev/null 2>&1 | grep volume
# Frame grab at time T, scaled to 720p wide-enough for vision models
ffmpeg -ss T -i clip.mp4 -frames:v 1 -vf "scale=1280:-2" -q:v 2 frame.jpg
```

**Frame sampling:** ≤20s → 3 frames (start/middle/end) · 20-60s → 5 frames · >60s → 1 every 15s.
Use `-ss` before `-i` (fast seek); grab the last frame at `duration - 0.1`.

**Vision prompt:** "Describe the shot briefly. Label shot size (wide/full/medium/close/extreme
close), camera (locked/handheld/moving), mood. Format: content|size|camera|mood". Add retry +
backoff — free tiers rate-limit at peak hours. Check the vision endpoint differs from the text one
on platforms that split them.

**Whisper:** `whisper.load_model("medium").transcribe("audio.wav")` → `result["segments"]`
(`start`, `end`, `text`). Whisper hallucinates text over music/ambience — drop transcripts for
clips with mean volume < -40 dB.

**FunASR:** `AutoModel(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc",
disable_update=True).generate(input="audio.wav")` → `text` + per-character `timestamp`
`[[start_ms, end_ms], ...]`. Group characters into sentences at `。！？，,.!?`. Punctuation added
by `ct-punc` has **no** timestamp, so advance the timestamp index only on non-punctuation
characters or every later sentence drifts. Empty text means no speech.

**Per-clip record** (`clip_analysis.json`, one list entry per clip):

```json
{"filename": "clip_001.mp4", "duration": 15.3, "resolution": "1920x1080",
 "visual": [{"time": "0:00", "description": "...", "shot_type": "close",
             "camera": "handheld", "mood": "warm"}],
 "audio": {"has_speech": true, "mean_volume_db": -20.5, "max_volume_db": -3.2,
           "transcript": [{"start": 0.5, "end": 2.3, "text": "..."}]}}
```

Flag vertical (9:16) clips here — mixed into a 16:9 edit they look jarring; drop them or move
them to a Shorts cut.

## Pre-Edit Cleanup Modes

`execution/vlog_edit_tools.py preprocess` marks recording cues, retakes, shaky lead-ins, and dead
tails. Suggestions only — the edit plan may keep a cue that has story value.

| Mode | Max silent b-roll | Cues | Retakes | Lead-in skipped |
|------|-------------------|------|---------|-----------------|
| strict | 8-10s | All removed | Keep one take | 1.5s |
| normal | 12-15s | Clear cues removed | Obvious repeats removed | 1.0s |
| loose | 20-25s | Only "rolling"-type cues | Mostly kept | 0.5s |

## Pacing Benchmarks (travel vlogs)

From the source workflow's analysis of high-performing travel vlogs:

- **Average shot length:** 3-4s. Montage shots < 2s; narrative shots > 8s; alternate them.
- **Content mix:** food 40-45% · scenery 30% · people 15% · daily life 15%.
- **Shot sizes:** medium/close 60-65%, wide/full 35-40%.
- **Structure:** highlight cold open → departure/arrival → place-by-place → emotional close.
  Roughly 25% setup / 50% development / 25% resolution.
- **Silent b-roll:** > 6s feels long; compress to 5-8s.
- **Cold-open montage:** 6-10 shots × 0.5-1s (5-8s total), one per major section, no source audio.
- Pick a focus — chronological "and then we…" edits are the main failure mode.

## Rendering Recipes

```bash
# Cut + normalise one clip (same settings for every segment so concat can copy)
ffmpeg -y -ss START -i in.mp4 -t DUR \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1" \
  -r 30 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 2 -movflags +faststart seg_001.mp4

# Join normalised segments
printf "file 'seg_001.mp4'\nfile 'seg_002.mp4'\n" > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart out.mp4

# 2x speed, audio kept in sync
ffmpeg -i in.mp4 -filter:v "setpts=0.5*PTS" -filter:a "atempo=2.0" out.mp4

# Section title (transparent PNG from Pillow) over the first 3 seconds
ffmpeg -y -i section.mp4 -i title.png \
  -filter_complex "[0:v][1:v]overlay=0:0:enable='between(t,0,3)'[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy titled.mp4

# BGM under dialogue (volume 0.08-0.12 with speech, 0.15-0.25 mostly b-roll, 0.3-0.4 montage)
ffmpeg -y -i video.mp4 -i bgm.m4a -filter_complex \
  "[1:a]volume=0.12[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart final.mp4
```

**Titles:** white text, soft blurred drop shadow (Gaussian radius ~6, alpha ~180), on a fully
transparent 1920×1080 RGBA canvas. Never black title cards. Fonts: Noto Sans CJK (Linux),
Hiragino Sans GB (macOS) for CJK text.

**BGM by vlog mood:** everyday → indie pop, ukulele, moderate · healing/artsy → acoustic folk,
piano, slow · food → jazz/bossa nova · winter → cinematic ambient, celesta · tropical → tropical
house, marimba · city → lo-fi hip hop. Keep chained tracks within ~20 BPM and a related key.

## Pitfalls

1. **Mid-speech cuts.** LLM plans routinely start/end inside a sentence. Always run
   `vlog_edit_tools.py fix-cuts` (0.3s tolerance — ASR timestamps drift ±0.2-0.3s).
2. **atempo drift.** After speed changes audio can end 0.4-0.8s before video per segment; over 8
   segments sync is gone. Check `ffprobe -select_streams v` vs `a` stream durations per segment
   (diff must be < 0.05s); pad with `-af apad -t <video duration>`.
3. **Clicks / offset after concat copy.** If audio pops at joins, extract each segment's audio to
   WAV (`apad`, `-t` = video duration, 48 kHz stereo), join with the `concat` *filter*, concat
   video with `-c copy`, then mux the two.
4. **xfade chains** drop frames cumulatively (black second half). Hard-cut, or fade each
   section's head/tail and concat.
5. **`shortest=1` with a PNG overlay** truncates the video to one frame. Leave it off.
6. **Overlay steals audio.** With `-filter_complex`, always `-map` the audio from the main input.
7. **`-shortest` clips the ending audio.** Prefer `-t <exact duration>`.
8. **Re-encoding stacks quality loss.** Do cut + scale + overlay in one filter chain where possible.
9. **CapCut/NLE import out of sync:** `-r 30 -vsync cfr -x264-params bframes=0 -ar 48000 -ac 2`.
10. **Fix the output resolution first** and keep it for every step.
11. **Leaked ffmpeg processes:** killing a background shell can orphan ffmpeg — check `ps aux | grep ffmpeg`.
12. **Harmless noise:** HEVC "Error constructing the frame RPS" and concat "Non-monotonic DTS" warnings.
13. **Verify before delivering:** count frames (`ffmpeg -i final.mp4 -f null -`), scrub the second
    half for A/V sync, confirm the last line of audio survives, and test any new render recipe on a
    5-8s clip first.
