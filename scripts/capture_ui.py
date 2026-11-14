from playwright.sync_api import sync_playwright

def settle(page):
    page.wait_for_timeout(1000)
    page.wait_for_function("""() => !document.querySelector('[data-testid="stStatusWidget"]')
        && !document.querySelector('[data-stale="true"]')
        && !document.querySelector('[data-testid="stSkeleton"]')""", timeout=90000)
    page.wait_for_timeout(2000)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 800})
        page.goto("http://localhost:8501")
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step1_tongquan.png")
        print("Captured step 1")

        # Step 2
        page.locator('div[data-testid="stRadio"] label').filter(has_text="Lỗi giao trễ").first.click()
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step2_loigiaotre.png")
        print("Captured step 2")

        # Step 3
        page.locator('div[data-testid="stRadio"] label').filter(has_text="Chi tiết seller").first.click()
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step3_chitietseller.png")
        print("Captured step 3")

        # Step 4
        page.locator('div[data-testid="stRadio"] label').filter(has_text="Kế hoạch").first.click()
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step4_kehoach.png")
        print("Captured step 4")

        # Step 5
        page.locator('div[data-testid="stRadio"] label').filter(has_text="What-if").first.click()
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step5_whatif.png")
        print("Captured step 5")

        # Step 6
        page.locator('div[data-testid="stRadio"] label').filter(has_text="Kiểm chứng").first.click()
        settle(page)
        page.screenshot(path="evidence/screenshots/ui_step6_kiemchung.png")
        print("Captured step 6")

        browser.close()
    print("Done all 6 screens!")

if __name__ == "__main__":
    main()

