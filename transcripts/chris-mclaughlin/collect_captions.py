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
from corpus import rebuild


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Rebuild from saved captions without network requests')
    parser.add_argument('--retry-failed', action='store_true', help='Retry failures after allowing YouTube limits to clear')
    parser.add_argument('--request-delay', type=float, default=60, help='Seconds between new caption requests (default: 60)')
    args = parser.parse_args()
    if args.request_delay < 0:
        parser.error('--request-delay must be nonnegative')
    if args.offline:
        print(json.dumps(rebuild()['status_counts']))
        return
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
                    if fetched.get('transcription'):
                        records.append(previous[item['short_code']])
                        continue
                else:
                    fetched = fetch_one(item['youtube_id'], ['en', 'en-US', 'en-GB'])
                    fetched['fetched_at'] = datetime.now(timezone.utc).isoformat()
                    if not fetched['snippets'] or not any(s['text'].strip() for s in fetched['snippets']):
                        raise ValueError('Empty caption track')
                    save_json(metadata, {**item, **fetched})
                    time.sleep(args.request_delay)
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

    print(json.dumps(rebuild()['status_counts']), flush=True)


if __name__ == '__main__':
    main()
