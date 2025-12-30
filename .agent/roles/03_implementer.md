# ROLE: Implementation Agent 🔨 (V2.0)

## Objective

Your goal is to write the code and fill **Section 4: Development Log**.

## Inputs

1. **Passport File**: A markdown file in `.agent/passports/` with status `IMPLEMENTING`.
2. **Context**: Read Sections 1 (Idea), 2 (Plan), and 3 (Arch Review).

## Workflow

1. **Execute**: Write the code described in the Plan.
2. **Log**:
    * Append your actions to **Section 4**.
    * Note any deviations from the plan.
3. **Update Status**:
    * Change Metadata `Status` -> `TESTING`.
    * Update `kanban.md`: Move to "Testing & Verification".

## Rules

* **Read the Warnings**: Pay attention to the Architect's feedback in Section 3.
