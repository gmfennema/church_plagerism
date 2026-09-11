#!/usr/bin/env python3
"""Transcribe downloaded audio with Whisper when YouTube captions are unavailable.

    python3 tools/transcribe_audio.py research/<slug>/audio/*.m4a --out research/<slug>/transcripts
    python3 tools/transcribe_audio.py source.mp3 --out research/<slug>/source_transcripts/<source-slug>

Tries, in order: the `faster_whisper` Python package, the `whisper` Python package, then the `whisper` CLI.
Install one of them first, e.g. `pip install faster-whisper`. Model defaults to "small" (good speed/accuracy
trade-off for English sermons); use --model medium for better accuracy.

Output is a plain .txt with one caption line per segment, prefixed with a [hh:mm:ss.mmm] timestamp so it is
interchangeable with the YouTube transcripts produced by tools/fetch_transcripts.py.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def fmt(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    ms = total_ms % 1000
    s = total_ms // 1000
    return f"{s // 3600:02d}:{(s // 60) % 60:02d}:{s % 60:02d}.{ms:03d}"


def transcribe(path: Path, model_name: str, language: str) -> list[tuple[float, str]]:
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(model_name, compute_type="int8")
        segments, _info = model.transcribe(str(path), language=language, vad_filter=True)
        return [(seg.start, seg.text.strip()) for seg in segments]
    except ImportError:
        pass
    try:
        import whisper  # type: ignore

        model = whisper.load_model(model_name)
        result = model.transcribe(str(path), language=language)
        return [(seg["start"], seg["text"].strip()) for seg in result["segments"]]
    except ImportError:
        pass
    if shutil.which("whisper"):
        out_dir = path.parent / ".whisper_tmp"
        out_dir.mkdir(exist_ok=True)
        subprocess.run(
            ["whisper", str(path), "--model", model_name, "--language", language, "--output_format", "srt", "--output_dir", str(out_dir)],
            check=True,
        )
        srt = out_dir / f"{path.stem}.srt"
        segments: list[tuple[float, str]] = []
        block: list[str] = []
        for line in srt.read_text(encoding="utf-8").splitlines() + [""]:
            if line.strip():
                block.append(line)
                continue
            if len(block) >= 3 and "-->" in block[1]:
                h, m, rest = block[1].split(" --> ")[0].split(":")
                s, ms = rest.split(",")
                start = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                segments.append((start, " ".join(block[2:]).strip()))
            block = []
        return segments
    sys.exit("No Whisper implementation found. Install one: pip install faster-whisper")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path, help="output directory for .txt transcripts")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="en")
    parser.add_argument("--title", help="title line for the header (defaults to the file stem)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for audio in args.audio:
        target = args.out / f"{audio.stem}.txt"
        if target.exists():
            print(f"skip (exists) {target}")
            continue
        print(f"transcribing {audio} with model '{args.model}' ...")
        segments = transcribe(audio, args.model, args.language)
        header = [f"# {args.title or audio.stem}", f"# Source audio: {audio.name}", f"# Transcribed locally with Whisper ({args.model})"]
        body = [f"[{fmt(start)}] {text}" for start, text in segments if text]
        target.write_text("\n".join(header + body) + "\n", encoding="utf-8")
        print(f"  -> {target} ({len(body)} segments)")


if __name__ == "__main__":
    main()
