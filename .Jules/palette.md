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

## 2024-05-25 - Icon-Only Button Labels
**Learning:** Icon-only buttons (like Trash, Plus, Settings) rely entirely on visual context and are invisible to screen readers without explicit labels. Tooltips (if hover-only) are insufficient.
**Action:** Added `aria-label` to all icon-only buttons in `CouncilSidebar.jsx` (New Session, Manage Council, Settings, Delete, Collapse) ensuring they are announceable and accessible to all users.

## 2024-05-24 - Accessible Interactive Cards
**Learning:** Interactive cards that act as radio buttons or links must implement `role="button"`, `tabIndex="0"`, and `onKeyDown` (Enter/Space) to be accessible. Simply adding `onClick` to a `div` is insufficient for keyboard users.
**Action:** When creating selection grids, ensure interactive containers have proper ARIA roles and keyboard event handlers. Always add visible focus indicators (`focus-visible:ring`) to these custom interactive elements.

## 2024-05-25 - Sidebar Tooltip Consistency
**Learning:** Collapsible sidebars often hide text labels, relying on icons. While `aria-label` provides accessibility, sighted users may struggle to recall icon meanings without visible text.
**Action:** Implemented tooltips that appear only when the sidebar is collapsed (for text-hidden items) or always (for icon-only items). Used `TooltipProvider` to manage delay and ensure consistent behavior across all sidebar actions.

## 2024-05-26 - Switch Label Accessibility
**Learning:** Toggle switches (like `Switch` components) often lack explicit text labels when used in a list context, relying on adjacent text that isn't programmatically associated.
**Action:** Added dynamic `aria-label` attributes to `Switch` components (e.g., `aria-label="Select [Model Name]"`) to ensure screen readers announce the purpose of the control, even without an explicit `<label>` element. Applied the same pattern to associated action buttons (Favorites, Chairman) to disambiguate controls in a repetitive list.

## 2024-03-24 - Search in Long Lists
**Learning:** Users with many options (e.g., >10 models) struggle to find specific items in scrollable lists.
**Action:** Implemented a real-time search filter with `aria-label` for accessibility in the configuration dialog. When presenting long lists, always include a filter input to improve efficiency and keyboard accessibility.

## 2025-02-28 - Copy Button Visibility
**Learning:** Actions revealed only on hover (like "Copy Code") are invisible and often inaccessible to keyboard-only users, as they cannot hover to trigger the visibility.
**Action:** Added `focus-within:opacity-100` to the container of the Copy button in `MarkdownRenderer.jsx`. This ensures that when a keyboard user tabs into the button, the container becomes visible, revealing the control.
