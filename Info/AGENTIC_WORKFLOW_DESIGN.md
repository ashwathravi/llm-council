# Agentic Development Workflow Propsoal: The Agentic Factory

This document outlines a file-based state machine workflow to automate the development process using Antigravity/Jules. It treats the development environment as an "Agentic Factory" with specialized agents working in concert.

## 🤖 Workflow Overview

The goal is to transform the development process where the developer acts as the **Product Manager**, and specialized AI Agents act as the **Engineering Team**.

### Core Philosophy: The Assembly Line

We use the filesystem as the database for the state machine. Files move through directories representing different stages of the lifecycle.

```text
.agent/
  inputs/
    design/             <-- Figma/Stitch exports, screenshots, specs
    ideas/              <-- Raw feature requests
  pipeline/
    01_planning/        <-- Planning Agent works here
    02_architecture/    <-- Architect Agent reviews here
    03_implementation/  <-- Implementation Agent builds here
    04_testing/         <-- Test Agent verifies here
    05_review/          <-- Review Agent validates (Recordings)
    06_done/            <-- Completed tasks
```

---

## 🎨 Design Integration (The Input Stage)

Before coding begins, design assets feed the Planning Agent.

**Tools**: Figma, Stitch (by Google).

1. **Export**: Export your design frames as images (PNG/JPG) or retrieve the dev mode specs/JSON.
2. **Ingest**: Place these assets into `.agent/inputs/design/<feature_name>/`.
3. **Reference**: In your idea file (e.g., `.agent/inputs/ideas/new_login.md`), explicitly reference these assets:
    > "Implement the login flow as shown in `.agent/inputs/design/login_flow/` using the color tokens defined in `design_tokens.json`."

**Workflow**: The **Planning Agent** reads these visual inputs to generate CSS variables, component structures, and layout requirements that match the design exactly.

---

## 👥 Specialized Agents

We divide the labor into five distinct AI roles.

### 1. Planning Agent 🧠

* **Trigger**: New file in `.agent/inputs/ideas/`.
* **Goal**: Turn vague ideas + designs into a concrete plan.
* **Actions**:
  * Reads codebase to understand context.
  * Asks clarifying questions (if requirements are ambiguous).
  * **Output**: Generates a **Plan Artifact** (files to touch, logic to change, edge cases).
* **Exit Criteria**: User Approval of the Plan Artifact.

### 2. Technical Architect Agent 📐

* **Trigger**: Plan Artifact approved.
* **Goal**: Ensure system integrity and best practices.
* **Actions**:
  * Reviews the Plan Artifact for security, scalability, and pattern consistency.
  * Suggests refactors or library choices.
* **Exit Criteria**: "Approved" stamp on the Plan Artifact. Moves task to `03_implementation`.

### 3. Implementation Agent 🔨

* **Trigger**: Task file in `03_implementation`.
* **Goal**: Write the code.
* **Actions**:
  * Writes code, installs dependencies.
  * Browses web for documentation/errors.
  * Fixes immediate compilation/runtime errors.
* **Exit Criteria**: Code compiles and basics work.

### 4. Test Agent 🧪

* **Trigger**: Implementation complete.
* **Goal**: Verify logic with rigorous testing.
* **Actions**:
  * Adds unit and functional tests.
  * Runs full regression suite.
  * **Output**: A "Passing Test Log" artifact.
* **Exit Criteria**: All tests pass (green build).

### 5. Review Agent 📹

* **Trigger**: Green build from Test Agent.
* **Goal**: Black-box user acceptance testing.
* **Actions**:
  * Spins up a browser sub-agent.
  * Clicks through the UI to verify the feature against the original Design/Idea specs.
  * **Output**: A **Browser Recording** video artifact.
* **Exit Criteria**: Human Manager watches video -> Merges PR.

---

## ⚡ Parallel Execution Workflows

To scale this, we can run multiple "Assembly Lines" in parallel using Git Branches.

### Workflow: "The Multithreaded Team"

1. **Branching**:
    * Each feature request in `inputs/ideas` spawns a dedicated git branch (e.g., `feature/dark-mode`, `feature/user-auth`).
2. **Context Isolation**:
    * Agents operating on `feature/dark-mode` only see that context.
    * This prevents "Implementation Agent A" from breaking files "Implementation Agent B" is editing.
3. **The Merger (CI/CD)**:
    * When the **Review Agent** signs off, the branch is marked as "Ready for Merge".
    * A final "Merge Agent" handles the rebase/merge into `main`, resolving conflicts if they arise.

### Example Scenario

* **Thread 1**: "Update Homepage" (In Review Stage) - *Review Agent recording video.*
* **Thread 2**: "Fix Login Bug" (In Test Stage) - *Test Agent running regressions.*
* **Thread 3**: "New Payment Gateway" (In Planning Stage) - *Planning Agent asking user for stripe keys.*

All three happen simultaneously. The User (Manager) simply monitors the `.agent/dashboard` (conceptual) or checks the Review folder for videos to approve.
