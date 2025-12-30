# Feature Passport 🎫

| Metadata | Value |
| :--- | :--- |
| **Feature Name** | [Enter Feature Name] |
| **Status** | `DRAFT` (Move to `PLANNING` when ready) |
| **Priority** | P2 |
| **Assignee** | Unassigned |

---

## 🚀 1. Idea & Context (User Input)

*Describe the feature here. Attach images from `.agent/assets` if needed.*

### Requirements

- [ ] Requirement 1
- [ ] Requirement 2

### Design References

- Link to Figma/Stitch or `.agent/assets/design_mockup.png`

---

## 🧠 2. Implementation Strategy (Planner Agent)

*Trigger: Status = `PLANNING`*

### Analysis

* **Files Touched**:
  - `src/components/Example.tsx`
- **Dependencies**: None

### Plan

1. Step 1
2. Step 2

> [!NOTE]
> **Questions for User**:
>
> 1. ...

**Next Step**: Change Status to `ARCHITECT_REVIEW`

---

## 📐 3. Architecture Sign-off (Architect Agent)

*Trigger: Status = `ARCHITECT_REVIEW`*

### Review

- [ ] Security Check
- [ ] Scalability Check

> [!TIP]
> **Feedback**:
> ...

**Decision**: ✅ APPROVED / ❌ REJECTED
**Next Step**: If Approved, change Status to `IMPLEMENTING`.

---

## 🔨 4. Development Log (Implementation Agent)

*Trigger: Status = `IMPLEMENTING`*

### Changelog

* Modified `src/foo.ts`
- Added `src/bar.ts`

### Hurdles & Resolutions

* *Issue*: Library X didn't work.
- *Fix*: Used Library Y instead.

**Next Step**: Change Status to `TESTING`

---

## 🧪 5. Validation (Test/Review Agent)

*Trigger: Status = `TESTING`*

### Test Results

- [ ] Unit Tests Passed
- [ ] Integration Tests Passed

### Visual Verification

* [ ] Screen Recording: `[review_video.webm](file:///...)`

**Next Step**: Change Status to `DONE`
