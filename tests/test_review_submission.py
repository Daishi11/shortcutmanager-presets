from __future__ import annotations

import io
import json
import unittest
import zipfile

from review_submission import analyze, load_submission


BASE_ISSUE = (
  '## Description\n'
  'Open a few public development resources with keyboard shortcuts.\n\n'
  '## Security and publication review\n'
  '- [x] Checked targets\n'
  '- [x] Public submission understood\n'
  '- [x] Publication authorized\n'
  '- [x] No scripts or secrets\n'
)


def sample(action=None):
  return {
    'format': 'shortcutmanager-presets',
    'version': 1,
    'name': 'Public URLs',
    'author': 'Test author',
    'description': 'Useful links',
    'items': [{
      'kind': 'action',
      'name': 'Website',
      'suggested_hotkey': None,
      'action': action or {
        'type': 'open_url', 'target': 'https://example.org',
      },
    }],
  }


def zipped(payload, filename='preset.json'):
  with io.BytesIO() as memory:
    with zipfile.ZipFile(memory, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
      archive.writestr(filename, payload)
    return memory.getvalue()


def packet(obj=None):
  return zipped(json.dumps(obj if obj is not None else sample()))


class SubmissionValidationTests(unittest.TestCase):
  def test_valid_url_preset_reaches_manual_review(self):
    status, notes, actions = analyze(BASE_ISSUE, packet())
    self.assertEqual(status, 'pending-review')
    self.assertEqual(actions, 1)
    self.assertEqual(notes, [])

  def test_missing_publisher_attestation_requests_changes(self):
    issue = BASE_ISSUE.replace('[x]', '[ ]', 1)
    status, notes, _ = analyze(issue, packet())
    self.assertEqual(status, 'changes-requested')
    self.assertTrue(any('checkboxes' in note for note in notes))

  def test_missing_description_requests_changes(self):
    issue = BASE_ISSUE.replace(
      'Open a few public development resources with keyboard shortcuts.',
      'What does the preset do, and who is it useful for?',
    )
    status, notes, _ = analyze(issue, packet())
    self.assertEqual(status, 'changes-requested')
    self.assertTrue(any('describe' in note for note in notes))

  def test_windows_app_path_rejected_as_nonportable(self):
    action = {
      'type': 'focus_or_launch',
      'target': 'E:\\Spiele\\Steam\\steam.exe',
      'launch_method': 'path',
      'launch_argument': '',
      'match_method': 'path',
      'match_value': 'E:\\Spiele\\Steam\\steam.exe',
    }
    status, notes, count = analyze(BASE_ISSUE, packet(sample(action)))
    self.assertEqual(status, 'changes-requested')
    self.assertEqual(count, 1)
    self.assertTrue(any('portable identity' in note for note in notes))

  def test_windows_aumid_still_requires_human_approval(self):
    action = {
      'type': 'focus_or_launch',
      'target': 'Microsoft.WindowsCalculator_8wekyb3d8bbwe!App',
      'launch_method': 'aumid',
      'launch_argument': '',
      'match_method': 'aumid',
      'match_value': 'Microsoft.WindowsCalculator_8wekyb3d8bbwe!App',
    }
    status, notes, count = analyze(BASE_ISSUE, packet(sample(action)))
    self.assertEqual((status, notes, count), ('pending-review', [], 1))

  def test_reject_zip_with_directory_traversal(self):
    with self.assertRaisesRegex(ValueError, 'exactly one'):
      load_submission(zipped(json.dumps(sample()), '../preset.json'))

  def test_reject_zip_with_additional_files(self):
    with io.BytesIO() as memory:
      with zipfile.ZipFile(memory, 'w') as archive:
        archive.writestr('preset.json', json.dumps(sample()))
        archive.writestr('extra.txt', 'unexpected')
      content = memory.getvalue()
    with self.assertRaisesRegex(ValueError, 'exactly one'):
      load_submission(content)

  def test_reject_duplicate_json_keys(self):
    with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
      load_submission(zipped(
        '{"format":"shortcutmanager-presets","format":"duplicate"}',
      ))

  def test_reject_oversized_zip(self):
    with self.assertRaisesRegex(ValueError, '1 MiB'):
      load_submission(b'0' * (1024 * 1024 + 1))

  def test_local_private_url_is_not_a_public_preset(self):
    preset = sample({'type': 'open_url', 'target': 'http://127.0.0.1:8080'})
    status, notes, _ = analyze(BASE_ISSUE, packet(preset))
    self.assertEqual(status, 'changes-requested')
    self.assertTrue(any('private URL' in note for note in notes))

  def test_download_error_is_not_blamed_on_contributor(self):
    status, notes, _ = analyze(BASE_ISSUE, None, 'TimeoutError')
    self.assertEqual(status, 'pending-review')
    self.assertTrue(any('temporary download' in note for note in notes))

  def test_unsupported_action_rejected(self):
    preset = sample({'type': 'run_script', 'target': 'calc.exe'})
    status, notes, _ = analyze(BASE_ISSUE, packet(preset))
    self.assertEqual(status, 'changes-requested')
    self.assertTrue(any('Package validation failed' in note for note in notes))


if __name__ == '__main__':
  unittest.main()
