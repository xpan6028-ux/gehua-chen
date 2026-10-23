"""Real Stata tests using auto and generated data only; never user research data.

Set STATA_EXE. Set ONECLICK_ADO_DIR to include the pinned official OneClick test.
Set STATA_TEST_ROOT to retain inspectable run artifacts in a chosen directory.
Run this file directly with Python. No third-party Python packages required.
"""
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stata_runner", SKILL / "scripts" / "stata_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
EXE = os.environ.get("STATA_EXE")
ADO = os.environ.get("ONECLICK_ADO_DIR")


def batch(directory, text):
    (directory / "fixture.do").write_text("version 14\nset more off\n" + text, encoding="utf-8")
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    cmd = [EXE, "/e", "/q", "do", "fixture.do"] if os.name == "nt" else [EXE, "-b", "do", "fixture.do"]
    subprocess.run(cmd, cwd=directory, timeout=60, check=True, startupinfo=startup, stdout=subprocess.DEVNULL)


@unittest.skipUnless(EXE, "set STATA_EXE to run actual Stata tests")
class StataIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ.get("STATA_TEST_ROOT", tempfile.mkdtemp(prefix="oneclick-test-")))
        cls.root.mkdir(parents=True, exist_ok=True)
        cls.fixture = cls.root / "synthetic.dta"
        batch(cls.root, r'''
clear
set obs 400
set seed 71243
generate double x = rnormal()
generate double c1 = rnormal()
generate double c2 = rnormal()
generate double y = 2*x + .3*c1 + rnormal()
generate double c_missing = .
generate double c_partial = c2
replace c_partial = . in 1/100
generate double x_constant = 1
generate int id = ceil(_n/10)
generate int period = mod(_n-1,10)+1
generate byte cl4 = ceil(_n/100)
generate byte y_binary = (runiform()<invlogit(.4*x+.3*c1))
generate double x_null = sin(2*_pi*_n/400)
generate double y_null = cos(2*_pi*_n/400)
generate double c_null1 = sin(4*_pi*_n/400)
generate double c_null2 = cos(6*_pi*_n/400)
save synthetic.dta, replace
sysuse auto, clear
keep if !missing(price, weight, mpg, rep78)
postfile truth long spec_id double N double b double se double p_value using truth.dta, replace
quietly regress price weight, vce(robust)
quietly lincom weight
post truth (1) (e(N)) (_b[weight]) (_se[weight]) (r(p))
quietly regress price weight mpg, vce(robust)
quietly lincom weight
post truth (2) (e(N)) (_b[weight]) (_se[weight]) (r(p))
quietly regress price weight rep78, vce(robust)
quietly lincom weight
post truth (3) (e(N)) (_b[weight]) (_se[weight]) (r(p))
quietly regress price weight mpg rep78, vce(robust)
quietly lincom weight
post truth (4) (e(N)) (_b[weight]) (_se[weight]) (r(p))
postclose truth
use truth.dta, clear
format N b se p_value %24.17g
export delimited using truth.csv, datafmt replace
''')
        if not cls.fixture.exists() or not (cls.root / "truth.csv").exists():
            raise RuntimeError("fixture Stata job failed; inspect fixture.log")
        cls.input_hash = runner.sha256(cls.fixture)

    def execute(self, **changes):
        c = dict(engine="fullspec", data_path=str(self.fixture), outcome="y", target="x",
                 candidates=["c1", "c2"], sample_policy="common", max_models=16)
        c.update(changes)
        path = self.root / (self._testMethodName + "-" + str(len(list(self.root.glob("*.json")))) + ".json")
        path.write_text(json.dumps(c), encoding="utf-8")
        m = runner.run(path, self.root / "产物 空格", execute=True, stata=EXE, ado_dir=ADO, timeout=60)
        self.assertEqual(runner.sha256(self.fixture), self.input_hash)
        self.assertEqual(m["state"], "completed", m)
        filename = "all_specs.csv" if c["engine"] == "fullspec" else "oneclick_selected.csv"
        with (Path(m["output_directory"]) / filename).open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        return m, rows

    def test_auto_matches_native_estimation_and_p_to_double_precision(self):
        c = json.loads((SKILL / "assets" / "fullspec_auto.json").read_text())
        path = self.root / "auto.json"
        path.write_text(json.dumps(c), encoding="utf-8")
        m = runner.run(path, self.root, True, EXE, timeout=60)
        self.assertEqual(m["state"], "completed", m)
        with (Path(m["output_directory"]) / "all_specs.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        with (self.root / "truth.csv").open(encoding="utf-8-sig", newline="") as f:
            truth = list(csv.DictReader(f))
        for actual, expected in zip(rows, truth):
            for field in ("N", "b", "se", "p_value"):
                self.assertTrue(math.isclose(float(actual[field]), float(expected[field]), rel_tol=1e-13, abs_tol=1e-14), (field, actual, expected))

    def test_failures_retained_without_previous_e_results(self):
        m, rows = self.execute(candidates=["c1", "c_missing"], sample_policy="per_spec")
        self.assertEqual(m["status_counts"], {"ok": 2, "estimation_failed": 2})
        for r in rows:
            if "c_missing" in r["subset"]:
                self.assertNotEqual(r["estimation_rc"], "0")
                for field in ("N", "b", "se", "p_value", "r2"):
                    self.assertEqual(r[field], "", (field, r))

    def test_all_nonsignificant_models_are_kept(self):
        _, rows = self.execute(outcome="y_null", target="x_null", candidates=["c_null1", "c_null2"])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["status"] == "ok" and float(r["p_value"]) > .99 and r["passes_alpha"] == "0" for r in rows))

    def test_omitted_target_is_not_valid_inference(self):
        _, rows = self.execute(target="x_constant")
        self.assertTrue(all(r["status"] in {"target_omitted", "target_absent"} for r in rows), rows)
        self.assertTrue(all(r["p_value"] == "" and r["estimation_rc"] == "0" for r in rows))

    def test_common_pool_and_per_spec_sample_difference(self):
        _, common = self.execute(candidates=["c1", "c_partial"])
        _, variable = self.execute(candidates=["c1", "c_partial"], sample_policy="per_spec")
        self.assertEqual({r["N"] for r in common}, {"300"})
        self.assertEqual({r["common_pool_complete"] for r in common}, {"1"})
        self.assertEqual({r["N"] for r in variable}, {"300", "400"})

    def test_logit_and_probit_preserve_missing_r2(self):
        for method in ("logit", "probit"):
            with self.subTest(method=method):
                _, rows = self.execute(method=method, outcome="y_binary", vce={"type": "robust"})
                self.assertTrue(all(r["status"] == "ok" and r["r2"] == "" and r["r2_p"] != "" for r in rows), rows)
                self.assertTrue(all(r["df_test"] == "" and r["converged"] == "1" for r in rows))

    def test_panel_fe_and_reghdfe_cluster(self):
        for changes in (dict(method="xtreg", panel_id="id", time_var="period", panel_model="fe"),
                        dict(method="reghdfe", fixed_effects=["id", "period"])):
            with self.subTest(changes=changes):
                _, rows = self.execute(**changes, vce={"type": "cluster", "cluster_var": "id"})
                self.assertTrue(all(r["status"] == "ok" and float(r["df_test"]) == 39 for r in rows), rows)

    def test_small_cluster_p_uses_native_t_not_normal(self):
        _, rows = self.execute(vce={"type": "cluster", "cluster_var": "cl4"})
        self.assertTrue(all(r["df_test"] == "3" for r in rows), rows)
        # With only four clusters, the exact native t p-value differs strongly from z.
        self.assertTrue(all(float(r["p_value"]) > math.erfc(abs(float(r["statistic"])) / math.sqrt(2)) for r in rows))

    def test_common_empty_pool_fails_even_when_process_exits_zero(self):
        c = dict(data_path=str(self.fixture), outcome="y", target="x", candidates=["c_missing"])
        path = self.root / "empty_pool.json"
        path.write_text(json.dumps(c))
        m = runner.run(path, self.root, True, EXE, timeout=60)
        self.assertEqual(m["state"], "failed")
        self.assertEqual(m["stata_status"]["job_rc"], "2000")

    def test_variable_abbreviations_are_not_silently_accepted(self):
        path = self.root / "abbreviation.json"
        path.write_text(json.dumps(dict(data_source="auto", outcome="pri", target="weight", candidates=[])))
        m = runner.run(path, self.root, True, EXE, timeout=60)
        self.assertEqual(m["state"], "failed")
        self.assertNotEqual(m["stata_status"]["job_rc"], "0")

    def test_process_zero_without_completion_marker_is_failure(self):
        path = self.root / "missing_marker.json"
        path.write_text(json.dumps(dict(data_source="auto", outcome="price", target="weight", candidates=[])))
        with patch.object(runner, "render_do", return_value="version 14\nexit, clear\n"):
            m = runner.run(path, self.root, True, EXE, timeout=60)
        self.assertEqual(m["process_rc"], 0)
        self.assertEqual(m["state"], "failed")
        self.assertEqual(m["stata_status"], {})

    def test_timeout_marks_incomplete_and_stops_own_child(self):
        path = self.root / "timeout.json"
        path.write_text(json.dumps(dict(data_source="auto", outcome="price", target="weight", candidates=[])))
        with patch.object(runner, "render_do", return_value="version 14\nsleep 10000\nexit, clear\n"):
            m = runner.run(path, self.root, True, EXE, timeout=1)
        self.assertEqual(m["state"], "timed_out")
        self.assertNotIn("output_rows", m)

    @unittest.skipUnless(ADO, "set ONECLICK_ADO_DIR for original OneClick test")
    def test_original_oneclick_pinned_source(self):
        m, rows = self.execute(engine="oneclick", full=True)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all("regress y x" in r["command"] for r in rows))
        self.assertNotIn("p_value", rows[0])
        self.assertEqual(m["oneclick_sha256"], runner.PINNED_ADO)

    @unittest.skipUnless(ADO, "set ONECLICK_ADO_DIR for original OneClick test")
    def test_original_no_selected_models_is_not_success_or_old_output(self):
        c = dict(engine="oneclick", data_path=str(self.fixture), outcome="y_null", target="x_null",
                 candidates=["c_null1", "c_null2"])
        path = self.root / "original_none.json"
        path.write_text(json.dumps(c))
        m = runner.run(path, self.root, True, EXE, ADO, timeout=60)
        self.assertEqual(m["state"], "failed")
        self.assertEqual(m["stata_status"]["job_rc"], "1")
        self.assertFalse((Path(m["output_directory"]) / "oneclick_selected.csv").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
