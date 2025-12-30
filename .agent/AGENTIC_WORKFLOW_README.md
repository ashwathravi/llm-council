# Agentic Workflow V3.0: The Autonomous Stream �

## 🌟 Concept

Version 3.0 eliminates the "relay race" friction of V2.0. Instead of constantly prompting the next agent, we shift to a **Deep Planning** model followed by **Autonomous Execution**.

* **Front-Loaded Effort**: You and the Planner Agent clarify *everything* upfront.
* **Zero-Friction Handoffs**: Once execution starts, agents handle the `Plan -> Architect -> Code -> Test` transitions automatically.

## 🔄 The V3.0 Process

### Phase 1: Deep Planning (Human-in-the-Loop) 🧠

The goal is to remove ambiguity before a single line of code is written.

1. **Ideation**: You create a Passport and fill "Idea & Context".
2. **Interrogation**: The Planner Agent reads your idea and **interviews you**.
    * *It will ask about edge cases.*
    * *It will point out contradictions.*
    * *It will require decisions on UI/UX details.*
3. **The Blueprint**: The Planner updates the `search` and `plan` sections until a "Blueprint" is finalized.
    * *For Large Features*: The Blueprint is broken into **Milestones** (e.g., `M1: API`, `M2: UI`).
    * *Atomic Units*: Each Milestone is a verifiable unit.
4. **Authorization**: You explicitly **APPROVE** the Blueprint. This is the "Green Button".

### Phase 2: Autonomous Execution (Agent Auto-Pilot) 🤖

Once the Blueprint is approved, the system executes the chain without user intervention.

1. **Architecture Check**: Agent validates the plan against security/system constraints. (Self-correction if minor issues found; notify user only if CRITICAL).
2. **Milestone Execution Loop**:
    * **Implement**: Agent writes the code for the current Milestone.
    * **Verify**: Agent acts as a "Gatekeeper", running tests/visual checks specific to this Milestone.
    * **Merge**: *Optionally*, the agent can merge/commit this atomic unit before starting the next Milestone.
3. **Completion**: Once all Milestones are verified, the full feature is ready for final review.

*The Agent will only pause and return to you if:*

* *Blocking Ambiguity*: A decision is needed that wasn't in the Blueprint.
* *Critical Failure*: The approach in the Blueprint is technically impossible.

### Phase 3: Final Review (Human-in-the-Loop) 🏁

You are notified only when the work is **DONE** (or critically blocked).

* Review the `passports/my_feature.md` for the "Verification" logs.
* Check the code/demo.
* Mark as `DONE` or request changes.

## 📂 Directory Structure

* **`kanban.md`**: The Status Board.
  * **Planning**: Ideas being refined.
  * **Approved for Auto-Run**: Items where the Blueprint is sealed. (Agents pick these up automatically).
  * **In Progress**: Active execution.
  * **Review**: Waiting for your final look.
* **`passports/`**: The Living Documents.

## 🚦 How to Use

1. **Create**:

    ```bash
    cp .agent/templates/feature_passport.md .agent/passports/my_feature.md
    ```

2. **Define**: Fill out Section 1.
3. **Initiate**:
    > "Help me refine the plan for [Feature Name]."
4. **Approve & Launch**:
    > "The plan looks good. Execute it."
    *(The agents will now take it from here until it's ready for review).*
