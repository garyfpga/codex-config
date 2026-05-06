#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


HOOK_DIR = Path.home() / ".codex" / "hooks"
SCHEMA_PATH = HOOK_DIR / "anti_lazy_classifier.schema.json"
LOG_PATH = HOOK_DIR / "anti_lazy_stop.log.jsonl"

CLASSIFIER_MODEL = os.environ.get("ANTI_LAZY_CLASSIFIER_MODEL", "gpt-5.3-codex-spark")
CLASSIFIER_EFFORT = os.environ.get("ANTI_LAZY_CLASSIFIER_EFFORT", "low")
CLASSIFIER_TIMEOUT = int(os.environ.get("ANTI_LAZY_CLASSIFIER_TIMEOUT", "45"))
MAX_MESSAGE_CHARS = int(os.environ.get("ANTI_LAZY_MAX_MESSAGE_CHARS", "20000"))
MAX_MATCHES = int(os.environ.get("ANTI_LAZY_MAX_MATCHES", "40"))

PATTERNS = [
    ("direct_difficulty", False, r"\b(this|that|it)\s+(is|looks|seems|may be|might be)\s+too\s+(hard|difficult|complex|complicated|big|risky)\b"),
    ("direct_difficulty", False, r"\b(if|when)\s+(this|that|it)\s+(is|gets|becomes)\s+too\s+(hard|difficult|complex|complicated)\b"),
    ("direct_difficulty", False, r"\b(can't|cannot|couldn't|won't|wouldn't)\s+(reasonably|realistically|safely|practically)?\s*(finish|complete|implement|do|solve)\b"),
    ("direct_difficulty", False, r"\b(not|no longer)\s+(feasible|practical|reasonable|realistic)\b"),
    ("fallback_path", True, r"\b(backup|back-up)\s+(plan|approach|path|strategy|implementation)\b"),
    ("fallback_path", True, r"\bescape\s+(plan|hatch|path|route)\b"),
    ("fallback_path", True, r"\bfallback\s+(plan|approach|path|strategy|implementation|option)\b"),
    ("fallback_path", True, r"\bfall\s+back\s+to\b"),
    ("fallback_path", False, r"\b(plan\s+b|alternate\s+(plan|path|approach|route|implementation)|alternative\s+(plan|path|approach|route|implementation))\b"),
    ("fallback_path", False, r"\b(easier|simpler|lighter|lower-risk|safer)\s+(path|route|approach|option|implementation|version)\b"),
    ("fallback_path", False, r"\bworkaround\b"),
    ("stub_substitute", True, r"\bstub\s+(substitute|implementation|version|out|it\s+out)\b"),
    ("stub_substitute", True, r"\bstub\s+for\s+now\b"),
    ("stub_substitute", True, r"\b(use|add|create|leave|ship|provide)\s+(a\s+)?(stub|placeholder|dummy|fake|mock|no-op|noop)\b"),
    ("stub_substitute", False, r"\bplaceholder\s+(implementation|logic|behavior|code|file|test|ui|screen|handler|response)\b"),
    ("stub_substitute", False, r"\b(dummy|fake|mocked|mock-only|no-op|noop|skeleton)\s+(implementation|logic|behavior|code|handler|response|version)\b"),
    ("stub_substitute", False, r"\bTODO\b|\bFIXME\b|\bnot\s+implemented\b|\bnotimplemented\b"),
    ("docs_only_substitute", True, r"\bdocs-only\s+(substitute|change|implementation|fix|solution)\b"),
    ("docs_only_substitute", True, r"\bdocument\s+(it|this|that|instead)\b"),
    ("docs_only_substitute", False, r"\b(update|write|add)\s+(the\s+)?(docs|documentation|README)\s+(instead|only)\b"),
    ("skip_verification", True, r"\bskip\s+(tests|testing|verification|review|checks|validation)\b"),
    ("skip_verification", True, r"\b(skipped|not\s+running|won't\s+run|will\s+not\s+run|cannot\s+run|can't\s+run)\s+(tests|testing|verification|review|checks|validation)\b"),
    ("skip_verification", False, r"\b(no|without)\s+(tests|testing|verification|review|checks|validation)\b"),
    ("skip_verification", False, r"\bassume\s+(the\s+)?(tests|checks|verification)\s+(pass|passes|will\s+pass|are\s+fine)\b"),
    ("skip_verification", False, r"\buntested\b|\bunverified\b|\bnot\s+verified\b|\bmanual\s+testing\s+only\b"),
    ("reduced_scope", False, r"\breduce(d)?\s+scope\b|\bscope\s+(cut|reduction|reduced)\b"),
    ("reduced_scope", False, r"\b(out\s+of\s+scope|beyond\s+scope|outside\s+scope)\s+(for\s+now|here|in\s+this\s+pass|in\s+this\s+version)?\b"),
    ("reduced_scope", False, r"\b(minimal|basic|partial|thin|lightweight)\s+(version|implementation|slice|pass)\b"),
    ("reduced_scope", False, r"\bMVP\s+(only|version|implementation|slice)\b"),
    ("deferral", False, r"\b(defer|deferred|punt|punt\s+on|postpone|leave)\s+(this|that|it|the\s+implementation|the\s+fix|the\s+work)\b"),
    ("deferral", False, r"\b(for\s+later|later\s+pass|future\s+work|follow-up|next\s+iteration|subsequent\s+pass)\b"),
    ("deferral", False, r"\b(can|could|should)\s+be\s+(added|implemented|finished|completed|fixed|handled)\s+later\b"),
    ("deferral", False, r"\bleave\s+(it|this|that)\s+(as-is|for\s+now|until\s+later)\b"),
    ("partial_completion", False, r"\bgood\s+enough\b|\bsufficient\s+for\s+now\b|\bclose\s+enough\b"),
    ("partial_completion", False, r"\bnot\s+(fully|completely)\s+(implemented|complete|done|finished|covered)\b"),
    ("partial_completion", False, r"\bonly\s+(partially|roughly|loosely)\s+(implemented|covered|done|verified)\b"),
    ("blocked_but_continuing", True, r"\b(blocked|can't\s+complete|cannot\s+complete)\b.{0,160}\b(so|therefore)\b.{0,160}\b(instead|fallback|stub|placeholder|document)\b"),
    ("approved_path_violation", True, r"\bwithout\s+(fresh\s+)?(explicit\s+)?(approval|user\s+approval)\b.{0,160}\b(backup|fallback|escape|stub|docs-only|skip|reduced\s+scope)\b"),
]


