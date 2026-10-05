# Contributing

SE-Bench targets complete engineering work packages with standard tools and
human steering. New tasks should define a starting state, objective, constraints,
available tools, interaction policy, and coordinated final deliverables.

Include the following before a task becomes a scored research item:

- Input provenance and redistribution rights.
- Explicit units, axes, signs, material properties, load cases and code editions
  where applicable.
- An engineering reference with an independent check and recorded reviewers.
- Allowed alternative models/designs and fixture-specific tolerances.
- Critical failure gates and diagnostic criteria.
- Human intervention scripts with conditional triggers and information budgets.
- Variant/family/project identifiers to prevent split leakage.
- Agent-visible assets separated from evaluator-only answers and event scripts.
- Tests that catch wrong engineering outcomes, stale artifacts, and broken
  workflow dependencies, rather than merely testing the reference script.

Do not use an LLM alone to establish engineering ground truth. Do not require
private chain-of-thought: grade observable operations, calculations, evidence,
and conclusions. Do not interpret a scripted reference client as an AI baseline.

For code changes, run `python -m unittest discover -s tests -v` with the solver
extra installed. Use a new workspace for demos after changing task or runtime
source; the runner intentionally rejects stale fingerprints.
