"""Internal process entry point; stdout is JSON only."""

import importlib.metadata
import json
import sys

from .model import canonical, digest, equilibrium_residual, validate_model


def main():
    import openseespy.opensees as ops

    model = json.load(sys.stdin)
    validate_model(model)
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    for key, xy in model["nodes"].items():
        ops.node(int(key), *xy)
    for key, flags in model["supports"].items():
        ops.fix(int(key), *flags)
    ops.geomTransf("Linear", 1)
    for key, element in model["elements"].items():
        section = model["sections"][element["section"]]
        ops.element("elasticBeamColumn", int(key), *map(int, element["nodes"]),
                    section["A_m2"], section["E_Pa"], section["I_m4"], 1)
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for key, values in model["load_case"]["nodal"].items():
        ops.load(int(key), *values)
    for key, q in model["load_case"]["uniform"].items():
        ops.eleLoad("-ele", int(key), "-type", "-beamUniform", q)
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")
    code = ops.analyze(1)
    if code != 0:
        raise RuntimeError(f"OpenSees analyze returned {code}")
    ops.reactions()
    displacements = {key: ops.nodeDisp(int(key)) for key in model["nodes"]}
    reactions = {key: ops.nodeReaction(int(key)) for key in model["supports"]}
    forces = {key: ops.eleResponse(int(key), "localForce") for key in model["elements"]}
    result = {
        "status": "converged", "model_sha256": digest(model), "revision": model["revision"],
        "load_case": model["load_case"]["name"], "units": "N-m-rad",
        "solver": {"name": "OpenSeesPy", "package_version": importlib.metadata.version("openseespy"),
                   "engine_version": ops.version(), "python_version": sys.version.split()[0]},
        "displacements": displacements, "reactions": reactions, "element_local_forces": forces,
        "equilibrium_residual_Fx_Fy_Mz": equilibrium_residual(model, reactions),
        "max_abs_ux_m": max(abs(value[0]) for value in displacements.values()),
        "warnings": ["Linear elastic first-order results; no strength or stability design certification."],
    }
    print(canonical(result))
    ops.wipe()


if __name__ == "__main__":
    main()
