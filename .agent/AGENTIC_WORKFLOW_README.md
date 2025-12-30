# Agentic Workflow V2.0: The Feature Passport 🎫

Welcome to the improved **Feature Passport** system.

## 🌟 Concept

Instead of managing distinct task files, we manage a single **Living Document** for each feature. This document, the "Passport", travels through the system, collecting stamps (approvals) and data (plans, logs, test results) from various agents.

## 📂 Directory Structure

* **`kanban.md`**: Your Command Center. View all active features here.
* **`passports/`**: The directory containing the actual `.md` passport files.
* **`templates/`**: Contains the blank Passport template.
* **`assets/`**: Place design images or screenshots here to reference in your passports.

## 🚦 How to Start a New Feature

1. **Create**:

    ```bash
    cp .agent/templates/feature_passport.md .agent/passports/my_new_feature.md
    ```

2. **Define**: Open `passports/my_new_feature.md` and fill out Section 1 (Idea & Context).
3. **Activate**: Open `kanban.md` and add `[My New Feature](passports/my_new_feature.md)` under the **Planning** header.
4. **Run**:
    * Tell the Planner Agent: "Check `.agent/kanban.md` for planning tasks." or "Check the Kanban board and run the appropriate agents."
    * The Agent will find your file, fill Section 2, and update the status.
