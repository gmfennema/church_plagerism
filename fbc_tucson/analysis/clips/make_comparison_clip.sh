#!/usr/bin/env bash
# Build a single back-to-back audio comparison: Alistair Begg first, then FBC Tucson.
#
# The passage is the "that's been true this week" confession:
#   Begg,  "The Faithfulness of God" (Truth For Life, 1 Thess. vol. 3)
#   FBC,   "The Faithfulness of God" (July 26, 2026) at 0:56:04
#
# Usage:
#   ./make_comparison_clip.sh --begg-mp3 ../../source_audio/10-thefaithfulnessofgod.mp3
#
# Both clips are loudness-matched so the comparison is not coloured by recording level.
# A short tone marks the switch from Begg to FBC.
set -euo pipefail

BEGG_MP3=""
BEGG_START="11:14"          # estimate: the passage sits 30.2% into the transcript
BEGG_DUR="36"
FBC_SRC="https://www.youtube.com/watch?v=MXAy4hKNfwc"
FBC_START="00:56:04"
FBC_DUR="42"
OUT="this_week_begg_then_fbc.mp3"
FFMPEG="${FFMPEG:-ffmpeg}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --begg-mp3)   BEGG_MP3="$2"; shift 2;;
    --begg-start) BEGG_START="$2"; shift 2;;
    --begg-dur)   BEGG_DUR="$2"; shift 2;;
    --fbc-src)    FBC_SRC="$2"; shift 2;;
    --fbc-start)  FBC_START="$2"; shift 2;;
    --fbc-dur)    FBC_DUR="$2"; shift 2;;
    --out)        OUT="$2"; shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

if [[ -z "$BEGG_MP3" ]]; then
  echo "error: --begg-mp3 is required (the Truth For Life mp3 you already downloaded)" >&2
  exit 2
fi
[[ -f "$BEGG_MP3" ]] || { echo "error: no such file: $BEGG_MP3" >&2; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1. FBC audio: download it unless a local file was supplied.
if [[ -f "$FBC_SRC" ]]; then
  FBC_AUDIO="$FBC_SRC"
else
  echo "==> downloading FBC audio with yt-dlp"
  yt-dlp -x --audio-format mp3 -o "$WORK/fbc.%(ext)s" "$FBC_SRC"
  FBC_AUDIO="$WORK/fbc.mp3"
fi

# 2. Cut each excerpt, downmix to mono 44.1k, normalise loudness to -16 LUFS.
cut_clip () { # $1 in  $2 start  $3 dur  $4 out
  "$FFMPEG" -hide_banner -loglevel error -y \
    -ss "$2" -t "$3" -i "$1" \
    -af "loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.25,afade=t=out:st=$(echo "$3 - 0.35" | bc):d=0.35" \
    -ac 1 -ar 44100 "$4"
}

echo "==> cutting Begg  $BEGG_START +${BEGG_DUR}s"
cut_clip "$BEGG_MP3"   "$BEGG_START" "$BEGG_DUR" "$WORK/a.wav"
echo "==> cutting FBC   $FBC_START +${FBC_DUR}s"
cut_clip "$FBC_AUDIO"  "$FBC_START"  "$FBC_DUR"  "$WORK/b.wav"

# 3. Marker between the two: silence, a soft 660 Hz blip, silence.
"$FFMPEG" -hide_banner -loglevel error -y \
  -f lavfi -i "sine=frequency=660:duration=0.18:sample_rate=44100" \
  -af "volume=0.09,adelay=700|700,apad=whole_dur=1.9" -ac 1 -ar 44100 "$WORK/gap.wav"

# 4. Concatenate: Begg, marker, FBC.
"$FFMPEG" -hide_banner -loglevel error -y \
  -i "$WORK/a.wav" -i "$WORK/gap.wav" -i "$WORK/b.wav" \
  -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]" -map "[out]" \
  -codec:a libmp3lame -q:a 3 \
  -metadata title="\"That's been true this week\" - Begg, then FBC Tucson" \
  -metadata artist="Sermon dependence review" \
  -metadata comment="Excerpts for critical comparison. Begg: Truth For Life, The Faithfulness of God. FBC Tucson: July 26 2026, 0:56:04." \
  "$OUT"

echo
echo "wrote $OUT"
"$FFMPEG" -hide_banner -i "$OUT" 2>&1 | grep -E "Duration|Stream #0" || true
echo
echo "If Begg's half starts mid-sentence, nudge --begg-start. The line to land on is"
echo "\"...despite the fact that we have been established in God's righteousness...\""
echo "and the excerpt should end on \"...the evil I should have renounced.\""
