"""Evaluator-side checks. Agents must not have access in held-out studies."""

import math

from .drawing import render
from .model import digest, equilibrium_residual, validate_model
from .runtime import Session, file_hash, read_json, report_markdown
from .task import reference_results


def close(actual, expected, rel_tol=1e-7, abs_tol=1e-8):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(close(actual[k], v, rel_tol, abs_tol) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(close(a, b, rel_tol, abs_tol) for a, b in zip(actual, expected))
    return (type(actual) in (int, float) and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol))


def grade(workspace):
    checks = {}
    errors = {}

    def check(name, function):
        try:
            checks[name] = bool(function())
        except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
            checks[name] = False
            errors[name] = str(exc)

    try:
        session = Session(workspace)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {"automated_success": False, "research_success": None, "human_review_required": True,
                "checks": {"workspace_integrity": False}, "errors": {"workspace_integrity": str(exc)}}
    state, root = session.state, session.root
    try:
        model = read_json(root / "model.json")
    except (OSError, ValueError):
        model = {}
    result_info = state.get("active_result") or {}
    report_info = state.get("report") or {}
    reference = reference_results()

    def result():
        return session._result()

    def report():
        return read_json(root / "report.json")

    def trace_valid():
        import json
        head = ""
        rows = []
        for sequence, line in enumerate((session.control / "trace.jsonl").read_text().splitlines(), 1):
            row = json.loads(line)
            saved = row.pop("sha256")
            if row["sequence"] != sequence or row["previous_sha256"] != head or digest(row) != saved:
                return False
            head = saved
            rows.append(row)
        if len(rows) != state["call_count"] or head != state["trace_head"]:
            return False
        review = [r for r in rows if r["tool"] == "review.request" and r["response"]["ok"]]
        submitted = [r for r in rows if r["tool"] == "submission.submit" and r["response"]["ok"]]
        return (len(review) == len(submitted) == 1
                and review[0]["sequence"] == state["review"]["sequence"]
                and submitted[0]["sequence"] == state["submission"]["sequence"]
                and review[0]["sequence"] < submitted[0]["sequence"]
                and review[0]["response"]["data"] == session.task["review_event"])

    check("submitted_after_human_revision", lambda: state["phase"] == "submitted" and state["review"] is not None and state["submission"] is not None)
    check("trace_integrity_and_checkpoint_order", trace_valid)
    check("within_tool_budget", lambda: state["call_count"] <= session.task["max_tool_calls"])
    check("model_contract", lambda: validate_model(model)["valid"])
    check("model_artifact_integrity", lambda: digest(model) == state["model_sha256"] == state["submission"]["model_sha256"])
    check("revision_applied", lambda: model["revision"] == session.expected["revision"] and model["nodes"] == session.expected["nodes"] and model["load_case"] == session.expected["load_case"])
    check("engineering_constraints_preserved", lambda: all(model[key] == session.initial[key] for key in ("sections", "supports", "elements", "units", "analysis")))

    def baseline_valid():
        review = state["review"]
        info = review["baseline_result"]
        baseline = read_json(root / info["path"])
        return (review["baseline_model"] == session.initial
                and info["file_sha256"] == file_hash(root / info["path"])
                and baseline["model_sha256"] == digest(session.initial)
                and all(close(baseline[field], reference["A"][field]) for field in ("displacements", "reactions", "element_local_forces")))

    check("baseline_analysis_valid", baseline_valid)
    check("current_analysis_provenance", lambda: result()["revision"] == model["revision"] and result()["run_id"] == state["submission"]["run_id"] and result()["load_case"] == model["load_case"]["name"])
    check("solver_version_recorded", lambda: all(result()["solver"].get(key) for key in ("name", "package_version", "engine_version", "python_version")))
    check("numerical_reference_agreement", lambda: all(close(result()[field], reference["B"][field]) for field in ("displacements", "reactions", "element_local_forces")))
    check("global_equilibrium", lambda: all(abs(v) <= 0.01 for v in equilibrium_residual(model, result()["reactions"])))
    check("current_drawing", lambda: session._drawing()["model_sha256"] == digest(model) and (root / "drawing.svg").read_text() == render(model))
    check("report_artifact_integrity", lambda: file_hash(root / "report.json") == report_info["file_sha256"] and file_hash(root / "report.md") == report_info["markdown_sha256"] and (root / "report.md").read_text() == report_markdown(report()))
    check("report_provenance", lambda: report()["model_sha256"] == digest(model) and report()["revision"] == model["revision"] and report()["run_id"] == result_info["run_id"])

    def roof_values():
        return {key: abs(result()["displacements"][key][0]) for key in ("3", "4")}

    check("reported_displacement", lambda: close(report()["max_roof_ux_m"], max(roof_values().values()), abs_tol=1e-9))
    check("governing_node", lambda: report()["governing_node"] in roof_values() and close(roof_values()[report()["governing_node"]], max(roof_values().values()), abs_tol=1e-9))
    limit = session.task["criteria"]["max_roof_horizontal_displacement_m"]
    check("correct_criterion_assessment", lambda: report()["limit_m"] == limit and report()["criterion_status"] == ("pass" if max(roof_values().values()) <= limit else "fail"))
    check("reported_equilibrium", lambda: close(report()["equilibrium_residual_Fx_Fy_Mz"], equilibrium_residual(model, result()["reactions"]), abs_tol=1e-6))
    check("scope_limitations_present", lambda: report()["scope"] == session.task["required_scope"])
    return {"task_id": session.task["id"], "task_sha256": session.task_hash,
            "agent_id": state["agent_id"], "automated_success": all(checks.values()),
            "research_success": None, "human_review_required": True,
            "human_review_note": "Engineering explanation, independent oracle review, and study isolation remain unvalidated.",
            "checks": checks, "errors": errors,
            "diagnostic_check_fraction": sum(checks.values()) / len(checks),
            "metrics": {"tool_calls": state["call_count"], "tool_errors": state["error_count"],
                        "tool_execution_success_rate": 1 - state["error_count"] / max(state["call_count"], 1),
                        "scripted_human_revisions": int(state["review"] is not None),
                        "started_at": state["started_at"],
                        "submitted_at": (state["submission"] or {}).get("submitted_at")}}
