import json
import tempfile
import unittest
from pathlib import Path
from distributed import collect, config, shard, source_hash, write_json
from workload import execute

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        write_json(self.directory / "request.json", {
            "run_id": "test", "config": config(103, 4, 42), "source_sha256": source_hash()})
        for i in range(4):
            shard(self.directory, i)
    def edit(self, index, change):
        path = self.directory / f"shard-{index}.json"
        value = json.loads(path.read_text())
        change(value)
        write_json(path, value)
    def test_matches_reference(self):
        self.assertEqual(collect(self.directory)["result_sha256"], execute(103,4,42)["result_sha256"])
    def test_missing(self):
        (self.directory / "shard-0.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            collect(self.directory)
    def test_duplicate(self):
        self.edit(1, lambda v: v["result"].update(shard_id=0))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            collect(self.directory)
    def test_provenance(self):
        self.edit(0, lambda v: v.update(run_id="other"))
        with self.assertRaisesRegex(ValueError, "provenance"):
            collect(self.directory)
    def test_bad_accounting(self):
        self.edit(0, lambda v: v["result"].update(inside_circle=10000))
        with self.assertRaisesRegex(ValueError, "accounting"):
            collect(self.directory)
    def test_invalid_config(self):
        for values in [(0,1,42),(5,6,42),(5,0,42),(5,1,"42")]:
            with self.assertRaises(ValueError): config(*values)
if __name__ == "__main__": unittest.main()
