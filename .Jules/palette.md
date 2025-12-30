## 2024-05-22 - Login Loading State
**Learning:** Users often double-click login buttons or feel uncertain during backend verification steps if no visual feedback is provided.
**Action:** Implemented a "Verifying credentials..." loading state with a spinner that replaces the Google Login button upon a successful OAuth response. This ensures users know the system is working while waiting for the backend JWT exchange. Used `aria-busy` and `role="alert"` (for errors) to ensure the state change is accessible.
