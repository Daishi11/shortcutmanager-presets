"""Standalone public-repo integrity check (no private app imports)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
PATH = re.compile(r'presets/(?:[A-Za-z0-9_-]+/){0,3}[A-Za-z0-9_-]+\.json')
ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
DIGEST = re.compile(r'[0-9a-f]{64}')
EXE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.exe', re.I)
BLOCKED_EXE = frozenset((
  'cmd.exe', 'powershell.exe', 'pwsh.exe', 'wscript.exe',
  'cscript.exe', 'mshta.exe', 'rundll32.exe', 'reg.exe',
  'regsvr32.exe', 'schtasks.exe', 'wmic.exe',
))
MAX_FILE = 512 * 1024
MAX_INDEX = 128 * 1024


def strict_pairs(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError(f'Duplicate JSON key: {key}')
    result[key] = value
  return result


def read(path: Path, max_size: int):
  data = path.read_bytes()
  if len(data) > max_size:
    raise ValueError(f'File too large: {path}')
  return json.loads(data.decode('utf-8'), object_pairs_hook=strict_pairs), data


def exactly(obj, keys: set[str]) -> None:
  if not isinstance(obj, dict) or set(obj) != keys:
    raise ValueError(f'Invalid JSON fields: expected {sorted(keys)}')


def valid_text(value, label, blank=False):
  if (not isinstance(value, str) or len(value) > 3000
      or (not blank and not value.strip())):
    raise ValueError(f'Invalid {label}')


def validate_action(node, depth, counts, package_version=1):
  counts[0] += 1
  if counts[0] > 250 or depth > 10:
    raise ValueError('Preset is too large or deeply nested.')
  if not isinstance(node, dict):
    raise ValueError('Invalid preset node.')
  if node.get('kind') == 'folder':
    exactly(node, {'kind', 'name', 'items'})
    valid_text(node['name'], 'folder name')
    if not isinstance(node['items'], list):
      raise ValueError('Folder items must be a list.')
    for child in node['items']:
      validate_action(child, depth + 1, counts, package_version)
    return
  exactly(node, {'kind', 'name', 'suggested_hotkey', 'action'})
  if node['kind'] != 'action':
    raise ValueError('Unsupported preset node.')
  valid_text(node['name'], 'action name')
  hotkey = node['suggested_hotkey']
  if hotkey is not None:
    valid_text(hotkey, 'hotkey suggestion')
  action = node['action']
  if not isinstance(action, dict):
    raise ValueError('Invalid action.')
  kind = action.get('type')
  if kind == 'portable_app':
    if package_version != 2:
      raise ValueError('Portable app actions require package version 2.')
    exactly(action, {'type', 'app_id', 'executable', 'behavior'})
    app_id = action['app_id']
    executable = action['executable']
    if (not isinstance(app_id, str)
        or app_id not in ('steam', 'discord', 'custom')
        or not isinstance(executable, str)
        or not EXE.fullmatch(executable)
        or executable.casefold() in BLOCKED_EXE
        or (app_id == 'steam' and executable.casefold() != 'steam.exe')
        or (app_id == 'discord' and executable.casefold() != 'discord.exe')
        or action['behavior'] not in ('launch_app', 'focus_or_launch')):
      raise ValueError('Invalid portable application identity.')
  elif kind == 'open_url':
    exactly(action, {'type', 'target'})
    try:
      url = urlsplit(action['target'])
      valid = (
        url.scheme in ('http', 'https') and bool(url.hostname)
        and not any(ch.isspace() for ch in action['target'])
      )
    except (TypeError, ValueError):
      valid = False
    if not valid:
      raise ValueError('Only HTTP(S) links are allowed.')
  elif kind in ('launch_app', 'focus_or_launch'):
    required = {
      'type', 'target', 'launch_method', 'launch_argument',
      'match_method', 'match_value',
    }
    if set(action) not in (required, required | {'match_executable'}):
      raise ValueError('Invalid application action fields.')
    for key in required - {'type'}:
      if not isinstance(action[key], str):
        raise ValueError(f'Invalid app action {key}.')
    valid_text(action['target'], 'app launch target')
    if 'match_executable' in action and not isinstance(
      action['match_executable'], str,
    ):
      raise ValueError('Invalid match_executable.')
    # App path safety requires human review before publication.
  else:
    raise ValueError('Scripts or unsupported preset actions are not allowed.')


def validate() -> int:
  index, _ = read(ROOT / 'index.json', MAX_INDEX)
  exactly(index, {'format', 'version', 'presets'})
  if (index['format'] != 'shortcutmanager-catalog'
      or type(index['version']) is not int or index['version'] != 1
      or not isinstance(index['presets'], list)
      or len(index['presets']) > 200):
    raise ValueError('Invalid catalog format/version/count.')

  names = set()
  paths = set()
  for row in index['presets']:
    exactly(row, {
      'id', 'name', 'author', 'description',
      'version', 'path', 'sha256',
    })
    if (
      not isinstance(row['id'], str) or not ID.fullmatch(row['id'])
      or len(row['id']) > 100
      or row['id'] in names
    ):
      raise ValueError('Invalid/duplicate preset ID.')
    names.add(row['id'])
    for field in ('name', 'author', 'version'):
      valid_text(row[field], field)
    valid_text(row['description'], 'description', blank=True)
    relative = row['path']
    if (not isinstance(relative, str)
        or not PATH.fullmatch(relative) or relative in paths):
      raise ValueError('Invalid/duplicate preset path.')
    paths.add(relative)
    if (not isinstance(row['sha256'], str)
        or not DIGEST.fullmatch(row['sha256'])):
      raise ValueError('Invalid SHA-256.')
    preset, content = read(ROOT / relative, MAX_FILE)
    if hashlib.sha256(content).hexdigest() != row['sha256']:
      raise ValueError(f'Preset hash mismatch: {relative}')
    exactly(preset, {
      'format', 'version', 'name', 'author', 'description', 'items',
    })
    if (preset['format'] != 'shortcutmanager-presets'
        or type(preset['version']) is not int or preset['version'] not in (1, 2)
        or not isinstance(preset['items'], list) or not preset['items']):
      raise ValueError(f'Invalid preset package: {relative}')
    if any(preset[field] != row[field] for field in (
      'name', 'author', 'description',
    )):
      raise ValueError(f'Preset metadata mismatch: {relative}')
    counts = [0]
    for node in preset['items']:
      validate_action(node, 1, counts, preset['version'])

  files = {
    str(path.relative_to(ROOT)).replace('\\', '/')
    for path in (ROOT / 'presets').rglob('*.json')
  }
  if files != paths:
    raise ValueError('Unindexed preset files found or index is incomplete.')
  print(f'Validated {len(index["presets"])} public preset collection(s).')
  return 0


if __name__ == '__main__':
  try:
    raise SystemExit(validate())
  except (ValueError, OSError, UnicodeError) as error:
    print(f'Catalog validation failed: {error}')
    raise SystemExit(1) from error
