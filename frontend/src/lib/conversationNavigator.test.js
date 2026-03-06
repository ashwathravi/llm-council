import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  buildTurnAnchorId,
  buildSnippet,
  getTurnStatus,
  buildConversationOutline,
  TURN_ANCHOR_PREFIX,
  NAVIGATOR_SNIPPET_MAX_LENGTH
} from './conversationNavigator.js';

describe('conversationNavigator', () => {
  describe('buildTurnAnchorId', () => {
    it('should return the correct anchor ID', () => {
      assert.strictEqual(buildTurnAnchorId(0), `${TURN_ANCHOR_PREFIX}0`);
      assert.strictEqual(buildTurnAnchorId(5), `${TURN_ANCHOR_PREFIX}5`);
    });
  });

  describe('buildSnippet', () => {
    it('should return (No text) for empty or null input', () => {
      assert.strictEqual(buildSnippet(''), '(No text)');
      assert.strictEqual(buildSnippet(null), '(No text)');
      assert.strictEqual(buildSnippet(undefined), '(No text)');
    });

    it('should normalize spaces', () => {
      assert.strictEqual(buildSnippet('  hello   world  '), 'hello world');
    });

    it('should truncate long text', () => {
      const longText = 'a'.repeat(NAVIGATOR_SNIPPET_MAX_LENGTH + 10);
      const expected = 'a'.repeat(NAVIGATOR_SNIPPET_MAX_LENGTH) + '...';
      assert.strictEqual(buildSnippet(longText), expected);
    });

    it('should not truncate text at or below max length', () => {
      const exactText = 'a'.repeat(NAVIGATOR_SNIPPET_MAX_LENGTH);
      assert.strictEqual(buildSnippet(exactText), exactText);
    });

    it('should respect custom maxLength', () => {
       assert.strictEqual(buildSnippet('hello world', 5), 'hello...');
    });
  });

  describe('getTurnStatus', () => {
    it('should return complete if no assistant message and not loading', () => {
      assert.strictEqual(getTurnStatus(null, false), 'complete');
    });

    it('should return in_progress if no assistant message and loading', () => {
      assert.strictEqual(getTurnStatus(null, true), 'in_progress');
    });

    it('should return in_progress if assistant message is loading', () => {
      const msg = {
        role: 'assistant',
        loading: { stage1: true }
      };
      assert.strictEqual(getTurnStatus(msg), 'in_progress');
    });

    it('should return has_errors if assistant message has direct errors', () => {
      const msg = {
        role: 'assistant',
        errors: ['error']
      };
      assert.strictEqual(getTurnStatus(msg), 'has_errors');
    });

    it('should return has_errors if assistant message has stage1_errors', () => {
      const msg = {
        role: 'assistant',
        metadata: { stage1_errors: ['error'] }
      };
      assert.strictEqual(getTurnStatus(msg), 'has_errors');
    });

    it('should return complete if assistant message has stage3 response', () => {
      const msg = {
        role: 'assistant',
        stage3: { response: 'Hello' }
      };
      assert.strictEqual(getTurnStatus(msg), 'complete');
    });

    it('should return in_progress if assistant message has empty stage3 response', () => {
      const msg = {
        role: 'assistant',
        stage3: { response: '' }
      };
      assert.strictEqual(getTurnStatus(msg), 'in_progress');
    });
  });

  describe('buildConversationOutline', () => {
    it('should return empty array for empty messages', () => {
      assert.deepStrictEqual(buildConversationOutline([]), []);
    });

    it('should build outline for a simple conversation', () => {
      const messages = [
        { role: 'user', content: 'hello' },
        { role: 'assistant', stage3: { response: 'hi' } }
      ];
      const outline = buildConversationOutline(messages);
      assert.strictEqual(outline.length, 1);
      assert.strictEqual(outline[0].turnNumber, 1);
      assert.strictEqual(outline[0].snippet, 'hello');
      assert.strictEqual(outline[0].status, 'complete');
    });

    it('should handle in-progress turns', () => {
      const messages = [
        { role: 'user', content: 'hello' }
      ];
      const outline = buildConversationOutline(messages, true);
      assert.strictEqual(outline[0].status, 'in_progress');
    });

    it('should handle multiple turns', () => {
      const messages = [
        { role: 'user', content: 'q1' },
        { role: 'assistant', stage3: { response: 'a1' } },
        { role: 'user', content: 'q2' },
        { role: 'assistant', loading: { stage2: true } }
      ];
      const outline = buildConversationOutline(messages);
      assert.strictEqual(outline.length, 2);
      assert.strictEqual(outline[0].status, 'complete');
      assert.strictEqual(outline[1].status, 'in_progress');
    });
  });
});
