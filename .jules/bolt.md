## 2024-10-24 - [Frontend Re-render Storm]
**Learning:** The application re-renders the entire message list for every single streaming token because `App.jsx` mutates state (preventing `memo` from working even if it were there) and `ChatInterface` lacks memoization.
**Action:** Always implement immutable state updates in React, especially for streaming data, and use `React.memo` for list items in chat interfaces.
