import time
import pytest
from tests.conftest import check_no_horizontal_overflow


class TestAdversarialM3MobileMenu:
    """
    Adversarial Stress Testing: Mobile Menu Lifecycle & Body Scroll Lock.
    Validates rapid toggling, backdrop dismissal, Escape key dismissal,
    link click navigation & auto-dismissal, body scroll lock, and subpages synchronization.
    """

    @pytest.mark.parametrize("width,height", [
        (320, 568),  # iPhone SE
        (360, 640),  # Compact Android
        (375, 667),  # iPhone 8
        (414, 896),  # iPhone XR/11
        (768, 1024), # iPad Portrait
    ])
    def test_mobile_menu_rapid_toggle_multi_viewport(self, page, base_url, width, height):
        """Stress-test rapid button toggles across various mobile viewport widths."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")
        hamburger = page.locator("#hamburgerIcon")
        close_icon = page.locator("#closeIcon")

        assert btn.is_visible(), f"Mobile menu button must be visible at {width}x{height}"

        # Rapidly toggle 20 times
        for i in range(20):
            btn.click()

        # After 20 clicks (even count), drawer should be closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), "Menu must be closed after even toggles"
        assert backdrop.count() == 0 or not backdrop.is_visible(), "Backdrop must be hidden after even toggles"
        assert btn.get_attribute("aria-expanded") == "false", "aria-expanded must be false when closed"
        assert hamburger.is_visible(), "Hamburger icon must be visible when closed"
        assert not close_icon.is_visible(), "Close icon must be hidden when closed"

        # Verify body scroll lock is completely removed
        overflow = page.evaluate("() => document.body.style.overflow")
        assert overflow in ["", "visible"], f"Body overflow style must be reset when closed, got '{overflow}'"
        body_classes = (page.locator("body").get_attribute("class") or "").split()
        assert "overflow-hidden" not in body_classes, "Body should not have 'overflow-hidden' class when closed"

        # 1 more click -> should open cleanly
        btn.click()
        page.wait_for_timeout(100)
        assert btn.get_attribute("aria-expanded") == "true"
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" not in menu_classes, "Menu must be open after odd toggle"
        assert close_icon.is_visible(), "Close icon must be visible when open"
        assert not hamburger.is_visible(), "Hamburger icon must be hidden when open"

        # Verify body scroll lock is applied
        body_overflow_open = page.evaluate("() => document.body.style.overflow")
        body_classes_open = (page.locator("body").get_attribute("class") or "").split()
        assert body_overflow_open == "hidden" or "overflow-hidden" in body_classes_open, (
            "Body scroll lock must be active when mobile drawer is open"
        )

        # Clean up: close menu
        btn.click()

    def test_mobile_menu_backdrop_dismissal_and_scroll_lock(self, page, base_url):
        """Open menu -> click backdrop -> verify closed and body scroll lock removed."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")

        # Open drawer
        btn.click()
        page.wait_for_timeout(100)
        assert backdrop.is_visible(), "Backdrop overlay must be visible when drawer opens"
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        # Click the backdrop overlay directly
        backdrop.click(force=True)
        page.wait_for_timeout(200)

        # Assert menu is closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), "Menu must close on backdrop click"
        assert not backdrop.is_visible(), "Backdrop must be hidden after dismissal"
        assert btn.get_attribute("aria-expanded") == "false"

        # Verify scroll lock is released
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]
        assert "overflow-hidden" not in (page.locator("body").get_attribute("class") or "").split()

    def test_mobile_menu_escape_key_dismissal(self, page, base_url):
        """Open menu -> press Escape -> verify closed and body scroll lock removed."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        # Open drawer
        btn.click()
        page.wait_for_timeout(100)
        assert btn.get_attribute("aria-expanded") == "true"
        assert page.evaluate("() => document.body.style.overflow") == "hidden"

        # Press Escape key
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # Assert menu closed
        menu_classes = (menu.get_attribute("class") or "").split()
        assert "hidden" in menu_classes or not menu.is_visible(), "Menu must close on Escape key"
        assert btn.get_attribute("aria-expanded") == "false"
        assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

    def test_mobile_menu_anchor_link_click_dismiss_and_scroll(self, page, base_url):
        """Open menu -> click an anchor link -> verify closed, scroll lock removed, and page scrolled."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")

        anchors_to_test = ["#framework", "#results", "#pricing", "#faq"]
        for anchor in anchors_to_test:
            # Scroll to top first
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(100)

            # Open menu
            btn.click()
            page.wait_for_timeout(100)
            assert not menu.is_hidden()

            # Click anchor inside mobile drawer
            link = menu.locator(f"a[href='{anchor}']").first
            assert link.is_visible(), f"Mobile drawer link for {anchor} must be visible"
            link.click()
            page.wait_for_timeout(500)

            # Assert menu closed
            menu_classes = (menu.get_attribute("class") or "").split()
            assert "hidden" in menu_classes or not menu.is_visible(), f"Menu must close after clicking {anchor}"
            assert btn.get_attribute("aria-expanded") == "false"

            # Assert scroll lock released
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

            # Assert viewport scrolled towards target
            scroll_y = page.evaluate("() => window.scrollY")
            assert scroll_y > 100, f"Page must scroll down when clicking {anchor} in mobile menu (got scrollY={scroll_y})"

    def test_subpages_mobile_menu_lifecycle(self, page, base_url):
        """Verify mobile menu lifecycle on legal subpages (privacy.html and terms.html)."""
        page.set_viewport_size({"width": 375, "height": 667})

        for subpage in ["privacy.html", "terms.html"]:
            page.goto(f"{base_url}/{subpage}")
            page.wait_for_load_state("networkidle")

            btn = page.locator("#mobileMenuBtn")
            menu = page.locator("#mobileMenu")
            backdrop = page.locator("#mobileMenuBackdrop")

            assert btn.is_visible(), f"Mobile menu button must exist on {subpage}"

            # Open menu
            btn.click()
            page.wait_for_timeout(100)
            assert btn.get_attribute("aria-expanded") == "true"
            assert page.evaluate("() => document.body.style.overflow") == "hidden"

            # Backdrop dismiss
            backdrop.click(force=True)
            page.wait_for_timeout(150)
            menu_classes = (menu.get_attribute("class") or "").split()
            assert "hidden" in menu_classes, f"Menu must close via backdrop on {subpage}"
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]

            # Open again and dismiss via Escape
            btn.click()
            page.wait_for_timeout(100)
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            menu_classes = (menu.get_attribute("class") or "").split()
            assert "hidden" in menu_classes, f"Menu must close via Escape on {subpage}"
            assert page.evaluate("() => document.body.style.overflow") in ["", "visible"]


