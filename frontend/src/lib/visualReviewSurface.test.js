import { describe, it } from 'node:test';
import assert from 'node:assert';
import { buildVisualReviewSurface } from './visualReviewSurface.js';

const imageArtifact = {
  id: 'img-1',
  kind: 'image',
  preview_url: '/artifact-files/mock.png',
};

const finding = {
  id: 'visual-finding-1',
  artifact_id: 'img-1',
  title: 'Weak contrast',
  comment: 'The primary action is hard to see.',
};

describe('visualReviewSurface', () => {
  it('preserves visual review sessions even before findings exist', () => {
    const surface = buildVisualReviewSurface({
      session_type: 'visual_review',
      primary_artifacts: [imageArtifact],
      visual_findings: [],
    });

    assert.strictEqual(surface.shouldShow, true);
    assert.strictEqual(surface.tabLabel, 'Visual');
  });

  it('shows Design Studio critique when image findings are available', () => {
    const surface = buildVisualReviewSurface({
      session_type: 'design_studio',
      primary_artifacts: [imageArtifact],
      visual_findings: [finding],
      visual_review: {
        panel_enabled: true,
        mode: 'design_studio_critique',
      },
    });

    assert.strictEqual(surface.shouldShow, true);
    assert.strictEqual(surface.tabLabel, 'Critique');
    assert.strictEqual(surface.title, 'Artifact Critique Surface');
    assert.strictEqual(surface.findings.length, 1);
  });

  it('does not show Design Studio image panels without artifact-tied findings', () => {
    const surface = buildVisualReviewSurface({
      session_type: 'design_studio',
      primary_artifacts: [imageArtifact],
      visual_findings: [],
      visual_review: { panel_enabled: true },
    });

    assert.strictEqual(surface.shouldShow, false);
  });

  it('ignores incomplete findings and non-image artifacts', () => {
    const surface = buildVisualReviewSurface({
      session_type: 'design_studio',
      primary_artifacts: [{ id: 'doc-1', kind: 'document', preview_url: '/doc' }],
      visual_findings: [{ artifact_id: 'img-1', title: 'Missing comment' }],
      visual_review: { panel_enabled: true },
    });

    assert.strictEqual(surface.shouldShow, false);
    assert.deepStrictEqual(surface.imageArtifacts, []);
    assert.deepStrictEqual(surface.findings, []);
  });
});
