import time
from playwright.sync_api import sync_playwright, expect

def verify_chat_rendering(page):
    page.set_viewport_size({"width": 1280, "height": 720})

    # Mock /api/conversations (List)
    page.route("**/api/conversations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='[{"id":"123","title":"Test Conversation","created_at":"2023-01-01T00:00:00Z","framework":"standard"}]'
    ))

    # Mock /api/conversations/123 (Detail)
    page.route("**/api/conversations/123", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''
        {
            "id": "123",
            "title": "Test Conversation",
            "framework": "standard",
            "messages": [
                {"role": "user", "content": "Hello World"},
                {"role": "assistant", "stage3": {"model": "chairman", "response": "Hello from the Council."}}
            ]
        }
        '''
    ))

    # Mock /api/models
    page.route("**/api/models", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='[{"id":"test-model","name":"Test Model"}]'
    ))

    # Mock /api/status
    page.route("**/api/status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"storage_mode":"filesystem","origin":"local"}'
    ))

    # Go to app
    page.goto("http://localhost:5173")

    # Click the conversation in the sidebar
    # We target the sidebar explicitly
    page.locator(".conversations-list").get_by_text("Test Conversation").click()

    # Wait for the user message
    expect(page.get_by_text("Hello World")).to_be_visible()

    # Wait for the assistant message
    expect(page.get_by_text("Hello from the Council.")).to_be_visible()

    # Screenshot
    page.screenshot(path="/home/jules/verification/verification.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    # Mock user in localStorage
    page.add_init_script("localStorage.setItem('user', JSON.stringify({name: 'Test User', id: 'user123', email: 'test@example.com'}));")
    page.add_init_script("localStorage.setItem('token', 'fake-jwt');")

    try:
        verify_chat_rendering(page)
    finally:
        browser.close()
