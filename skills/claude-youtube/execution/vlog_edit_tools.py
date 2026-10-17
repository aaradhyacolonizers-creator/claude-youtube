"""
Pre-render helpers for the automated vlog editing workflow (/youtube edit).

Two subcommands, both stdlib-only and both printing JSON to stdout:

  preprocess  Read clip_analysis.json and annotate each clip with a suggested
              usable range: recording cues ("okay, rolling", "开始了"),
              repeated takes, shaky lead-in and dead tail after the last line.
              Suggestions only -- nothing is trimmed. The LLM edit plan keeps
              the final say.

  fix-cuts    Check an edit_plan.json against the transcripts and widen any
              clip whose start/end lands in the middle of speech. Re-checks
              after fixing and reports anything still cut.

clip_analysis.json is a list of objects shaped like:
  {"filename": "clip_001.mp4", "duration": 15.3,
   "audio": {"has_speech": true, "mean_volume_db": -20.5,
             "transcript": [{"start": 0.5, "end": 2.3, "text": "..."}]}}

edit_plan.json:
  {"title": "...", "structure": [{"section": "...", "clips": [
     {"file": "clip_001.mp4", "start": 0.0, "end": 12.0, "note": "..."}]}]}

Workflow adapted from vlog-auto-edit by nyx研究所 (https://github.com/znyupup).

Usage:
    python execution/vlog_edit_tools.py preprocess --analysis clip_analysis.json
    python execution/vlog_edit_tools.py preprocess --analysis clip_analysis.json --mode strict
    python execution/vlog_edit_tools.py fix-cuts --analysis clip_analysis.json \\
        --plan edit_plan.json --out edit_plan_fixed.json
"""

import argparse
import json
import sys
from difflib import SequenceMatcher

# Phrases people say when they hit record. Only treated as cues near the
# start (or end) of a clip, since mid-clip they may carry meaning.
# Prefix cues are unambiguous ("rolling, so today..."); filler words like
# "okay" only count when they are the whole segment.
PREFIX_CUES = [
    "okay rolling", "ok rolling", "rolling", "are we recording", "recording",
    "action", "开始了", "好了开始", "开始录了", "好了 开始",
]
EXACT_CUES = ["okay go", "ok go", "alright", "okay", "ok",
              "走了", "好了", "来了"]
END_CUES = ["okay", "ok", "cut", "stop", "done", "好了", "走了", "好了 走"]

# Per-mode tuning: how long silent footage may run, how aggressively
# to drop cues/repeats, and how much shaky lead-in to skip.
MODES = {
    "strict": {"max_broll": 10.0, "repeat_threshold": 0.5, "lead_in": 1.5,
               "cues": "all"},
    "normal": {"max_broll": 15.0, "repeat_threshold": 0.6, "lead_in": 1.0,
               "cues": "all"},
    "loose": {"max_broll": 25.0, "repeat_threshold": 0.8, "lead_in": 0.5,
              "cues": "explicit"},
}
EXPLICIT_CUES = {"okay rolling", "ok rolling", "rolling", "action", "开始了"}
SILENT_DB = -40.0  # below this mean volume, treat transcript as hallucinated


def _norm(text):
    """Lowercase and strip punctuation/whitespace for cue matching."""
    keep = [c for c in text.lower() if c.isalnum() or c == " "]
    return " ".join("".join(keep).split())


def _transcript(clip):
    """Return the clip's speech segments, ignoring likely ASR hallucinations."""
    audio = clip.get("audio") or {}
    if not audio.get("has_speech"):
        return []
    mean_db = audio.get("mean_volume_db")
    if mean_db is not None and mean_db < SILENT_DB:
        return []
    return [s for s in audio.get("transcript", []) if s.get("text", "").strip()]


def detect_cues(segments, duration, mode):
    """Find recording cues in the first/last 3 seconds of a clip."""
    allowed = EXPLICIT_CUES if MODES[mode]["cues"] == "explicit" else None
    zones = []
    for seg in segments:
        text = _norm(seg["text"])
        if seg["start"] < 3.0:
            for cue in PREFIX_CUES + EXACT_CUES:
                if allowed is not None and cue not in allowed:
                    continue
                prefix = cue in PREFIX_CUES and (
                    text.startswith(cue + " ") or
                    (not cue.isascii() and text.startswith(cue)))
                if text == cue or prefix:
                    zones.append({"type": "recording_cue", "action": "skip",
                                  "range": [seg["start"], seg["end"]],
                                  "text": seg["text"].strip()})
                    break
        elif seg["end"] > duration - 3.0 and allowed is None and text in END_CUES:
            zones.append({"type": "recording_cue", "action": "skip",
                          "range": [seg["start"], seg["end"]],
                          "text": seg["text"].strip()})
    return zones


def detect_repeats(segments, threshold):
    """Flag retakes: near-duplicate lines, keeping the longer (usually final) take."""
    flagged = {}
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            if len(a["text"].strip()) <= 4:
                continue
            ratio = SequenceMatcher(None, a["text"], b["text"]).ratio()
            if ratio < threshold:
                continue
            # Prefer keeping the later take on a tie: it's usually the clean one.
            skip, kept = (a, b) if len(a["text"]) <= len(b["text"]) else (b, a)
            key = (skip["start"], skip["end"])
            if key not in flagged:
                flagged[key] = {"type": "repeat", "action": "suggest_skip",
                                "range": [skip["start"], skip["end"]],
                                "text": skip["text"].strip(),
                                "kept": kept["text"].strip(),
                                "similarity": round(ratio, 2)}
    return list(flagged.values())


