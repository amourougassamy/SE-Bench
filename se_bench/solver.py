"""Run each OpenSees analysis in an isolated subprocess (OpenSees is stateful)."""

import importlib.util
import json
import os
import subprocess
import sys

from .model import ContractError, canonical, digest, validate_model


def available():
    return importlib.util.find_spec("openseespy") is not None


def solve(model, timeout_s=30):
    validate_model(model)
    if not available():
        raise ContractError("OpenSeesPy is unavailable. Install with: python -m pip install -e '.[solver]'")
    env = os.environ.copy()
    # Linux wheels initialize MPI even for this serial adapter. Resolve the
    # local interface explicitly in containers whose hostname has no address.
    env.setdefault("MPICH_INTERFACE_HOSTNAME", "localhost")
    try:
        process = subprocess.run([sys.executable, "-m", "se_bench.solver_worker"],
                                 input=canonical(model), text=True, capture_output=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired as exc:
        raise ContractError(f"Solver exceeded {timeout_s} seconds; no usable result") from exc
    if process.returncode:
        raise ContractError(f"Solver failed (exit {process.returncode}): {process.stderr[-1500:]}")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ContractError("Solver returned invalid JSON; no usable result") from exc
    if result.get("status") != "converged" or result.get("model_sha256") != digest(model):
        raise ContractError("Solver did not produce a converged result for the current model")
    canonical(result)  # Reject NaN/Infinity even if a solver returned them.
    return result
