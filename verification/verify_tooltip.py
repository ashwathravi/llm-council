from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print("Navigating...")
            page.goto("http://localhost:5173/")

            print("Waiting for badge...")
            # Use get_by_text to find the badge
            badge = page.get_by_text("annual_report_2023.pdf")
            expect(badge).to_be_visible()

            print("Badge found. Looking for delete button...")
            # Find the delete button.
            # It should have aria-label "Remove annual_report_2023.pdf"
            delete_button = page.get_by_label("Remove annual_report_2023.pdf")
            expect(delete_button).to_be_visible()

            print("Button found. Hovering...")
            # Hover to show tooltip
            delete_button.hover()

            print("Waiting for tooltip...")
            # Wait for tooltip text "Remove document"
            tooltip = page.get_by_text("Remove document")
            expect(tooltip).to_be_visible()

            print("Taking screenshot...")
            # Take screenshot
            page.screenshot(path="verification/tooltip_verification.png")
            print("Screenshot saved.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
