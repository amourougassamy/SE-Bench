"""Provider-neutral JSON Schema descriptions; no model/vendor dependency."""


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def vector(length, item=None):
    return {"type": "array", "items": item or {"type": "number"}, "minItems": length, "maxItems": length}


def mapping(value):
    return {"type": "object", "additionalProperties": value, "maxProperties": 200}


MODEL_SCHEMA = obj({
    "revision": {"type": "string", "minLength": 1, "maxLength": 40},
    "units": {"type": "string", "const": "N-m-Pa"},
    "analysis": {"type": "string", "const": "linear_static_2d"},
    "nodes": mapping(vector(2)),
    "sections": mapping(obj({key: {"type": "number", "exclusiveMinimum": 0} for key in ("A_m2", "E_Pa", "I_m4")})),
    "elements": mapping(obj({"nodes": vector(2, {"type": "string"}), "section": {"type": "string"}})),
    "supports": mapping(vector(3, {"type": "integer", "enum": [0, 1]})),
    "load_case": obj({"name": {"type": "string", "minLength": 1, "maxLength": 60},
                      "nodal": mapping(vector(3)), "uniform": mapping({"type": "number"})}),
})

REPORT_SCHEMA = obj({
    "run_id": {"type": "string"}, "max_roof_ux_m": {"type": "number", "minimum": 0},
    "governing_node": {"type": "string"}, "criterion_status": {"type": "string", "enum": ["pass", "fail"]},
    "equilibrium_residual_Fx_Fy_Mz": vector(3),
    "scope": {"type": "string", "minLength": 1, "maxLength": 5000},
    "explanation": {"type": "string", "minLength": 1, "maxLength": 5000},
})

def definition(name, description, properties=None):
    properties = properties or {}
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties), "additionalProperties": False}}


TOOLS = [
    definition("task.read", "Read the brief, initial model/schematic, criteria, constraints, and tool-call budget."),
    definition("model.get", "Read the current model and its content hash."),
    definition("model.put", "Replace the model. Successful edits invalidate active validation, analysis, drawing, and report. Units N-m-Pa; global x-right/y-up; local-y element loads.",
               {"model": MODEL_SCHEMA}),
    definition("model.validate", "Validate units, finite positive section properties, topology, supports and loads. This does not prove stability."),
    definition("solver.run", "Run OpenSees linear elastic 2D analysis for the validated current model; return run id and solver status."),
    definition("results.get", "Inspect current analysis results, warnings, displacement and reaction fields. Superseded results cannot support current deliverables.",
               {"run_id": {"type": "string"}}),
    definition("drawing.render", "Generate an SVG schematic of the current model, tagged with its revision and hash. This is not a construction detail."),
    definition("review.request", "Request the scripted engineer revision after valid baseline analysis, result inspection, and schematic. Available once."),
    definition("report.write", "Write a structured assessment and Markdown report for the current inspected analysis. Provide run_id, max_roof_ux_m, governing_node, criterion_status ('pass' or 'fail'), equilibrium_residual_Fx_Fy_Mz (3 numbers), scope (task required_scope), and explanation (nonempty text).",
               {"report": REPORT_SCHEMA}),
    definition("submission.submit", "Finalize the current coordinated deliverables. Submission is terminal; assessment correctness is evaluated separately."),
]

BY_NAME = {tool["name"]: tool for tool in TOOLS}
