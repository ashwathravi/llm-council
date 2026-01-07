import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

const Stage3 = memo(function Stage3({ finalResponse, citations = [] }) {
  if (!finalResponse) {
    return null;
  }

  const hasCitations = Array.isArray(citations) && citations.length > 0;

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Final Council Answer</h3>
      <div className="final-response">
        <div className="chairman-label">
          Chairman: {finalResponse.model.split('/')[1] || finalResponse.model}
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
      {hasCitations && (
        <div className="citation-panel">
          <div className="citation-title">Sources</div>
          <ul className="citation-list">
            {citations.map((citation, index) => (
              <li key={`${citation.document_id || 'doc'}-${index}`} className="citation-item">
                <div className="citation-meta">
                  <span className="citation-name">{citation.filename}</span>
                  {citation.page_number ? (
                    <span className="citation-page">p. {citation.page_number}</span>
                  ) : null}
                </div>
                {citation.snippet && (
                  <div className="citation-snippet">{citation.snippet}</div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

export default Stage3;
