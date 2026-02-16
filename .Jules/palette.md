## 2024-05-22 - Login Loading State
**Learning:** Users often double-click login buttons or feel uncertain during backend verification steps if no visual feedback is provided.
**Action:** Implemented a "Verifying credentials..." loading state with a spinner that replaces the Google Login button upon a successful OAuth response. This ensures users know the system is working while waiting for the backend JWT exchange. Used `aria-busy` and `role="alert"` (for errors) to ensure the state change is accessible.

## 2024-05-23 - Tooltip Accessibility
**Learning:** Tooltips triggered only by `:hover` exclude keyboard users.
**Action:** Converted an icon-only `<span>` tooltip trigger into a semantic `<button>`. Used CSS `:focus + .tooltip` selector (alongside `:hover`) and `aria-describedby` to ensure keyboard users can access the help text via Tab navigation.

## 2024-05-24 - Disabled Button Accessibility
**Learning:** Standard `disabled` attributes remove elements from the tab order, preventing keyboard and screen reader users from discovering *why* an action is unavailable.
**Action:** Replaced `disabled` attribute with `aria-disabled="true"` and custom CSS to maintain focusability. Added `aria-describedby` pointing to a tooltip that explains the constraint (e.g., "Start a conversation to attach files"), ensuring all users can understand the interface state. Also fixed `ModelSelect` keyboard navigation (Escape to close, focus tracking).

## 2024-05-25 - Sidebar Navigation Accessibility
**Learning:** Complex list items (like conversation rows with internal actions) often default to `div` with `onClick`, excluding keyboard users. Nested buttons are invalid HTML, complicating the structure.
**Action:** Implemented `role="button"`, `tabIndex={0}`, and `onKeyDown` (Enter/Space) on the container `div` to make the row selectable via keyboard without breaking layout or HTML validity. Ensure internal actions (like delete) stop propagation. Added dynamic `aria-label` attributes to icon-only buttons that change context based on sidebar collapse state.
