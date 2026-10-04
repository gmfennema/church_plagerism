#!/usr/bin/env python3
"""Collect captions for confirmed manifest matches; never download audio/video."""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[1] / 'tools'))
from fetch_transcripts import fetch_one, format_timestamp


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Rebuild from saved captions without network requests')
    parser.add_argument('--retry-failed', action='store_true', help='Retry failures after allowing YouTube limits to clear')
    args = parser.parse_args()
    items = json.loads((BASE / 'manifest.json').read_text())['items']
    assert len({item['short_code'] for item in items}) == len(items)
    output = BASE / 'items'
    output.mkdir(exist_ok=True)
    coverage_path = BASE / 'coverage.json'
    previous = {r['short_code']: r for r in json.loads(coverage_path.read_text())['items']} if coverage_path.exists() else {}
    blocked = False
    records = []
    for index, item in enumerate(items, 1):
        record = {**item, 'status': 'no_confirmed_youtube_match'}
        if item.get('youtube_id'):
            slug = re.sub(r'[^a-z0-9]+', '-', item['title'].lower()).strip('-')
            stem = f"{item['date'][:10]}_{item['short_code']}_{slug}"
            metadata = output / (stem + '.json')
            target = output / (stem + '.txt')
            if not metadata.exists() and (args.offline or blocked or (item['short_code'] in previous and not args.retry_failed)):
                record = previous.get(item['short_code'], {**item, 'status': 'not_attempted'})
                records.append(record)
                continue
            try:
                if metadata.exists():
                    fetched = json.loads(metadata.read_text())
                else:
                    fetched = fetch_one(item['youtube_id'], ['en', 'en-US', 'en-GB'])
                    fetched['fetched_at'] = datetime.now(timezone.utc).isoformat()
                    if not fetched['snippets'] or not any(s['text'].strip() for s in fetched['snippets']):
                        raise ValueError('Empty caption track')
                    save_json(metadata, {**item, **fetched})
                    time.sleep(10)
                source = 'YouTube auto captions' if fetched['is_generated'] else 'YouTube human captions'
                header = [f"Title: {item['title']}", f"Date: {item['date'][:10]}",
                          f"Speaker: {item['speaker']}", f"Passage: {item.get('scripture', '')}",
                          f"Item ID: {item['short_code']}", f"Church URL: {item['site_url']}",
                          f"Source URL: {item['youtube_url']}", f"Transcript source: {source}",
                          f"Language: {fetched['language_code']}", f"Fetched: {fetched['fetched_at']}"]
                body = [f"[{format_timestamp(s['start'])}] {s['text'].strip()}" for s in fetched['snippets'] if s['text'].strip()]
                target.write_text('\n'.join(header) + '\n\n' + '\n'.join(body) + '\n', encoding='utf-8')
                record.update(status='complete', transcript_file=str(target.relative_to(BASE)),
                              caption_file=str(metadata.relative_to(BASE)), transcript_source=source,
                              snippet_count=len(body), word_count=sum(len(s['text'].split()) for s in fetched['snippets']),
                              first_timestamp=fetched['snippets'][0]['start'],
                              last_timestamp=fetched['snippets'][-1]['start'])
                print(f"[{index}/{len(items)}] complete: {item['title']}", flush=True)
            except Exception as exc:
                record.update(status='caption_fetch_failed', error_type=type(exc).__name__, error=str(exc)[:1000])
                print(f"[{index}/{len(items)}] {type(exc).__name__}: {item['title']}", flush=True)
                if type(exc).__name__ in {'IpBlocked', 'RequestBlocked', 'TooManyRequests'}:
                    blocked = True
                    print('YouTube blocked requests; stopping network access for this run.', flush=True)
                time.sleep(3)
        records.append(record)
        save_json(BASE / 'coverage.json', {'generated_at': datetime.now(timezone.utc).isoformat(), 'items': records})

    complete = sorted((r for r in records if r['status'] == 'complete'), key=lambda r: (r['date'], r['short_code']))
    counts = {status: sum(r['status'] == status for r in records) for status in sorted({r['status'] for r in records})}
    combined = ['CHRIS MCLAUGHLIN — CAPTION TRANSCRIPT COLLECTION',
                f"Included: {len(complete)} of {len(items)} manifest recordings.",
                'Scope: English captions from confirmed YouTube matches only; audio transcription is pending.',
                'Captions are preserved as retrieved and may contain recognition errors.',
                'See coverage.json for omitted recordings and fetch errors.', '', 'CONTENTS']
    for n, record in enumerate(complete, 1):
        combined.append(f"{n:03d} | {record['short_code']} | {record['date'][:10]} | {record['title']}")
    for n, record in enumerate(complete, 1):
        marker = f"SERMON {n:03d} | {record['short_code']}"
        combined.extend(['', '=' * 80, f'START {marker}', '=' * 80,
                         (BASE / record['transcript_file']).read_text().rstrip(),
                         '=' * 80, f'END {marker}', '=' * 80])
    (BASE / 'chris-mclaughlin-all.txt').write_text('\n'.join(combined) + '\n', encoding='utf-8')
    save_json(BASE / 'coverage.json', {'generated_at': datetime.now(timezone.utc).isoformat(),
                                     'manifest_count': len(items), 'status_counts': counts,
                                     'transcript_word_count': sum(r['word_count'] for r in complete), 'items': records})
    report = ['# Caption coverage', '', f'Manifest recordings: {len(items)}',
              f'Completed captions: {len(complete)}', '',
              '| Date | ID | Title | Status |', '|---|---|---|---|']
    report.extend(f"| {r['date'][:10]} | {r['short_code']} | {r['title'].replace('|', '/')} | {r['status']} |" for r in sorted(records, key=lambda r: r['date']))
    (BASE / 'coverage.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print(json.dumps(counts), flush=True)


if __name__ == '__main__':
    main()