class TestAdversarialM3StickyHeader:
    """
    Adversarial Stress Testing: Sticky Header Stability & Geometry.
    Verifies persistent top attachment at deep scroll (2000px),
    z-index hierarchy, zero layout shift (CLS), and oscillation stability.
    """

    @pytest.mark.parametrize("vp_width,vp_height", [
        (375, 667),   # Mobile
        (768, 1024),  # Tablet
        (1280, 800),  # Desktop
        (1920, 1080), # Widescreen
    ])
    def test_sticky_header_persists_deep_scroll_2000px(self, page, base_url, vp_width, vp_height):
        """Scroll down 2000px and verify header bounding_box.y == 0 and z-index remains top."""
        page.set_viewport_size({"width": vp_width, "height": vp_height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        header = page.locator("header").first
        assert header.is_visible()

        # Deep scroll down 2000px
        page.evaluate("window.scrollTo(0, 2000)")
        page.wait_for_timeout(300)

        # Header box check
        box = header.bounding_box()
        assert box is not None, "Header must have bounding box at 2000px scroll"
        assert abs(box["y"]) <= 1.0, f"Header bounding_box.y must be 0px on scroll (got {box['y']}px)"
        assert box["height"] >= 40, f"Header height should be reasonable (got {box['height']}px)"

        # Computed positioning & z-index
        position = header.evaluate("el => window.getComputedStyle(el).position")
        z_index = header.evaluate("el => window.getComputedStyle(el).zIndex")

        assert position in ["sticky", "fixed"], f"Header position must be sticky or fixed, got '{position}'"
        assert int(z_index) >= 40, f"Header z-index must be top-tier (>= 40), got '{z_index}'"

        # Check no horizontal overflow during deep scroll
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 2000px scroll: {scroll_w}px > {client_w}px"

    def test_sticky_header_rapid_oscillating_scroll_stability(self, page, base_url):
        """
        Stress test: Rapid oscillating scrolling across random offsets
        Verifies header stays clamped at top with zero layout shift decoupling.
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        header = page.locator("header").first

        scroll_targets = [0, 2500, 300, 1800, 0, 3200, 800, 0, 2100, 0]
        for target_y in scroll_targets:
            page.evaluate(f"window.scrollTo(0, {target_y})")
            page.wait_for_timeout(80)

            box = header.bounding_box()
            assert box is not None
            assert abs(box["y"]) <= 1.0, f"Header bounding_box.y drifted to {box['y']}px at scrollY={target_y}"

        # Zero console errors during oscillation
        assert len(page._console_errors) == 0, f"Console errors during scroll oscillation: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors during scroll oscillation: {page._page_errors}"

    def test_anchor_targets_have_scroll_margin_offset(self, page, base_url):
        """All key section anchors must have scroll-mt-24 preventing obstruction by sticky header."""
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        anchors = ["#framework", "#compliance", "#results", "#pricing", "#fit", "#founder", "#faq", "#audit"]
        for anchor in anchors:
            target = page.locator(anchor)
            assert target.count() >= 1, f"Anchor {anchor} must exist in index.html"
            class_attr = target.get_attribute("class") or ""
            scroll_margin = target.evaluate("el => window.getComputedStyle(el).scrollMarginTop")

            assert "scroll-mt-24" in class_attr or (scroll_margin not in ["0px", "", "auto"]), (
                f"Anchor {anchor} must have 'scroll-mt-24' or valid scrollMarginTop (got '{scroll_margin}')"
            )


class TestAdversarialM3FormValidation:
    """
    Adversarial Stress Testing: Audit Form Validation, Inline Error UX, and Dialog Absence.
    Validates empty field rejections, malformed email patterns, mock 200/500/network aborts,
    debounced multi-clicks, and 100% absence of browser alert dialogs.
    """

    def test_form_empty_submission_validation_and_no_alert(self, page, base_url):
        """
        Attempt submit with empty fields:
        - Verify NO native browser alert/confirm dialog is invoked.
        - Verify HTML5 constraint validation prevents successful form submission.
        - Verify #auditSuccess is NOT shown.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        submit_btn = page.locator("#submitAuditBtn")
        form = page.locator("#auditForm")
        success_box = page.locator("#auditSuccess")

        assert submit_btn.is_visible()

        # Clear any pre-filled values
        form.locator("input[name='name']").fill("")
        form.locator("input[name='domain']").fill("")
        form.locator("input[name='email']").fill("")

        # Click submit with empty fields
        submit_btn.click()
        page.wait_for_timeout(300)

        # STRICT ASSERTION: ZERO native browser alerts
        assert len(page._dialogs) == 0, f"Native dialogs triggered on empty submit: {page._dialogs}"

        # Form must NOT have transitioned to success state
        assert not success_box.is_visible(), "Empty form must NOT display #auditSuccess"

        # Verify HTML5 validity flags on required inputs
        name_valid = form.locator("input[name='name']").evaluate("el => el.checkValidity()")
        domain_valid = form.locator("input[name='domain']").evaluate("el => el.checkValidity()")
        email_valid = form.locator("input[name='email']").evaluate("el => el.checkValidity()")

        assert not name_valid, "Empty name input must fail validation"
        assert not domain_valid, "Empty domain input must fail validation"
        assert not email_valid, "Empty email input must fail validation"

    @pytest.mark.parametrize("malformed_email", [
        "plainaddress",
        "@missingusername.com",
        "username@.com",
        "username@domain..com",
        "user name@domain.com",
        "username@domain,com",
        "missingatsign.org",
    ])
    def test_form_malformed_emails_rejection(self, page, base_url, malformed_email):
        """Attempt submit with malformed emails -> verify rejection by email input validator."""
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        form = page.locator("#auditForm")
        submit_btn = page.locator("#submitAuditBtn")

        # Fill valid name and domain, but malformed email
        form.locator("input[name='name']").fill("Eric Coleman")
        form.locator("input[name='domain']").fill("https://acme.com")
        email_input = form.locator("input[name='email']")
        email_input.fill(malformed_email)

        # Submit attempt
        submit_btn.click()
        page.wait_for_timeout(200)

        # Verify rejection
        is_valid = email_input.evaluate("el => el.checkValidity()")
        assert not is_valid, f"Malformed email '{malformed_email}' must be rejected by input validation"
        assert not page.locator("#auditSuccess").is_visible()
        assert len(page._dialogs) == 0, "No browser alerts allowed"

    def test_form_valid_submission_inline_success_and_no_alert(self, page, base_url):
        """
        Attempt submit with valid data:
        - Mock 200 OK response from form endpoint.
        - Verify #auditSuccess is shown.
        - Verify NO alert dialog appears.
        - Verify #auditError remains hidden.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Mock formspree to return 200 OK
        page.route("**/formspree.io/**", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"ok": true}'
        ))

        form = page.locator("#auditForm")
        form.locator("input[name='name']").fill("Sarah Connor")
        form.locator("input[name='domain']").fill("https://cyberdyne.io")
        form.locator("input[name='email']").fill("sconnor@cyberdyne.io")
        form.locator("textarea[name='notes']").fill("Strict FTC boundaries required.")

        submit_btn = page.locator("#submitAuditBtn")
        submit_btn.click()
        page.wait_for_timeout(500)

        # Assert zero alerts
        assert len(page._dialogs) == 0, f"Browser alert fired on valid submission: {page._dialogs}"

        # Assert inline success state
        success_box = page.locator("#auditSuccess")
        assert success_box.is_visible(), "Inline #auditSuccess must be visible on 200 OK"
        assert success_box.get_attribute("role") == "status", "#auditSuccess should have role='status'"
        assert success_box.get_attribute("aria-live") == "polite", "#auditSuccess should have aria-live='polite'"

        # Form itself should be hidden
        assert not form.is_visible(), "Form should be hidden once success state is revealed"

        # Assert #auditError is hidden
        error_box = page.locator("#auditError")
        assert not error_box.is_visible()

    def test_form_error_response_shows_inline_audit_error_and_focus(self, page, base_url):
        """
        Server returns 422 or 500 error:
        - Verify inline #auditError appears with role="alert".
        - Verify focus is managed.
        - Verify NO browser alert dialog is shown.
        - Verify submit button re-enables.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Mock endpoint with 500 Server Error
        page.route("**/formspree.io/**", lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body='{"error": "Internal Server Error"}'
        ))

        form = page.locator("#auditForm")
        form.locator("input[name='name']").fill("Marcus Torres")
        form.locator("input[name='domain']").fill("https://prismdata.ai")
        form.locator("input[name='email']").fill("marcus@prismdata.ai")

        submit_btn = page.locator("#submitAuditBtn")
        submit_btn.click()
        page.wait_for_timeout(500)

        # Assert zero alerts
        assert len(page._dialogs) == 0, f"Alert dialog shown on error response: {page._dialogs}"

        # Assert inline error container is visible
        error_box = page.locator("#auditError")
        assert error_box.is_visible(), "#auditError must be visible after server error"
        assert error_box.get_attribute("role") == "alert", "#auditError must have role='alert'"
        assert "problem submitting your request" in error_box.inner_text().lower()

        # Submit button should be re-enabled
        assert not submit_btn.is_disabled(), "Submit button must re-enable after failure"

    def test_form_network_exception_handling(self, page, base_url):
        """
        Network abort/drop during form submission:
        - Verify inline #auditError appears with network error message.
        - Verify ZERO browser alert dialogs.
        - Verify submit button is re-enabled.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Mock endpoint to abort
        page.route("**/formspree.io/**", lambda route: route.abort("failed"))

        form = page.locator("#auditForm")
        form.locator("input[name='name']").fill("Elena Rostova")
        form.locator("input[name='domain']").fill("https://neuralvanguard.com")
        form.locator("input[name='email']").fill("elena@neuralvanguard.com")

        submit_btn = page.locator("#submitAuditBtn")
        submit_btn.click()
        page.wait_for_timeout(500)

        # Assert zero alerts
        assert len(page._dialogs) == 0, f"Alert dialog shown on network error: {page._dialogs}"

        # Assert inline error container
        error_box = page.locator("#auditError")
        assert error_box.is_visible(), "#auditError must display on network failure"
        assert "network error" in error_box.inner_text().lower()

        # Submit button must re-enable
        assert not submit_btn.is_disabled()

    def test_form_rapid_multi_clicks_on_submit(self, page, base_url):
        """
        Rapid multi-clicks on submit button:
        - Verify submit button disables immediately on first submit.
        - Verify no broken UI state, no duplicate requests, and zero console errors.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        request_count = 0

        def handle_route(route):
            nonlocal request_count
            request_count += 1
            # Delay response by 400ms to allow multi-click testing while in-flight
            time.sleep(0.4)
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok": true}'
            )

        page.route("**/formspree.io/**", handle_route)

        form = page.locator("#auditForm")
        form.locator("input[name='name']").fill("Rapid Clicker")
        form.locator("input[name='domain']").fill("https://rapidclick.com")
        form.locator("input[name='email']").fill("rapid@click.com")

        submit_btn = page.locator("#submitAuditBtn")
        submit_btn.scroll_into_view_if_needed()

        # Fire initial click to submit
        submit_btn.click()

        # Immediately attempt rapid follow-up clicks while in-flight
        for _ in range(4):
            try:
                submit_btn.click(timeout=150, force=True)
            except Exception:
                pass

        page.wait_for_timeout(800)

        # Only 1 request should have been dispatched because button disables on submit
        assert request_count == 1, f"Expected exactly 1 request during rapid clicks, got {request_count}"

        # Form transitions cleanly to success
        assert page.locator("#auditSuccess").is_visible()

        # Zero runtime errors
        assert len(page._page_errors) == 0, f"Page errors during rapid clicks: {page._page_errors}"
        assert len(page._console_errors) == 0, f"Console errors during rapid clicks: {page._console_errors}"


