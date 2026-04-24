import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  buildDesignStudioHandoffView,
  getDesignStudioHandoffSection,
  hasDesignStudioHandoffSectionContent,
} from './designStudioHandoff.js';

describe('designStudioHandoff', () => {
  it('builds a renderable handoff view with state and platform sections', () => {
    const view = buildDesignStudioHandoffView({
      status: 'ready',
      selected_direction_ref: {
        id: 'direction-b',
        label: 'Direction B',
        source_model: 'model-b',
        summary: 'A guided workspace.',
      },
      selected_direction: {
        label: 'Selected Direction',
        content: 'Direction B is approved.',
        items: [],
      },
      rationale: {
        label: 'Rationale',
        content: '- Better scan path.',
        items: ['Better scan path.'],
      },
      state_notes: {
        label: 'State Notes',
        content: '- Empty state is explicit.',
        items: ['Empty state is explicit.'],
      },
      platform_constraints: {
        label: 'Platform Constraints',
        content: '- iOS actions stay thumb reachable.',
        items: ['iOS actions stay thumb reachable.'],
      },
    });

    assert.strictEqual(view.hasContent, true);
    assert.strictEqual(view.selectedRef.label, 'Direction B');
    assert.strictEqual(view.selectedSection.content, 'Direction B is approved.');
    assert.deepStrictEqual(
      view.sections.map((section) => section.label),
      ['Rationale', 'State Notes', 'Platform Constraints']
    );
  });

  it('normalizes legacy sections array entries', () => {
    const section = getDesignStudioHandoffSection({
      sections: [
        {
          key: 'component_map',
          label: 'Component Map',
          content: '',
          items: ['Workspace: split comparison layout.'],
        },
      ],
    }, 'component_map');

    assert.strictEqual(section.label, 'Component Map');
    assert.deepStrictEqual(section.items, ['Workspace: split comparison layout.']);
    assert.strictEqual(hasDesignStudioHandoffSectionContent(section), true);
  });

  it('treats pending or empty handoffs as non-renderable', () => {
    assert.strictEqual(buildDesignStudioHandoffView({ status: 'pending' }).hasContent, false);
    assert.strictEqual(buildDesignStudioHandoffView({ status: 'ready' }).hasContent, false);
  });
});
