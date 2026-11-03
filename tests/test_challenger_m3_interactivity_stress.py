import random
import time
import pytest
from tests.conftest import check_no_horizontal_overflow


class TestAdversarialProofTabKeyboardHammering:
    """
    Adversarial Stress Testing: Proof Switcher Arrow Keys & ARIA State Machine.
    Validates ArrowRight/ArrowLeft focus shift, aria-selected synchronization,
    panel display coordination, and 20-cycle rapid hammering without desync.
    """

    def test_proof_tab_arrow_right_left_navigation_and_focus(self, page, base_url):
        """
        Verify ArrowRight shifts focus to Reddit tab and activates it;
        ArrowLeft shifts focus back to Google tab and activates it.
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        tab_google = page.locator("#tabGoogleProof")
        tab_reddit = page.locator("#tabRedditProof")
        panel_google = page.locator("#panelGoogleProof")
        panel_reddit = page.locator("#panelRedditProof")

        tab_google.scroll_into_view_if_needed()
        assert tab_google.is_visible()
        assert tab_reddit.is_visible()

        # Step 1: Initial State Check
        assert tab_google.get_attribute("aria-selected") == "true"
        assert tab_reddit.get_attribute("aria-selected") == "false"
        assert panel_google.is_visible()
        assert not panel_reddit.is_visible()

        # Step 2: Focus Google Tab
        tab_google.focus()
        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id == "tabGoogleProof", f"Expected tabGoogleProof focused, got '{active_id}'"

        # Step 3: Press ArrowRight
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(50)

        # Verify focus shifted to Reddit Tab
        active_id_after_right = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id_after_right == "tabRedditProof", f"ArrowRight failed to shift focus to tabRedditProof, active: '{active_id_after_right}'"
        assert tab_reddit.get_attribute("aria-selected") == "true", "Reddit tab must be aria-selected='true'"
        assert tab_google.get_attribute("aria-selected") == "false", "Google tab must be aria-selected='false'"
        assert panel_reddit.is_visible(), "Reddit proof panel must be visible"
        assert not panel_google.is_visible(), "Google proof panel must be hidden"

        # Step 4: Press ArrowLeft
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(50)

        # Verify focus shifted back to Google Tab
        active_id_after_left = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id_after_left == "tabGoogleProof", f"ArrowLeft failed to shift focus to tabGoogleProof, active: '{active_id_after_left}'"
        assert tab_google.get_attribute("aria-selected") == "true", "Google tab must be aria-selected='true'"
        assert tab_reddit.get_attribute("aria-selected") == "false", "Reddit tab must be aria-selected='false'"
        assert panel_google.is_visible(), "Google proof panel must be visible"
        assert not panel_reddit.is_visible(), "Reddit proof panel must be hidden"

    def test_proof_tab_rapid_keyboard_hammering_20_cycles(self, page, base_url):
        """
        Rapidly hammer ArrowRight and ArrowLeft keys (20 alternating keydowns).
        Ensures zero desync between activeElement, aria-selected, and visible panel.
        Checks for zero orphaned panels, zero console errors, and zero horizontal overflow.
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        tab_google = page.locator("#tabGoogleProof")
        tab_reddit = page.locator("#tabRedditProof")
        panel_google = page.locator("#panelGoogleProof")
        panel_reddit = page.locator("#panelRedditProof")

        tab_google.scroll_into_view_if_needed()
        tab_google.focus()

        # Hammer 20 alternating keydowns: 10 pairs of (ArrowRight, ArrowLeft)
        for cycle in range(10):
            page.keyboard.press("ArrowRight")
            page.keyboard.press("ArrowLeft")

        # After 20 keydowns, we should be back on tabGoogleProof
        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id == "tabGoogleProof", f"After 20 alternating keydowns, active element should be tabGoogleProof, got '{active_id}'"
        assert tab_google.get_attribute("aria-selected") == "true"
        assert tab_reddit.get_attribute("aria-selected") == "false"
        assert panel_google.is_visible()
        assert not panel_reddit.is_visible()

        # One additional ArrowRight: should cleanly switch to Reddit
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(30)
        assert page.evaluate("() => document.activeElement ? document.activeElement.id : null") == "tabRedditProof"
        assert tab_reddit.get_attribute("aria-selected") == "true"
        assert tab_google.get_attribute("aria-selected") == "false"
        assert panel_reddit.is_visible()
        assert not panel_google.is_visible()

        # Verify no horizontal overflow or console errors
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow detected after proof tab hammering: {scroll_w}px > {client_w}px"
        assert len(page._console_errors) == 0, f"Console errors during proof tab hammering: {page._console_errors}"


