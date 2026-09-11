#!/usr/bin/env python3
"""Fetch YouTube transcripts for a church's sermons into research/<slug>/transcripts/.

Examples:
    python3 tools/fetch_transcripts.py --church fbc-tucson "https://youtube.com/playlist?list=PL..."
    python3 tools/fetch_transcripts.py --church fbc-tucson "https://www.youtube.com/@handle/videos" --limit 20
    python3 tools/fetch_transcripts.py --church fbc-tucson "https://www.youtube.com/watch?v=VIDEOID"
    python3 tools/fetch_transcripts.py --church fbc-tucson <url> --audio-fallback   # download audio when captions are disabled

Requirements: yt-dlp on PATH; `pip install youtube-transcript-api`.

Outputs (all under research/<slug>/):
    transcripts/<Title>_<videoId>.txt   timestamped, human-readable
    transcripts/<Title>_<videoId>.json  snippets + metadata
    playlists/<playlistOrChannelId>.json  per-video status for this fetch
    failures.json                      videos with no accessible transcript (merged across runs)
    audio/<videoId>.m4a                only with --audio-fallback (gitignored); transcribe with tools/transcribe_audio.py

The script never invents transcripts: videos with captions disabled are recorded in failures.json.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def safe_stem(title: str, video_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._")
    return f"{cleaned[:90]}_{video_id}"


def format_timestamp(seconds: float) -> str:
    total_ms = round(float(seconds) * 1000)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    return f"{total_s // 3600:02d}:{(total_s // 60) % 60:02d}:{total_s % 60:02d}.{ms:03d}"


def enumerate_url(url: str, limit: int | None) -> dict[str, Any]:
    """Return {"id", "title", "channel", "entries": [...]} for a playlist, channel or single video."""
    if shutil.which("yt-dlp") is None:
        sys.exit("yt-dlp is not on PATH. Install it: https://github.com/yt-dlp/yt-dlp#installation")
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
    ]
    if limit:
        command += ["--playlist-end", str(limit)]
    command.append(url)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        sys.exit(f"yt-dlp returned no data: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    if data.get("_type") in {"playlist", "multi_video"}:
        entries = [e for e in data.get("entries", []) if e]
        return {
            "id": data.get("id") or "playlist",
            "title": data.get("title"),
            "channel": data.get("channel") or data.get("uploader"),
            "entries": entries,
        }
    # single video
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "channel": data.get("channel") or data.get("uploader"),
        "entries": [data],
    }


def fetch_one(video_id: str, languages: list[str]) -> dict[str, Any]:
    from youtube_transcript_api import YouTubeTranscriptApi  # imported lazily for a clearer error

    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    try:
        transcript = transcript_list.find_manually_created_transcript(languages)
    except Exception:  # noqa: BLE001 - fall back to auto captions
        transcript = transcript_list.find_transcript(languages)
    fetched = transcript.fetch()
    snippets = [
        {"start": s.start, "duration": s.duration, "text": s.text}
        for s in fetched
    ]
    return {
        "language_code": transcript.language_code,
        "language": transcript.language,
        "is_generated": transcript.is_generated,
        "snippets": snippets,
    }


def download_audio(video_url: str, audio_dir: Path) -> Path | None:
    audio_dir.mkdir(parents=True, exist_ok=True)
    template = str(audio_dir / "%(id)s.%(ext)s")
    result = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "m4a", "--no-warnings", "-o", template, video_url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"    audio download failed: {result.stderr.strip()[:200]}")
        return None
    matches = sorted(audio_dir.glob("*.m4a"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="YouTube playlist, channel /videos page, or single video URL")
    parser.add_argument("--church", required=True, help="church slug (data/churches/<slug>.json)")
    parser.add_argument("--limit", type=int, help="only the first N entries")
    parser.add_argument("--languages", default="en,en-US,en-GB", help="comma-separated preference order")
    parser.add_argument("--audio-fallback", action="store_true", help="download audio for videos without captions")
    parser.add_argument("--force", action="store_true", help="re-fetch transcripts that already exist")
    args = parser.parse_args()

    research = ROOT / "research" / args.church
    transcripts_dir = research / "transcripts"
    playlists_dir = research / "playlists"
    audio_dir = research / "audio"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    playlists_dir.mkdir(parents=True, exist_ok=True)
    languages = [code.strip() for code in args.languages.split(",") if code.strip()]

    listing = enumerate_url(args.url, args.limit)
    print(f"{listing['title'] or listing['id']}  ({listing['channel']})  {len(listing['entries'])} video(s)")

    entries_out: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, entry in enumerate(listing["entries"], start=1):
        video_id = entry.get("id")
        title = entry.get("title") or video_id
        video_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        if not video_url.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        upload_date = entry.get("upload_date")
        record: dict[str, Any] = {
            "playlist_index": index,
            "video_id": video_id,
            "title": title,
            "url": video_url,
            "upload_date": upload_date,
        }
        stem = safe_stem(title, video_id)
        txt_path = transcripts_dir / f"{stem}.txt"
        json_path = transcripts_dir / f"{stem}.json"
        if txt_path.exists() and not args.force:
            print(f"  [{index:02d}] skip (exists) {title}")
            record["status"] = "exists"
            entries_out.append(record)
            continue
        try:
            fetched = fetch_one(video_id, languages)
        except Exception as exc:  # noqa: BLE001 - we want to keep going
            reason = type(exc).__name__
            print(f"  [{index:02d}] FAIL {reason}: {title}")
            record["status"] = "failed"
            record["failure"] = reason
            failure = {**record, "message": str(exc).strip()[:300]}
            if args.audio_fallback:
                audio_path = download_audio(video_url, audio_dir)
                if audio_path:
                    failure["audio_path"] = str(audio_path.relative_to(ROOT))
                    print(f"        audio saved -> {audio_path.relative_to(ROOT)}")
            failures.append(failure)
            entries_out.append(record)
            continue

        header = [
            f"# {title}",
            f"# {video_url}",
            f"# Language: {fetched['language']} ({fetched['language_code']})",
            f"# Upload date: {upload_date or 'unknown'}",
            f"# Fetched: {datetime.now(timezone.utc).isoformat()}",
        ]
        lines = [f"[{format_timestamp(s['start'])}] {s['text'].strip()}" for s in fetched["snippets"]]
        txt_path.write_text("\n".join(header + lines).rstrip() + "\n", encoding="utf-8")
        json_path.write_text(
            json.dumps({**record, "status": "success", **fetched, "snippet_count": len(fetched["snippets"])}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        record["status"] = "success"
        record["is_generated"] = fetched["is_generated"]
        entries_out.append(record)
        print(f"  [{index:02d}] ok   {title}  ({len(fetched['snippets'])} snippets{', auto' if fetched['is_generated'] else ''})")

    listing_out = {
        "source_url": args.url,
        "id": listing["id"],
        "title": listing["title"],
        "channel": listing["channel"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries_out),
        "successful": sum(e["status"] in {"success", "exists"} for e in entries_out),
        "failed": sum(e["status"] == "failed" for e in entries_out),
        "entries": entries_out,
    }
    listing_path = playlists_dir / f"{re.sub(r'[^A-Za-z0-9_-]+', '_', str(listing['id']))}.json"
    listing_path.write_text(json.dumps(listing_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    failures_path = research / "failures.json"
    existing: dict[str, Any] = {"failures": []}
    if failures_path.exists():
        try:
            existing = json.loads(failures_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    merged = {f["video_id"]: f for f in existing.get("failures", []) if f.get("video_id")}
    for f in failures:
        merged[f["video_id"]] = f
    failures_path.write_text(
        json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "failures": list(merged.values())}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n{listing_out['successful']} transcript(s) available, {listing_out['failed']} failed. Listing -> {listing_path.relative_to(ROOT)}")
    if failures:
        print(f"Failures recorded in {failures_path.relative_to(ROOT)}"
              + ("" if args.audio_fallback else " (re-run with --audio-fallback to download audio for local transcription)"))


if __name__ == "__main__":
    main()