def normalize_for_match(text):
    return text.translate(
        {
            ord("\u2018"): "'",
            ord("\u2019"): "'",
            ord("\u201c"): '"',
            ord("\u201d"): '"',
            ord("\u2013"): "-",
            ord("\u2014"): "-",
            ord("\u00a0"): " ",
        }
    )


def read_hook_input():
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def find_candidates(message):
    normalized = normalize_for_match(message)
    matches = []
    seen = set()

    for category, high_signal, pattern in PATTERNS:
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for found in regex.finditer(normalized):
            start, end = found.span()
            key = (category, start, end)
            if key in seen:
                continue
            seen.add(key)
            snippet_start = max(0, start - 80)
            snippet_end = min(len(message), end + 80)
            snippet = " ".join(message[snippet_start:snippet_end].split())
            matches.append(
                {
                    "category": category,
                    "high_signal": high_signal,
                    "match": message[start:end],
                    "snippet": snippet,
                    "span": [start, end],
                }
            )
            if len(matches) >= MAX_MATCHES:
                return matches

    return matches


def has_high_signal(matches):
    return any(match.get("high_signal") for match in matches)


def classifier_prompt(message, matches):
    truncated = message[-MAX_MESSAGE_CHARS:]
    match_summary = [
        {
            "category": match["category"],
            "match": match["match"],
            "snippet": match["snippet"],
            "high_signal": match["high_signal"],
        }
        for match in matches[:MAX_MATCHES]
    ]

    return """You are a conservative classifier for a Codex Stop hook.

Decide whether the assistant's latest message is actually evasive or lazy.

Return lazy=true only when the assistant is ending or reporting progress while choosing, recommending, or accepting a reduced/easier/stubbed/docs-only/skipped-verification path instead of completing the assigned work.

Return lazy=false for:
- legitimate blocker reports that stop and ask for approval before changing approach
- policy discussion or planning about forbidden fallback language
- quotes, examples, test fixtures, grep output, docs, or user-provided text
- honest verification reports such as "tests were not run" when the work was otherwise completed and no skipped verification was presented as acceptable progress
- cases where the assistant is describing forbidden behavior in order to avoid it

Be conservative on the final decision. It is better to return lazy=false for ambiguous discussion than to block a valid turn.

Regex candidate matches:
{matches}

Latest assistant message:
<assistant_message>
{message}
</assistant_message>
""".format(
        matches=json.dumps(match_summary, ensure_ascii=False, indent=2),
        message=truncated,
    )


