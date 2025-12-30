# Feature Passport 🎫

| Metadata | Value |
| :--- | :--- |
| **Feature Name** | [Enter Feature Name] |
| **Status** | `DRAFT` -> `PLANNING` -> `APPROVED` -> `IN_PROGRESS` -> `REVIEW` -> `DONE` |
| **Priority** | P2 |
| **Assignee** | Agent |

---

## 🧠 Phase 1: Deep Planning (Human & Planner Agent)

### 1.1 Idea & Context (User Input)

*Describe the feature here. Attach images from `.agent/assets` if needed.*

### 1.2 Requirements & Corner Cases (User Input)

- [ ] Requirement 1
- [ ] Requirement 2
- *Corner Case*: What happens if...?

### 1.3 Clarification Log (Iterative)

*(Agent asks questions here, User answers)*

- **Q**: [Agent Q]
- **A**: [User A]

### 1.4 The Blueprint (Planner Agent)

*The finalized technical plan. To be approved by User.*

#### Files to Create/Modify

- `src/path/to/file.ts`

#### Milestones

*If the feature is huge, the Planner will break it down here.*

**Milestone 1: [Name]**

1. Step 1
2. Step 2

**Milestone 2: [Name]**

1. ...

> [!IMPORTANT]
> **Approval**:
>
> - [ ] I have reviewed the Clarification Log and The Blueprint.
> - [ ] I authorize the agents to Execute this plan. (Transition Status to `APPROVED`).

---

## 🏃 Phase 2: Autonomous Execution (Auto-Pilot)

*Triggers automatically when Status = `APPROVED`*

### 2.1 Architecture Review (Architect Agent)

- [ ] Security/Consistency Check Passed
- *Adjustments made to Blueprint*: (None/List)

### 2.2 Execution Log (Implementation Agent)

#### Milestone 1

* [ ] Step 1
- [ ] Verification (Tests/Screenshots): `[link](...)`

#### Milestone 2

* [ ] Step 1...

### 2.3 Final Assembly

**Outcome**: Status moved to `REVIEW`

---

## 🏁 Phase 3: Final Review (User)

- [ ] I have verified the functionality.
- [ ] Code looks good.

**Action**: Move Status to `DONE`.
