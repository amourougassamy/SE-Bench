# Benchmark design

## Research question

Can an AI system sustain an engineering objective across a long sequence of
standard-tool operations, design iterations, and human revisions while keeping
its model, analysis, drawings, and engineering conclusions consistent?

Long horizon means persistent dependencies and opportunities to lose state. It
is not defined by elapsed solver time, verbosity, or tool-call count alone.
The first small fixture validates infrastructure; the corpus must grow to
meaningfully test this question.

## Unit of evaluation

A work package consists of starting documents/models, an engineering objective,
available tools, prescribed human interactions, final deliverables, and
independently verified acceptance criteria. Agents may use different valid plans
and may coordinate specialized vision/drawing agents. Their internal architecture
is not prescribed.

The current fixture uses a supplied, labeled model and a canonical schematic
renderer. Its narrow contract intentionally preserves node/element identifiers.
Later design tasks must accept equivalent valid models and drawings rather than
requiring exact agreement with one authored solution.

## Three pillars

| Pillar | Observable evidence | Future diagnostic measures |
| --- | --- | --- |
| Goal persistence and coordination | Preserved constraints, correct revisions, coordinated artifacts | Revision propagation, forgotten requirements, stale deliverables |
| Precise tool use | Correct model/tool semantics, inspected return states, recovery | Semantic error categories, recoveries, invalid operations |
| Engineering interpretation | Valid conclusions, governing results, limits and appropriate requests for help | Unsupported conclusions, missed failures, needless abstention |

Tool execution success is reported separately from semantic correctness. A valid
API request can still analyze the wrong revision or load case.

## Human steering

Each task should specify the initial brief, clarification facts, review
checkpoints, conditional event rules, and allowed actions. Event rules should
depend on engineering state rather than an arbitrary call number. Every system
receives equivalent information and revision instructions under the same policy.

Separate mandatory review, necessary clarification, and rescue from an agent
mistake. Record human intervention content and timing. The current fixture has
one deterministic revision and no free-form clarification oracle.

## Scoring

The intended primary measure is complete work-package success, requiring all
critical engineering gates and relevant human review. Report diagnostic stages
to explain failures without allowing presentation quality to compensate for an
incorrect model or conclusion.

Current `automated_success` requires all 20 implemented checks. The reference
client passes them while correctly reporting that the revised structure fails
its displacement criterion. `research_success` is explicitly unset; narrative
quality, independent oracle review, and isolated evaluation are unfinished.

Runtime traces record calls, errors, per-tool duration, task/source fingerprints,
solver versions, and checkpoint order. They do not yet capture provider token
usage, monetary cost, confidence calibration, or human rescue costs. Do not
report those metrics as measured by this implementation.

## Pilot and study plan

1. Validate the current lifecycle and artifact consistency mechanics.
2. Add real agent bridges and a second solver/application adapter.
3. Author several longer work packages with alternative valid solution paths,
   several revisions, and delayed error discovery.
4. Obtain two-engineer independent review of task truth and critical gates.
5. Run a human pilot; resolve ambiguous grading and estimate variation.
6. Freeze development/test splits by work-package family and project. All
   geometry/numerical/format variants stay together.
7. Compare agent-plus-tool configurations under declared resource and steering
   policies. Repeat runs and estimate uncertainty clustered by family.

Keep controlled comparison of reasoning agents separate from comparison of
complete products with different tools. Test harness-specific advantages with
ablations, including supplied geometry versus drawing interpretation, complete
versus revised tasks, and available versus unavailable domain tools.

## Existing work and novelty

The candidate contribution combines persistent project state, real engineering
tools, controlled steering, and consistency across final deliverables. Novelty
has not been established. Relevant benchmarks for detailed comparison include:

- [AECBench](https://arxiv.org/abs/2509.18776): AEC knowledge and application tasks.
- [Nomic AEC-Bench](https://github.com/nomic-ai/aec-bench): multimodal document workflows.
- [StructureClaw-Bench](https://github.com/structureclaw/structureclaw-benchmark): structural workflows and interactive robustness.

Compare actual task definitions, evaluation boundaries, and intervention
protocols before making a publication claim. This repository has no model
leaderboard or evaluated AI results yet.