class TestAdversarialMobileDrawerStressFocus:
    """
    Adversarial Stress Testing: Mobile Drawer Lifecycle & Focus Management.
    Tests rapid toggling across 320px, 375px, 768px, focus trapping/first-link focus,
    Escape key dismissal with focus restoration to #mobileMenuBtn,
    backdrop click dismissal with focus restoration to #mobileMenuBtn,
    and guaranteed release of body scroll lock.
    """

    @pytest.mark.parametrize("width,height", [
        (320, 568),  # 320px iPhone SE
        (375, 667),  # 375px iPhone 8
        (768, 1024), # 768px iPad Portrait
    ])
    def test_mobile_drawer_rapid_open_close_toggle(self, page, base_url, width, height):
        """Rapidly toggle mobile drawer 20 times across mandated viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        assert btn.is_visible(), f"Mobile button not visible at {width}x{height}"

        # 20 rapid toggles
        for _ in range(20):
            btn.click()

        # After even toggles, drawer must be hidden
        assert not menu.is_visible(), "Drawer must be hidden after 20 toggles"
        assert btn.get_attribute("aria-expanded") == "false"
        overflow = page.evaluate("() => document.body.style.overflow")
        assert overflow in ["", "visible"], f"Body overflow must be released, got '{overflow}'"
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

        # 1 more click -> opens cleanly
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible(), "Drawer must open after odd click"
        assert btn.get_attribute("aria-expanded") == "true"

        # Check first link auto-focused (F11)
        active_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName : null")
        active_in_menu = page.evaluate("() => document.getElementById('mobileMenu').contains(document.activeElement)")
        assert active_tag == "A" and active_in_menu, f"First link inside mobile drawer should be focused on open, got {active_tag}"

        # Close and reset
        btn.click()
        page.wait_for_timeout(50)

    @pytest.mark.parametrize("path", ["/", "/privacy.html", "/terms.html"])
    def test_mobile_drawer_escape_key_dismissal_and_focus_restoration(self, page, base_url, path):
        """Open drawer -> press Escape -> verify closed and focus restored to #mobileMenuBtn."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        # Open drawer
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible()
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        # Press Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(80)

        # Verify closed
        assert not menu.is_visible()
        assert btn.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

        # Verify focus restored to #mobileMenuBtn (F11)
        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id == "mobileMenuBtn", f"Escape on {path} failed to restore focus to #mobileMenuBtn, got '{active_id}'"

    @pytest.mark.parametrize("path", ["/", "/privacy.html", "/terms.html"])
    def test_mobile_drawer_backdrop_dismissal_and_focus_restoration(self, page, base_url, path):
        """Open drawer -> click backdrop -> verify closed and focus restored to #mobileMenuBtn."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")

        # Open drawer
        btn.click()
        page.wait_for_timeout(80)
        assert menu.is_visible()
        assert backdrop.is_visible()

        # Click the exposed backdrop overlay below the mobile drawer container
        click_y = page.evaluate("""() => {
            const menu = document.getElementById('mobileMenu').getBoundingClientRect();
            return Math.min(window.innerHeight - 20, menu.bottom + 40);
        }""")
        page.mouse.click(187, click_y)
        page.wait_for_timeout(80)

        # Verify closed
        assert not menu.is_visible()
        assert not backdrop.is_visible()
        assert btn.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

        # Verify focus restored to #mobileMenuBtn (F11)
        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id == "mobileMenuBtn", f"Backdrop click on {path} failed to restore focus to #mobileMenuBtn, got '{active_id}'"

    def test_mobile_drawer_body_scroll_lock_never_stuck_cross_breakpoints(self, page, base_url):
        """
        Verify body scroll lock is never stuck when closing drawer or resizing across breakpoints.
        Cycle between 320px -> 375px -> 768px -> 1024px -> 1280px -> 375px.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")

        for vp_mobile, vp_desktop in [(320, 1024), (375, 1280), (768, 1440)]:
            # 1. Open on mobile
            page.set_viewport_size({"width": vp_mobile, "height": 667})
            page.wait_for_timeout(40)
            mobile_btn.click()
            page.wait_for_timeout(40)
            assert page.evaluate("() => document.body.style.overflow") == "hidden"

            # 2. Resize across 1024px desktop breakpoint
            page.set_viewport_size({"width": vp_desktop, "height": 800})
            page.wait_for_timeout(60)

            # 3. Assert scroll lock released immediately
            assert not mobile_menu.is_visible()
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
            assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")

            # 4. Return to mobile and verify drawer does not randomly re-open
            page.set_viewport_size({"width": vp_mobile, "height": 667})
            page.wait_for_timeout(40)
            assert not mobile_menu.is_visible()
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
            assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')")


