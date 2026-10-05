"""Portable, explicit SI model contract for the initial linear 2D adapter."""

import hashlib
import json
import math


class ContractError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ContractError(f"{label} requires exactly these fields: {', '.join(expected)}")


def number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError(f"{label} must be a finite number")
    if positive and value <= 0:
        raise ContractError(f"{label} must be positive")
    return float(value)


def tag(value, label):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or not (0 < int(value) < 1000000) or str(int(value)) != value:
        raise ContractError(f"{label} must be a canonical positive integer string below 1000000")


def validate_model(model):
    exact_keys(model, ["revision", "units", "analysis", "nodes", "sections", "elements", "supports", "load_case"], "model")
    if model["units"] != "N-m-Pa" or model["analysis"] != "linear_static_2d":
        raise ContractError("This adapter requires N-m-Pa units and linear_static_2d analysis")
    if not isinstance(model["revision"], str) or not model["revision"] or len(model["revision"]) > 40:
        raise ContractError("revision must be a nonempty string of at most 40 characters")
    nodes, sections, elements = model["nodes"], model["sections"], model["elements"]
    for label, value in [("nodes", nodes), ("sections", sections), ("elements", elements)]:
        if not isinstance(value, dict) or not value or len(value) > 200:
            raise ContractError(f"{label} must be a nonempty object with at most 200 entries")
    for key, xy in nodes.items():
        tag(key, "node id")
        if not isinstance(xy, list) or len(xy) != 2:
            raise ContractError(f"node {key} requires [x, y]")
        for v in xy:
            number(v, "node coordinate")
    for name, sec in sections.items():
        if not isinstance(name, str) or not name or len(name) > 60:
            raise ContractError("section name must contain 1 to 60 characters")
        exact_keys(sec, ["A_m2", "E_Pa", "I_m4"], f"section {name}")
        for key, value in sec.items():
            number(value, key, positive=True)
    graph = {key: set() for key in nodes}
    for key, element in elements.items():
        tag(key, "element id")
        exact_keys(element, ["nodes", "section"], f"element {key}")
        ends = element["nodes"]
        if not isinstance(ends, list) or len(ends) != 2 or any(not isinstance(n, str) or n not in nodes for n in ends):
            raise ContractError(f"element {key} requires two existing node ids")
        if ends[0] == ends[1] or math.dist(nodes[ends[0]], nodes[ends[1]]) < 1e-9:
            raise ContractError(f"element {key} has zero length")
        if not isinstance(element["section"], str) or element["section"] not in sections:
            raise ContractError(f"element {key} references an unknown section")
        graph[ends[0]].add(ends[1])
        graph[ends[1]].add(ends[0])
    supports = model["supports"]
    if not isinstance(supports, dict) or not supports:
        raise ContractError("supports must be a nonempty object")
    for node, dofs in supports.items():
        if node not in nodes or not isinstance(dofs, list) or len(dofs) != 3 or any(type(v) is not int or v not in (0, 1) for v in dofs):
            raise ContractError("support requires an existing node and [ux, uy, rz] restraint flags 0 or 1")
    reached, todo = set(), list(supports)
    while todo:
        node = todo.pop()
        if node not in reached:
            reached.add(node)
            todo.extend(graph[node] - reached)
    if reached != set(nodes):
        raise ContractError("every node must be connected to a support")
    case = model["load_case"]
    exact_keys(case, ["name", "nodal", "uniform"], "load_case")
    if not isinstance(case["name"], str) or not case["name"] or len(case["name"]) > 60:
        raise ContractError("load case name must contain 1 to 60 characters")
    for key in ("nodal", "uniform"):
        if not isinstance(case[key], dict):
            raise ContractError(f"load_case.{key} must be an object")
    for node, values in case["nodal"].items():
        if node not in nodes or not isinstance(values, list) or len(values) != 3:
            raise ContractError("nodal load requires existing node and [Fx_N, Fy_N, Mz_Nm]")
        for v in values:
            number(v, "nodal load")
    for element, value in case["uniform"].items():
        if element not in elements:
            raise ContractError("uniform load references an unknown element")
        number(value, "local_y_uniform_load_N_per_m")
    return {"valid": True, "node_count": len(nodes), "element_count": len(elements),
            "limitations": ["linear elastic 2D only", "validation does not prove stability", "no code strength checks"]}


def load_resultant(model):
    """Global Fx, Fy, Mz about origin, including local-y distributed loads."""
    fx = fy = mz = 0.0
    for node, values in model["load_case"]["nodal"].items():
        x, y = model["nodes"][node]
        px, py, moment = values
        fx += px
        fy += py
        mz += moment + x * py - y * px
    for key, q in model["load_case"]["uniform"].items():
        i, j = model["elements"][key]["nodes"]
        xi, yi = model["nodes"][i]
        xj, yj = model["nodes"][j]
        px, py = -q * (yj - yi), q * (xj - xi)
        fx += px
        fy += py
        mz += (xi + xj) / 2 * py - (yi + yj) / 2 * px
    return [fx, fy, mz]


def equilibrium_residual(model, reactions):
    residual = load_resultant(model)
    for node, values in reactions.items():
        x, y = model["nodes"][node]
        fx, fy, mz = values
        residual[0] += fx
        residual[1] += fy
        residual[2] += mz + x * fy - y * fx
    return residual
