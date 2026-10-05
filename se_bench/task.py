"""Frozen public development fixture and evaluator-side task expectations."""

from copy import deepcopy
from importlib.resources import files
import json

from .drawing import render
from .model import digest


def load_task():
    root = files("se_bench").joinpath("tasks/portal_revision")
    task = json.loads(root.joinpath("task.json").read_text())
    initial = json.loads(root.joinpath("starting_model.json").read_text())
    brief = root.joinpath("brief.md").read_text()
    final = deepcopy(initial)
    changes = task["review_event"]["changes"]
    final["revision"] = changes["revision"]
    final["nodes"].update(changes["nodes"])
    final["load_case"]["uniform"].update(changes["uniform"])
    reference = json.loads(root.joinpath("reference_results.json").read_text())
    task_hash = digest({"task": task, "initial": initial, "brief": brief, "reference": reference})
    return task, initial, final, brief, task_hash


def reference_results():
    return json.loads(files("se_bench").joinpath("tasks/portal_revision/reference_results.json").read_text())


def public_package():
    task, initial, _, brief, task_hash = load_task()
    return {"id": task["id"], "version": task["version"], "status": task["status"],
            "task_sha256": task_hash, "brief": brief, "criteria": task["criteria"],
            "required_scope": task["required_scope"], "starting_model": initial,
            "starting_drawing_svg": render(initial), "max_tool_calls": task["max_tool_calls"]}
