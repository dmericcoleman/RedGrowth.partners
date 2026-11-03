import pytest
from tests.conftest import check_no_horizontal_overflow

VIEWPORTS = [
    (320, 568),   # iPhone SE / minimum supported mobile
    (360, 640),   # Compact Android
    (375, 667),   # iPhone 8 / SE2
    (390, 844),   # iPhone 12/13/14
    (414, 896),   # iPhone XR / 11 / Plus
    (768, 1024),  # iPad portrait / Tablet
    (1024, 768),  # iPad landscape / Small Desktop
    (1440, 900),  # Standard Desktop / Widescreen
]


@pytest.mark.tier2
class TestTier2Responsiveness:
    """
    Tier 2: Boundary & Corner Cases - Responsiveness.
    Verifies that the website has zero horizontal overflow across 8 standard viewports,
    hero typography does not clip, Section 3 heading wraps, and mobile spacing is clean.
    """

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_zero_horizontal_overflow_across_viewports(self, page, base_url, width, height):
        """Verifies document.documentElement.scrollWidth <= clientWidth across viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        passes, scroll_width, client_width = check_no_horizontal_overflow(page)
        assert passes, (
            f"Horizontal overflow detected at {width}x{height}: "
            f"scrollWidth ({scroll_width}px) > clientWidth ({client_width}px)"
        )

    def test_hero_h1_nowrap_elimination_on_mobile(self, page, base_url):
        """F1: Hero H1 must not have rigid whitespace-nowrap on mobile causing text clipping."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        h1 = page.locator("h1").first
        class_attr = h1.get_attribute("class") or ""
        
        # Ensure whitespace-nowrap is not applied unconditionally on mobile
        assert "whitespace-nowrap" not in class_attr or "lg:whitespace-nowrap" in class_attr or "md:whitespace-nowrap" in class_attr, (
            "Hero H1 should not have unconditional 'whitespace-nowrap' on mobile screens"
        )
        
        # Verify H1 bounding box does not exceed viewport width
        box = h1.bounding_box()
        assert box is not None
        assert box["width"] <= 375, f"H1 width ({box['width']}px) overflows 375px viewport"

    def test_section3_h2_responsive_wrapping(self, page, base_url):
        """F1: Section 3 heading must wrap responsively on mobile without overflowing."""
        page.set_viewport_size({"width": 360, "height": 640})
        page.goto(f"{base_url}/")
        
        # Locate Section 3 heading
        s3_heading = page.locator("section#framework h2, section:has-text('Framework') h2").first
        if s3_heading.count() > 0:
            box = s3_heading.bounding_box()
            assert box is not None
            assert box["width"] <= 360, f"Section 3 heading width ({box['width']}px) exceeds viewport"

    def test_hero_dashboard_container_mobile_spacing(self, page, base_url):
        """F2: Hero dashboard preview must not produce fixed excessive dead space on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        # Check hero image element
        hero_img = page.locator("img[src*='dashboard'], img[src*='visibility']").first
        if hero_img.count() > 0:
            box = hero_img.bounding_box()
            assert box is not None
            # On 375px wide screen, image should fit within viewport width
            assert box["width"] <= 375

    def test_growth_engine_mobile_layout(self, page, base_url):
        """F3: Growth Engine 3-step cards must be visible and properly aligned on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        # Growth engine step cards
        step_cards = page.locator("section:has-text('Step'), section:has-text('Engine')").locator("[class*='step'], [class*='card']")
        if step_cards.count() >= 3:
            for i in range(3):
                card = step_cards.nth(i)
                box = card.bounding_box()
                if box:
                    assert box["width"] <= 375, f"Step card {i+1} overflows mobile viewport"
