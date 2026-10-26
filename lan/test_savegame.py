"""Save tests use disposable copies only; never write the supplied originals."""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import savegame as save

SAMPLES = Path(__file__).resolve().parent.parent / 'SaveGame/76561197960271872'


class EnvelopeTests(unittest.TestCase):
    def test_windows_cross_api_ctime_difference_not_a_content_change(self):
        path = SimpleNamespace(st_dev=7, st_ino=42, st_size=100,
                               st_mtime_ns=123456789, st_ctime_ns=111)
        opened = SimpleNamespace(**vars(path))
        opened.st_ctime_ns = 222
        self.assertTrue(save._same_open_file(path, opened, windows=True))
        self.assertFalse(save._same_open_file(path, opened, windows=False))
        for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns'):
            changed = SimpleNamespace(**vars(opened))
            setattr(changed, field, getattr(changed, field) + 1)
            self.assertFalse(save._same_open_file(path, changed, windows=True))
        # Within either API, ctime is still part of the full safety fingerprint.
        self.assertNotEqual(save._identity(path), save._identity(opened))

    def test_envelope_sizes_and_corruption(self):
        for size in (0, 1, 16, 17, 255, 4096):
            payload = bytes(i % 251 for i in range(size))
            encoded = save.encode_envelope(payload)
            self.assertEqual(save.decode_envelope(encoded), payload)
            damaged = bytearray(encoded)
            damaged[-1] ^= 1
            with self.assertRaises(save.SaveError):
                save.decode_envelope(damaged)

    def test_compression_roundtrip(self):
        plain = b'not a schema; codec test only' * 200
        self.assertEqual(save.decode_save(save.encode_save(plain)), plain)


@unittest.skipUnless((SAMPLES / 'MainGameSaveData').is_file(), 'original sample unavailable')
class SaveCopyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='szero-save-tests-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'MainGameSaveData'
        self.original = (SAMPLES / self.path.name).read_bytes()
        self.path.write_bytes(self.original)

    def plan(self, mode='characters'):
        return save.plan_unlock(self.path, mode)

    def test_ctime_api_difference_allowed_but_handle_change_still_refused(self):
        real_fstat = os.fstat
        compare = save._same_open_file
        for change_during_read in (False, True):
            calls = 0
            def windows_fstat(fd):
                nonlocal calls
                info = real_fstat(fd)
                calls += 1
                values = {key: getattr(info, key) for key in
                          ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns',
                           'st_ctime_ns', 'st_mode', 'st_nlink')}
                values['st_ctime_ns'] += 100 + int(change_during_read and calls > 1)
                return SimpleNamespace(**values)
            with patch.object(save.os, 'fstat', side_effect=windows_fstat), \
                 patch.object(save, '_same_open_file', side_effect=lambda a,b: compare(a,b,windows=True)):
                if change_during_read:
                    with self.assertRaisesRegex(save.SaveError, 'changed while reading'):
                        save._read_source(self.path)
                else:
                    self.assertEqual(save._read_source(self.path)[1], self.original)

    def test_original_samples_integrity_and_byte_exact_envelope(self):
        for name, expected in (
            ('MainGameSaveData', '110e57e39f88a88acba1ba7855e0949fa8bfe437afa690634062e007b2c0279c'),
            ('SystemSaveData', 'c16145d3a91dd839ef4e95ea032fb3ab215ee36b7ea44397b67397f4e0715a6c')):
            original = (SAMPLES / name).read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(), expected)
            self.assertEqual(save.encode_envelope(save.decode_envelope(original)), original)

    def test_character_preview_and_idempotent_atomic_write(self):
        plan = self.plan()
        self.assertEqual(plan.changed_rows, 62)
        self.assertEqual(self.path.read_bytes(), self.original)
        plain = save.decode_save(self.original)
        expected = save._patched(plain, plan.edits)
        result = save.apply_unlock(plan, confirmed=True, game_running=lambda: False)
        self.assertEqual(result.changed_rows, 62)
        self.assertEqual(result.backup_path.read_bytes(), self.original)
        self.assertEqual(save.decode_save(self.path.read_bytes()), expected)
        self.assertEqual(self.plan().changed_rows, 0)
        # Every byte outside the explicit structural edit spans is preserved.
        before = after = 0
        for offset, size, replacement in plan.edits:
            self.assertEqual(plain[before:offset], expected[after:after+offset-before])
            after += offset-before+len(replacement)
            before = offset+size
        self.assertEqual(plain[before:], expected[after:])

    def test_earned_subset_preview(self):
        plan = self.plan('everything')
        self.assertEqual(plan.changed_rows, 865)
        result = save.apply_unlock(plan, confirmed=True, game_running=lambda: False)
        self.assertEqual(result.backup_path.read_bytes(), self.original)
        self.assertEqual(self.plan('everything').changed_rows, 0)

    def test_confirmation_running_stale_and_forged_plan_refuse(self):
        plan = self.plan()
        for confirmed, running in ((False, False), (True, True), (True, None)):
            with self.assertRaises(save.SaveError):
                save.apply_unlock(plan, confirmed=confirmed, game_running=lambda: running)
        with self.assertRaises(save.SaveError):
            save.apply_unlock(replace(plan, changed_rows=999), confirmed=True, game_running=lambda: False)
        self.path.write_bytes(self.original + b'changed')
        with self.assertRaises(save.SaveError):
            save.apply_unlock(plan, confirmed=True, game_running=lambda: False)

    def test_replace_failure_retains_original_and_backup(self):
        plan = self.plan()
        with patch.object(save.os, 'replace', side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):
                save.apply_unlock(plan, confirmed=True, game_running=lambda: False)
        self.assertEqual(self.path.read_bytes(), self.original)
        backups = list(self.path.parent.glob('*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.original)
        self.assertFalse(list(self.path.parent.glob('*.lock')))
        self.assertFalse(list(self.path.parent.glob('.SzeroLAN-save-*')))

    def test_links_and_readonly_refuse(self):
        plan = self.plan()
        self.path.chmod(0o444)
        with self.assertRaises(save.SaveError):
            save.apply_unlock(plan, confirmed=True, game_running=lambda: False)
        self.path.chmod(0o600)
        other = self.path.parent / 'other'
        self.path.rename(other)
        self.path.symlink_to(other)
        with self.assertRaises(save.SaveError):
            self.plan()
        self.path.unlink()
        os.link(other, self.path)
        with self.assertRaises(save.SaveError):
            self.plan()

    def test_wrong_slot_corrupt_or_unsupported_schema_refuse(self):
        self.path.write_bytes((SAMPLES / 'SystemSaveData').read_bytes())
        with self.assertRaises(save.SaveError):
            self.plan()
        self.path.write_bytes(save.encode_save(b'not a supported schema'))
        with self.assertRaises(save.SaveError):
            self.plan()


if __name__ == '__main__':
    unittest.main()