def run_classifier(message, matches):
    with tempfile.TemporaryDirectory(prefix="anti-lazy-classifier-") as temp_dir:
        output_path = Path(temp_dir) / "classifier-output.json"
        cmd = [
            "codex",
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--disable",
            "codex_hooks",
            "-C",
            "/tmp",
            "-s",
            "read-only",
            "-m",
            CLASSIFIER_MODEL,
            "-c",
            'model_reasoning_effort="{}"'.format(CLASSIFIER_EFFORT),
            "--output-schema",
            str(SCHEMA_PATH),
            "--output-last-message",
            str(output_path),
            "-",
        ]

        completed = subprocess.run(
            cmd,
            input=classifier_prompt(message, matches),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/tmp",
            timeout=CLASSIFIER_TIMEOUT,
        )

        if completed.returncode != 0:
            return {
                "ok": False,
                "error": "classifier_exit_{}".format(completed.returncode),
                "stderr": completed.stderr[-2000:],
            }

        try:
            raw_output = output_path.read_text(encoding="utf-8")
            verdict = json.loads(raw_output)
        except Exception as exc:
            return {
                "ok": False,
                "error": "classifier_parse_failed: {}".format(exc),
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
            }

        return {
            "ok": True,
            "verdict": verdict,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        }


def correction_prompt(matches, classifier_result=None, fallback=False):
    categories = sorted({match["category"] for match in matches})
    snippets = [match["snippet"] for match in matches[:5]]
    classifier_reason = ""
    if classifier_result and classifier_result.get("ok"):
        classifier_reason = classifier_result.get("verdict", {}).get("reason", "")

    return """Anti-lazy Stop hook: your last response appears to use evasive or reduced-scope behavior.

Matched categories: {categories}
Matched snippets: {snippets}
Classifier reason: {classifier_reason}
Fallback decision: {fallback}

Continue now instead of ending. First self-audit in one concise sentence by naming the phrase or behavior that triggered this. Then re-anchor to the current user request, approved plan, and acceptance criteria, and complete the real assigned work using the approved path.

Do not use a backup plan, escape plan, fallback implementation, reduced scope, docs-only substitute, stub substitute, skipped review, skipped verification, execution-mode switch, or easier alternate path without fresh explicit user approval at the moment the deviation is needed.

If the approved work is genuinely blocked, report BLOCKED with the exact blocker, current status, and the smallest approval or question needed before changing scope, strategy, verification, or implementation path.""".format(
        categories=", ".join(categories),
        snippets=json.dumps(snippets, ensure_ascii=False),
        classifier_reason=classifier_reason,
        fallback=str(fallback).lower(),
    )


def write_log(entry):
    try:
        HOOK_DIR.mkdir(parents=True, exist_ok=True)
        entry = dict(entry)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        fd = os.open(str(LOG_PATH), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as log_file:
            log_file.write(line)
        os.chmod(str(LOG_PATH), 0o600)
    except Exception:
        pass


def emit_block(reason):
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def main():
    started = time.time()
    data = read_hook_input()
    if not isinstance(data, dict):
        return 0

    event_name = data.get("hook_event_name") or data.get("hookEventName")
    if event_name != "Stop":
        return 0

    if data.get("stop_hook_active"):
        return 0

    message = data.get("last_assistant_message")
    if not isinstance(message, str) or not message.strip():
        return 0

    matches = find_candidates(message)
    if not matches:
        return 0

    log_base = {
        "action": "candidate",
        "cwd": data.get("cwd"),
        "session_id": data.get("session_id"),
        "turn_id": data.get("turn_id"),
        "model": data.get("model"),
        "matches": matches,
        "last_assistant_message": message,
    }

    classifier_result = None
    try:
        classifier_result = run_classifier(message, matches)
    except subprocess.TimeoutExpired:
        classifier_result = {"ok": False, "error": "classifier_timeout"}
    except Exception as exc:
        classifier_result = {"ok": False, "error": "classifier_failed: {}".format(exc)}

    elapsed_ms = int((time.time() - started) * 1000)

    if classifier_result.get("ok"):
        verdict = classifier_result.get("verdict", {})
        is_lazy = bool(verdict.get("lazy"))
        confidence = float(verdict.get("confidence", 0) or 0)
        should_block = is_lazy and confidence >= 0.65
        write_log(
            {
                **log_base,
                "action": "block" if should_block else "allow",
                "elapsed_ms": elapsed_ms,
                "classifier_result": classifier_result,
            }
        )
        if should_block:
            emit_block(correction_prompt(matches, classifier_result=classifier_result))
        return 0

    strong_fallback = has_high_signal(matches)
    write_log(
        {
            **log_base,
            "action": "block" if strong_fallback else "allow",
            "elapsed_ms": elapsed_ms,
            "classifier_result": classifier_result,
            "fallback": "strong_high_signal" if strong_fallback else "fail_open",
        }
    )

    if strong_fallback:
        emit_block(correction_prompt(matches, classifier_result=classifier_result, fallback=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
