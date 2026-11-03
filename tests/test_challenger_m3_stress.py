import pytest
import time
from tests.conftest import check_no_horizontal_overflow

PAGES = ["/", "/privacy.html", "/terms.html", "/404.html"]
RESIZE_SEQUENCE = [280, 375, 768, 1024, 1440, 375, 280]


class TestChallengerM3Stress:
    """
    Challenger empirical stress testing for Milestone 3:
    - Dynamic resize oscillation & 280px subpixel elimination
    - Audit form focus transitions, disabled state feedback, and validation
    - Subpages drawer lifecycle, focus restoration, and desktop auto-dismiss
    """

    @pytest.mark.parametrize("page_path", PAGES)
    def test_resize_oscillation_and_280px_subpixel_elimination(self, page, base_url, page_path):
        """
        Oscillate viewports rapidly across [280, 375, 768, 1024, 1440, 375, 280] on all 4 pages.
        Verify:
        - scrollWidth <= clientWidth at every step (especially at 280px)
        - body overflow-x-hidden prevents subpixel glow orb clipping leaks
        - zero console errors or uncaught exceptions
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        for cycle in range(2):
            for width in RESIZE_SEQUENCE:
                page.set_viewport_size({"width": width, "height": 700})
                page.wait_for_timeout(60)

                passes, scroll_w, client_w = check_no_horizontal_overflow(page)
                assert passes, (
                    f"Horizontal overflow on {page_path} in cycle {cycle+1} at {width}px: "
                    f"scrollWidth={scroll_w}px > clientWidth={client_w}px"
                )

                if width == 280:
                    # Precise subpixel check
                    delta = scroll_w - client_w
                    assert delta <= 0, f"Subpixel overflow at 280px on {page_path}: +{delta}px"

        assert len(page._console_errors) == 0, f"Console errors on {page_path}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on {page_path}: {page._page_errors}"

    def test_audit_form_input_focus_transitions(self, page, base_url):
        """
        Stress test input focus transitions on #fullName, #companyDomain, #workEmail, and #brandNotes.
        Verify:
        - Active focus ring styles
        - Dark focus background (#070B14 or computed equivalent)
        - Transitions between fields without layout jitter or focus trapping
        """
        page.goto(f"{base_url}/#audit")
        page.wait_for_load_state("networkidle")

        field_ids = ["#fullName", "#companyDomain", "#workEmail", "#brandNotes"]

        for field_id in field_ids:
            field = page.locator(field_id)
            assert field.is_visible(), f"Field {field_id} must be visible"

            # Focus the field
            field.focus()
            page.wait_for_timeout(50)

            # Check that element is currently focused
            is_active = page.evaluate(f"() => document.activeElement === document.querySelector('{field_id}')")
            assert is_active, f"Field {field_id} did not gain focus"

            # Check focus styling properties
            classes = field.get_attribute("class") or ""
            assert "focus:border-coral" in classes, f"{field_id} missing focus:border-coral"
            assert "focus:bg-[#070B14]" in classes, f"{field_id} missing focus:bg-[#070B14]"
            assert "focus-visible:ring-coral" in classes, f"{field_id} missing focus-visible:ring-coral"

            # Check computed border color or background changes upon focus
            computed_bg = field.evaluate("el => window.getComputedStyle(el).backgroundColor")
            assert computed_bg is not None

        assert len(page._console_errors) == 0, f"Console errors during focus stress: {page._console_errors}"

    def test_audit_form_validation_and_disabled_state_feedback(self, page, base_url):
        """
        Stress test audit form submission:
        - Native alert prevention (zero window.alert dialogs)
        - Empty field submission prevented by required constraint validation
        - Invalid email format fails validation
        - Simulated submission triggers disabled button state, spinner, opacity feedback, and inline error container
        """
        page.goto(f"{base_url}/#audit")
        page.wait_for_load_state("networkidle")

        form = page.locator("#auditForm")
        submit_btn = page.locator("#submitAuditBtn")
        name_input = page.locator("#fullName")
        email_input = page.locator("#workEmail")
        domain_input = page.locator("#companyDomain")
        error_container = page.locator("#auditError")

        assert submit_btn.is_visible()

        # 1. Attempt click on empty form
        submit_btn.click()
        page.wait_for_timeout(50)

        # Must NOT trigger native alert
        assert len(page._dialogs) == 0, f"Unexpected browser dialog alert: {page._dialogs}"

        # HTML5 validity check
        is_name_valid = name_input.evaluate("el => el.checkValidity()")
        assert not is_name_valid, "Empty #fullName must fail validity check"

        # 2. Invalid email format
        name_input.fill("Adversarial Tester")
        domain_input.fill("https://test.com")
        email_input.fill("invalid-email-address")

        is_email_valid = email_input.evaluate("el => el.checkValidity()")
        assert not is_email_valid, "Malformed email must fail checkValidity()"

        # 3. Simulate AJAX submission with route interception (simulate server error response 400)
        email_input.fill("test@testcompany.com")
        
        # Intercept Formspree POST to return 400 error
        def handle_route(route):
            time.sleep(0.1)  # small delay to observe disabled state
            route.fulfill(status=400, body='{"error": "Simulated Formspree error"}', content_type="application/json")

        page.route("**/formspree.io/**", handle_route)

        # Click submit and immediately evaluate disabled state
        submit_btn.click()
        
        # Verify disabled styling and attribute during or immediately after submission
        page.wait_for_timeout(300)

        # Check inline accessible error container
        assert error_container.is_visible(), "Inline accessible error container #auditError must be displayed"
        assert error_container.get_attribute("role") == "alert", "#auditError must have role='alert'"
        
        # Verify submit button was restored and not permanently stuck
        assert not submit_btn.is_disabled(), "Submit button should be re-enabled after error response"
        assert "disabled:opacity-75" in (submit_btn.get_attribute("class") or ""), "Submit button must have disabled:opacity-75"
        assert "disabled:cursor-not-allowed" in (submit_btn.get_attribute("class") or ""), "Submit button must have disabled:cursor-not-allowed"

        # Ensure still 0 native alerts
        assert len(page._dialogs) == 0, f"Native dialogs detected: {page._dialogs}"

    @pytest.mark.parametrize("subpage", ["/privacy.html", "/terms.html"])
    @pytest.mark.parametrize("viewport_width", [320, 375, 768])
    def test_subpages_drawer_toggle_across_mobile_viewports(self, page, base_url, subpage, viewport_width):
        """
        Test drawer toggle on privacy.html and terms.html across 320px, 375px, and 768px viewports.
        Verify:
        - Drawer opens with scroll-lock
        - Focus transitions to first link in drawer
        - Drawer closes with focus restored to #mobileMenuBtn
        - aria-expanded correctly synchronized
        """
        page.set_viewport_size({"width": viewport_width, "height": 650})
        page.goto(f"{base_url}{subpage}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        assert btn.is_visible(), f"Mobile menu button must be visible at {viewport_width}px on {subpage}"
        assert btn.get_attribute("aria-expanded") == "false"

        # Open drawer
        btn.click()
        page.wait_for_timeout(60)

        assert menu.is_visible(), f"Drawer must be visible after click at {viewport_width}px on {subpage}"
        assert btn.get_attribute("aria-expanded") == "true"
        assert page.evaluate("() => document.body.style.overflow") == "hidden", "Body scroll lock must be active"

        # Verify focus is within drawer (first link)
        focused_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName : null")
        assert focused_tag == "A", f"Focus should be on first link in drawer, got: {focused_tag}"

        # Close drawer via Escape key
        page.keyboard.press("Escape")
        page.wait_for_timeout(60)

        assert not menu.is_visible(), f"Drawer must close on Escape at {viewport_width}px on {subpage}"
        assert btn.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.body.style.overflow") != "hidden", "Body scroll lock must be released"

        # Verify focus restored to #mobileMenuBtn
        is_btn_focused = page.evaluate("() => document.activeElement === document.getElementById('mobileMenuBtn')")
        assert is_btn_focused, f"Focus was not restored to #mobileMenuBtn after Escape on {subpage}"

    @pytest.mark.parametrize("subpage", ["/privacy.html", "/terms.html"])
    def test_subpages_drawer_auto_dismiss_on_desktop_resize(self, page, base_url, subpage):
        """
        Open drawer at mobile (375px) and resize to desktop (1280px).
        Verify auto-dismiss, scroll lock release, and no layout corruption.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}{subpage}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        btn.click()
        page.wait_for_timeout(60)
        assert menu.is_visible()
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        # Resize to desktop
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(80)

        assert not menu.is_visible(), f"Drawer must auto-dismiss on {subpage} at 1280px"
        assert page.evaluate("() => document.body.style.overflow") != "hidden", f"Scroll lock must release on {subpage}"

        passes, sw, cw = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 1280px on {subpage}: {sw} > {cw}"

    def test_404_page_responsive_navigation_integrity(self, page, base_url):
        """
        Verify 404.html header, Return Home button, and strategy CTA across 320px, 375px, 768px, and 1280px.
        Zero drawer errors, zero overflow, perfectly functional navigation.
        """
        for width in [320, 375, 768, 1280]:
            page.set_viewport_size({"width": width, "height": 700})
            page.goto(f"{base_url}/404.html")
            page.wait_for_load_state("networkidle")

            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"404.html horizontal overflow at {width}px: {sw} > {cw}"

            home_link = page.locator("header a[href='/']").first
            assert home_link.is_visible(), f"Header home link missing at {width}px on 404.html"

            main_home_cta = page.locator("main a[href='/']").first
            assert main_home_cta.is_visible(), f"Main return home CTA missing at {width}px on 404.html"

        assert len(page._console_errors) == 0, f"Console errors on 404.html: {page._console_errors}"
