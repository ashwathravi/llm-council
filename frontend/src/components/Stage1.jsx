import { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

const Stage1 = memo(function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs" role="tablist" aria-label="Model responses">
        {responses.map((resp, index) => (
          <button
            key={index}
            role="tab"
            id={`stage1-tab-${index}`}
            aria-selected={activeTab === index}
            aria-controls={`stage1-panel-${index}`}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
          </button>
        ))}
      </div>

      <div
        className="tab-content"
        role="tabpanel"
        id={`stage1-panel-${activeTab}`}
        aria-labelledby={`stage1-tab-${activeTab}`}
        tabIndex="0"
      >
        <div className="model-name">{responses[activeTab].model}</div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
});

export default Stage1;
