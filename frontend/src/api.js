/**
 * API client for the LLM Council backend.
 */

// Use localhost in development, relative path in production (same origin)
const API_BASE = import.meta.env.DEV ? 'http://localhost:8001' : '';

const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

export const api = {
  /**
   * Verify Google ID token and get session.
   */
  async login(idToken) {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken })
    });
    if (!response.ok) {
      throw new Error('Login failed');
    }
    return response.json();
  },

  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Get available models from OpenRouter (via backend).
   */
  async getModels() {
    const response = await fetch(`${API_BASE}/api/models`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    return response.json();
  },

  /**
   * Get backend status.
   */
  async getStatus() {
    const response = await fetch(`${API_BASE}/api/status`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error('Failed to get status');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error("Failed to delete conversation");
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation(framework = 'standard', councilModels = [], chairmanModel = null) {
    console.log("API: createConversation payload prep", { framework, councilModels, chairmanModel });
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        framework,
        council_models: councilModels,
        chairman_model: chairmanModel
      }),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep the last part in the buffer as it might be incomplete
      buffer = lines.pop();

      for (const line of lines) {
        if (line.trim().startsWith('data: ')) {
          const data = line.trim().slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }

    // Process any remaining buffer if it looks like a complete line (though usually streams end with newline)
    if (buffer && buffer.trim().startsWith('data: ')) {
      try {
        const event = JSON.parse(buffer.trim().slice(6));
        onEvent(event.type, event);
      } catch (e) {
        console.error('Failed to parse (final) SSE event:', e);
      }
    }
  },

  /**
   * Export conversation to file.
   * Triggers a browser download.
   */
  async exportConversation(conversationId, format = 'md') {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/export?format=${format}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) {
      throw new Error('Failed to export conversation');
    }

    // Create blob and download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // Filename is usually in Content-Disposition header, but we can guess or let browser handle it
    // Or we can try to extract it from headers if needed.
    // For simplicity, we just trigger click.
    a.download = `conversation_${conversationId}.${format === 'md' ? 'md' : 'pdf'}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};
