## 2024-05-22 - Login Loading State
**Learning:** Users often double-click login buttons or feel uncertain during backend verification steps if no visual feedback is provided.
**Action:** Implemented a "Verifying credentials..." loading state with a spinner that replaces the Google Login button upon a successful OAuth response. This ensures users know the system is working while waiting for the backend JWT exchange. Used `aria-busy` and `role="alert"` (for errors) to ensure the state change is accessible.

## 2024-05-23 - Tooltip Accessibility
**Learning:** Tooltips triggered only by `:hover` exclude keyboard users.
**Action:** Converted an icon-only `<span>` tooltip trigger into a semantic `<button>`. Used CSS `:focus + .tooltip` selector (alongside `:hover`) and `aria-describedby` to ensure keyboard users can access the help text via Tab navigation.
