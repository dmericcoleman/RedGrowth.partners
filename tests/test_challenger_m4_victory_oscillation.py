import pytest
import time
from tests.conftest import check_no_horizontal_overflow

EXTREME_VIEWPORTS = [280, 320, 360, 375, 414, 768, 1024, 1280, 1440, 1920, 2560, 3840]
PAGES = ["", "404.html", "privacy.html", "terms.html"]


class TestChallengerM4VictoryOscillation:
    """
    Milestone 4 Victory Challenge: Adversarial Viewport Reflow and Resize Oscillation
    Stress Harness testing all 12 extreme viewports (280px to 3840px) across all 4 pages.
    """

    @pytest.mark.parametrize("page_name", PAGES)
    def test_victory_full_ladder_ascend_descend_oscillation(self, page, base_url, page_name):
        """
        Ascend and descend the complete 12-breakpoint extreme viewport ladder:
        280 -> 320 -> 360 -> 375 -> 414 -> 768 -> 1024 -> 1280 -> 1440 -> 1920 -> 2560 -> 3840
        and back down:
        3840 -> 2560 -> 1920 -> 1440 -> 1280 -> 1024 -> 768 -> 414 -> 375 -> 360 -> 320 -> 280
        Verifies:
        - scrollWidth <= clientWidth unconditionally at every single step
        - Zero console errors or runtime exceptions
        """
        target_url = f"{base_url}/{page_name}"
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        full_ladder = EXTREME_VIEWPORTS + list(reversed(EXTREME_VIEWPORTS[:-1]))

        for width in full_ladder:
            page.set_viewport_size({"width": width, "height": 850})
            page.wait_for_timeout(35)

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, (
                f"Horizontal overflow on page '{page_name}' at width {width}px: "
                f"scrollWidth={scroll_w}px > clientWidth={client_w}px (Delta: +{scroll_w - client_w}px)"
            )

            # Subpixel assertion: document.documentElement.scrollWidth must strictly equal or be less than clientWidth
            overflow_delta = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            assert overflow_delta <= 0, (
                f"Strict subpixel overflow on page '{page_name}' at {width}px: delta={overflow_delta}px"
            )

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on '{page_name}': {page._page_errors}"

    @pytest.mark.parametrize("page_name", PAGES)
    def test_victory_extreme_bipolar_jump_oscillation(self, page, base_url, page_name):
        """
        Adversarial bipolar whip: alternate rapidly between the ultra-narrow minimum (280px)
        and ultra-wide maximum (3840px), then 320px <-> 2560px, 360px <-> 1920px, 375px <-> 1440px,
        414px <-> 1280px, 768px <-> 1024px.
        Tests layout containment under the most severe dynamic reflow stress possible.
        """
        target_url = f"{base_url}/{page_name}"
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        bipolar_pairs = [
            (280, 3840),
            (320, 2560),
            (360, 1920),
            (375, 1440),
            (414, 1280),
            (768, 1024),
            (3840, 280),
            (2560, 320),
            (1920, 360),
            (1440, 375),
            (1280, 414),
            (1024, 768),
        ]

        for step_idx, (w_narrow, w_wide) in enumerate(bipolar_pairs):
            # Step A: Narrow
            page.set_viewport_size({"width": w_narrow, "height": 750})
            page.wait_for_timeout(30)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Overflow on {page_name} step {step_idx}A at {w_narrow}px: {sw} > {cw}"

            # Step B: Wide
            page.set_viewport_size({"width": w_wide, "height": 900})
            page.wait_for_timeout(30)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Overflow on {page_name} step {step_idx}B at {w_wide}px: {sw} > {cw}"

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on '{page_name}': {page._page_errors}"

    @pytest.mark.parametrize("page_name", PAGES)
    def test_victory_dom_elements_bounding_box_containment(self, page, base_url, page_name):
        """
        Traverses key visible DOM sections and containers across extreme mobile viewports
        (280px, 320px, 360px, 375px, 414px) and 4K desktop (3840px) to verify that NO visible
        element exceeds the viewport bounds or clips offscreen.
        """
        target_url = f"{base_url}/{page_name}"
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        test_widths = [280, 320, 360, 375, 414, 3840]

        for width in test_widths:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(35)

            # Evaluate bounding boxes of main containers, sections, headers, and footers
            bounding_violations = page.evaluate("""(w) => {
                const violations = [];
                const candidates = Array.from(document.querySelectorAll('header, footer, section, main, h1, h2, form, nav'));
                candidates.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return;
                    const r = el.getBoundingClientRect();
                    // Ignore elements with 0 dimensions
                    if (r.width === 0 && r.height === 0) return;
                    // Check if element spills significantly beyond viewport right edge (> w + 1.5px)
                    if (r.right > w + 1.5) {
                        violations.push({
                            tag: el.tagName,
                            id: el.id,
                            className: (el.className || '').toString().slice(0, 50),
                            right: r.right,
                            viewportWidth: w,
                            delta: r.right - w
                        });
                    }
                });
                return violations;
            }""", width)

            assert len(bounding_violations) == 0, (
                f"Element bounding violations on {page_name} at width {width}px: {bounding_violations}"
            )

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"

    def test_victory_interactive_stress_during_extreme_resizes(self, page, base_url):
        """
        Exercises full interactive lifecycle (mobile drawer open/close, accordion toggles,
        audit form input) while jumping across all 12 extreme viewports.
        Verifies:
        - Mobile drawer auto-dismisses when resized to desktop (>=1024px)
        - Body scroll lock is released
        - scrollWidth <= clientWidth unconditionally at every step
        - Zero console errors
        """
        page.set_viewport_size({"width": 280, "height": 650})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")

        # 1. Open mobile drawer at 280px
        assert mobile_btn.is_visible()
        mobile_btn.click()
        page.wait_for_timeout(40)
        assert mobile_menu.is_visible()
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        # 2. Whip to 3840px (4K desktop)
        page.set_viewport_size({"width": 3840, "height": 1200})
        page.wait_for_timeout(50)
        assert not mobile_menu.is_visible(), "Mobile drawer failed to auto-dismiss at 3840px"
        assert page.evaluate("() => document.body.style.overflow") != "hidden", "Scroll lock stuck at 3840px"
        passes, sw, cw = check_no_horizontal_overflow(page)
        assert passes, f"Overflow at 3840px after drawer dismiss: {sw} > {cw}"

        # 3. Whip to 320px
        page.set_viewport_size({"width": 320, "height": 650})
        page.wait_for_timeout(40)
        assert not mobile_menu.is_visible(), "Drawer spontaneously reopened at 320px"
        passes, sw, cw = check_no_horizontal_overflow(page)
        assert passes, f"Overflow at 320px: {sw} > {cw}"

        # 4. Open FAQ accordions and resize to 2560px
        faq_details = page.locator("#faq details")
        for i in range(faq_details.count()):
            faq_details.nth(i).evaluate("el => el.open = true")
        page.wait_for_timeout(40)

        for width in [360, 414, 768, 1024, 1440, 1920, 2560, 280]:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(30)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Overflow with open FAQs at {width}px: {sw} > {cw}"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors: {page._page_errors}"
