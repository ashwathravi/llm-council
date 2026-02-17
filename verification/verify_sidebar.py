from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to app...")
        page.goto("http://localhost:3000")

        print("Waiting for sidebar...")
        new_session_btn = page.get_by_text("New Session")
        expect(new_session_btn).to_be_visible(timeout=10000)

        print("Checking for Council Members section...")
        council_members = page.get_by_text("Council Members")
        expect(council_members).to_be_visible()

        print("Taking screenshot...")
        page.screenshot(path="verification/sidebar_verified.png")

        print("Verification successful!")
        browser.close()

if __name__ == "__main__":
    run()
