import React, { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

const MessageItem = memo(({ msg }) => {
  return (
    <div className="message-group">
      {msg.role === 'user' ? (
        <div className="user-message">
          <div className="message-label">You</div>
          <div className="message-content">
            <div className="markdown-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        </div>
      ) : (
        <div className="assistant-message">
          <div className="message-label">LLM Council</div>

          {msg.errors && msg.errors.length > 0 && (
            <div className="stage-error-panel">
              <div className="stage-error-title">Model errors</div>
              <ul className="stage-error-list">
                {msg.errors.map((error, errorIndex) => (
                  <li key={errorIndex}>
                    <strong>{error.model}:</strong> {error.error}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Stage 1 */}
          {msg.loading?.stage1 && (
            <div className="stage-loading">
              <div className="spinner"></div>
              <span>Running Stage 1: Collecting individual responses...</span>
            </div>
          )}
          {msg.stage1 && <Stage1 responses={msg.stage1} />}

          {/* Stage 2 */}
          {msg.loading?.stage2 && (
            <div className="stage-loading">
              <div className="spinner"></div>
              <span>Running Stage 2: Peer rankings...</span>
            </div>
          )}
          {msg.stage2 && (
            <Stage2
              rankings={msg.stage2}
              labelToModel={msg.metadata?.label_to_model}
              aggregateRankings={msg.metadata?.aggregate_rankings}
            />
          )}

          {/* Stage 3 */}
          {msg.loading?.stage3 && (
            <div className="stage-loading">
              <div className="spinner"></div>
              <span>Running Stage 3: Final synthesis...</span>
            </div>
          )}
          {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
        </div>
      )}
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

export default MessageItem;