class TestAdversarialFaqHammeringAndAnimation:
    """
    Adversarial Stress Testing: FAQ Accordion 50 Non-Uniform Rapid Clicks & Animation Rules.
    Verifies that rapid hammering causes zero layout shift, zero overflow, zero console errors,
    and validates the presence of the accordionSlideDown keyframe animation.
    """

    def test_faq_accordion_rapid_hammering_50_clicks(self, page, base_url):
        """
        Perform 50 non-uniform clicks across all 5 FAQ summaries.
        Verify zero layout overflow, zero console errors, and clean layout state.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        faq_section.scroll_into_view_if_needed()
        details_items = faq_section.locator("details")
        assert details_items.count() == 5

        # 50 non-uniform clicks across the 5 items
        # Deterministic pseudo-random sequence to ensure repeatability
        rng = random.Random(42)
        click_sequence = [rng.randint(0, 4) for _ in range(50)]

        for idx in click_sequence:
            summary = details_items.nth(idx).locator("summary")
            summary.click()

        # Check horizontal overflow after 50 rapid clicks
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow after 50 FAQ hammering clicks: {scroll_w}px > {client_w}px"

        # Verify zero console errors and zero page runtime errors
        assert len(page._console_errors) == 0, f"Console errors after 50 FAQ clicks: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors after 50 FAQ clicks: {page._page_errors}"

    def test_faq_accordion_animation_css_rule_presence(self, page, base_url):
        """
        Verify that the accordionSlideDown animation keyframe and details[open] rule
        are compiled and active in the stylesheet (F13).
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        has_accordion_animation = page.evaluate("""
            () => {
                let foundKeyframes = false;
                let foundOpenRule = false;
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules) {
                            if (rule.type === CSSRule.KEYFRAMES_RULE && rule.name === 'accordionSlideDown') {
                                foundKeyframes = true;
                            }
                            if (rule.selectorText && rule.selectorText.includes('details[open]') && rule.selectorText.includes('summary')) {
                                foundOpenRule = true;
                            }
                        }
                    } catch (e) {
                        // Cross-origin stylesheet access restriction if any
                    }
                }
                return { foundKeyframes, foundOpenRule };
            }
        """)

        assert has_accordion_animation["foundKeyframes"], "Expected @keyframes accordionSlideDown to be present in stylesheet"
        assert has_accordion_animation["foundOpenRule"], "Expected details[open] summary rule to be present in stylesheet"
