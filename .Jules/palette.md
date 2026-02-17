## 2024-05-24 - Accessible Interactive Cards
**Learning:** Interactive cards that act as radio buttons or links must implement `role="button"`, `tabIndex="0"`, and `onKeyDown` (Enter/Space) to be accessible. Simply adding `onClick` to a `div` is insufficient for keyboard users.
**Action:** When creating selection grids, ensure interactive containers have proper ARIA roles and keyboard event handlers. Always add visible focus indicators (`focus-visible:ring`) to these custom interactive elements.
