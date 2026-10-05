"""Stateful tool host for trusted local development runs.

Evaluator state lives outside the tool-visible artifact set, but this filesystem
layout is NOT a sandbox. See docs/protocol.md before running untrusted agents.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from . import __version__
from .drawing import render
from .model import ContractError, canonical, digest, exact_keys, number, validate_model
from .solver import solve
from .task import load_task, public_package
from .tools import BY_NAME, TOOLS


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hash():
    return digest({p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))})


def report_markdown(report):
    return (f"# Portal frame assessment — revision {report['revision']}\n\n"
            f"Model SHA256: `{report['model_sha256']}`\n\n"
            f"Analysis: `{report['run_id']}`\n\n"
            f"Maximum roof horizontal displacement: **{report['max_roof_ux_m'] * 1000:.6f} mm**\n\n"
            f"Governing node: {report['governing_node']}\n\n"
            f"Prescribed limit: {report['limit_m'] * 1000:g} mm. Assessment: **{report['criterion_status'].upper()}**.\n\n"
            f"Equilibrium residual [Fx N, Fy N, Mz N.m]: {report['equilibrium_residual_Fx_Fy_Mz']}\n\n"
            f"{report['explanation']}\n\n"
            f"Scope: {report['scope']}\n")


class Session:
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()
        self.control = self.root / ".evaluator"
        self.state_path = self.control / "state.json"
        self.task, self.initial, self.expected, _, self.task_hash = load_task()
        if not self.state_path.is_file():
            raise ContractError("Workspace is not initialized; run se-bench init first")
        self.state = read_json(self.state_path)
        if self.state["task_sha256"] != self.task_hash:
            raise ContractError("Task changed since initialization; create a fresh workspace")
        if self.state["implementation_sha256"] != implementation_hash():
            raise ContractError("Runner changed since initialization; create a fresh workspace")

    @classmethod
    def create(cls, workspace, agent_id="unspecified"):
        root = Path(workspace).resolve()
        if root.exists() and any(root.iterdir()):
            raise ContractError("Refusing to overwrite a nonempty workspace")
        root.mkdir(parents=True, exist_ok=True)
        (root / ".evaluator").mkdir()
        (root / "results").mkdir()
        task, initial, _, _, task_hash = load_task()
        write_json(root / "model.json", initial)
        write_json(root / "task_package.json", public_package())
        (root / "starting_drawing.svg").write_text(render(initial))
        state = {"schema_version": 1, "task_id": task["id"], "task_sha256": task_hash,
                 "runner_version": __version__, "implementation_sha256": implementation_hash(),
                 "agent_id": agent_id, "started_at": datetime.now(timezone.utc).isoformat(),
                 "phase": "baseline", "call_count": 0, "error_count": 0, "trace_head": "",
                 "model_sha256": digest(initial), "validated_sha256": None,
                 "active_result": None, "inspected_run_id": None, "drawing": None,
                 "report": None, "review": None, "submission": None}
        write_json(root / ".evaluator/state.json", state)
        (root / ".evaluator/trace.jsonl").touch()
        return cls(root)

    def _model(self):
        model = read_json(self.root / "model.json")
        if digest(model) != self.state["model_sha256"]:
            raise ContractError("Model was edited outside model.put; artifact integrity failed")
        return model

    def _result(self):
        info = self.state["active_result"]
        if not info or info["model_sha256"] != self.state["model_sha256"]:
            raise ContractError("No current analysis; validate and run the solver")
        path = self.root / info["path"]
        if not path.is_file() or file_hash(path) != info["file_sha256"]:
            raise ContractError("Analysis artifact integrity failed")
        result = read_json(path)
        if result["model_sha256"] != self.state["model_sha256"] or result["status"] != "converged":
            raise ContractError("Analysis result is stale or unusable")
        return result

    def _drawing(self):
        info = self.state["drawing"]
        path = self.root / "drawing.svg"
        if not info or info["model_sha256"] != self.state["model_sha256"] or not path.is_file() or file_hash(path) != info["file_sha256"]:
            raise ContractError("No intact drawing for the current model; call drawing.render")
        return info

    def call(self, name, arguments=None):
        arguments = {} if arguments is None else arguments
        started = time.monotonic()
        # Reject values that cannot safely be represented in the audit log.
        try:
            canonical(arguments)
        except (ValueError, TypeError):
            arguments = {"invalid_payload": repr(arguments)[:500]}
        self.state["call_count"] += 1
        try:
            if self.state["call_count"] > self.task["max_tool_calls"]:
                raise ContractError("Tool-call budget exhausted")
            if self.state["phase"] == "submitted":
                raise ContractError("Submission is terminal; create another workspace for a new attempt")
            if name not in BY_NAME:
                raise ContractError(f"Unknown tool: {name}")
            schema = BY_NAME[name]["parameters"]
            exact_keys(arguments, schema["required"], "arguments")
            for key, spec in schema["properties"].items():
                if spec["type"] == "object" and not isinstance(arguments[key], dict):
                    raise ContractError(f"{key} must be an object")
                if spec["type"] == "string" and not isinstance(arguments[key], str):
                    raise ContractError(f"{key} must be a string")
            data = self._dispatch(name, arguments)
            response = {"ok": True, "data": data}
        except (ContractError, OSError, KeyError, TypeError, ValueError) as exc:
            self.state["error_count"] += 1
            response = {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
        entry = {"sequence": self.state["call_count"], "timestamp": datetime.now(timezone.utc).isoformat(),
                 "tool": name, "arguments": arguments, "response": response,
                 "duration_s": round(time.monotonic() - started, 6), "phase_after": self.state["phase"],
                 "previous_sha256": self.state["trace_head"]}
        entry["sha256"] = digest(entry)
        with (self.control / "trace.jsonl").open("a") as handle:
            handle.write(canonical(entry) + "\n")
        self.state["trace_head"] = entry["sha256"]
        write_json(self.state_path, self.state)
        return response

    def _dispatch(self, name, args):
        if name == "task.read":
            return public_package()
        model = self._model()
        current = self.state["model_sha256"]
        if name == "model.get":
            return {"model": model, "model_sha256": current}
        if name == "model.put":
            updated = args["model"]
            validate_model(updated)
            write_json(self.root / "model.json", updated)
            self.state.update(model_sha256=digest(updated), validated_sha256=None,
                              active_result=None, inspected_run_id=None, drawing=None, report=None)
            return {"model_sha256": self.state["model_sha256"], "revision": updated["revision"],
                    "invalidated": ["validation", "active_result", "drawing", "report"]}
        if name == "model.validate":
            validation = validate_model(model)
            self.state["validated_sha256"] = current
            return {**validation, "model_sha256": current}
        if name == "solver.run":
            if self.state["validated_sha256"] != current:
                raise ContractError("Validate the current model before analysis")
            result = solve(model, timeout_s=self.task["solver_timeout_s"])
            run_id = f"run-{self.state['call_count']:04d}"
            result["run_id"] = run_id
            path = self.root / "results" / f"{run_id}.json"
            write_json(path, result)
            self.state["active_result"] = {"run_id": run_id, "path": str(path.relative_to(self.root)),
                                           "model_sha256": current, "file_sha256": file_hash(path)}
            self.state["inspected_run_id"] = None
            self.state["report"] = None
            return {"run_id": run_id, "status": result["status"], "model_sha256": current,
                    "solver": result["solver"], "warnings": result["warnings"]}
        if name == "results.get":
            result = self._result()
            if args["run_id"] != result["run_id"]:
                raise ContractError("Requested run is not the active analysis")
            self.state["inspected_run_id"] = result["run_id"]
            return result
        if name == "drawing.render":
            text = render(model)
            (self.root / "drawing.svg").write_text(text)
            self.state["drawing"] = {"model_sha256": current, "file_sha256": file_hash(self.root / "drawing.svg")}
            return {"path": "drawing.svg", "model_sha256": current, "svg": text}
        if name == "review.request":
            if self.state["phase"] != "baseline":
                raise ContractError("The engineer revision has already been issued")
            if model != self.initial:
                raise ContractError("Baseline review must assess the supplied initial model")
            result = self._result()
            self._drawing()
            if self.state["inspected_run_id"] != result["run_id"]:
                raise ContractError("Inspect baseline results before requesting review")
            self.state["review"] = {"event": self.task["review_event"], "baseline_result": self.state["active_result"].copy(),
                                    "baseline_model": model, "baseline_drawing": self.state["drawing"].copy(),
                                    "sequence": self.state["call_count"]}
            self.state["phase"] = "revision"
            return self.task["review_event"]
        if name == "report.write":
            if self.state["phase"] != "revision":
                raise ContractError("Final report requires the engineer's revision")
            result = self._result()
            if self.state["inspected_run_id"] != result["run_id"]:
                raise ContractError("Inspect current analysis results before reporting")
            report = args["report"]
            exact_keys(report, ["run_id", "max_roof_ux_m", "governing_node", "criterion_status",
                                "equilibrium_residual_Fx_Fy_Mz", "scope", "explanation"], "report")
            if report["run_id"] != result["run_id"]:
                raise ContractError("Report must cite the current analysis")
            value = number(report["max_roof_ux_m"], "max_roof_ux_m")
            if value < 0:
                raise ContractError("Maximum absolute displacement cannot be negative")
            if report["criterion_status"] not in ("pass", "fail"):
                raise ContractError("criterion_status must be pass or fail")
            if not isinstance(report["governing_node"], str) or report["governing_node"] not in model["nodes"]:
                raise ContractError("governing_node must identify an existing node")
            residual = report["equilibrium_residual_Fx_Fy_Mz"]
            if not isinstance(residual, list) or len(residual) != 3:
                raise ContractError("Equilibrium residual must contain three numbers")
            for value in residual:
                number(value, "equilibrium residual")
            for field in ("scope", "explanation"):
                if not isinstance(report[field], str) or not report[field].strip() or len(report[field]) > 5000:
                    raise ContractError(f"{field} must contain 1 to 5000 characters")
            report = {**report, "model_sha256": current, "revision": model["revision"],
                      "limit_m": self.task["criteria"]["max_roof_horizontal_displacement_m"]}
            write_json(self.root / "report.json", report)
            (self.root / "report.md").write_text(report_markdown(report))
            self.state["report"] = {"model_sha256": current, "file_sha256": file_hash(self.root / "report.json"),
                                     "markdown_sha256": file_hash(self.root / "report.md"), "run_id": result["run_id"]}
            return {"paths": ["report.json", "report.md"], "model_sha256": current,
                    "notice": "Recorded; assessment correctness is checked by the evaluator."}
        if name == "submission.submit":
            if self.state["phase"] != "revision":
                raise ContractError("Complete the engineer revision before submission")
            result = self._result()
            self._drawing()
            info = self.state["report"]
            if not info or info["model_sha256"] != current or info["run_id"] != result["run_id"]:
                raise ContractError("No report for the current model and analysis")
            if any(not (self.root / path).is_file() or file_hash(self.root / path) != info[key]
                   for path, key in [("report.json", "file_sha256"), ("report.md", "markdown_sha256")]):
                raise ContractError("Report artifact integrity failed")
            self.state["phase"] = "submitted"
            self.state["submission"] = {"model_sha256": current, "run_id": result["run_id"],
                                        "sequence": self.state["call_count"], "submitted_at": datetime.now(timezone.utc).isoformat()}
            return {"submitted": True, "run_id": result["run_id"], "model_sha256": current}
        raise ContractError("Unimplemented tool")

    @staticmethod
    def tools():
        return TOOLS
