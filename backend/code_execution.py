"""Guarded code execution loop for code-review workspaces."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import code_artifacts, config
from .openrouter import query_model
from .session_context import (
    DEFAULT_EXECUTION_MODE,
    normalize_execution_mode,
    normalize_primary_artifacts,
    normalize_session_type,
)

NO_PATCH_TOKEN = "NO_PATCH"
DIFF_FENCE_RE = re.compile(r"```diff\s*(.*?)```", re.IGNORECASE | re.DOTALL)
DIFF_HEADER_RE = re.compile(r"^\+\+\+\s+(?:b/)?([^\t\n]+)", re.MULTILINE)
OUTPUT_SUMMARY_RE = re.compile(r"\s+")


def _truncate_text(value: str, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 16].rstrip()}\n... [truncated]"


def extract_candidate_patch(response_text: Optional[str]) -> Optional[str]:
    if not isinstance(response_text, str):
        return None

    text = response_text.strip()
    if not text:
        return None
    if NO_PATCH_TOKEN in text:
        return None

    fenced_match = DIFF_FENCE_RE.search(text)
    if fenced_match:
        text = fenced_match.group(1).strip()

    has_unified_diff = "diff --git " in text or (
        re.search(r"^--- ", text, re.MULTILINE)
        and re.search(r"^\+\+\+ ", text, re.MULTILINE)
    )
    return text if has_unified_diff else None


def _safe_workspace_relpath(raw_path: Optional[str], fallback_name: str) -> Path:
    candidate = str(raw_path or fallback_name or "artifact.txt").replace("\\", "/").strip()
    parts: List[str] = []
    for segment in candidate.split("/"):
        cleaned = segment.strip().replace(":", "_")
        if not cleaned or cleaned in {".", ".."}:
            continue
        parts.append(cleaned)
    if not parts:
        parts = [fallback_name or "artifact.txt"]
    return Path(*parts)


def _build_check_summary(output: str) -> str:
    normalized = OUTPUT_SUMMARY_RE.sub(" ", output or "").strip()
    if not normalized:
        return ""
    if len(normalized) <= 160:
        return normalized
    return f"{normalized[:157].rstrip()}..."


def _get_ready_code_artifacts(primary_artifacts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    ready_artifacts = []
    for artifact in normalize_primary_artifacts(list(primary_artifacts or [])):
        if artifact.get("kind") != "code":
            continue
        if artifact.get("status") != "ready":
            continue
        if not artifact.get("storage_path"):
            continue
        ready_artifacts.append(artifact)
    return ready_artifacts


def _build_patch_prompt(
    *,
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    retrieval_context: Optional[str],
    workspace_files: List[str],
) -> str:
    stage1_text = "\n\n".join(
        f"Model: {result.get('model', 'unknown')}\nResponse: {result.get('response', '')}"
        for result in stage1_results
    )
    stage2_text = "\n\n".join(
        f"Model: {result.get('model', 'unknown')}\nFeedback: {result.get('ranking', '')}"
        for result in stage2_results
    )
    file_list = "\n".join(f"- {path}" for path in workspace_files) or "- No files"
    retrieval_block = (
        f"\nADDITIONAL CONTEXT:\n{_truncate_text(retrieval_context or '', 8000)}\n"
        if retrieval_context else ""
    )

    return f"""You are preparing a guarded candidate patch for a code review workflow.

USER REQUEST:
{user_query}

WORKSPACE FILES:
{file_list}
{retrieval_block}
STAGE 1 FINDINGS:
{stage1_text}

STAGE 2 FEEDBACK:
{stage2_text}

