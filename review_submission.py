"""Read-only validation of untrusted community ZIP submissions.

Runs on trusted default-branch source. Never extracts or executes ZIP content,
and never publishes preset content. The GitHub token can comment/label only.
"""
from __future__ import annotations

import io
import ipaddress
import json
import ntpath
import os
import re
import urllib.parse
import urllib.request
import zipfile

from verify_catalog import exactly, valid_text, validate_action

MAX_ZIP = 1024 * 1024
MAX_PRESET = 512 * 1024
REVIEW_MARKER = '<!-- shortcutmanager-review-v1 -->'
ATTACHMENT = re.compile(
  r'https://github\.com/user-attachments/files/[0-9]+/'
  r'[A-Za-z0-9_.-]+\.zip(?=[)\s]|$)', re.I,
)
ISSUE_STATUSES = frozenset((
  'pending-review', 'changes-requested', 'approved', 'published',
))
CHECK = re.compile(r'^\s*-\s*\[x\]\s+', re.I | re.M)


def strict_pairs(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('Duplicate JSON field.')
    result[key] = value
  return result


def load_submission(zip_bytes: bytes) -> dict:
  if len(zip_bytes) > MAX_ZIP:
    raise ValueError('ZIP exceeds the 1 MiB submission limit.')
  try:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
      entries = archive.infolist()
      if len(entries) != 1 or entries[0].filename != 'preset.json':
        raise ValueError('ZIP must contain exactly one preset.json.')
      entry = entries[0]
      if entry.is_dir() or entry.file_size > MAX_PRESET:
        raise ValueError('Preset JSON is too large or is not a file.')
      if entry.flag_bits & 1:
        raise ValueError('Encrypted presets are not accepted.')
      # No extractall/extract, and verify size a second time after decompression.
      with archive.open(entry) as file:
        raw = file.read(MAX_PRESET + 1)
  except (zipfile.BadZipFile, RuntimeError, EOFError, OSError) as error:
    raise ValueError('ZIP cannot be opened safely.') from error
  if len(raw) > MAX_PRESET:
    raise ValueError('Preset JSON exceeds 512 KiB.')
  try:
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=strict_pairs)
  except (UnicodeError, json.JSONDecodeError) as error:
    raise ValueError('Malformed JSON.') from error
  exactly(data, {
    'format', 'version', 'name', 'author', 'description', 'items',
  })
  if (
    data['format'] != 'shortcutmanager-presets'
    or type(data['version']) is not int or data['version'] not in (1, 2)
    or not isinstance(data['items'], list) or not data['items']
  ):
    raise ValueError('Unsupported preset format or version.')
  for key in ('name', 'author'):
    valid_text(data[key], key)
  valid_text(data['description'], 'description', blank=True)
  counts = [0]
  for node in data['items']:
    validate_action(node, 1, counts, data['version'])
  return data


def _action_issues(action: dict, number: int) -> list[str]:
  problems = []
  kind = action['type']
  if kind == 'portable_app':
    # Custom identities are deliberately pathless and cannot launch until
    # the recipient explicitly maps a matching local EXE. This is not a
    # technical rejection: the human reviewer still assesses the app intent.
    return problems
  target = action['target']
  if kind == 'open_url':
    parsed = urllib.parse.urlsplit(target)
    host = parsed.hostname or ''
    try:
      ip = ipaddress.ip_address(host)
    except ValueError:
      ip = None
    if (
      host.lower() in ('localhost', 'localhost.localdomain')
      or host.lower().endswith(('.local', '.internal', '.localhost'))
      or (ip is not None and not ip.is_global)
    ):
      problems.append(f'Action {number}: local/private URL is not portable.')
    if re.search(r'(?i)(token|api[_-]?key|password|passwd|secret|session|auth)=', target):
      problems.append(f'Action {number}: URL may contain credentials.')
  else:
    method = action['launch_method']
    if method in ('path', 'squirrel'):
      problems.append(
        f'Action {number}: absolute application path must be replaced '
        'with a portable identity.'
      )
    if method not in ('path', 'squirrel', 'aumid', 'appsfolder'):
      problems.append(f'Action {number}: unsupported launch method.')
    if action['match_method'] not in ('path', 'squirrel', 'aumid'):
      problems.append(f'Action {number}: unsupported match method.')
    if ntpath.isabs(action['match_value']):
      problems.append(f'Action {number}: local window-match path.')
    for field in ('launch_argument', 'match_executable'):
      value = action.get(field, '')
      if re.search(r'(?i)[A-Z]:[\\/]|\\\\[^\\]+\\[^\\]+|%USERPROFILE%', value):
        problems.append(f'Action {number}: local path in {field}.')
      if re.search(r'(?i)(token|api[_-]?key|password|passwd|secret)\s*[:=]', value):
        problems.append(f'Action {number}: possible credentials in {field}.')
    if re.search(
      r'(?i)(^|\s)(/c|-command|-enc(?:odedcommand)?|--exec)(\s|$)',
      action['launch_argument'],
    ):
      problems.append(f'Action {number}: command-launch arguments require review.')
  return problems


