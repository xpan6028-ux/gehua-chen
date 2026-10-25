"""Cross-directory CLI tests; only Python/PowerShell, never Stata."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("portable_runner", SKILL / "scripts/stata_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def subprocess_options():
    if os.name != "nt":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": startup}


class PortabilityTests(unittest.TestCase):
    def test_cli_from_two_unrelated_directories(self):
        with tempfile.TemporaryDirectory(prefix="gehua paths ") as td:
            root = Path(td)
            cfgdir = root / "配置"
            cfgdir.mkdir()
            cfg = cfgdir / "demo.json"
            cfg.write_text(json.dumps(dict(data_source="auto", outcome="price", target="weight", candidates=["mpg", "rep78"])))
            plans = []
            for label in ("unrelated-a", "unrelated-b"):
                cwd = root / label
                cwd.mkdir()
                result = subprocess.run([sys.executable, str(SKILL / "scripts/stata_runner.py"),
                                         "plan", str(cfg), "--output-root", "results"],
                                        cwd=cwd, capture_output=True, text=True, encoding="utf-8", **subprocess_options())
                self.assertEqual(result.returncode, 0, result.stderr)
                m = json.loads(result.stdout)
                directory = Path(m["output_directory"])
                self.assertEqual(directory.parent, cfgdir / "results")
                self.assertFalse((cwd / "results").exists())
                self.assertFalse(m["executed_stata"])
                plans.append(json.loads((directory / "plan.json").read_text()))
            self.assertEqual(plans[0], plans[1])
            self.assertEqual(len(plans[0]), 4)

    def test_relocated_skill_keeps_resources_in_its_own_directory(self):
        with tempfile.TemporaryDirectory(prefix="another-agent ") as td:
            root = Path(td)
            relocated = root / "其他工具 技能" / "gehua-chen"
            shutil.copytree(SKILL, relocated, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            cwd = root / "project"
            cwd.mkdir()
            p = subprocess.run([sys.executable, str(relocated / "scripts/stata_runner.py"), "plan",
                                str(relocated / "assets/fullspec_auto.json"), "--output-root", str(root / "output")],
                               cwd=cwd, capture_output=True, text=True, encoding="utf-8", **subprocess_options())
            self.assertEqual(p.returncode, 0, p.stderr)
            m = json.loads(p.stdout)
            job = (Path(m["output_directory"]) / "job.do").read_text(encoding="utf-8")
            self.assertIn(runner.stata_path(relocated / "assets/oc_collect.ado"), job)
            self.assertIn('cd "' + runner.stata_path(m["output_directory"]) + '"', job)

    def test_original_plan_requires_neither_stata_nor_ado(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "original.json"
            cfg.write_text(json.dumps(dict(engine="oneclick", data_source="auto", outcome="price", target="weight", candidates=["mpg", "rep78"])))
            with patch.object(runner, "find_stata", side_effect=AssertionError("plan must not search Stata")):
                m = runner.run(cfg, Path(td) / "results")
            self.assertEqual(m["state"], "planned")
            self.assertFalse(m["execution_environment_checked"])
            self.assertIsNone(m["oneclick_sha256"])
            self.assertEqual(m["original_combination_slots"], 4)
            with self.assertRaisesRegex(ValueError, "requires --ado-dir"):
                runner.run(cfg, Path(td) / "run-results", execute=True)

    def test_plan_allows_not_yet_supplied_data_but_run_rejects_it(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "future.json"
            cfg.write_text(json.dumps(dict(data_path="data/not-yet.dta", outcome="y", target="x", candidates=["c1"])))
            m = runner.run(cfg, "results")
            directory = Path(m["output_directory"])
            saved = json.loads((directory / "config.json").read_text())
            self.assertEqual(Path(saved["data_path"]), Path(td) / "data/not-yet.dta")
            self.assertIsNone(m["input_sha256"])
            self.assertEqual(m["planned_models"], 2)
            with self.assertRaises((OSError, ValueError)):
                runner.run(cfg, "results", execute=True)

    def test_plan_with_no_data_source_does_not_substitute_auto(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "variables-only.json"
            cfg.write_text(json.dumps(dict(outcome="y", target="x", candidates=["a", "b", "c"])))
            m = runner.run(cfg, "results")
            self.assertEqual(m["planned_models"], 8)
            self.assertFalse(m["data_configured"])
            job = (Path(m["output_directory"]) / "job.do").read_text(encoding="utf-8")
            self.assertNotIn("sysuse auto", job)
            self.assertIn("provide data_path or data_source", job)
            with self.assertRaisesRegex(ValueError, "requires exactly one"):
                runner.run(cfg, "results", execute=True)

    def test_invalid_data_format_is_not_a_planning_dependency(self):
        with self.assertRaisesRegex(ValueError, "dta"):
            runner.validate(dict(data_path="spreadsheet.xlsx", outcome="y", target="x"), require_data=False)

    def test_stata_command_name_resolves_via_path(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "stata-test"
            exe.write_text("not executed")
            with patch.object(runner.shutil, "which", return_value=str(exe)):
                self.assertEqual(runner.find_stata("stata-test"), exe.resolve())

    def test_relative_ado_path_is_config_relative_in_plan(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "original.json"
            cfg.write_text(json.dumps(dict(engine="oneclick", data_source="auto", outcome="price", target="weight", candidates=["mpg", "rep78"])))
            m = runner.run(cfg, "results", ado_dir="vendor/oneclick")
            job = (Path(m["output_directory"]) / "job.do").read_text(encoding="utf-8")
            self.assertIn(runner.stata_path(Path(td) / "vendor/oneclick"), job)
            self.assertIsNone(m["oneclick_sha256"])

    @unittest.skipUnless(os.name == "nt" and (shutil.which("pwsh") or shutil.which("powershell")), "Windows PowerShell demo entry")
    def test_powershell_demo_entry_from_another_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="ps demo ") as td:
            ps = shutil.which("pwsh") or shutil.which("powershell")
            p = subprocess.run([ps, "-NoProfile", "-File", str(SKILL / "scripts/run_demo.ps1"),
                                "-Action", "plan", "-PythonExe", sys.executable,
                                "-OutputRoot", str(Path(td) / "output")],
                               cwd=td, capture_output=True, text=True, encoding="utf-8", **subprocess_options())
            self.assertEqual(p.returncode, 0, p.stderr)
            m = json.loads(p.stdout)
            self.assertEqual(m["planned_models"], 4)
            self.assertFalse(m["executed_stata"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
