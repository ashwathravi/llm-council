## 2024-05-22 - Login Loading State
**Learning:** Users often double-click login buttons or feel uncertain during backend verification steps if no visual feedback is provided.
**Action:** Implemented a "Verifying credentials..." loading state with a spinner that replaces the Google Login button upon a successful OAuth response. This ensures users know the system is working while waiting for the backend JWT exchange. Used `aria-busy` and `role="alert"` (for errors) to ensure the state change is accessible.

## 2024-05-23 - Tooltip Accessibility
**Learning:** Tooltips triggered only by `:hover` exclude keyboard users.
**Action:** Converted an icon-only `<span>` tooltip trigger into a semantic `<button>`. Used CSS `:focus + .tooltip` selector (alongside `:hover`) and `aria-describedby` to ensure keyboard users can access the help text via Tab navigation.

## 2024-05-24 - Disabled Button Accessibility
**Learning:** Standard `disabled` attributes remove elements from the tab order, preventing keyboard and screen reader users from discovering *why* an action is unavailable.
**Action:** Replaced `disabled` attribute with `aria-disabled="true"` and custom CSS to maintain focusability. Added `aria-describedby` pointing to a tooltip that explains the constraint (e.g., "Start a conversation to attach files"), ensuring all users can understand the interface state. Also fixed `ModelSelect` keyboard navigation (Escape to close, focus tracking).

## 2024-05-25 - Icon-Only Button Labels
**Learning:** Icon-only buttons (like Trash, Plus, Settings) rely entirely on visual context and are invisible to screen readers without explicit labels. Tooltips (if hover-only) are insufficient.
**Action:** Added `aria-label` to all icon-only buttons in `CouncilSidebar.jsx` (New Session, Manage Council, Settings, Delete, Collapse) ensuring they are announceable and accessible to all users.

## 2024-05-24 - Accessible Interactive Cards
**Learning:** Interactive cards that act as radio buttons or links must implement `role="button"`, `tabIndex="0"`, and `onKeyDown` (Enter/Space) to be accessible. Simply adding `onClick` to a `div` is insufficient for keyboard users.
**Action:** When creating selection grids, ensure interactive containers have proper ARIA roles and keyboard event handlers. Always add visible focus indicators (`focus-visible:ring`) to these custom interactive elements.
