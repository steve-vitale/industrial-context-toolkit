"""Fetching an acquired group by pin: unknown groups and changed upstream bytes are refused; nothing is downloaded."""
import tempfile
import unittest
from pathlib import Path

import fetch_public_group as f


class FetchPublicGroupTests(unittest.TestCase):
    def test_every_pinned_file_group_is_known_and_unknown_is_refused(self):
        self.assertIn('nestor-excavators', f.groups())
        with self.assertRaisesRegex(SystemExit, 'unknown pinned-file group'):
            f.fetch('no-such-group', 1)

    def test_changed_upstream_bytes_are_refused_and_never_saved(self):
        calls = []

        def transport(url, byte_range=None):
            calls.append(url)
            return b'not the pinned bytes'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SystemExit, 'refused'):
                f.fetch('nestor-excavators', 2, dest=Path(tmp), transport=transport)
            self.assertTrue(calls and all(u.startswith('https://raw.githubusercontent.com/usnistgov/nestor/') for u in calls))
            self.assertEqual([p for p in Path(tmp).rglob('*') if p.is_file()], [])

    def test_size_ceiling_is_checked_before_any_transfer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SystemExit, 'over --max-mb'):
                f.fetch('nestor-excavators', 0.01, dest=Path(tmp), transport=lambda *a, **k: self.fail('fetched'))


if __name__ == '__main__':
    unittest.main()
