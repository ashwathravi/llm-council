## 2024-10-24 - [Frontend Re-render Storm]
**Learning:** The application re-renders the entire message list for every single streaming token because `App.jsx` mutates state (preventing `memo` from working even if it were there) and `ChatInterface` lacks memoization.
**Action:** Always implement immutable state updates in React, especially for streaming data, and use `React.memo` for list items in chat interfaces.

## 2025-01-02 - [Nested Component Re-renders]
**Learning:** Even with `MessageItem` memoized, its children (`Stage1`, `Stage2`, `Stage3`) were re-rendering unnecessarily during streaming updates of sibling stages. For example, during Stage 3 streaming, Stage 1 and 2 components (which are static) were re-rendering on every token because the parent `MessageItem` re-rendered.
**Action:** Memoize computational/heavy presentation components (`React.memo`) that are children of frequently updating parents, even if they seem static.
