import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from src.catalog_snapshot_integrity import verify_snapshot
from src.catalog_batch import batch_import

class SnapshotIntegrity(unittest.TestCase):
    def make(self, root):
        root=Path(root)
        raw=b'<html>2026-2027 Requirements</html>'
        (root/'math-major-ba.html').write_bytes(raw)
        manifest={'catalog_year':'2026-2027','total_programs':1,'records':[{'id':'math-major-ba','status':'candidate','sha256':hashlib.sha256(raw).hexdigest()}]}
        (root/'batch_manifest.json').write_text(json.dumps(manifest))
        return root
    def test_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(verify_snapshot(self.make(d))['candidate_pages'],1)
    def test_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make(d)
            (root/'math-major-ba.html').write_text('changed')
            with self.assertRaisesRegex(ValueError,'modified'):verify_snapshot(root)
    def test_stale_page(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make(d)
            (root/'stale.html').write_text('old')
            with self.assertRaisesRegex(ValueError,'Stale'):verify_snapshot(root)
    def test_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make(d)
            manifest=json.loads((root/'batch_manifest.json').read_text())
            manifest['records'].append(dict(manifest['records'][0]))
            manifest['total_programs']=2
            (root/'batch_manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'duplicate'):verify_snapshot(root)
    def test_partial_batch_rejected_when_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make(d)
            manifest=json.loads((root/'batch_manifest.json').read_text())
            manifest['records'].append({'id':'other-minor','status':'missing'})
            manifest['total_programs']=2
            (root/'batch_manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Incomplete'):verify_snapshot(root,require_complete=True)
    def test_unsafe_id(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make(d)
            manifest=json.loads((root/'batch_manifest.json').read_text())
            manifest['records'][0]['id']='../evil'
            (root/'batch_manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Unsafe'):verify_snapshot(root)

if __name__=='__main__':unittest.main()
