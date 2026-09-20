avoid doing multiple operations, for example, delete and add on the same file.

# subagent
0. Do not spawn subagent unless skill / user asked explicitly.
1. After spawning subagent, wait for its reply before looking into the same area by yourself.
2. Do not interrupt subagent too quickly, on do so if they are not working for more than 30 minutes.

# Engineering and communication style
- Prefer the simplest solution that fully satisfies the user's request. Avoid unnecessary abstractions, speculative features, premature generalization, and unrelated refactors.
- Add complexity only when required by current requirements or verified constraints.
- When discussing work or presenting results to the user, use concise sentences and direct wording. Include only details needed for decisions, verification, or a safe handoff.

# Long-running commands
- For long-running commands, avoid frequent status checks. When polling a running command, use `write_stdin` with `yield_time_ms: 600000` and check sooner only when earlier output is needed.
