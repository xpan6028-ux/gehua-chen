"""No Stata required: validation, budgets, lazy subset selection and output checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stata_runner", SKILL / "scripts" / "stata_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def config(**updates):
    c = dict(data_source="auto", outcome="price", target="weight", candidates=["mpg", "rep78"])
    c.update(updates)
    return c


class RunnerTest(unittest.TestCase):
    def test_empty_and_full_subsets(self):
        specs = runner.plan(runner.validate(config()))
        self.assertEqual([s["controls"] for s in specs], [[], ["mpg"], ["rep78"], ["mpg", "rep78"]])

    def test_count_restriction_not_exponential_allocation(self):
        c = runner.validate(config(candidates=["c" + str(i) for i in range(20)], min_controls=19))
        self.assertEqual(len(runner.plan(c)), 21)
        with self.assertRaisesRegex(ValueError, "storage exceeds"):
            runner.validate(config(engine="oneclick", candidates=c["candidates"], min_controls=19))

    def test_model_budget_before_enumeration(self):
        with self.assertRaisesRegex(ValueError, "exceed max_models"):
            runner.validate(config(candidates=["c" + str(i) for i in range(20)]))

    def test_no_arbitrary_code_or_roles(self):
        invalid = [config(target="weight; erase x"), config(candidates=["mpg", "mpg"]),
                   config(fixed_controls=["i.rep78"]), config(options="anything"),
                   config(vce={"type": "cluster", "cluster_var": "x\nclear"}),
                   config(fixed_controls=["c.mpg#c.weight"])]
        for c in invalid:
            with self.subTest(c=c), self.assertRaises(ValueError):
                runner.validate(c)

    def test_options_are_explicit(self):
        c = runner.validate(config(method="xtreg", panel_id="id", panel_model="fe", fixed_controls=["i.year"],
                                   vce={"type": "cluster", "cluster_var": "id"}))
        self.assertEqual(runner.command(c, ["mpg"]), "xtreg price weight i.year mpg, fe vce(cluster id)")
        with self.assertRaises(ValueError):
            runner.validate(config(method="xtreg", panel_id="id"))
        with self.assertRaises(ValueError):
            runner.validate(config(engine="oneclick", method="logit"))

    def test_engine_boundary(self):
        for c in (config(full=True), config(engine="oneclick", max_controls=1), config(alpha=True)):
            with self.subTest(c=c), self.assertRaises(ValueError):
                runner.validate(c)

    def test_invalid_types_and_reserved_names_rejected(self):
        invalid = [config(engine=[]), config(method=[]), config(sample_policy=[]),
                   config(vce={"type": []}), config(target="_all"), config(candidates=["_n"]),
                   config(fixed_controls=["i._cons"]), config(target="double"),
                   config(target="str123"), config(data_path=1)]
        invalid[-1].pop("data_source")
        for c in invalid:
            with self.subTest(c=c), self.assertRaises(ValueError):
                runner.validate(c)

    def test_completion_marker_not_inferred_from_output_text(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "missing.txt"
            self.assertEqual(runner.read_status(p), {})
            p.write_text("job_rc=198\nterminal_marker=1\n", encoding="utf-8")
            self.assertEqual(runner.read_status(p)["job_rc"], "198")

    def test_output_must_match_entire_plan(self):
        c = runner.validate(config())
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "all_specs.csv"
            p.write_text("spec_id,command,subset,status,p_value,se\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "complete ordered plan"):
                runner.verify_output(c, runner.plan(c), Path(td))


if __name__ == "__main__":
    unittest.main()
