#!/usr/bin/env python3
"""Local Apple Silicon transcription, one recording at a time, with Git checkpoints."""
import argparse
import fcntl
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from corpus import BASE, now, rebuild, save_json, stem

ROOT = BASE.parents[1]
WORK = ROOT / '.transcription'
MODEL_REPO = 'mlx-community/whisper-large-v3-turbo'
SOURCE = 'Local Whisper large-v3-turbo (MLX)'

# Model/tokenizer downloads happen during setup; no telemetry or cloud audio processing.
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['DO_NOT_TRACK'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(WORK / 'cache' / 'huggingface')
os.environ['TIKTOKEN_CACHE_DIR'] = str(WORK / 'cache' / 'tiktoken')


def log(message):
    print(f'{now()} {message}', flush=True)


def command(arguments, **kwargs):
    return subprocess.run(arguments, check=True, **kwargs)


def duration(path):
    result = command(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                      '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], capture_output=True, text=True)
    return float(result.stdout.strip())


def fetch_audio(item, directory):
    if item.get('audio_url') and not item['audio_url'].split('?', 1)[0].endswith('.m3u8'):
        path = directory / 'recording.mp3'
        command(['curl', '--fail', '--location', '--silent', '--show-error',
                 '--connect-timeout', '20', '--max-time', '600', '--retry', '2',
                 '--retry-delay', '10', '--max-filesize', '524288000',
                 '--output', str(path), item['audio_url']])
    elif item.get('audio_url') or item.get('video_url'):
        # Stream the source and retain only its audio; never save an MP4.
        path = directory / 'recording.wav'
        command(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                 '-rw_timeout', '30000000', '-i', item.get('audio_url') or item['video_url'],
                 '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(path)], timeout=900)
    else:
        raise ValueError('No direct audio or video source')
    actual = duration(path)
    expected = item['duration_ms']/1000
    if actual < 60 or abs(actual-expected) > max(60, expected*.1):
        raise ValueError(f'Unexpected audio duration: {actual:.1f}s versus manifest {expected:.1f}s')
    return path, actual


def sync(total, new_count):
    branch = command(['git', 'branch', '--show-current'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if branch != 'main':
        raise RuntimeError(f'Checkout changed to {branch}; refusing to commit the running job there')
    staged = command(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    if any(p != '.gitignore' and not p.startswith('transcripts/chris-mclaughlin/') for p in staged):
        raise RuntimeError('Unrelated staged files found; stopping rather than including them in a transcript commit')
    command(['git', 'diff', '--check'], cwd=ROOT)
    # Include only our collection and its ignored-workspace rule.
    command(['git', 'add', '--', '.gitignore', 'transcripts/chris-mclaughlin'], cwd=ROOT)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT)
    if changed.returncode not in (0, 1):
        raise RuntimeError('Could not inspect staged checkpoint changes')
    if changed.returncode == 1:
        command(['git', 'commit', '-m', f'Add {new_count} local sermon transcripts ({total}/99 collected)'], cwd=ROOT)
    # Keep the user's default account unchanged; use the existing owner sign-in only here.
    credential = command(['gh', 'auth', 'token', '--hostname', 'github.com', '--user', 'gmfennema'],
                         capture_output=True, text=True)
    environment = os.environ.copy()
    environment['GH_TOKEN'] = credential.stdout.strip()
    command(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
             'push', 'origin', 'main'], cwd=ROOT, env=environment)
    revision = command(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    log(f'SYNCED {total}/99 at {revision}')
    return revision


def committed_local_count():
    result = subprocess.run(['git', 'show', 'HEAD:transcripts/chris-mclaughlin/coverage.json'], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode:
        return 0
    return sum(r.get('transcript_source') == SOURCE for r in json.loads(result.stdout)['items'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, help='Stop after this many new transcripts')
    parser.add_argument('--sync', action='store_true', help='Commit/push every ten new transcripts and the final remainder')
    parser.add_argument('--checkpoint-size', type=int, default=10)
    args = parser.parse_args()
    if args.checkpoint_size < 1 or (args.limit is not None and args.limit < 1):
        parser.error('Limits must be positive')
    WORK.mkdir(exist_ok=True)
    lock = (WORK / 'worker.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another transcription worker is already running')
    setup = json.loads((WORK / 'model.json').read_text())
    model_path = Path(setup['path'])
    if not (model_path / 'config.json').exists():
        raise SystemExit('Download the local model before running this worker')
    import mlx_whisper
    import mlx.core as mx
    mx.random.seed(0)
    log(f'MODEL {setup["repo"]} revision={setup["revision"]}; local GPU processing')
    coverage = rebuild()
    done = {r['short_code'] for r in coverage['items'] if r['status'] == 'complete'}
    items = json.loads((BASE / 'manifest.json').read_text())['items']
    # Finish blocked caption matches first, then other Sunday sermons, then weekday teachings.
    queue = sorted((i for i in items if i['short_code'] not in done),
                   key=lambda i: (not bool(i.get('youtube_id')), not bool(i.get('video_url'))))
    synced_count = committed_local_count()
    initial_local = sum(r.get('transcript_source') == SOURCE for r in coverage['items'])
    completed, failures = 0, []
    state = {'pid': os.getpid(), 'started_at': now(), 'status': 'running', 'initial_local_transcripts': initial_local,
             'queue_count': len(queue), 'new_completed': 0, 'failures': failures, 'checkpoint_size': args.checkpoint_size}
    state_path = WORK / 'run.json'
    save_json(state_path, state)
    # A resumed run must push an already committed checkpoint before doing more work.
    if args.sync:
        ahead = command(['git', 'rev-list', '--count', 'origin/main..HEAD'], cwd=ROOT, capture_output=True, text=True)
        if int(ahead.stdout.strip()):
            sync(len(done), 0)
        if initial_local-synced_count >= args.checkpoint_size:
            sync(len(done), initial_local-synced_count)
            synced_count = initial_local
    try:
        for index, item in enumerate(queue, 1):
            state.update(current_id=item['short_code'], current_title=item['title'], stage='download', updated_at=now())
            save_json(state_path, state)
            log(f'START {index}/{len(queue)} {item["short_code"]} {item["title"]}')
            try:
                # The directory is removed even on an exception. Only one recording is stored at a time.
                with tempfile.TemporaryDirectory(prefix='audio-', dir=WORK) as directory:
                    audio, audio_seconds = fetch_audio(item, Path(directory))
                    state.update(stage='transcribe', audio_seconds=audio_seconds, updated_at=now())
                    save_json(state_path, state)
                    started = time.monotonic()
                    result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=str(model_path),
                             language='en', task='transcribe', verbose=None, word_timestamps=True,
                             condition_on_previous_text=False, hallucination_silence_threshold=2.0)
                    elapsed = time.monotonic()-started
                    segments = result['segments']
                    snippets = [{'start': float(s['start']), 'duration': float(s['end']-s['start']),
                                 'text': s['text'].strip(), 'avg_logprob': float(s['avg_logprob']),
                                 'no_speech_prob': float(s['no_speech_prob']),
                                 'compression_ratio': float(s['compression_ratio']),
                                 'temperature': float(s['temperature'])} for s in segments if s['text'].strip()]
                    words = sum(len(s['text'].split()) for s in snippets)
                    if not snippets or words < audio_seconds/60*20:
                        raise ValueError(f'Transcript unusually sparse: {words} words / {audio_seconds/60:.1f} minutes')
                    flags = []
                    if snippets[-1]['start'] + snippets[-1]['duration'] < audio_seconds-120:
                        flags.append('Transcript ends over two minutes before audio; possible silence or missed speech')
                    repeated = Counter(s['text'].lower() for s in snippets if len(s['text'].split()) >= 8)
                    if any(count >= 5 for count in repeated.values()):
                        flags.append('An identical segment occurs at least five times; review for repetition artifacts')
                    if any(s['avg_logprob'] < -1.0 for s in snippets):
                        flags.append('One or more segments have average decoder log probability below -1.0')
                    provenance = {'engine': 'mlx-whisper', 'engine_version': importlib.metadata.version('mlx-whisper'),
                                  'mlx_version': importlib.metadata.version('mlx'), 'model_repo': setup['repo'],
                                  'model_revision': setup['revision'], 'language': 'en', 'word_timestamps': True,
                                  'condition_on_previous_text': False, 'hallucination_silence_threshold': 2.0,
                                  'audio_duration_seconds': audio_seconds, 'processing_seconds': elapsed,
                                  'speed_multiple': audio_seconds/elapsed, 'audio_retained': False,
                                  'cloud_audio_processing': False, 'manually_corrected': False}
                    metadata = {**item, 'transcript_source': SOURCE,
                                'transcript_source_url': item.get('audio_url') or item['video_url'],
                                'language_code': 'en', 'transcribed_at': now(), 'transcription': provenance,
                                'quality_flags': flags, 'snippets': snippets}
                    metadata_path = BASE / 'items' / (stem(item) + '.json')
                    save_json(metadata_path, metadata)
                    try:
                        coverage = rebuild()
                    except Exception:
                        metadata_path.unlink(missing_ok=True)
                        raise
                    samples = [snippets[0]['text'], snippets[len(snippets)//2]['text'], snippets[-1]['text']]
                    log(f'COMPLETE {item["title"]}: {words} words, {elapsed:.1f}s, {audio_seconds/elapsed:.1f}x playback, flags={flags}')
                    log('SAMPLES ' + json.dumps(samples, ensure_ascii=False))
                log(f'AUDIO DELETED {item["short_code"]}')
                completed += 1
                state.update(new_completed=completed, stage='saved', updated_at=now())
                save_json(state_path, state)
            except Exception as exc:
                failure = {'id': item['short_code'], 'title': item['title'], 'error_type': type(exc).__name__, 'error': str(exc)[:1500], 'at': now()}
                failures.append(failure)
                coverage = json.loads((BASE / 'coverage.json').read_text())
                for r in coverage['items']:
                    if r['short_code'] == item['short_code'] and r['status'] != 'complete':
                        r.update(status='transcription_failed', error_type=failure['error_type'], error=failure['error'])
                save_json(BASE / 'coverage.json', coverage)
                coverage = rebuild()
                state.update(updated_at=now())
                save_json(state_path, state)
                log('FAILED ' + json.dumps(failure))
                if len(failures) >= 3 and completed == 0:
                    raise RuntimeError('Three initial failures; stopping to diagnose setup') from exc
                continue
            local_count = initial_local+completed
            total = coverage['status_counts'].get('complete', 0)
            if args.sync and local_count-synced_count >= args.checkpoint_size:
                state.update(stage='sync', updated_at=now())
                save_json(state_path, state)
                state['last_synced_commit'] = sync(total, local_count-synced_count)
                synced_count = local_count
                save_json(state_path, state)
            if args.limit is not None and completed >= args.limit:
                break
        if args.sync and initial_local+completed > synced_count:
            state['last_synced_commit'] = sync(coverage['status_counts'].get('complete', 0), initial_local+completed-synced_count)
        state.update(status='finished' if not failures else 'finished_with_failures', stage='done', updated_at=now())
        save_json(state_path, state)
        log(f'FINISHED new={completed}, failed={len(failures)}, total={coverage["status_counts"].get("complete", 0)}/99')
    except BaseException as exc:
        state.update(status='stopped', error_type=type(exc).__name__, error=str(exc)[:1500], updated_at=now())
        save_json(state_path, state)
        raise


if __name__ == '__main__':
    main()
