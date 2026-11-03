import pytest


@pytest.mark.tier3
class TestTier3NavigationAnchors:
    """
    Tier 3: Cross-Feature Combinations - Navigation & Anchor Interactions.
    Verifies sticky header behavior during scroll, target anchor scroll offsets (scroll-mt-24),
    and mobile drawer accessibility (backdrop dismissal, Escape key, scroll lock).
    """

    def test_sticky_header_persists_on_scroll(self, page, base_url):
        """F11: Top header must remain fixed or sticky at top of viewport when scrolling."""
        page.goto(f"{base_url}/")
        
        header = page.locator("header").first
        assert header.is_visible()
        
        # Scroll down 1200px
        page.evaluate("window.scrollTo(0, 1200)")
        page.wait_for_timeout(400)
        
        # Verify header is still visible in viewport and pinned at top
        header_box = header.bounding_box()
        assert header_box is not None, "Header must have bounding box"
        assert 0 <= header_box["y"] <= 10, f"Header must stay pinned at top of viewport (got y={header_box['y']}px)"
        
        # Verify computed position is fixed or sticky
        position = header.evaluate("el => window.getComputedStyle(el).position")
        assert position in ["fixed", "sticky"], f"Header position must be 'fixed' or 'sticky', got '{position}'"

    def test_anchor_links_scroll_targets_into_view(self, page, base_url):
        """F11: Clicking nav anchor links scrolls target sections into view."""
        page.goto(f"{base_url}/")
        
        anchors = ["#framework", "#compliance", "#results", "#pricing", "#audit"]
        for anchor in anchors:
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            
            link = page.locator(f"header nav a[href='{anchor}']").first
            if link.count() > 0 and link.is_visible():
                link.click()
                page.wait_for_timeout(800)
                
                target = page.locator(anchor)
                assert target.count() >= 1, f"Target anchor {anchor} must exist in DOM"
                target_box = target.bounding_box()
                assert target_box is not None, f"Target anchor {anchor} must have bounding box"
                
                # Target top should be within viewport visible range
                viewport_height = page.viewport_size["height"]
                assert 0 <= target_box["y"] <= viewport_height + 150, (
                    f"Target {anchor} should have scrolled into view (y={target_box['y']})"
                )

    def test_anchor_target_scroll_offset_prevents_overlap(self, page, base_url):
        """F11: Anchor targets must have scroll-mt-24 (or equivalent) so headings are not hidden by sticky header."""
        page.goto(f"{base_url}/")
        
        anchors = ["#framework", "#compliance", "#results", "#pricing", "#audit"]
        
        for anchor in anchors:
            target = page.locator(anchor)
            if target.count() > 0:
                class_attr = target.get_attribute("class") or ""
                scroll_margin_top = target.evaluate("el => window.getComputedStyle(el).scrollMarginTop")
                has_scroll_mt_class = "scroll-mt-" in class_attr
                has_valid_pixel_margin = scroll_margin_top not in ["0px", "", "auto"]
                
                assert has_scroll_mt_class or has_valid_pixel_margin, (
                    f"Anchor target {anchor} must have 'scroll-mt-24' or scrollMarginTop to prevent hiding under sticky nav"
                )

    def test_mobile_drawer_link_click_closes_drawer(self, page, base_url):
        """F12: Clicking a link inside the mobile drawer must close the drawer."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        
        # Open drawer
        btn.click()
        page.wait_for_timeout(200)
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" not in menu_classes, "Drawer should be open after button click"
        
        # Click an anchor link in mobile drawer
        drawer_link = menu.locator("a[href='#framework']").first
        drawer_link.click()
        page.wait_for_timeout(300)
        
        # Drawer should now be closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), "Drawer should be closed after link click"

    def test_mobile_drawer_dismiss_on_backdrop_click(self, page, base_url):
        """F12: Clicking outside / backdrop of mobile menu must close the drawer."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        
        # Open drawer
        btn.click()
        page.wait_for_timeout(200)
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" not in menu_classes, "Drawer should be open after button click"
        
        # Click outside menu (below drawer, e.g. at y=600)
        page.mouse.click(180, 600)
        page.wait_for_timeout(300)
        
        # Verify drawer closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), (
            "Mobile drawer should dismiss when clicking outside/backdrop"
        )

    def test_mobile_drawer_dismiss_on_escape_key(self, page, base_url):
        """F12: Pressing Escape key must close the mobile menu drawer."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        
        # Open drawer
        btn.click()
        page.wait_for_timeout(200)
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" not in menu_classes, "Drawer should be open after button click"
        
        # Press Escape key
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        
        # Verify drawer closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), (
            "Mobile drawer should dismiss when pressing Escape key"
        )

    def test_mobile_drawer_locks_body_scroll(self, page, base_url):
        """F12: Opening the mobile drawer should lock body scroll (overflow: hidden)."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        
        # Open drawer
        btn.click()
        page.wait_for_timeout(200)
        
        body_overflow = page.evaluate("() => window.getComputedStyle(document.body).overflow")
        body_classes = page.locator("body").get_attribute("class") or ""
        
        assert body_overflow == "hidden" or "overflow-hidden" in body_classes, (
            "Body scroll should be locked (overflow: hidden) when mobile drawer is open"
        )