def suggest_range(segments, duration, skip_zones, mode):
    """Suggest start/end from first/last usable speech, lead-in and b-roll caps."""
    cfg = MODES[mode]
    skipped = {(z["range"][0], z["range"][1]) for z in skip_zones
               if z["action"] == "skip"}
    speech = [s for s in segments if (s["start"], s["end"]) not in skipped]

    if not speech:
        start = min(cfg["lead_in"], duration / 4) if duration > 5.0 else 0.0
        end = min(duration, start + cfg["max_broll"])
        return round(start, 2), round(end, 2)

    first, last = speech[0]["start"], speech[-1]["end"]
    start = max(0.0, first - 0.5) if first > 2.0 else 0.0
    # Never start inside a skipped cue that precedes the first kept line.
    for lo, hi in skipped:
        if lo <= start < hi:
            start = hi
    if start == 0.0 and duration > 5.0:
        start = min(cfg["lead_in"], max(0.0, first - 0.2))
    end = last + 1.5 if duration - last > 3.0 else duration
    return round(start, 2), round(min(end, duration), 2)


def preprocess(clips, mode):
    """Annotate every clip with skip zones and a suggested usable range."""
    results = []
    for clip in clips:
        duration = float(clip.get("duration", 0))
        segments = _transcript(clip)
        cues = detect_cues(segments, duration, mode)
        repeats = detect_repeats(segments, MODES[mode]["repeat_threshold"])
        start, end = suggest_range(segments, duration, cues, mode)
        results.append({
            "filename": clip.get("filename") or clip.get("file"),
            "duration": duration,
            "has_speech": bool(segments),
            "original_range": [0.0, duration],
            "suggested_range": [start, end],
            "skip_zones": sorted(cues + repeats, key=lambda z: z["range"][0]),
            "speech_range": ([segments[0]["start"], segments[-1]["end"]]
                             if segments else None),
        })
    return {"mode": mode, "clip_count": len(results), "clips": results}


def speech_index(clips):
    """Map filename -> [(start, end, text)] for clips with real speech."""
    index = {}
    for clip in clips:
        segs = _transcript(clip)
        if segs:
            name = clip.get("filename") or clip.get("file")
            index[name] = [(float(s["start"]), float(s["end"]), s["text"])
                           for s in segs]
    return index


def find_cuts(plan, speech, margin):
    """List every clip boundary that falls inside a speech segment."""
    issues = []
    for sec in plan.get("structure", []):
        for clip in sec.get("clips", []):
            cs, ce = float(clip["start"]), float(clip["end"])
            for ss, se, txt in speech.get(clip["file"], []):
                if ss >= ce or se <= cs:
                    continue
                if ss < cs - margin:
                    issues.append({"file": clip["file"], "edge": "start",
                                   "clip": [cs, ce], "speech": [ss, se],
                                   "text": txt.strip()})
                if se > ce + margin:
                    issues.append({"file": clip["file"], "edge": "end",
                                   "clip": [cs, ce], "speech": [ss, se],
                                   "text": txt.strip()})
    return issues


def fix_cuts(plan, speech, durations, margin):
    """Widen clips in place until no boundary splits a line. Returns a fix log."""
    fixes = []
    for sec in plan.get("structure", []):
        for clip in sec.get("clips", []):
            limit = durations.get(clip["file"])
            # Widening can pull a neighbouring line into range, so repeat
            # until stable (bounded: each pass only ever widens).
            for _ in range(10):
                cs, ce = float(clip["start"]), float(clip["end"])
                changed = False
                for ss, se, txt in speech.get(clip["file"], []):
                    if ss >= ce or se <= cs:
                        continue
                    if ss < cs - margin:
                        cs = round(max(0.0, ss - 0.1), 2)
                        fixes.append({"file": clip["file"], "edge": "start",
                                      "from": float(clip["start"]), "to": cs,
                                      "text": txt.strip()[:40]})
                        clip["start"] = cs
                        changed = True
                    if se > ce + margin:
                        ce = round(se + 0.2, 2)
                        if limit:
                            ce = min(ce, limit)
                        fixes.append({"file": clip["file"], "edge": "end",
                                      "from": float(clip["end"]), "to": ce,
                                      "text": txt.strip()[:40]})
                        clip["end"] = ce
                        changed = True
                if not changed:
                    break
    return fixes


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-render helpers for automated vlog editing.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("preprocess", help="Suggest usable range per clip")
    p.add_argument("--analysis", required=True, help="clip_analysis.json")
    p.add_argument("--mode", choices=sorted(MODES), default="normal")

    f = sub.add_parser("fix-cuts", help="Fix clips that cut speech mid-line")
    f.add_argument("--analysis", required=True, help="clip_analysis.json")
    f.add_argument("--plan", required=True, help="edit_plan.json")
    f.add_argument("--out", help="Write the fixed plan here")
    f.add_argument("--margin", type=float, default=0.3,
                   help="ASR timestamp tolerance in seconds (default 0.3)")

    args = parser.parse_args()
    clips = _load(args.analysis)

    if args.command == "preprocess":
        print(json.dumps(preprocess(clips, args.mode), ensure_ascii=False,
                         indent=2))
        return

    plan = _load(args.plan)
    speech = speech_index(clips)
    durations = {(c.get("filename") or c.get("file")): float(c["duration"])
                 for c in clips if c.get("duration")}
    before = find_cuts(plan, speech, args.margin)
    fixes = fix_cuts(plan, speech, durations, args.margin)
    after = find_cuts(plan, speech, args.margin)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"issues_found": len(before), "fixes_applied": len(fixes),
                      "issues_remaining": len(after), "fixes": fixes,
                      "remaining": after, "output": args.out},
                     ensure_ascii=False, indent=2))
    if after:
        sys.exit(1)


if __name__ == "__main__":
    main()
