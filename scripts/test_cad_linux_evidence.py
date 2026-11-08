"""Offline retained Linux CAD UI evidence and bounded archive receiving controls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import cad_handoff as ch


class RetainedLinuxNativeEvidence(unittest.TestCase):
    def module(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_linux7.py"
        spec = importlib.util.spec_from_file_location("cad_linux_native_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_returned_files_observations_and_receiving_controls(self):
        summary = self.module().check()
        self.assertFalse(summary["whole_cad_qualified"])

    def test_pointer_states_and_neutral_source_candidate_replay(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_receiver8.py"
        spec = importlib.util.spec_from_file_location("cad_pointer_state_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["neutral_source_candidate_different_pixels"], 0)
        self.assertEqual(result["pointer_neutral_views"], 9)
        self.assertEqual(len(result["receiving_refusals"]), 5)
        self.assertFalse(result["whole_cad_qualified"])

    def test_font_profiles_complete_frames_and_planted_receiving_errors(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_font9.py"
        spec = importlib.util.spec_from_file_location("cad_font_frame_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["native_views"], 36)
        self.assertEqual(result["unique_native_attributes"], 144)
        self.assertEqual(result["default_long_overview_pixels_outside_exact_model_bounds"], 62)
        self.assertEqual(len(result["receiving_refusals"]), 7)
        self.assertFalse(result["whole_cad_qualified"])

    def test_evidence_extraction_rejects_paths_links_and_omission(self):
        import hashlib
        import io
        import tarfile
        module = self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, (name, kind) in enumerate((("raw/note.txt", "valid"), ("raw/../../escape", "path"),
                                                 ("raw/note:alternate", "path"), ("raw/link", "link"),
                                                 ("raw/note.txt", "omitted"))):
                base = root / str(index)
                base.mkdir()
                archive = base / "evidence.tar.xz"
                data = b"original evidence"
                with tarfile.open(archive, "w:xz") as packed:
                    if kind != "omitted":
                        entry = tarfile.TarInfo(name)
                        entry.size = len(data)
                        if kind == "link":
                            entry.type, entry.linkname = tarfile.SYMTYPE, "../../escape"
                        packed.addfile(entry, io.BytesIO(data))
                ch.write_json(base / "INVENTORY.json", dict(raw_bytes=len(data),
                    archive=dict(path=archive.name, bytes=archive.stat().st_size, sha256=ch.digest(archive)),
                    files={name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())}))
                with self.subTest(kind=kind, name=name):
                    if kind == "valid":
                        extracted = module.unpack(base, base / "out")
                        self.assertEqual((extracted / "note.txt").read_bytes(), data)
                    else:
                        with self.assertRaises(ValueError):
                            module.unpack(base, base / "out")
                    self.assertFalse((root / "escape").exists())



if __name__ == "__main__":
    unittest.main()
