---
name: ro
description: Use this skill only when the user explicitly invokes $ro or asks to use the ro/read-only skill. Provides a read-only code discussion mode where Codex may inspect, discuss, run commands, and create tracked temporary files, but must not edit existing repo files.
---

# RO

## Purpose

Use `$ro` as a read-only discussion mode for codebases. In this mode, inspect and run code freely enough to understand behavior, but do not modify existing project files.

This skill is an instruction-level guardrail, not an OS sandbox. Apply it strictly and state any limitation if a requested action cannot be done without changing existing files.

## Activation

- Activate only when the user explicitly invokes `$ro` or asks to use the `ro` skill.
- Keep `$ro` active for the current task or discussion until the user explicitly disables it or asks for implementation outside read-only mode.
- When `$ro` first needs a temp artifact, announce the active instance id and temp root.

## Write Rules

- Never edit, overwrite, rename, delete, format, migrate, or code-generate over existing repo files.
- Do not use `apply_patch` against existing files.
- Do not run commands whose purpose is to modify existing repo files.
- You may create and edit only temporary files that belong to this `$ro` session and are recorded in the manifest.
- Before writing a path, verify it does not already exist unless it is already recorded in the current `$ro` manifest.
- If the user asks for a code change, provide a proposed patch, diff, or explanation in the response instead of applying it.
- If a command unexpectedly modifies existing repo files, stop, report what changed, and do not try to revert without explicit user confirmation.

## Allowed Actions

- Read and search files, configs, schemas, tests, docs, and git history.
- Run existing files, tests, builds, checks, and scripts when they are useful for discussion.
- Create temp scripts, fixtures, notes, logs, or command outputs under the `$ro` temp root.
- Execute temp scripts from the `$ro` temp root.
- Write cache/build outputs only when they are normal side effects of a command and are not repo-tracked source changes.

## Temp Workspace

Use this layout by default:

```text
<repo>/.codex-ro/<instance-id>/
```

Choose the instance id as follows:

1. Use `$CODEX_THREAD_ID` when available.
2. Otherwise use `YYYYMMDD-HHMMSS-<short-random>`.

Create this manifest before or with the first temp artifact:

```text
<repo>/.codex-ro/<instance-id>/manifest.json
```

The manifest must contain:

```json
{
  "instance_id": "...",
  "repo_root": "...",
  "created_at": "...",
  "artifacts": [
    {
      "path": "...",
      "kind": "script|fixture|note|log|output|other",
      "purpose": "...",
      "created_at": "...",
      "last_touched_at": "..."
    }
  ]
}
```

When adding or editing a temp artifact, update its manifest entry in the same turn. Paths may be absolute or repo-relative, but use one style consistently within the manifest.

Temporary files outside `.codex-ro/<instance-id>/` are allowed only when the user explicitly asks for that location. Record them in the same manifest.

## Cleanup And Revert

When the user says "clean up", "cleanup", "revert", or asks to remove `$ro` temp files:

1. Read the current manifest.
2. List the recorded artifacts that would be removed.
3. Ask for confirmation before deleting anything.
4. After confirmation, delete only manifest-listed artifacts.
5. Remove empty `.codex-ro/<instance-id>` directories.

Never use broad deletion, `git checkout`, `git reset`, or other destructive repo-wide commands for `$ro` cleanup.

## Communication

- Be explicit when a requested action is blocked by `$ro`.
- Prefer concrete findings, file references, command outputs, and proposed diffs.
- When temp files are created, mention the temp root and manifest location briefly.
