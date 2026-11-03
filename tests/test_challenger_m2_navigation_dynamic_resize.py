import pytest
import time
from tests.conftest import check_no_horizontal_overflow

PAGES_WITH_NAV = ["/", "/privacy.html", "/terms.html"]
ALL_PAGES = ["/", "/privacy.html", "/terms.html", "/404.html"]
TABLET_VIEWPORTS = [768, 800, 834, 900, 1023]


class TestChallengerMilestone2DynamicResizeAndNav:
    """
    Adversarial Stress Verification Suite for Milestone 2:
    - Dynamic window resize across 375px -> 768px -> 1024px -> 375px with open drawer.
    - Full drawer lifecycle (toggle, backdrop, Escape, link clicks) on privacy.html and terms.html.
    - Tablet viewport inspection (768px - 1023px) ensuring clean mobile drawer display,
      no cramped desktop links, and zero layout overflow.
    - Zero console error and page error verification.
    """

    @pytest.mark.parametrize("page_path", PAGES_WITH_NAV)
    def test_dynamic_resize_drawer_dismiss_and_scroll_lock_release(self, page, base_url, page_path):
        """
        Adversarial Scenario:
        1. Open drawer at 375px mobile viewport.
        2. Verify scroll lock is applied (body style overflow == 'hidden' and class 'overflow-hidden').
        3. Resize to 768px (tablet portrait).
        4. Cross 1024px desktop breakpoint (1024px & 1280px).
        5. Verify drawer is automatically dismissed, aria-expanded is 'false',
           and body scroll lock is 100% released (overflow == '' and no 'overflow-hidden').
        6. Resize back down to 375px: verify drawer stays closed and scroll lock remains released.
        7. Verify zero horizontal overflow throughout.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        response = page.goto(f"{base_url}{page_path}")
        assert response.status == 200, f"Page {page_path} returned status {response.status}"
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")

        assert btn.is_visible(), f"Mobile menu button must be visible at 375px on {page_path}"

        # 1. Open drawer
        btn.click()
        page.wait_for_timeout(100)

        assert menu.is_visible(), f"Drawer must be visible when opened at 375px on {page_path}"
        assert btn.get_attribute("aria-expanded") == "true"
        assert page.evaluate("() => document.body.style.overflow") == "hidden", (
            f"Body scroll lock must be 'hidden' when drawer is open on {page_path}"
        )
        assert page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
            f"Body must have 'overflow-hidden' class on {page_path}"
        )

        # 2. Resize to 768px (Tablet)
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(60)
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 768px on {page_path}: {scroll_w}px > {client_w}px"

        # 3. Cross 1024px desktop breakpoint
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(100)

        assert not menu.is_visible(), f"Drawer must be dismissed when resized to 1024px on {page_path}"
        if backdrop.count() > 0:
            assert not backdrop.is_visible(), f"Backdrop must be hidden at 1024px on {page_path}"
        assert btn.get_attribute("aria-expanded") == "false"

        body_overflow = page.evaluate("() => document.body.style.overflow")
        assert body_overflow in ["", "visible"], (
            f"Body scroll lock must be completely released at 1024px on {page_path}, got '{body_overflow}'"
        )
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
            f"Body 'overflow-hidden' class must be removed at 1024px on {page_path}"
        )

        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 1024px on {page_path}: {scroll_w}px > {client_w}px"

        # 4. Enlarge to desktop 1440px
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(60)
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 1440px on {page_path}: {scroll_w}px > {client_w}px"

        # 5. Shrink back down to 375px
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(80)

        assert not menu.is_visible(), f"Drawer must not re-open spontaneously when shrinking back to 375px on {page_path}"
        assert btn.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"], (
            f"Body scroll lock must stay released when returned to 375px on {page_path}"
        )
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow after return to 375px on {page_path}: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors on {page_path}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on {page_path}: {page._page_errors}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_subpage_drawer_full_interaction_matrix(self, page, base_url, subpage):
        """
        Comprehensive test of drawer interactions on legal subpages:
        - Hamburger click open/close
        - Backdrop click dismiss
        - Escape key dismiss
        - Drawer navigation link click dismiss
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")
        hamburger = page.locator("#hamburgerIcon")
        close_icon = page.locator("#closeIcon")

        # Cycle 1: Hamburger open and hamburger close
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible()
        assert close_icon.is_visible()
        assert not hamburger.is_visible()
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        btn.click()
        page.wait_for_timeout(80)
        assert not menu.is_visible()
        assert hamburger.is_visible()
        assert not close_icon.is_visible()
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

        # Cycle 2: Open and backdrop dismiss
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible()
        backdrop.click(force=True)
        page.wait_for_timeout(80)
        assert not menu.is_visible()
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

        # Cycle 3: Open and Escape key dismiss
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(80)
        assert not menu.is_visible()
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

        # Cycle 4: Open and click each anchor link inside drawer
        links = menu.locator("a")
        link_count = links.count()
        assert link_count >= 5, f"Expected at least 5 links in {subpage} drawer, found {link_count}"

        for idx in range(min(link_count, 3)):  # test first 3 links
            btn.click()
            page.wait_for_timeout(80)
            assert menu.is_visible()
            link = links.nth(idx)
            link.click()
            page.wait_for_timeout(100)
            assert not menu.is_visible(), f"Menu must dismiss after clicking link {idx} on {subpage}"
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

        assert len(page._console_errors) == 0, f"Console errors on {subpage}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on {subpage}: {page._page_errors}"

    @pytest.mark.parametrize("vp_width", TABLET_VIEWPORTS)
    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_tablet_viewports_clean_mobile_drawer_display(self, page, base_url, vp_width, subpage):
        """
        Verify that in tablet viewports (768px - 1023px):
        - Desktop links (<nav>) are hidden (`hidden lg:flex`).
        - Mobile hamburger button (#mobileMenuBtn) is visible.
        - Header elements do not collide or overflow horizontally.
        - The hamburger button has valid bounding box and touch target size (>= 36px).
        - No horizontal overflow exists.
        """
        page.set_viewport_size({"width": vp_width, "height": 1024})
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")

        desktop_nav = page.locator("header nav")
        mobile_btn = page.locator("#mobileMenuBtn")
        header = page.locator("header").first
        logo = page.locator("header a[aria-label='RedGrowth.partners Home']")

        # Desktop nav must be hidden at tablet viewports (<1024px)
        assert not desktop_nav.is_visible(), (
            f"Desktop nav must be hidden at tablet width {vp_width}px on {subpage}"
        )

        # Mobile button must be visible
        assert mobile_btn.is_visible(), (
            f"Mobile menu button must be visible at tablet width {vp_width}px on {subpage}"
        )

        # Touch target size of hamburger button
        btn_box = mobile_btn.bounding_box()
        assert btn_box is not None
        assert btn_box["width"] >= 36 and btn_box["height"] >= 36, (
            f"Mobile button touch target too small at {vp_width}px on {subpage}: {btn_box['width']}x{btn_box['height']}"
        )

        # Logo must be visible and within header bounds
        assert logo.is_visible()
        logo_box = logo.bounding_box()
        assert logo_box is not None
        assert logo_box["x"] >= 0
        assert logo_box["x"] + logo_box["width"] < btn_box["x"], (
            f"Logo overlaps or touches mobile button at {vp_width}px on {subpage}"
        )

        # Header horizontal containment
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, (
            f"Horizontal overflow at {vp_width}px on {subpage}: {scroll_w}px > {client_w}px"
        )

        assert len(page._console_errors) == 0, f"Console errors on {subpage}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on {subpage}: {page._page_errors}"

    def test_rapid_resize_oscillation_under_continuous_drawer_toggling(self, page, base_url):
        """
        Adversarial Stress:
        Rapidly resize viewports between 360px and 1280px while continuously firing drawer toggles.
        Ensures no race condition leaves the body trapped in an unscrollable state or corrupts the DOM.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        widths = [375, 500, 768, 1024, 1280, 800, 400, 360, 1024, 1440, 375]

        for w in widths:
            page.set_viewport_size({"width": w, "height": 800})
            if w < 1024:
                # Toggle drawer
                mobile_btn.click()
                page.wait_for_timeout(30)
            else:
                page.wait_for_timeout(40)
                # At desktop, body MUST NOT be locked
                body_overflow = page.evaluate("() => document.body.style.overflow")
                assert body_overflow in ["", "visible"], (
                    f"Body locked at desktop width {w}px during rapid resize oscillation! Got '{body_overflow}'"
                )
                assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow at {w}px during rapid toggling: {scroll_w}px > {client_w}px"

        # Final settle at 1280px
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(100)
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors: {page._page_errors}"
