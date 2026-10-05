# Working on SE-Bench

- Preserve the project focus: complete structural-engineering workflows using
  standard tools, with persistent goals, drawing/model coordination, human
  steering, and defensible interpretation of solver results.
- Keep agent/provider adapters separate from task definitions, engineering tool
  adapters, and evaluator logic.
- Use real solvers for engineering execution. Label mocks and scripted reference
  clients explicitly; do not present them as evaluated AI agents.
- Treat changes to a model or load case as invalidating dependent analysis and
  deliverables. Maintain units, axes, solver versions, and artifact provenance.
- Prefer tests of engineering failure modes and workflow consistency. Run the
  stdlib unittest suite with the pinned solver extra for integration verification.
- Keep development fixtures clearly distinguished from independently reviewed
  benchmark tasks. Do not claim publication readiness or research success while
  oracle review, human grading, or evaluation isolation remain incomplete.
- Do not put credentials, proprietary drawings, or unlicensed code extracts in
  the repository. Keep run artifacts and virtual environments untracked.
