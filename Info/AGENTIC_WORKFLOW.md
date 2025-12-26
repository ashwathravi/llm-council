# Agentic Development Workflow Proposal

This document outlines a file-based state machine workflow to automate the development process using Antigravity/Jules.

## 🤖 Workflow Overview

The goal is to transform the development process into an "Agentic Factory" where the developer acts as the Architect/Manager, and the AI acts as the builder.

| Step | Action | Automatable? | Recommended Approach |
| :--- | :--- | :--- | :--- |
| **1** | Define Idea | ❌ Manual | You provide the high-level intent (e.g., "Add Dark Mode"). |
| **2** | Plan & Prompt | ✅ **High** | AI generates a structured "Plan" artifact that outputs multiple Task definition files. |
| **3** | Queue Tasks | ✅ **High** | Save these task files into a `.agent/tasks/todo/` folder. |
| **4** | **Implement** | ⚠️ **Semi** | **The Core Loop.** AI reads a task, codes it, and runs tests. *Requires human "check-in" between tasks.* |
| **5** | Code Review | ✅ **High** | AI runs linters/integrity checks and "reviews itself" before asking for verification. |
| **6** | Cleanup | ✅ **Full** | Automated via git commands in a workflow script. |
| **7-9** | Looping | ⚠️ **Semi** | Driven by the manager triggering the "Next Task" workflow. |

## 🚀 Solution: The "Task Pipeline"

We use the filesystem as the database for the state machine.

### Directory Structure

```text
.agent/
  tasks/
    01_idea_input/      <-- User writes high level ideas here
    02_todo/            <-- AI generates structured sub-tasks here
    03_in_progress/     <-- The current active task being worked on
    04_review/          <-- Implementation complete, waiting for verification
    05_done/            <-- Completed and merged tasks
```

### Proposed Workflows

We can create **3 Custom Workflows** to drive this state machine:

#### 1. The Planner (`/plan_feature`)
*   **Input**: You provide a high-level idea in `01_idea_input/`.
*   **Agent Action**:
    1.  Analyzes the codebase and the new requirement.
    2.  Creates an implementation strategy.
    3.  Generates distinct task markdown files in `02_todo/` (e.g., `task_01_db_schema.md`, `task_02_api.md`).

#### 2. The Builder (`/build_next`)
*   **Action**:
    1.  Moves the top priority file from `02_todo` -> `03_in_progress`.
    2.  Reads the instructions in that file.
    3.  Writes code.
    4.  Runs tests (`npm test` / `pytest`).
    5.  **Self-Correction**: If tests fail, fixes them immediately.
    6.  Moves file to `04_review` when passing.

#### 3. The Merger (`/ship_it`)
*   **Action**:
    1.  Runs final regression tests.
    2.  Commits changes (`git commit -m "feat: <task_summary>"`).
    3.  Moves file from `04_review` -> `05_done`.
    4.  (Optional) Deletes/cleans up branches or artifacts.

---

### Implementation Plan

1.  **Initialize**: Create the `.agent/tasks/` directory structure.
2.  **Define Workflows**: Create `.md` workflow definitions for the agent to follow.
3.  **Execute**: Start dropping ideas into `01_idea_input` and run `/plan_feature`.
