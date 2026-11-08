"""Offline retained Linux CAD UI evidence and bounded archive receiving controls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import cad_handoff as ch


class RetainedLinuxNativeEvidence(unittest.TestCase):
    def public_module(self, name):
        folder = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/public-validation-11"
        spec = importlib.util.spec_from_file_location("cad_public11_" + name, folder / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_bitmap_window_contract_uses_size_instead_of_maximum(self):
        convert = self.public_module("window").xywh
        for bounds in ([-10, -14, 46, 10], [10, 20, 30, 50], [-30, -40, -10, -20], [0, 0, 1, 1]):
            x, y, width, height = convert(bounds)
            self.assertEqual([x, y, x + width, y + height], bounds)
        for bounds in ([0, 0, 0, 1], [0, 0, 1, -1], [0, 0, float('inf'), 1], [True, 0, 1, 1]):
            with self.assertRaises(ValueError):
                convert(bounds)

    def test_public_native_receiving_rejects_missing_case_and_wrong_profile(self):
        import json
        receiving = self.public_module("receive")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native.stdout'
            profile = {'configuration_file': '/home/cad/.config/QCAD/QCAD3.conf'}
            path.write_text('ICT_TRANSFER11_PROFILE ' + json.dumps(profile) + '\nICT_QUAL_NATIVE {"id":"one"}\n', encoding='utf-8')
            self.assertEqual(len(receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one'])), 1)
            with self.assertRaisesRegex(ValueError, 'coverage'):
                receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one', 'omitted'])
            profile['configuration_file'] = '/work/installed-but-unselected.conf'
            path.write_text('ICT_TRANSFER11_PROFILE ' + json.dumps(profile) + '\nICT_QUAL_NATIVE {"id":"one"}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'profile'):
                receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one'])

    def test_public_native_receiving_checks_every_stored_field(self):
        receiving = self.public_module("receive")
        rows = [{'attributes': {'ICT_ID': 'asset', 'MODEL': 'expected', 'FOREIGN': 'keep'}}]
        expected = {'asset': dict(rows[0]['attributes'])}
        self.assertEqual(receiving.native_fields(rows, expected), 3)
        rows[0]['attributes']['FOREIGN'] = 'lost'
        with self.assertRaisesRegex(ValueError, 'fields'):
            receiving.native_fields(rows, expected)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            receiving.fields(rows + rows)

    def test_fresh_public_candidates_native_returns_and_retained_failures(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_public11.py"
        spec = importlib.util.spec_from_file_location("cad_public11_full", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result['exact_candidates'], 6)
        self.assertEqual(result['native_fields'], 72)
        self.assertEqual(result['fresh_process_fields'], 72)
        self.assertEqual(result['corrected_images'], 24)
        self.assertEqual(result['source_revision_loss_controls'], 36)
        self.assertTrue(all(r['strict_differences'] > 0 for r in result['native_strict']))
        self.assertFalse(result['whole_cad_qualified'])

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

    def test_minimal_layout_revisions_native_paper_and_foreign_bytes(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_layout10.py"
        spec = importlib.util.spec_from_file_location("cad_layout_preparation_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["minimal_proposals"], 5)
        self.assertEqual(result["verified_profile_paper_images"], 25)
        self.assertEqual(result["semantic_input_controls"], 17)
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
