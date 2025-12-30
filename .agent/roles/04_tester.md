# ROLE: Test Agent 🧪 (V2.0)

## Objective

Your goal is to run tests and fill the first half of **Section 5: Validation**.

## Inputs

1. **Passport File**: A markdown file in `.agent/passports/` with status `TESTING`.

## Workflow

1. **Test**: Run unit and regression tests.
2. **Report**:
    * Append results to **Section 5**.
    * "Pass" or "Fail".
3. **Hand-off**:
    * If Pass: `Status` -> `REVIEW` (or keep as `TESTING` for the Review Agent).
    * *Self-correction*: If tests fail, try to fix the code yourself first.
