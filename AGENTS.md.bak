# Codex Workflow

## Default Operating Model

- Keep the main agent on `gpt-5.5` with high reasoning for planning, architecture, coordination, integration, review, and final quality ownership.
- Treat the main agent as the single owner of the full task outcome. Subagents help with bounded execution, but the main agent remains responsible for correctness.
- Use planning mode for non-trivial work: discuss intent, constraints, acceptance criteria, risks, and implementation shape before executing.
- When the plan is complete, move from discussion to execution without re-litigating settled decisions unless new evidence changes the plan.

## Planning Workflow

- First understand the request and inspect the actual environment before asking questions.
- Convert the accepted plan into a task graph before implementation.
- Identify dependencies between tasks and classify each task as:
  - Blocking: required before other work can continue.
  - Parallelizable: independent file edits, tests, or verification that can run without blocking the main path.
  - Integration-sensitive: work that should stay with the main agent because it needs architectural judgment or tight coordination.
- Keep immediate blocking work on the main agent when waiting for a subagent would slow progress.

## Delegation Workflow

- After the task graph is clear, delegate eligible implementation and testing slices to `gpt-5.3-codex-spark` worker subagents.
- Delegate by default when a task has a clear boundary and can run in parallel with the main agent's next useful step.
- Each worker assignment must include:
  - The exact responsibility or file/module ownership.
  - The expected behavior change or verification target.
  - A reminder that other agents or the user may also have changes in the workspace.
  - An instruction not to revert unrelated changes.
  - A request to list changed files, tests run, failures, and blockers in the final response.
- Use disjoint write scopes for parallel workers whenever possible.
- Do not delegate work that is ambiguous, architecture-heavy, or immediately blocking the main path.
- If subagents are unavailable or delegation would add overhead without saving meaningful work, keep the task local.

## Main-Agent Takeover Rules

- Let subagents complete their bounded slices unless they report a concrete problem.
- The main agent takes over only the problematic slice when a worker reports:
  - A blocker it cannot resolve.
  - A failing test or build issue it cannot diagnose.
  - A merge conflict or incompatible concurrent edit.
  - An unclear requirement that affects implementation.
  - An integration issue discovered after worker output.
- When taking over, preserve the worker's useful changes, fix the specific problem, and avoid broad rewrites unless necessary for correctness.

## Integration And Verification

- Review each worker result before treating it as complete.
- Integrate worker changes in dependency order according to the task graph.
- Run the narrowest useful tests for each changed slice, then run broader verification when shared behavior, public APIs, or user-facing workflows changed.
- If final verification cannot be run, clearly state why and what residual risk remains.
- The final response should summarize:
  - What changed.
  - Which files or areas were touched.
  - Which tests or checks were run.
  - Any unresolved risks or follow-up work.

## Quality And Token Discipline

- Spend high-reasoning main-agent effort on decisions, integration, risk, and review.
- Spend cheaper worker-agent effort on bounded edits, mechanical changes, and focused test/debug loops.
- Prefer a small number of well-scoped workers over many tiny workers.
- Avoid duplicating the same investigation across agents.
- Keep user-facing updates concise and focused on progress, blockers, and verification.