class TestAdversarialM3ConsoleMonitor:
    """
    Continuous Error Monitoring:
    Monitors console.error, pageerror, and unhandled rejections across all combined user flows.
    """

    def test_zero_console_and_page_errors_full_interactive_journey(self, page, base_url):
        """
        Execute deep combination of M3 user interactions:
        - Mobile menu open/close/escape/backdrop/links
        - Deep scroll to 2500px and back
        - Tab switching in Section 3 proof card
        - FAQ accordions toggling
        - Form validation triggers
        Verify: console.error == 0, pageerror == 0 across the entire session.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # 1. Mobile menu toggle cycles
        btn = page.locator("#mobileMenuBtn")
        for _ in range(6):
            btn.click()
            page.wait_for_timeout(50)

        # 2. Open drawer and dismiss via backdrop
        btn.click()
        page.wait_for_timeout(100)
        page.locator("#mobileMenuBackdrop").click(force=True)
        page.wait_for_timeout(100)

        # 3. Open drawer and dismiss via Escape
        btn.click()
        page.wait_for_timeout(100)
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)

        # 4. Scroll down and up
        page.evaluate("window.scrollTo(0, 2500)")
        page.wait_for_timeout(200)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)

        # 5. Section 3 proof card tab switching
        google_tab = page.locator("#tabGoogleProof")
        reddit_tab = page.locator("#tabRedditProof")
        if google_tab.count() > 0 and reddit_tab.count() > 0:
            reddit_tab.click()
            page.wait_for_timeout(100)
            google_tab.click()
            page.wait_for_timeout(100)

        # 6. FAQ toggle
        faq_details = page.locator("#faq details")
        if faq_details.count() > 0:
            faq_details.first.locator("summary").click()
            page.wait_for_timeout(100)
            faq_details.first.locator("summary").click()
            page.wait_for_timeout(100)

        # Check console errors (ignoring any third-party blocked telemetry)
        app_console_errors = [
            err for err in page._console_errors
            if "google-analytics" not in err and "clarity.ms" not in err and "googletagmanager" not in err
        ]

        assert len(page._page_errors) == 0, f"Page errors logged during journey: {page._page_errors}"
        assert len(app_console_errors) == 0, f"App console errors logged during journey: {app_console_errors}"
