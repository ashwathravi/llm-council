
from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Mock the API calls
        page.route("**/api/auth/login", lambda route: route.fulfill(
            status=200,
            body='{"access_token": "mock_token", "token_type": "bearer", "user": {"id": "mock_user", "name": "Mock User", "email": "mock@example.com"}}',
            headers={"content-type": "application/json"}
        ))

        page.route("**/api/conversations", lambda route: route.fulfill(
            status=200,
            body='[{"id": "1", "title": "Mock Conv", "created_at": "2023-01-01", "framework": "standard"}]',
            headers={"content-type": "application/json"}
        ))

        page.route("**/api/models", lambda route: route.fulfill(
            status=200,
            body="[]",
            headers={"content-type": "application/json"}
        ))

        page.route("**/api/status", lambda route: route.fulfill(
            status=200,
            body='{"storage_mode": "database", "origin": "local"}',
            headers={"content-type": "application/json"}
        ))

        page.goto("http://localhost:5173")

        # Inject auth token to simulate logged in state
        page.evaluate("""() => {
            localStorage.setItem('auth_token', 'mock_token');
            localStorage.setItem('auth_user', JSON.stringify({"id": "mock_user", "name": "Mock User", "email": "mock@example.com"}));
        }""")

        page.reload()

        # Wait for sidebar
        try:
            page.wait_for_selector(".sidebar", timeout=5000)
            print("Sidebar found")
        except:
            print("Sidebar not found")
            return

        # Resize to mobile
        page.set_viewport_size({"width": 375, "height": 667})
        time.sleep(1)

        # Check if sidebar is open
        sidebar = page.locator(".sidebar")
        is_open = "open" in sidebar.get_attribute("class")
        print(f"Sidebar open initially: {is_open}")

        if is_open:
            # Test closing it
            print("Testing closing sidebar...")
            page.screenshot(path="verification/mobile_sidebar_open.png")

            # Click close button
            if page.is_visible(".sidebar-close-btn"):
                page.click(".sidebar-close-btn")
                time.sleep(1)

                # Verify it's closed
                is_open_after = "open" in sidebar.get_attribute("class")
                print(f"Sidebar open after close: {is_open_after}")

                if not is_open_after:
                     print("SUCCESS: Sidebar closed.")
                else:
                     print("FAILURE: Sidebar still open.")

                page.screenshot(path="verification/mobile_sidebar_closed.png")
            else:
                print("Close button not found")
        else:
            # Test opening it
            print("Sidebar is closed, opening it...")
            page.click(".menu-btn")
            time.sleep(1)
            page.screenshot(path="verification/mobile_sidebar_open.png")

            # Now close it
            page.click(".sidebar-close-btn")
            time.sleep(1)
            page.screenshot(path="verification/mobile_sidebar_closed.png")

if __name__ == "__main__":
    run()
