"""A scripted reference client, not an AI baseline or measured model result."""

from .model import ContractError
from .runtime import Session


def run_demo(workspace):
    session = Session.create(workspace, agent_id="scripted-reference-client")

    def call(name, **args):
        response = session.call(name, args)
        if not response["ok"]:
            raise ContractError(response["error"]["message"])
        return response["data"]

    package = call("task.read")
    call("model.get")
    call("model.validate")
    baseline = call("solver.run")
    call("results.get", run_id=baseline["run_id"])
    call("drawing.render")
    review = call("review.request")
    model = call("model.get")["model"]
    changes = review["changes"]
    model["revision"] = changes["revision"]
    model["nodes"].update(changes["nodes"])
    model["load_case"]["uniform"].update(changes["uniform"])
    call("model.put", model=model)
    call("model.validate")
    analysis = call("solver.run")
    result = call("results.get", run_id=analysis["run_id"])
    roof = {node: abs(result["displacements"][node][0]) for node in ("3", "4")}
    governing = max(roof, key=roof.get)
    displacement = roof[governing]
    limit = package["criteria"]["max_roof_horizontal_displacement_m"]
    status = "pass" if displacement <= limit else "fail"
    call("drawing.render")
    call("report.write", report={
        "run_id": analysis["run_id"], "max_roof_ux_m": displacement,
        "governing_node": governing, "criterion_status": status,
        "equilibrium_residual_Fx_Fy_Mz": result["equilibrium_residual_Fx_Fy_Mz"],
        "scope": package["required_scope"],
        "explanation": (f"After the instructed span and load revision, the maximum absolute roof horizontal "
                        f"displacement is {displacement*1000:.6f} mm at node {governing}. "
                        f"Against the unchanged {limit*1000:g} mm limit, the assessment is {status}. "
                        "Sections and base restraints were retained. Global force and moment residuals "
                        "are negligible. Engineering review is required before choosing any remedial "
                        "change; this assessment does not establish strength or stability adequacy.")})
    call("submission.submit")
    return session
