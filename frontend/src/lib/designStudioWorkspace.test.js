import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  buildDesignStudioWorkspaceView,
  formatDesignStudioScore,
} from './designStudioWorkspace.js';

describe('designStudioWorkspace', () => {
  it('returns an empty workspace for missing candidate metadata', () => {
    const view = buildDesignStudioWorkspaceView();

    assert.strictEqual(view.status, 'empty');
    assert.deepStrictEqual(view.candidateCards, []);
    assert.strictEqual(view.selectedCard, null);
  });

  it('keeps empty candidate arrays explicit instead of producing blank panels', () => {
    const view = buildDesignStudioWorkspaceView({
      candidate_directions: [],
      comparison: { status: 'pending' },
    });

    assert.strictEqual(view.status, 'empty');
    assert.strictEqual(view.hasComparison, false);
    assert.deepStrictEqual(view.failedVariants, []);
  });

  it('handles one pending candidate without comparison data', () => {
    const view = buildDesignStudioWorkspaceView({
      candidate_directions: [
        {
          id: 'direction-a',
          label: 'Direction A',
          response_label: 'Response A',
          source_model: 'model-a',
          summary: 'A concise product surface.',
        },
      ],
      comparison: { status: 'pending' },
    });

    assert.strictEqual(view.status, 'single');
    assert.strictEqual(view.selectedDirectionId, 'direction-a');
    assert.strictEqual(view.selectedCard.label, 'Direction A');
    assert.strictEqual(view.candidateCards[0].isSelected, true);
  });

  it('sorts compared candidates by aggregate rank and attaches scorecards', () => {
    const view = buildDesignStudioWorkspaceView({
      candidate_directions: [
        { id: 'direction-a', label: 'Direction A', source_model: 'model-a' },
        { id: 'direction-b', label: 'Direction B', source_model: 'model-b' },
      ],
      selected_direction_id: 'direction-b',
      comparison: {
        status: 'complete',
        ranked_directions: [
          {
            direction_id: 'direction-b',
            rank: 1,
            average_rank: 1.2,
            rankings_count: 3,
            total_weight: 2.5,
            weighted: true,
          },
          {
            direction_id: 'direction-a',
            rank: 2,
            average_rank: 2,
            rankings_count: 3,
          },
        ],
        rubric_summaries: [
          {
            direction_id: 'direction-b',
            overall_score: 4.4,
            criteria: [{ key: 'clarity', label: 'Clarity', average_score: 4.6 }],
          },
        ],
      },
    });

    assert.strictEqual(view.status, 'complete');
    assert.strictEqual(view.candidateCards[0].id, 'direction-b');
    assert.strictEqual(view.candidateCards[0].isSelected, true);
    assert.strictEqual(view.candidateCards[0].averageRank, 1.2);
    assert.strictEqual(view.candidateCards[0].overallScore, 4.4);
    assert.strictEqual(view.candidateCards[0].criteria[0].label, 'Clarity');
  });

  it('keeps malformed comparison fields and partial failures from breaking the view', () => {
    const view = buildDesignStudioWorkspaceView(
      {
        candidate_directions: [
          { id: 'direction-a', label: 'Direction A', source_model: 'model-a' },
          { id: 'direction-b', label: 'Direction B', source_model: 'model-b' },
        ],
        comparison: {
          status: 'complete',
          ranked_directions: 'bad-data',
          rubric_summaries: [{ direction_id: 'direction-a', criteria: 'bad-data' }],
        },
      },
      [{ model: 'model-c', error: 'timeout' }]
    );

    assert.strictEqual(view.status, 'complete');
    assert.strictEqual(view.hasPartialFailures, true);
    assert.deepStrictEqual(view.failedVariants, [{ model: 'model-c', error: 'timeout' }]);
    assert.deepStrictEqual(view.candidateCards[0].criteria, []);
  });

  it('keeps pending comparison states operable with multiple variants', () => {
    const view = buildDesignStudioWorkspaceView({
      candidate_directions: [
        { id: 'direction-a', label: 'Direction A', source_model: 'model-a' },
        { id: 'direction-b', label: 'Direction B', source_model: 'model-b' },
      ],
      comparison: { status: 'pending' },
    });

    assert.strictEqual(view.status, 'pending');
    assert.strictEqual(view.hasComparison, true);
    assert.strictEqual(view.candidateCards.length, 2);
    assert.strictEqual(view.selectedDirectionId, 'direction-a');
  });

  it('formats numeric scores for compact UI labels', () => {
    assert.strictEqual(formatDesignStudioScore(4), '4');
    assert.strictEqual(formatDesignStudioScore(4.25), '4.3');
    assert.strictEqual(formatDesignStudioScore(null), 'n/a');
  });
});