Return either:
1. The exact token {NO_PATCH_TOKEN} if there is no narrowly-supported safe patch to try.
2. A single unified diff inside a ```diff fenced block.

Rules:
- Only modify files that already exist in the workspace file list.
- Keep the patch minimal and directly tied to the review findings.
- Do not include prose before or after the diff block.
- Prefer the smallest patch that makes the issue measurably better.
"""


async def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=config.CODE_EXECUTION_COMMAND_TIMEOUT_SECONDS,
        )
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        timed_out = True

    output = "\n".join(
        part for part in (
            stdout.decode("utf-8", errors="replace").strip(),
            stderr.decode("utf-8", errors="replace").strip(),
        )
        if part
    ).strip()

    if timed_out:
        output = "\n".join(filter(None, [output, "Command timed out."])).strip()

    status = "passed"
    exit_code = process.returncode
    if timed_out or exit_code not in (0, None):
        status = "failed"

    truncated_output = _truncate_text(output, config.CODE_EXECUTION_MAX_OUTPUT_CHARS)
    return {
        "command": " ".join(command),
        "status": status,
        "exit_code": exit_code,
        "output": truncated_output,
        "summary": _build_check_summary(truncated_output),
    }


def _make_skipped_check(kind: str, label: str, reason: str) -> Dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "command": None,
        "status": "skipped",
        "exit_code": None,
        "output": reason,
        "summary": reason,
    }


def _detect_checks(workspace_root: Path, workspace_files: List[str]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    workspace_paths = [Path(path) for path in workspace_files]
    has_python = any(path.suffix == ".py" for path in workspace_paths)
    has_python_tests = any(
        path.name.startswith("test_") or "tests" in path.parts
        for path in workspace_paths
    )

    if has_python:
        checks.append({
            "kind": "check",
            "label": "Python compileall",
            "command": ["python", "-m", "compileall", "."],
            "env": None,
        })

        if shutil.which("ruff"):
            checks.append({
                "kind": "lint",
                "label": "Ruff",
                "command": ["ruff", "check", "."],
                "env": None,
            })
        else:
            checks.append(_make_skipped_check("lint", "Ruff", "ruff is not installed in this environment."))

        if has_python_tests:
            if shutil.which("pytest"):
                checks.append({
                    "kind": "test",
                    "label": "Pytest",
                    "command": ["pytest", "-q"],
                    "env": None,
                })
            else:
                checks.append(_make_skipped_check("test", "Pytest", "pytest is not installed in this environment."))

    package_json_path = workspace_root / "package.json"
    if package_json_path.exists():
        has_node_modules = (workspace_root / "node_modules").exists()
        if not shutil.which("npm"):
            checks.append(_make_skipped_check("check", "npm", "npm is not installed in this environment."))
        elif not has_node_modules:
            checks.append(_make_skipped_check("check", "npm workspace", "node_modules is missing, so npm scripts were skipped."))
        else:
            try:
                package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            except Exception:
                package_json = {}
            scripts = package_json.get("scripts") if isinstance(package_json, dict) else {}
            if isinstance(scripts, dict) and "lint" in scripts:
                checks.append({
                    "kind": "lint",
                    "label": "npm lint",
                    "command": ["npm", "run", "lint", "--", "--color=false"],
                    "env": None,
                })
            if isinstance(scripts, dict) and "test" in scripts:
                checks.append({
                    "kind": "test",
                    "label": "npm test",
                    "command": ["npm", "run", "test", "--", "--runInBand"],
                    "env": {"CI": "true"},
                })

    return checks


def _summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {"passed": 0, "failed": 0, "skipped": 0}
    for check in checks:
        status = check.get("status")
        if status in summary:
            summary[status] += 1
    return summary


def build_execution_context_block(report: Optional[Dict[str, Any]]) -> str:
    if not isinstance(report, dict):
        return ""

    mode = normalize_execution_mode(
        report.get("mode"),
        session_type=report.get("session_type"),
    )
    if mode == DEFAULT_EXECUTION_MODE:
        return ""

    lines = [
        "EXECUTION LOOP RESULTS:",
        f"- Mode: {mode}",
        f"- Status: {report.get('status', 'unknown')}",
    ]

    reason = report.get("reason")
    if isinstance(reason, str) and reason.strip():
        lines.append(f"- Note: {reason.strip()}")

    candidate_patch = report.get("candidate_patch") or {}
    patch_status = candidate_patch.get("status")
    if patch_status:
        lines.append(f"- Candidate patch: {patch_status}")
    changed_files = candidate_patch.get("changed_files") or []
    if changed_files:
        lines.append(f"- Changed files: {', '.join(changed_files)}")
    patch_error = candidate_patch.get("error")
    if isinstance(patch_error, str) and patch_error.strip():
        lines.append(f"- Patch error: {patch_error.strip()}")

    checks = report.get("checks") or []
    summary = report.get("summary") or {}
    if checks:
        lines.append(
            "- Checks:"
            f" {summary.get('passed', 0)} passed,"
            f" {summary.get('failed', 0)} failed,"
            f" {summary.get('skipped', 0)} skipped"
        )
        for check in checks[:8]:
            command = check.get("command") or check.get("label") or "check"
            detail = check.get("summary") or check.get("output") or ""
            bullet = f"  - {check.get('kind', 'check')}: {command} => {check.get('status', 'unknown')}"
            if detail:
                bullet = f"{bullet} ({detail})"
            lines.append(bullet)

    lines.append(
        "- Treat passing checks as supporting evidence and failed checks as verified signals. "
        "If the loop was skipped or the patch failed, do not present that as validation."
    )
    return "\n".join(lines)


async def run_code_execution_loop(
    *,
    session_type: Optional[str],
    execution_mode: Optional[str],
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairman_model: Optional[str],
    primary_artifacts: Optional[List[Dict[str, Any]]],
    retrieval_context: Optional[str],
) -> Dict[str, Any]:
    normalized_session_type = normalize_session_type(session_type)
    normalized_mode = normalize_execution_mode(
        execution_mode,
        session_type=normalized_session_type,
    )
    report: Dict[str, Any] = {
        "mode": normalized_mode,
        "session_type": normalized_session_type,
        "status": "disabled" if normalized_mode == DEFAULT_EXECUTION_MODE else "skipped",
        "reason": "",
        "workspace_files": [],
        "candidate_patch": {
            "status": "not_attempted",
            "changed_files": [],
            "excerpt": "",
            "error": "",
        },
        "checks": [],
        "summary": {"passed": 0, "failed": 0, "skipped": 0},
    }

    if normalized_mode == DEFAULT_EXECUTION_MODE:
        report["reason"] = "Safe execution loop is disabled for this session."
        return report

    if not config.CODE_EXECUTION_LOOP_ENABLED:
        report["reason"] = "Safe execution loop is disabled by server configuration."
        return report

    ready_artifacts = _get_ready_code_artifacts(primary_artifacts)
    if not ready_artifacts:
        report["reason"] = "No ready code artifacts were available for execution."
        return report

    if not chairman_model:
        report["reason"] = "No chairman model is configured for candidate patch generation."
        return report

    report["status"] = "completed"

    try:
        with tempfile.TemporaryDirectory(prefix="llm-council-exec-") as tmpdir:
            workspace_root = Path(tmpdir)
            used_paths = set()
            workspace_files: List[str] = []

            for index, artifact in enumerate(ready_artifacts, start=1):
                fallback_name = artifact.get("filename") or f"artifact_{index}.txt"
                relative_path = _safe_workspace_relpath(
                    artifact.get("label") or artifact.get("filename"),
                    fallback_name,
                )
                candidate_path = relative_path
                suffix = 2
                while candidate_path.as_posix() in used_paths:
                    candidate_path = candidate_path.with_name(
                        f"{relative_path.stem}_{suffix}{relative_path.suffix}"
                    )
                    suffix += 1
                used_paths.add(candidate_path.as_posix())

                content = code_artifacts.load_code_file(artifact["storage_path"])
                target_path = workspace_root / candidate_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                workspace_files.append(candidate_path.as_posix())

            report["workspace_files"] = workspace_files

            patch_prompt = _build_patch_prompt(
                user_query=user_query,
                stage1_results=stage1_results,
                stage2_results=stage2_results,
                retrieval_context=retrieval_context,
                workspace_files=workspace_files,
            )
            patch_response = await query_model(
                chairman_model,
                [{"role": "user", "content": patch_prompt}],
                timeout=config.CODE_EXECUTION_PATCH_TIMEOUT_SECONDS,
            )
            if patch_response.get("error"):
                report["candidate_patch"]["status"] = "generation_failed"
                report["candidate_patch"]["error"] = patch_response["error"]
                report["reason"] = "Candidate patch generation failed."
                return report

            patch_text = extract_candidate_patch(patch_response.get("content"))
            if not patch_text:
                report["candidate_patch"]["status"] = "no_patch"
                report["reason"] = "The chairman model did not propose a safe candidate patch."
                return report

            report["candidate_patch"]["excerpt"] = _truncate_text(
                patch_text,
                config.CODE_EXECUTION_MAX_PATCH_CHARS,
            )
            report["candidate_patch"]["changed_files"] = list(dict.fromkeys(DIFF_HEADER_RE.findall(patch_text)))

            if not shutil.which("git"):
                report["candidate_patch"]["status"] = "apply_failed"
                report["candidate_patch"]["error"] = "git is not installed in this environment."
                report["reason"] = "Candidate patch could not be applied."
                return report

            patch_path = workspace_root / "candidate.patch"
            patch_path.write_text(patch_text, encoding="utf-8")

            check_apply = await _run_command(
                ["git", "apply", "--check", "--recount", "--whitespace=nowarn", str(patch_path)],
                cwd=workspace_root,
            )
            if check_apply["status"] != "passed":
                report["candidate_patch"]["status"] = "apply_failed"
                report["candidate_patch"]["error"] = check_apply["output"] or "git apply --check failed."
                report["reason"] = "Candidate patch could not be applied cleanly."
                return report

            apply_result = await _run_command(
                ["git", "apply", "--recount", "--whitespace=nowarn", str(patch_path)],
                cwd=workspace_root,
            )
            if apply_result["status"] != "passed":
                report["candidate_patch"]["status"] = "apply_failed"
                report["candidate_patch"]["error"] = apply_result["output"] or "git apply failed."
                report["reason"] = "Candidate patch could not be applied cleanly."
                return report

            report["candidate_patch"]["status"] = "applied"

            detected_checks = _detect_checks(workspace_root, workspace_files)
            if not detected_checks:
                report["reason"] = "No runnable auto-detected checks matched this workspace."
                return report

            executed_checks: List[Dict[str, Any]] = []
            for check in detected_checks:
                if check.get("status") == "skipped":
                    executed_checks.append(check)
                    continue

                env = None
                if isinstance(check.get("env"), dict):
                    env = {**os.environ, **check["env"]}
                result = await _run_command(
                    check["command"],
                    cwd=workspace_root,
                    env=env,
                )
                executed_checks.append({
                    "kind": check.get("kind"),
                    "label": check.get("label"),
                    **result,
                })

            report["checks"] = executed_checks
            report["summary"] = _summarize_checks(executed_checks)
            return report
    except Exception as exc:
        report["status"] = "failed"
        report["reason"] = f"Execution loop failed unexpectedly: {exc}"
        return report
