# Roadmap

## Implemented in this first increment

- [x] Provider-neutral tool schemas and JSON-lines host.
- [x] Explicit model units/axes/load contract with validation.
- [x] Real OpenSeesPy subprocess adapter with pinned Linux dependencies.
- [x] Baseline → scripted human revision → final submission lifecycle.
- [x] Revision/hash propagation and invalidation of dependent artifacts.
- [x] SVG schematic and JSON/Markdown assessment artifacts.
- [x] Evaluator for numerical results, equilibrium, constraints, provenance,
      updated drawings, and correct criterion assessment.
- [x] Scripted reference client and automated regression/integration tests.

## Next: usable AI pilot

1. Add a model-provider bridge that maps tool schemas, records exact model and
   decoding settings, and collects usage, cost, latency, retries, and failures.
2. Isolate the host/evaluator and unpublished fixtures from the evaluated agent.
3. Add bounded clarification and human-review responses; distinguish necessary
   clarification from rescue intervention.
4. Independently verify the portal reference and review explanation rubrics.
5. Add test cases for solver warnings, invalid geometry, recoverable tool errors,
   and revisions that invalidate earlier engineering conclusions.

## Next: genuinely sustained engineering packages

Candidate A — a small multi-bay framing revision with load take-down, separate
service/strength cases, multiple human changes, and coordinated drawings.

Candidate B — a floor opening relocation with diaphragm/collector checks,
several affected details, and an architectural revision after initial analysis.

Candidate C — an existing model investigation with incomplete diagnostics,
competing explanations, controlled reruns, and a documented repair.

Use real task dependency depth and revision burden to establish difficulty.
Avoid padding tasks with unnecessary tool calls or sleeps. Longer cases should
allow valid alternative workflows and designs.

## Adapters and vision

- Add a second standard engineering solver/application adapter to test
  portability; potential targets include ETABS or SAP2000 on an appropriately
  licensed Windows worker. No connection to those tools currently exists.
- Define a drawing-observation contract with sheet/detail evidence, geometry,
  confidence/ambiguity, and engineering relationships.
- Add diagram-only inputs once vision accuracy can be independently graded.
- Extend output checking from canonical schematics to equivalent valid drawings
  and coordinated details produced by standard drawing tools.
- Permit agent teams through the same serialized host API without prescribing
  a particular agent topology.

## Publication gates

- Complete item-level literature/benchmark overlap analysis.
- Establish redistribution rights and choose code/data licenses.
- Obtain independent expert reference and rubric review.
- Freeze family/project-level development and held-out splits.
- Run controlled human baselines and model-plus-tool experiments.
- Report clustered uncertainty, repeated-run variation, and failure taxonomy.
- Release reproducible public development tasks and study configuration.

No publication novelty, operational safety, broad engineering coverage, or
model capability claims are established by the current scaffold.
