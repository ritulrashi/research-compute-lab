import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from workload import execute, sample_shard


class WorkloadTests(unittest.TestCase):
    def test_worker_count_does_not_change_result(self):
        serial = execute(samples=10003, shards=7, seed=7, workers=1)
        parallel = execute(samples=10003, shards=7, seed=7, workers=2)
        self.assertEqual(serial["result"], parallel["result"])
        self.assertEqual(serial["result_sha256"], parallel["result_sha256"])

    def test_shards_cover_every_sample_once(self):
        result = execute(samples=103, shards=8)["result"]
        self.assertEqual(sum(x["samples"] for x in result["results"]), 103)
        self.assertEqual([x["shard_id"] for x in result["results"]], list(range(8)))
        self.assertTrue(all(0 <= x["inside_circle"] <= x["samples"] for x in result["results"]))

    def test_known_seed_and_repeatability(self):
        first = sample_shard((0, 1000, 42))
        self.assertEqual(first, sample_shard((0, 1000, 42)))
        self.assertNotEqual(first, sample_shard((0, 1000, 43)))

    def test_invalid_configuration_rejected(self):
        for kwargs in [{"samples": 0}, {"shards": -1}, {"workers": 0},
                       {"samples": 2, "shards": 3}, {"seed": "bad"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                execute(**kwargs)

    def test_cli_writes_parseable_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/"run.json"
            script = Path(__file__).resolve().parents[1]/"workload.py"
            result = subprocess.run([sys.executable, str(script), "--samples", "1000",
                                     "--workers", "2", "--output", str(output)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(report["result"]["samples"], 1000)
            self.assertEqual(len(report["result_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
