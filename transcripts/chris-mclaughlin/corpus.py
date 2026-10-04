"""Shared, offline assembly and integrity checks for the sermon corpus."""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def save_text(path, text):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)


def save_json(path, value):
    save_text(path, json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def stem(item):
    slug = re.sub(r'[^a-z0-9]+', '-', item['title'].lower()).strip('-')
    return f"{item['date'][:10]}_{item['short_code']}_{slug}"


def timestamp(seconds):
    total_ms = round(seconds * 1000)
    ms = total_ms % 1000
    s = total_ms // 1000
    return f'{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}.{ms:03d}'


def source(metadata):
    return metadata.get('transcript_source') or ('YouTube auto captions' if metadata['is_generated'] else 'YouTube human captions')


def write_item(item, metadata):
    segments = metadata['snippets']
    if not segments or not any(s['text'].strip() for s in segments):
        raise ValueError(f"Empty transcript: {item['short_code']}")
    if not all(s['start'] >= 0 and s['duration'] >= 0 for s in segments):
        raise ValueError(f"Invalid timestamps: {item['short_code']}")
    if not all(segments[i]['start'] <= segments[i+1]['start'] for i in range(len(segments)-1)):
        raise ValueError(f"Unordered timestamps: {item['short_code']}")
    transcript_source = source(metadata)
    source_url = metadata.get('transcript_source_url') or item['youtube_url']
    header = [f"Title: {item['title']}", f"Date: {item['date'][:10]}",
              f"Speaker: {item['speaker']}", f"Passage: {item.get('scripture', '')}",
              f"Item ID: {item['short_code']}", f"Church URL: {item['site_url']}",
              f"Source URL: {source_url}", f"Transcript source: {transcript_source}",
              f"Language: {metadata['language_code']}",
              f"Fetched: {metadata.get('fetched_at') or metadata.get('transcribed_at')}"]
    if metadata.get('transcription'):
        provenance = metadata['transcription']
        header.extend([f"Model: {provenance['model_repo']}", f"Model revision: {provenance['model_revision']}",
                       'Machine transcription; not manually corrected.'])
    body = '\n'.join(f"[{timestamp(s['start'])}] {s['text'].strip()}" for s in segments if s['text'].strip()) + '\n'
    path = BASE / 'items' / (stem(item) + '.txt')
    save_text(path, '\n'.join(header) + '\n\n' + body)
    return path, body


def rebuild():
    items = json.loads((BASE / 'manifest.json').read_text())['items']
    assert len({i['short_code'] for i in items}) == len(items)
    coverage_path = BASE / 'coverage.json'
    previous = {r['short_code']: r for r in json.loads(coverage_path.read_text())['items']} if coverage_path.exists() else {}
    records, samples = [], []
    (BASE / 'items').mkdir(exist_ok=True)
    for item in items:
        metadata_path = BASE / 'items' / (stem(item) + '.json')
        if not metadata_path.exists():
            records.append(previous.get(item['short_code'], {**item, 'status': 'pending'}))
            continue
        metadata = json.loads(metadata_path.read_text())
        assert metadata['short_code'] == item['short_code']
        target, body = write_item(item, metadata)
        segments = metadata['snippets']
        record = {**item, 'status': 'complete', 'transcript_file': str(target.relative_to(BASE)),
                  'metadata_file': str(metadata_path.relative_to(BASE)), 'transcript_source': source(metadata),
                  'snippet_count': sum(bool(s['text'].strip()) for s in segments),
                  'word_count': sum(len(s['text'].split()) for s in segments),
                  'first_timestamp': segments[0]['start'], 'last_timestamp': segments[-1]['start']}
        if not metadata.get('transcription'):
            record['caption_file'] = str(metadata_path.relative_to(BASE))
        else:
            record['transcription'] = metadata['transcription']
            record['quality_flags'] = metadata.get('quality_flags', [])
        records.append(record)
        samples.append({'id': item['short_code'], 'title': item['title'],
                        'first': segments[0]['text'], 'middle': segments[len(segments)//2]['text'], 'last': segments[-1]['text'],
                        'transcript_end_seconds': segments[-1]['start'] + segments[-1]['duration'],
                        'archive_duration_seconds': item['duration_ms']/1000})
        assert target.read_text().split('\n\n', 1)[1] == body

    complete = sorted((r for r in records if r['status'] == 'complete'), key=lambda r: (r['date'], r['short_code']))
    counts = dict(sorted(Counter(r['status'] for r in records).items()))
    sources = dict(sorted(Counter(r['transcript_source'] for r in complete).items()))
    lines = ['CHRIS MCLAUGHLIN — SERMON TRANSCRIPT COLLECTION',
             f"Included: {len(complete)} of {len(items)} manifest recordings.",
             'Sources: YouTube captions and locally generated machine transcriptions; see each recording header.',
             'Text is preserved as generated and may contain recognition errors; consequential quotations require audio verification.',
             'See coverage.json for omitted recordings and processing errors.', '', 'CONTENTS']
    for n, r in enumerate(complete, 1):
        lines.append(f"{n:03d} | {r['short_code']} | {r['date'][:10]} | {r['title']}")
    for n, r in enumerate(complete, 1):
        marker = f"SERMON {n:03d} | {r['short_code']}"
        text = (BASE / r['transcript_file']).read_text().rstrip()
        lines.extend(['', '='*80, f'START {marker}', '='*80, text, '='*80, f'END {marker}', '='*80])
    combined = '\n'.join(lines) + '\n'
    assert combined.count('\nSTART SERMON ') == combined.count('\nEND SERMON ') == len(complete)
    assert all((BASE / r['transcript_file']).read_text().rstrip() in combined for r in complete)
    save_text(BASE / 'chris-mclaughlin-all.txt', combined)
    coverage = {'generated_at': now(), 'manifest_count': len(items), 'status_counts': counts,
                'transcript_sources': sources, 'transcript_word_count': sum(r['word_count'] for r in complete), 'items': records}
    save_json(coverage_path, coverage)
    report = ['# Transcript coverage', '', f'Manifest recordings: {len(items)}', f'Completed transcripts: {len(complete)}',
              f"Sources: {json.dumps(sources, ensure_ascii=False)}", '',
              'Machine transcripts are not manually corrected. See verification.json for integrity checks and text samples.', '',
              '| Date | ID | Title | Status | Transcript source |', '|---|---|---|---|---|']
    report.extend(f"| {r['date'][:10]} | {r['short_code']} | {r['title'].replace('|', '/')} | {r['status']} | {r.get('transcript_source', '')} |" for r in sorted(records, key=lambda r: r['date']))
    save_text(BASE / 'coverage.md', '\n'.join(report) + '\n')
    save_json(BASE / 'verification.json', {'verified_transcripts': len(complete), 'matching_start_end_boundaries': True,
              'all_individual_files_in_combined': True, 'timestamps_monotonic': True, 'caption_segments_preserved_exactly': True,
              'combined_bytes': len(combined.encode()), 'transcript_words': coverage['transcript_word_count'],
              'combined_sha256': hashlib.sha256(combined.encode()).hexdigest(),
              'duration_discrepancies_over_10_percent_or_60_seconds': [s['id'] for s in samples if abs(s['transcript_end_seconds']-s['archive_duration_seconds']) > max(60, s['archive_duration_seconds']*.1)],
              'verification_scope': 'Structural and text-sample checks. Not a manual word-for-word audio verification. Names and references may be misrecognized.',
              'text_samples': samples})
    return coverage


if __name__ == '__main__':
    print(json.dumps(rebuild()['status_counts']))
