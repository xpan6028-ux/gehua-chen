"""Offline tests: compare workload counts to independent subset enumeration."""
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/model_budget.py"
spec = importlib.util.spec_from_file_location("model_budget", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BudgetTests(unittest.TestCase):
    def test_counts_against_enumerated_subsets(self):
        for k in range(2, 9):
            subsets = [s for size in range(k + 1) for s in itertools.combinations(range(k), size)]
            default = module.budget(k)
            self.assertEqual(default["estimated_regression_calls_from_source"], len(subsets))
            self.assertEqual(default["screen_displayed_count_from_source"], len(subsets) - 1)
            for minimum in range(1, k + 2):
                expected = len([s for s in subsets if len(s) >= minimum])
                result = module.budget(k, minimum)
                self.assertEqual(result["estimated_regression_calls_from_source"], expected)
                self.assertEqual(result["combination_slots_and_minimum_working_rows"], len(subsets))

    def test_large_pool_high_threshold(self):
        result = module.budget(20, 19)
        self.assertEqual(result["estimated_regression_calls_from_source"], 21)
        self.assertEqual(result["combination_slots_and_minimum_working_rows"], 1048576)
        self.assertFalse(result["executed_stata"])

    def test_invalid_inputs(self):
        for args in [(1, None), (-2, None), (2, 0), (2, -1), (1001, None)]:
            with self.assertRaises(ValueError):
                module.budget(*args)

    def test_cli_json(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "5", "--threshold", "3"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["estimated_regression_calls_from_source"], 16)

    def test_cli_rejects_too_few_candidates(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "1"], capture_output=True)
        self.assertNotEqual(run.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
