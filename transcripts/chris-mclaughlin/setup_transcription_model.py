#!/usr/bin/env python3
"""Download the pinned local model; audio is never sent to a model service."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.transcription'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['DO_NOT_TRACK'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['HF_HOME'] = str(WORK / 'cache' / 'huggingface')

from huggingface_hub import snapshot_download

repo = 'mlx-community/whisper-large-v3-turbo'
revision = 'a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb'
path = snapshot_download(repo, revision=revision, local_dir=str(WORK / 'models' / 'large-v3-turbo'),
                         allow_patterns=['config.json', 'weights.npz', '*.safetensors'])
(WORK / 'model.json').write_text(json.dumps({'repo': repo, 'revision': revision, 'path': str(Path(path).resolve())}, indent=2) + '\n')
print(f'Local model ready: {repo} at {revision}')