def analyze(body: str, zip_bytes: bytes | None, download_error: str = '') -> tuple[str, list[str], int]:
  """Return ('changes-requested'|'pending-review', notes, action count)."""
  notes = []
  if len(CHECK.findall(body)) < 4:
    notes.append('The four publication/security consent checkboxes are not all checked.')
  match = re.search(r'(?ms)^## Description\s*\n(.*?)(?=^## |\Z)', body)
  description = match.group(1).strip() if match else ''
  if not description or description == 'What does the preset do, and who is it useful for?':
    notes.append('Please describe what the collection does and who it is useful for.')
  if download_error:
    notes.append('Attachment could not be verified (temporary download error).')
    return 'pending-review', notes, 0
  if zip_bytes is None:
    notes.append('Attach exactly one ZIP via the GitHub issue editor.')
    return 'changes-requested', notes, 0
  try:
    data = load_submission(zip_bytes)
  except (ValueError, TypeError, KeyError) as error:
    notes.append(f'Package validation failed: {error}')
    return 'changes-requested', notes, 0
  count = 0
  seen_hotkeys = set()

  def walk(items):
    nonlocal count
    for node in items:
      if node['kind'] == 'folder':
        walk(node['items'])
      else:
        count += 1
        notes.extend(_action_issues(node['action'], count))
        hotkey = node['suggested_hotkey']
        if hotkey is not None:
          normalized = hotkey.strip().casefold()
          if normalized in seen_hotkeys:
            notes.append(f'Action {count}: duplicate suggested hotkey (review order).')
          seen_hotkeys.add(normalized)

  walk(data['items'])
  return ('changes-requested' if notes else 'pending-review'), notes, count


def _request(url: str, *, token: str | None = None, method: str = 'GET', data=None, max_bytes: int | None = None):
  headers = {
    'User-Agent': 'ShortcutManager-Preset-Reviewer',
    'Accept': 'application/vnd.github+json' if 'api.github.com' in url else 'application/octet-stream',
  }
  if token and 'api.github.com' in url:
    headers['Authorization'] = f'Bearer {token}'
    headers['X-GitHub-Api-Version'] = '2022-11-28'
  payload = json.dumps(data).encode('utf-8') if data is not None else None
  if payload is not None:
    headers['Content-Type'] = 'application/json'
  with urllib.request.urlopen(
    urllib.request.Request(url, headers=headers, data=payload, method=method),
    timeout=25,
  ) as response:
    content = response.read((max_bytes + 1) if max_bytes is not None else -1)
  if max_bytes is not None and len(content) > max_bytes:
    raise ValueError('ZIP download exceeds size limit.')
  return json.loads(content) if 'api.github.com' in url else content


def review_issue(repo: str, issue_number: int, token: str) -> None:
  base = f'https://api.github.com/repos/{repo}/issues/{issue_number}'
  issue = _request(base, token=token)
  if 'pull_request' in issue or issue['state'] != 'open':
    return
  labels = {label['name'] for label in issue.get('labels', [])}
  if 'published' in labels:
    return
  body = issue.get('body') or ''
  attachments = ATTACHMENT.findall(body)
  error = ''
  zip_bytes = None
  if len(attachments) == 1:
    try:
      zip_bytes = _request(attachments[0], max_bytes=MAX_ZIP)
    except (OSError, ValueError, TimeoutError) as exc:
      error = f'{type(exc).__name__}'  # Never expose URLs/credentials in comments.
  status, notes, count = analyze(body, zip_bytes, error)
  if len(attachments) > 1:
    status = 'changes-requested'
    notes.append('Multiple ZIP attachments found. Keep one current submission.')
  lines = [
    REVIEW_MARKER,
    '### Automated ShortcutManager submission check',
    '',
    f'**Technical status:** {status}',
    f'**Validated actions:** {count}',
    '',
    'This is an automated data-only check; no submitted code was executed.',
    'It is **not** a safety guarantee or a publication approval.',
    '',
  ]
  if notes:
    lines.extend(['**Follow-ups:**', *[f'- {note}' for note in notes]])
  else:
    lines.append(
      'Technical checks passed. Awaiting human/AI content review '
      'and explicit maintainer approval.'
    )
  lines.extend([
    '',
    'No preset will be published or merged by this workflow.',
  ])
  report = '\n'.join(lines)
  comments = _request(base + '/comments?per_page=100', token=token)
  own_comment = next(
    (comment for comment in comments
     if REVIEW_MARKER in (comment.get('body') or '')
     and comment.get('user', {}).get('type') == 'Bot'),
    None,
  )
  if own_comment is None:
    _request(base + '/comments', token=token, method='POST', data={'body': report})
  else:
    _request(
      f'https://api.github.com/repos/{repo}/issues/comments/{own_comment["id"]}',
      token=token, method='PATCH', data={'body': report},
    )
  # Create missing status labels in the trusted repository if necessary.
  labels_base = f'https://api.github.com/repos/{repo}/labels'
  known = {
    label['name'] for label in _request(labels_base + '?per_page=100', token=token)
  }
  if status not in known:
    _request(labels_base, token=token, method='POST', data={
      'name': status,
      'color': 'd97706' if status == 'changes-requested' else 'bfd4f2',
      'description': 'Technical submission review status',
    })
  next_labels = (labels - ISSUE_STATUSES) | {status}
  _request(base + '/labels', token=token, method='PUT', data={
    'labels': sorted(next_labels),
  })


def main() -> None:
  repo = os.environ['GITHUB_REPOSITORY']
  token = os.environ['GITHUB_TOKEN']
  event = json.load(open(os.environ['GITHUB_EVENT_PATH'], encoding='utf-8'))
  issue = event.get('issue')
  number = (
    issue.get('number') if isinstance(issue, dict)
    else os.environ.get('REVIEW_ISSUE_NUMBER')
  )
  if not number or not str(number).isdigit() or int(number) <= 0:
    raise ValueError('A valid issue number is required.')
  review_issue(repo, int(number), token)


if __name__ == '__main__':
  main()
