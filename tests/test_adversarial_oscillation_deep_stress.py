import pytest
from tests.conftest import check_no_horizontal_overflow

PAGES = ["404.html", "privacy.html", "terms.html", ""]
LADDER = [280, 320, 360, 375, 390, 414, 500, 640, 768, 900, 1024, 1280, 1440, 1600, 1920, 2560, 3840, 2560, 1920, 1440, 1024, 768, 375, 280]


class TestAdversarialOscillationDeepStress:
    """
    Milestone 3 Re-Verification Deep Stress:
    Adversarial multi-cycle rapid viewport resize oscillation (1280px <-> 280px),
    full viewport ladder (280px to 3840px), and header element bounding headroom verification.
    """

    @pytest.mark.parametrize("page_name", PAGES)
    def test_rapid_resize_oscillation_20_cycles(self, page, base_url, page_name):
        """
        Executes 20 rapid oscillation cycles between 1280px and 280px.
        Verifies:
        - scrollWidth <= clientWidth at both 1280px and 280px on every cycle
        - Right bounding edge of header content elements at 280px <= 270px (headroom >= 10px)
        - Zero console errors or runtime exceptions
        """
        target_url = f"{base_url}/{page_name}"
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        for cycle in range(1, 21):
            # 1. Desktop 1280px
            page.set_viewport_size({"width": 1280, "height": 800})
            page.wait_for_timeout(30)
            passes, sw_1280, cw_1280 = check_no_horizontal_overflow(page)
            assert passes, f"{page_name} cycle {cycle} overflow at 1280px: {sw_1280} > {cw_1280}"

            # 2. Ultra-compact mobile 280px
            page.set_viewport_size({"width": 280, "height": 700})
            page.wait_for_timeout(40)
            passes, sw_280, cw_280 = check_no_horizontal_overflow(page)
            assert passes, f"{page_name} cycle {cycle} overflow at 280px: {sw_280} > {cw_280} (+{sw_280 - cw_280}px)"

            # 3. Header element bounding box headroom measurement at 280px
            header_data = page.evaluate("""() => {
                const header = document.querySelector('header');
                if (!header) return null;
                const contentElements = Array.from(header.querySelectorAll('a, button'));
                let maxRight = 0;
                let rightmostTag = '';
                let rightmostText = '';
                contentElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return;
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.right > maxRight) {
                        maxRight = r.right;
                        rightmostTag = el.tagName;
                        rightmostText = (el.innerText || el.getAttribute('aria-label') || '').trim();
                    }
                });
                return {
                    maxChildRight: maxRight,
                    rightmostTag,
                    rightmostText
                };
            }""")

            assert header_data is not None, f"Header not found on {page_name}"
            child_right = header_data["maxChildRight"]
            headroom = 280.0 - child_right

            assert child_right <= 270.0, (
                f"{page_name} cycle {cycle} at 280px: header element right edge {child_right:.2f}px "
                f"exceeds 270px maximum (headroom {headroom:.2f}px < 10px)"
            )
            assert headroom >= 10.0, (
                f"{page_name} cycle {cycle} at 280px: headroom {headroom:.2f}px is less than 10px required"
            )

        assert len(page._console_errors) == 0, f"Console errors on {page_name}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on {page_name}: {page._page_errors}"

    @pytest.mark.parametrize("page_name", PAGES)
    def test_full_viewport_ladder_280px_to_3840px(self, page, base_url, page_name):
        """
        Ascends and descends the complete viewport ladder (280px -> 3840px -> 280px, 24 steps).
        Verifies zero horizontal overflow at every breakpoint.
        """
        target_url = f"{base_url}/{page_name}"
        page.goto(target_url)
        page.wait_for_load_state("networkidle")

        for width in LADDER:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(25)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow on {page_name} at width {width}px: {sw} > {cw} (+{sw - cw}px)"

        assert len(page._console_errors) == 0, f"Console errors on {page_name}: {page._console_errors}"

    def test_404_interactive_headroom_and_button_geometry(self, page, base_url):
        """
        Validates 404.html header Return Home button geometry, hover state, and exact headroom at 280px.
        """
        page.goto(f"{base_url}/404.html")
        page.wait_for_load_state("networkidle")
        page.set_viewport_size({"width": 280, "height": 700})
        page.wait_for_timeout(50)

        btn = page.locator("header a[aria-label='Return Home']")
        assert btn.is_visible(), "Return Home button must be visible on 404.html header"

        box = btn.bounding_box()
        assert box is not None
        btn_right = box["x"] + box["width"]
        headroom = 280.0 - btn_right

        assert btn_right <= 270.0, f"Button right edge {btn_right:.2f}px exceeds 270px limit"
        assert headroom >= 10.0, f"Headroom {headroom:.2f}px is less than 10px required"

        # Test hover state
        btn.hover()
        page.wait_for_timeout(40)
        passes, sw, cw = check_no_horizontal_overflow(page)
        assert passes, f"Hovering Return Home button triggered horizontal overflow: {sw} > {cw}"
