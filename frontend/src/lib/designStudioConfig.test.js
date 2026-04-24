import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  DEFAULT_DESIGN_STUDIO_CONFIG,
  getDesignTargetLabel,
  getStudioGoalLabel,
  normalizeSessionConfig,
} from './designStudioConfig.js';

describe('designStudioConfig', () => {
  it('normalizes design studio defaults', () => {
    assert.deepStrictEqual(
      normalizeSessionConfig('design_studio'),
      {
        ...DEFAULT_DESIGN_STUDIO_CONFIG,
      }
    );
  });

  it('normalizes invalid design studio values', () => {
    assert.deepStrictEqual(
      normalizeSessionConfig('design_studio', {
        design_target: 'desktop_app',
        studio_goal: 'ship_it',
        approved_direction_id: '   ',
      }),
      {
        design_target: 'web_app',
        studio_goal: 'generate',
        approved_direction_id: null,
      }
    );
  });

  it('preserves valid design studio values and trims approved direction', () => {
    assert.deepStrictEqual(
      normalizeSessionConfig('design_studio', {
        design_target: 'mixed',
        studio_goal: 'compare',
        approved_direction_id: '  direction-7  ',
      }),
      {
        design_target: 'mixed',
        studio_goal: 'compare',
        approved_direction_id: 'direction-7',
      }
    );
  });

  it('normalizes legacy both target to mixed', () => {
    assert.strictEqual(
      normalizeSessionConfig('design_studio', { design_target: 'both' }).design_target,
      'mixed'
    );
  });

  it('clears config for non-design sessions', () => {
    assert.deepStrictEqual(
      normalizeSessionConfig('general', {
        design_target: 'mixed',
        studio_goal: 'handoff',
      }),
      {}
    );
  });

  it('returns readable labels', () => {
    assert.strictEqual(getDesignTargetLabel('mixed'), 'Mixed Web + iOS');
    assert.strictEqual(getDesignTargetLabel('both'), 'Mixed Web + iOS');
    assert.strictEqual(getStudioGoalLabel('handoff'), 'Handoff');
  });
});
