import pytest
from unittest.mock import AsyncMock, patch

from backend.code_execution import (
    build_execution_context_block,
    extract_candidate_patch,
    run_code_execution_loop,
)


def test_extract_candidate_patch_reads_diff_fence():
    response_text = """
    ```diff
    diff --git a/app.py b/app.py
    --- a/app.py
    +++ b/app.py
    @@ -1 +1 @@
    -print("old")
    +print("new")
    ```
    """

    patch_text = extract_candidate_patch(response_text)
    assert patch_text is not None
    assert "diff --git a/app.py b/app.py" in patch_text
    assert '+print("new")' in patch_text


def test_build_execution_context_block_includes_checks_and_patch_state():
    context = build_execution_context_block({
        "mode": "safe_patch_checks",
        "session_type": "code_review",
        "status": "completed",
        "reason": "One check failed after the candidate patch was applied.",
        "candidate_patch": {
            "status": "applied",
            "changed_files": ["app.py"],
            "error": "",
        },
        "checks": [
            {
                "kind": "check",
                "command": "python -m compileall .",
                "status": "passed",
                "summary": "Compilation succeeded.",
            },
            {
                "kind": "test",
                "command": "pytest -q",
                "status": "failed",
                "summary": "1 failed, 2 passed",
            },
        ],
        "summary": {"passed": 1, "failed": 1, "skipped": 0},
    })

    assert "EXECUTION LOOP RESULTS:" in context
    assert "Candidate patch: applied" in context
    assert "Changed files: app.py" in context
    assert "pytest -q => failed" in context


@pytest.mark.asyncio
async def test_run_code_execution_loop_generates_patch_and_records_checks():
    primary_artifacts = [
        {
            "id": "code-1",
            "kind": "code",
            "label": "app.py",
            "status": "ready",
            "storage_path": "conv/app.py",
        }
    ]

    async_run = AsyncMock(side_effect=[
        {"command": "git apply --check", "status": "passed", "exit_code": 0, "output": "", "summary": ""},
        {"command": "git apply", "status": "passed", "exit_code": 0, "output": "", "summary": ""},
        {"command": "python -m compileall .", "status": "passed", "exit_code": 0, "output": "Compiled 1 file", "summary": "Compiled 1 file"},
    ])

    def fake_which(name):
        mapping = {
            "git": "/usr/bin/git",
        }
        return mapping.get(name)

    with patch("backend.code_execution.query_model", new_callable=AsyncMock) as mock_query_model, \
         patch("backend.code_execution.code_artifacts.load_code_file", return_value='print("old")\n'), \
         patch("backend.code_execution._run_command", async_run), \
         patch("backend.code_execution.shutil.which", side_effect=fake_which):
        mock_query_model.return_value = {
            "content": """```diff
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-print("old")
+print("new")
```""",
        }

        report = await run_code_execution_loop(
            session_type="code_review",
            execution_mode="safe_patch_checks",
            user_query="Fix the greeting",
            stage1_results=[{"model": "model-a", "response": "Update the print statement."}],
            stage2_results=[{"model": "model-b", "ranking": "Response A is best."}],
            chairman_model="chair-model",
            primary_artifacts=primary_artifacts,
            retrieval_context="CODE REVIEW ARTIFACT:\n- File: app.py",
        )

    assert report["status"] == "completed"
    assert report["candidate_patch"]["status"] == "applied"
    assert report["candidate_patch"]["changed_files"] == ["app.py"]
    assert report["summary"]["passed"] == 1
    assert report["summary"]["skipped"] == 1
    assert any(check["label"] == "Python compileall" and check["status"] == "passed" for check in report["checks"])
    assert any(check["label"] == "Ruff" and check["status"] == "skipped" for check in report["checks"])
