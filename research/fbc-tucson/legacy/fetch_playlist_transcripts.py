#!/usr/bin/env python3
"""Fetch a YouTube playlist's available transcripts into a local project."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi


DEFAULT_PLAYLIST = (
    "https://youtube.com/playlist?list=PLEFrfWIivGoZxyyOR8G49a2HKwczrRut5"
)


def safe_stem(title: str, video_id: str) -> str:
    """Return a filesystem-safe, stable filename stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._")
    return f"{cleaned[:99]}_{video_id}"


def enumerate_playlist(playlist_url: str) -> dict[str, Any]:
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        playlist_url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        detail = result.stderr.strip() or "yt-dlp returned no playlist data"
        raise RuntimeError(detail)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse yt-dlp output: {exc}") from exc


def format_timestamp(seconds: float) -> str:
    total_milliseconds = round(float(seconds) * 1000)
    milliseconds = total_milliseconds % 1000
    total_seconds = total_milliseconds // 1000
    second = total_seconds % 60
    minute = (total_seconds // 60) % 60
    hour = total_seconds // 3600
    return f"{hour:02d}:{minute:02d}:{second:02d}.{milliseconds:03d}"


def transcript_text(snippets: list[dict[str, Any]]) -> str:
    lines = [
        f"[{format_timestamp(snippet['start'])}] {snippet['text'].strip()}"
        for snippet in snippets
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playlist_url", nargs="?", default=DEFAULT_PLAYLIST)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory where playlist.json, failures.json, and transcripts/ are written.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    transcripts_dir = output_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    playlist_data = enumerate_playlist(args.playlist_url)
    entries = playlist_data.get("entries") or []
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    api = YouTubeTranscriptApi()

    for playlist_index, entry in enumerate(entries, start=1):
        video_id = (entry or {}).get("id") if isinstance(entry, dict) else None
        title = ((entry or {}).get("title") if isinstance(entry, dict) else None) or "Unavailable video"
        url = ((entry or {}).get("webpage_url") if isinstance(entry, dict) else None) or (
            f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        )
        base = {
            "playlist_index": playlist_index,
            "video_id": video_id,
            "title": title,
            "url": url,
        }

        if not video_id:
            failure = {**base, "reason": "missing_video_id", "message": "yt-dlp returned no video ID"}
            failures.append(failure)
            results.append({**base, "status": "failed", "failure": failure["reason"]})
            continue

        print(f"[{playlist_index:02d}/{len(entries):02d}] {title}", flush=True)
        try:
            fetched = api.fetch(video_id)
            snippets = [
                {
                    "text": snippet.text,
                    "start": snippet.start,
                    "duration": snippet.duration,
                }
                for snippet in fetched.snippets
            ]
            metadata = {
                **base,
                "status": "success",
                "language_code": fetched.language_code,
                "language": fetched.language,
                "is_generated": fetched.is_generated,
                "snippet_count": len(snippets),
            }
            stem = safe_stem(title, video_id)
            write_json(transcripts_dir / f"{stem}.json", {**metadata, "snippets": snippets})
            (transcripts_dir / f"{stem}.txt").write_text(
                f"# {title}\n"
                f"# https://www.youtube.com/watch?v={video_id}\n"
                f"# Language: {fetched.language} ({fetched.language_code})\n"
                f"# Generated: {fetched.is_generated}\n\n"
                + transcript_text(snippets),
                encoding="utf-8",
            )
            results.append(metadata)
        except Exception as exc:  # Transcript API exposes several version-specific exceptions.
            reason = type(exc).__name__
            failure = {**base, "reason": reason, "message": str(exc)}
            failures.append(failure)
            results.append({**base, "status": "failed", "failure": reason})
            print(f"  skipped: {reason}", file=sys.stderr, flush=True)

    completed_at = datetime.now(timezone.utc).isoformat()
    write_json(
        output_dir / "playlist.json",
        {
            "playlist_url": args.playlist_url,
            "playlist_id": playlist_data.get("id"),
            "playlist_title": playlist_data.get("title"),
            "channel": playlist_data.get("channel") or playlist_data.get("uploader"),
            "fetched_at": completed_at,
            "total_entries": len(entries),
            "successful_transcripts": sum(item.get("status") == "success" for item in results),
            "failed_entries": len(failures),
            "entries": results,
        },
    )
    write_json(
        output_dir / "failures.json",
        {"playlist_url": args.playlist_url, "fetched_at": completed_at, "failures": failures},
    )
    print(
        f"Done: {len(results) - len(failures)} transcripts saved; "
        f"{len(failures)} entries recorded in failures.json."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
