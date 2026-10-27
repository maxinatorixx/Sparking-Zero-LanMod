"""Reversible own-mod controls never uninstall shared loaders or other mods."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import installer


class InstallControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.win64 = self.root / "SparkingZERO/Binaries/Win64"
        self.win64.mkdir(parents=True)
        self.exe = self.win64 / "SparkingZERO-Win64-Shipping.exe"
        self.exe.write_bytes(b"synthetic supported game for installer tests")

    def tearDown(self):
        self.temporary.cleanup()

    def install(self):
        return Path(installer.install(self.root))

    def test_empty_selection_has_no_enabled_mod(self):
        self.assertIsNone(installer.installed_runtime(self.root))
        with self.assertRaises((OSError, ValueError)):
            installer.uninstall(self.root)
        self.assertEqual(self.exe.read_bytes(), b"synthetic supported game for installer tests")

    def test_install_uninstall_keeps_shared_files_without_creating_uninstall_backups(self):
        config = self.root / "SzeroLAN.json"
        config.write_text('{"server_host":"192.0.2.1","unknown":"preserve"}')
        mods = self.win64 / "Mods/mods.txt"
        mods.parent.mkdir()
        mods.write_bytes(b"\xef\xbb\xbfOtherMod : 1\r\n")
        other = self.win64 / "Mods/OtherMod/scripts/main.lua"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"preserve another mod")
        runtime = self.install()
        self.assertEqual(installer.installed_runtime(self.root), str(runtime))
        loader_bytes = {relative: (self.win64 / relative).read_bytes()
                        for relative in ("UE4SS.dll", "dwmapi.dll", "UE4SS-settings.ini")}
        mod = runtime.with_name("native_search.dll")
        before = {p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()}
        self.assertIsNone(installer.uninstall(self.root))
        self.assertIsNone(installer.installed_runtime(self.root))
        self.assertFalse(mod.exists())
        for relative, data in loader_bytes.items():
            self.assertEqual((self.win64 / relative).read_bytes(), data)
        self.assertEqual(config.read_text(), '{"server_host":"192.0.2.1","unknown":"preserve"}')
        self.assertEqual(other.read_bytes(), b"preserve another mod")
        self.assertEqual(mods.read_bytes(), b"\xef\xbb\xbfSzeroLAN : 0\r\nOtherMod : 1\r\n")
        self.assertFalse(list(self.win64.glob("SzeroLAN-uninstall-*")))
        after = {p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()}
        self.assertLess(after, before)  # Uninstall only removes files/edits existing metadata.
        self.install()
        self.assertIsNotNone(installer.installed_runtime(self.root))

    def test_uninstall_preserves_existing_install_and_unrelated_backups(self):
        runtime = self.install()
        original_backup = self.win64 / "UE4SS.dll.original.bak"
        original_backup.write_bytes(b"preexisting loader before installation")
        other_backup = self.win64 / "Mods/OtherMod/main.lua.bak"
        other_backup.parent.mkdir()
        other_backup.write_bytes(b"unrelated user backup")
        receipt = self.win64 / "SzeroLAN-install.json"
        data = json.loads(receipt.read_text())
        data["transactions"][0]["changes"].append({
            "path": "SparkingZERO/Binaries/Win64/UE4SS.dll",
            "backup": original_backup.relative_to(self.root).as_posix()})
        receipt.write_text(json.dumps(data))
        self.assertIsNone(installer.uninstall(self.root))
        self.assertEqual(original_backup.read_bytes(), b"preexisting loader before installation")
        self.assertEqual(other_backup.read_bytes(), b"unrelated user backup")
        self.assertFalse(list(self.win64.glob("SzeroLAN-uninstall-*")))
        self.assertFalse(runtime.with_name("native_search.dll").exists())

    def test_existing_nested_ue4ss_and_loader_settings_are_preserved(self):
        loader = self.win64 / "ue4ss"
        loader.mkdir()
        (loader / "UE4SS.dll").write_bytes(b"unrelated existing compatible loader")
        (loader / "UE4SS-settings.ini").write_bytes(b"user loader settings")
        runtime = self.install()
        self.assertTrue(runtime.is_relative_to(loader))
        installer.uninstall(self.root)
        self.assertEqual((loader / "UE4SS.dll").read_bytes(), b"unrelated existing compatible loader")
        self.assertEqual((loader / "UE4SS-settings.ini").read_bytes(), b"user loader settings")
        self.assertFalse((self.win64 / "dwmapi.dll").exists())

    def test_modified_own_file_refuses_before_disabling_mod_or_deleting_any_file(self):
        runtime = self.install()
        changed = runtime.with_name("main.lua")
        changed.write_bytes(b"user customization")
        mods = self.win64 / "Mods/mods.txt"
        previous = mods.read_bytes()
        with self.assertRaises(ValueError):
            installer.uninstall(self.root)
        self.assertEqual(changed.read_bytes(), b"user customization")
        self.assertTrue(runtime.with_name("native_search.dll").exists())
        self.assertEqual(mods.read_bytes(), previous)
        self.assertFalse(list(self.win64.glob("SzeroLAN-uninstall-*")))

    def test_symlink_own_file_refuses_uninstall_and_detection(self):
        runtime = self.install()
        own = runtime.with_name("main.lua")
        other = self.root / "untouched.lua"
        other.write_bytes(own.read_bytes())
        own.unlink()
        own.symlink_to(other)
        self.assertIsNone(installer.installed_runtime(self.root))
        with self.assertRaises(ValueError):
            installer.uninstall(self.root)
        self.assertTrue(own.is_symlink())
        self.assertTrue(other.exists())

    def test_write_failure_restores_disabled_flag_and_all_removed_files(self):
        runtime = self.install()
        files = {p: p.read_bytes() for p in runtime.parent.iterdir() if p.is_file()}
        mods = self.win64 / "Mods/mods.txt"
        previous = mods.read_bytes()
        write = installer.atomic_write
        receipt = self.win64 / "SzeroLAN-install.json"
        failed = False

        def fail_receipt(path, content):
            nonlocal failed
            if Path(path) == receipt and not failed:
                failed = True
                raise OSError("simulated failure after removals")
            return write(path, content)

        with patch.object(installer, "atomic_write", side_effect=fail_receipt):
            with self.assertRaises(OSError):
                installer.uninstall(self.root)
        for path, content in files.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(mods.read_bytes(), previous)
        self.assertIsNotNone(installer.installed_runtime(self.root))
        self.assertFalse(list(self.win64.glob("SzeroLAN-uninstall-*")))

    def test_receipt_cannot_authorize_files_outside_our_mod_directory(self):
        runtime = self.install()
        unrelated = self.root / "SaveGame/Mods/SzeroLAN/private.txt"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b"do not delete")
        receipt = self.win64 / "SzeroLAN-install.json"
        data = json.loads(receipt.read_text())
        data["transactions"][-1]["files"].append({
            "path": unrelated.relative_to(self.root).as_posix(),
            "sha256": installer.digest(unrelated)})
        receipt.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            installer.uninstall(self.root)
        self.assertEqual(unrelated.read_bytes(), b"do not delete")
        self.assertTrue(runtime.with_name("main.lua").exists())


if __name__ == "__main__":
    unittest.main()
