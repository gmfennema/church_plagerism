# Audio comparison clips

`make_comparison_clip.sh` builds a single back-to-back excerpt: Alistair Begg first,
then the FBC Tucson delivery of the same words. It is the "that's been true this week"
confession discussed in the report (Findings · Character).

The audio itself is **not** in this repository. The Truth For Life mp3s are excluded by
`.gitignore`, and the FBC audio has to come from the livestream.

## Run

```bash
cd fbc_tucson/analysis/clips
./make_comparison_clip.sh --begg-mp3 ../../source_audio/10-thefaithfulnessofgod.mp3
```

Needs `ffmpeg` on PATH, and `yt-dlp` unless you pass `--fbc-src` a local file.
Output is `this_week_begg_then_fbc.mp3`, about 80 seconds.

## The two excerpts

| | Source | In-point | Length |
|---|---|---|---|
| Begg | Truth For Life, *The Faithfulness of God* (1 Thess. vol. 3) | ~11:14 (estimated) | 36 s |
| FBC | July 26, 2026 livestream, video `MXAy4hKNfwc` | 0:56:04 | 42 s |

Both are loudness-matched to -16 LUFS so the comparison is not coloured by recording
level, and a soft tone marks the switch.

**The Begg in-point is an estimate.** The Whisper transcript in `source_transcripts/`
carries no timestamps, so the start was derived from word position: the passage begins
30.2% of the way through a 4,761-word transcript. Nudge `--begg-start` until the excerpt
opens on "...despite the fact that we have been established in God's righteousness..."
and closes on "...the evil I should have renounced."

To get an exact in-point instead of estimating, re-transcribe the local mp3 with word
timestamps, e.g. `whisper --model small --word_timestamps True <mp3>`, and search the
output for "been true this week".

## Note on use

These are short excerpts of publicly published sermons, assembled for critical comparison
and documented in the accompanying report. Keep them that way.
