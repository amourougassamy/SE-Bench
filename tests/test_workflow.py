from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from se_bench.cli import request
from se_bench.demo import run_demo
from se_bench.evaluator import grade
from se_bench.model import ContractError
from se_bench.runtime import Session, read_json, write_json
from se_bench.solver import available


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"
        self.session = Session.create(self.root)

    def test_nonempty_workspace_is_preserved(self):
        with self.assertRaises(ContractError):
            Session.create(self.root)
        self.assertTrue((self.root / "model.json").is_file())

    def test_invalid_call_recorded_and_recoverable(self):
        self.assertFalse(self.session.call("model.get", {"unexpected": 1})["ok"])
        self.assertTrue(self.session.call("model.get")["ok"])
        resumed = Session(self.root)
        self.assertEqual(resumed.state["error_count"], 1)
        self.assertEqual(resumed.state["call_count"], 2)

    def test_invalid_protocol_and_nan_are_recorded(self):
        self.assertFalse(request(self.session, '{bad-json')["ok"])
        self.assertFalse(request(self.session, '{"tool":"model.put","arguments":{"model":NaN}}')["ok"])
        self.assertEqual(self.session.state["error_count"], 2)

    def test_early_solver_review_and_submission_are_rejected(self):
        for name in ("solver.run", "review.request", "submission.submit"):
            self.assertFalse(self.session.call(name)["ok"])
        self.assertFalse(grade(self.root)["automated_success"])

    def test_rejected_edit_preserves_model(self):
        before = (self.root / "model.json").read_bytes()
        model = self.session.call("model.get")["data"]["model"]
        model["units"] = "kN-m"
        self.assertFalse(self.session.call("model.put", {"model": model})["ok"])
        self.assertEqual(before, (self.root / "model.json").read_bytes())

    def test_budget_exhaustion(self):
        self.session.task["max_tool_calls"] = 1
        self.assertTrue(self.session.call("model.get")["ok"])
        self.assertFalse(self.session.call("model.get")["ok"])

    def test_solver_failure_does_not_advance_state_and_can_recover(self):
        self.session.call("model.validate")
        with patch("se_bench.runtime.solve", side_effect=ContractError("injected tool failure")):
            self.assertFalse(self.session.call("solver.run")["ok"])
        self.assertIsNone(self.session.state["active_result"])
        self.assertEqual(self.session.state["phase"], "baseline")
        self.assertTrue(self.session.call("model.get")["ok"])


@unittest.skipUnless(available(), "Install .[solver] for end-to-end workflow checks")
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"

    def call(self, session, name, **args):
        response = session.call(name, args)
        self.assertTrue(response["ok"], response)
        return response["data"]

    def revised_session(self):
        session = Session.create(self.root)
        self.call(session, "model.validate")
        result = self.call(session, "solver.run")
        self.call(session, "results.get", run_id=result["run_id"])
        self.call(session, "drawing.render")
        self.call(session, "review.request")
        self.call(session, "model.put", model=deepcopy(session.expected))
        self.call(session, "model.validate")
        result = self.call(session, "solver.run")
        result = self.call(session, "results.get", run_id=result["run_id"])
        self.call(session, "drawing.render")
        return session, result

    def report(self, session, result):
        roof = {node: abs(result["displacements"][node][0]) for node in ("3", "4")}
        return {"run_id": result["run_id"], "max_roof_ux_m": max(roof.values()),
                "governing_node": max(roof, key=roof.get), "criterion_status": "fail",
                "equilibrium_residual_Fx_Fy_Mz": result["equilibrium_residual_Fx_Fy_Mz"],
                "scope": session.task["required_scope"], "explanation": "The revised displacement exceeds the prescribed limit."}

    def test_demo_passes_automatic_checks_but_requires_human_review(self):
        run_demo(self.root)
        result = grade(self.root)
        self.assertTrue(result["automated_success"], result)
        self.assertTrue(result["human_review_required"])
        self.assertIsNone(result["research_success"])
        self.assertEqual(result["metrics"]["tool_calls"], 15)
        self.assertEqual(read_json(self.root / "report.json")["criterion_status"], "fail")

    def test_wrong_engineering_conclusion_fails_even_with_coordinated_files(self):
        session, result = self.revised_session()
        report = self.report(session, result)
        report["criterion_status"] = "pass"
        self.call(session, "report.write", report=report)
        self.call(session, "submission.submit")
        scored = grade(self.root)
        self.assertFalse(scored["automated_success"])
        self.assertFalse(scored["checks"]["correct_criterion_assessment"])
        self.assertTrue(scored["checks"]["report_artifact_integrity"])

    def test_model_edit_invalidates_all_dependent_state(self):
        session, result = self.revised_session()
        self.call(session, "report.write", report=self.report(session, result))
        model = deepcopy(session.expected)
        model["nodes"]["4"][0] = 9
        self.call(session, "model.put", model=model)
        for field in ("validated_sha256", "active_result", "inspected_run_id", "drawing", "report"):
            self.assertIsNone(session.state[field])
        self.assertFalse(session.call("results.get", {"run_id": result["run_id"]})["ok"])
        self.assertFalse(session.call("submission.submit")["ok"])

    def test_wrong_revision_and_changed_section_fail(self):
        session, _ = self.revised_session()
        model = deepcopy(session.expected)
        model["revision"] = "A"
        model["sections"]["COLUMN"]["I_m4"] *= 2
        self.call(session, "model.put", model=model)
        self.call(session, "model.validate")
        result = self.call(session, "solver.run")
        result = self.call(session, "results.get", run_id=result["run_id"])
        self.call(session, "drawing.render")
        self.call(session, "report.write", report=self.report(session, result))
        self.call(session, "submission.submit")
        scored = grade(self.root)
        self.assertFalse(scored["checks"]["revision_applied"])
        self.assertFalse(scored["checks"]["engineering_constraints_preserved"])

    def test_uninspected_results_and_duplicate_review_rejected(self):
        session, _ = self.revised_session()
        self.assertFalse(session.call("review.request")["ok"])
        latest = self.call(session, "solver.run")
        result = read_json(self.root / "results" / (latest["run_id"] + ".json"))
        self.assertFalse(session.call("report.write", {"report": self.report(session, result)})["ok"])

    def test_external_artifact_edits_and_trace_removal_fail_closed(self):
        run_demo(self.root)
        (self.root / "drawing.svg").write_text("stale drawing")
        trace = self.root / ".evaluator/trace.jsonl"
        trace.write_text("\n".join(trace.read_text().splitlines()[1:]) + "\n")
        scored = grade(self.root)
        self.assertFalse(scored["checks"]["current_drawing"])
        self.assertFalse(scored["checks"]["trace_integrity_and_checkpoint_order"])

    def test_corrupt_model_is_a_failed_grade(self):
        run_demo(self.root)
        (self.root / "model.json").write_text("{bad-json")
        scored = grade(self.root)
        self.assertFalse(scored["automated_success"])
        self.assertFalse(scored["checks"]["model_contract"])

    def test_submission_is_terminal(self):
        session = run_demo(self.root)
        self.assertFalse(session.call("model.put", {"model": session.initial})["ok"])
        self.assertEqual(session.state["phase"], "submitted")


if __name__ == "__main__":
    unittest.main()
