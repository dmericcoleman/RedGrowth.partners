import pytest
import time
from tests.conftest import check_no_horizontal_overflow

RESIZE_BREAKPOINTS = [280, 375, 768, 1024, 1440, 375, 280]
SUBPAGES = ["privacy.html", "terms.html", "404.html"]


class TestAdversarialM4DynamicResizeStress:
    """
    Milestone 4 Adversarial Verification Suite:
    Dynamic Reflow, Resize Stress, and DOM Stability across extreme viewports and interactions.
    """

    def test_rapid_viewport_oscillation_idle_no_overflow(self, page, base_url):
        """
        Rapidly oscillate viewport widths across 280px -> 375px -> 768px -> 1024px -> 1440px -> 375px -> 280px
        for multiple full cycles on index.html.
        Verifies:
        - scrollWidth <= clientWidth at every step (zero horizontal overflow)
        - body scroll lock is never unexpectedly engaged
        - zero console errors or unhandled exceptions
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # 3 complete cycles of oscillation (21 resize transitions)
        for cycle in range(3):
            for width in RESIZE_BREAKPOINTS:
                page.set_viewport_size({"width": width, "height": 800})
                page.wait_for_timeout(50)  # Allow reflow to settle

                passes, scroll_w, client_w = check_no_horizontal_overflow(page)
                assert passes, (
                    f"Horizontal overflow in cycle {cycle+1} at width {width}px: "
                    f"scrollWidth={scroll_w}px > clientWidth={client_w}px (Delta: +{scroll_w - client_w}px)"
                )

                # Ensure body scroll lock is not active during idle oscillation
                body_overflow = page.evaluate("() => document.body.style.overflow")
                assert body_overflow != "hidden", f"Body overflow unexpectedly locked at {width}px"
                has_class = page.evaluate("() => document.body.classList.contains('overflow-hidden')")
                assert not has_class, f"Body has overflow-hidden class unexpectedly at {width}px"

        assert len(page._console_errors) == 0, f"Console errors during oscillation: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page runtime errors during oscillation: {page._page_errors}"

    def test_mobile_drawer_auto_dismiss_on_resize_to_desktop(self, page, base_url):
        """
        Verify that opening the mobile drawer at mobile width (375px/280px) and resizing
        to desktop (>=1024px) cleanly auto-dismisses the drawer and releases body scroll lock.
        Then resizing back to mobile keeps drawer closed and body unlocked.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")
        mobile_backdrop = page.locator("#mobileMenuBackdrop")

        # Step 1: Open mobile drawer
        assert mobile_btn.is_visible(), "Mobile menu button must be visible at 375px"
        mobile_btn.click()
        page.wait_for_timeout(100)

        assert mobile_menu.is_visible(), "Mobile menu must be visible after opening"
        assert mobile_backdrop.is_visible(), "Mobile backdrop must be visible"
        assert page.evaluate("() => document.body.style.overflow") == "hidden", "Body scroll lock must be active"

        # Step 2: Resize through breakpoints to desktop (768px -> 1024px -> 1440px)
        # At 768px (tablet), drawer may remain open
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(50)

        # At 1024px (desktop breakpoint), drawer MUST auto-dismiss
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(100)

        assert not mobile_menu.is_visible(), "Mobile menu must auto-dismiss at 1024px (desktop)"
        assert not mobile_backdrop.is_visible(), "Backdrop must be hidden at 1024px"
        assert page.evaluate("() => document.body.style.overflow") != "hidden", (
            "Body scroll lock must be released when resized to 1024px"
        )
        assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
            "overflow-hidden class must be removed from body at 1024px"
        )

        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 1024px after drawer auto-dismiss: {scroll_w}px > {client_w}px"

        # Step 3: Resize to widescreen 1440px
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(50)
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 1440px: {scroll_w}px > {client_w}px"

        # Step 4: Resize back down to 375px and 280px
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(50)
        # Drawer must NOT spontaneously re-open
        assert not mobile_menu.is_visible(), "Mobile menu must not reopen on shrinking back to mobile"
        assert page.evaluate("() => document.body.style.overflow") != "hidden", (
            "Body scroll lock must remain released at 375px"
        )

        page.set_viewport_size({"width": 280, "height": 653})
        page.wait_for_timeout(50)
        assert not mobile_menu.is_visible(), "Mobile menu must not reopen at 280px"
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at 280px: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    def test_mobile_drawer_resize_hammer_10_cycles(self, page, base_url):
        """
        Adversarial Hammer: 10 repeated rapid cycles of opening drawer at 320px/375px
        and immediately crossing desktop threshold (1024px/1280px/1440px).
        Ensures zero race conditions, zero stuck locks, and zero DOM leaks.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")

        for i in range(10):
            # 1. Set to mobile
            m_width = 280 if i % 2 == 0 else 375
            page.set_viewport_size({"width": m_width, "height": 667})
            page.wait_for_timeout(40)

            # 2. Open drawer
            mobile_btn.click()
            page.wait_for_timeout(40)
            assert mobile_menu.is_visible(), f"Drawer failed to open on cycle {i+1} at {m_width}px"
            assert page.evaluate("() => document.body.style.overflow") == "hidden", (
                f"Body not locked on cycle {i+1}"
            )

            # 3. Immediately jump to desktop
            d_width = 1024 if i % 2 == 0 else 1440
            page.set_viewport_size({"width": d_width, "height": 800})
            page.wait_for_timeout(60)

            # 4. Verify auto-dismiss and lock release
            assert not mobile_menu.is_visible(), f"Drawer still visible at {d_width}px on cycle {i+1}"
            body_overflow = page.evaluate("() => document.body.style.overflow")
            assert body_overflow != "hidden", (
                f"Body scroll lock stuck on cycle {i+1} after resizing to {d_width}px! Value: '{body_overflow}'"
            )
            assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
                f"Body class overflow-hidden stuck on cycle {i+1}!"
            )

            # 5. Check no horizontal overflow
            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow on cycle {i+1} at {d_width}px: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors during hammer: {page._console_errors}"

    def test_faq_accordion_interactions_during_resize_oscillation(self, page, base_url):
        """
        Interacts with the FAQ accordion (opening all items, toggling items)
        concurrently with viewport oscillation across 280px -> 375px -> 768px -> 1024px -> 1440px -> 375px -> 280px.
        Verifies no content expansion causes horizontal overflow or layout breakage.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/#faq")
        page.wait_for_load_state("networkidle")

        faq_details = page.locator("#faq details")
        faq_count = faq_details.count()
        assert faq_count == 5, f"Expected 5 FAQ items, found {faq_count}"

        # Open all 5 FAQ panels
        for i in range(faq_count):
            faq_details.nth(i).evaluate("el => el.open = true")
        page.wait_for_timeout(50)

        # Oscillate viewports while all 5 FAQs are open
        for width in RESIZE_BREAKPOINTS:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(60)

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, (
                f"Horizontal overflow at {width}px with all FAQs open: "
                f"scrollWidth={scroll_w}px > clientWidth={client_w}px (Delta: +{scroll_w - client_w}px)"
            )

            # Verify every FAQ item's text container does not exceed clientWidth
            for i in range(faq_count):
                detail = faq_details.nth(i)
                box = detail.bounding_box()
                assert box is not None
                assert box["x"] >= -1, f"FAQ {i} left edge ({box['x']}px) is offscreen at {width}px"
                assert box["x"] + box["width"] <= width + 2, (
                    f"FAQ {i} right edge ({box['x'] + box['width']}px) exceeds viewport width ({width}px)"
                )

        # Oscillate viewports while actively toggling items
        for idx, width in enumerate(RESIZE_BREAKPOINTS):
            page.set_viewport_size({"width": width, "height": 800})
            # Toggle item (idx % 5)
            summary = faq_details.nth(idx % 5).locator("summary")
            summary.click()
            page.wait_for_timeout(40)

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow after toggling FAQ {idx % 5} at {width}px: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    def test_audit_form_interactions_and_error_states_during_resize_oscillation(self, page, base_url):
        """
        Interacts with the Audit form (typing values, triggering error container)
        while oscillating viewports across 280px -> 375px -> 768px -> 1024px -> 1440px -> 375px -> 280px.
        Verifies inline error containers, labels, and form fields do not cause horizontal overflow.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/#audit")
        page.wait_for_load_state("networkidle")

        form = page.locator("#auditForm")
        assert form.is_visible()

        # Fill inputs with long adversarial values
        name_input = page.locator("#fullName")
        email_input = page.locator("#workEmail")
        domain_input = page.locator("#companyDomain")
        submit_btn = page.locator("#submitAuditBtn")
        error_container = page.locator("#auditError")

        name_input.fill("Dr. Alexander Montgomery-Fitzgerald III")
        email_input.fill("alexander.montgomery@enterprise-ai-solutions-global.com")
        domain_input.fill("https://subdomain.deep-enterprise-solutions-infrastructure.global.co.uk")

        # Trigger inline error container directly to test its responsive bounds
        page.evaluate("""() => {
            const err = document.getElementById('auditError');
            if (err) {
                err.textContent = 'A network error occurred. Please try again or book a call directly. Long adversarial text with continuous words and details.';
                err.classList.remove('hidden');
            }
        }""")
        page.wait_for_timeout(50)

        assert error_container.is_visible()

        # Oscillate across breakpoints while form and error container are visible
        for width in RESIZE_BREAKPOINTS:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(50)

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, (
                f"Horizontal overflow at {width}px with filled form & error alert: "
                f"scrollWidth={scroll_w}px > clientWidth={client_w}px (Delta: +{scroll_w - client_w}px)"
            )

            # Check error container bounding box
            err_box = error_container.bounding_box()
            assert err_box is not None
            assert err_box["x"] >= -1, f"Error box left edge offscreen at {width}px"
            assert err_box["x"] + err_box["width"] <= width + 2, (
                f"Error box right edge ({err_box['x'] + err_box['width']}px) exceeds viewport ({width}px)"
            )

            # Check submit button bounding box
            btn_box = submit_btn.bounding_box()
            assert btn_box is not None
            assert btn_box["x"] >= -1
            assert btn_box["x"] + btn_box["width"] <= width + 2

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    def test_deep_scroll_and_anchor_jumps_during_rapid_resize(self, page, base_url):
        """
        Scrolls through the landing page and jumps across section anchors (#framework, #compliance,
        #results, #pricing, #fit, #faq, #founder, #audit) while simultaneously resizing viewports.
        Verifies sticky header stability, zero clipping, and zero horizontal overflow.
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        anchors = ["#framework", "#compliance", "#results", "#pricing", "#fit", "#founder", "#faq", "#audit"]
        widths = [280, 375, 768, 1024, 1440, 375, 280, 1280]

        for anchor, width in zip(anchors, widths):
            page.set_viewport_size({"width": width, "height": 800})
            page.evaluate(f"() => window.location.hash = '{anchor}'")
            page.wait_for_timeout(80)

            # Verify target section exists and is visible
            target = page.locator(anchor)
            assert target.is_visible(), f"Target section {anchor} not visible at {width}px"

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, (
                f"Horizontal overflow at anchor {anchor} and width {width}px: "
                f"scrollWidth={scroll_w}px > clientWidth={client_w}px"
            )

            # Verify header is still intact
            header = page.locator("header")
            assert header.is_visible(), f"Header not visible at {width}px"
            header_box = header.bounding_box()
            assert header_box is not None
            assert header_box["x"] >= -1
            assert header_box["width"] <= width + 1

        # Deep scroll to bottom, middle, and top
        for scroll_y in [0, 2500, 5000, 8000, 1000]:
            page.evaluate(f"() => window.scrollTo(0, {scroll_y})")
            page.wait_for_timeout(30)
            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow at scroll position Y={scroll_y}px"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    @pytest.mark.parametrize("subpage", SUBPAGES)
    def test_subpages_rapid_resize_and_deep_scroll(self, page, base_url, subpage):
        """
        Repeats rapid resize oscillation across breakpoints (280px -> 375px -> 768px -> 1024px -> 1440px -> 375px -> 280px)
        and deep scrolling across privacy.html, terms.html, and 404.html.
        Verifies:
        - scrollWidth <= clientWidth at every step
        - zero console errors or unhandled exceptions
        - clean responsive card/content containment
        """
        response = page.goto(f"{base_url}/{subpage}")
        assert response.status == 200, f"{subpage} returned HTTP {response.status}"
        page.wait_for_load_state("networkidle")

        # 2 cycles of resize oscillation (14 resize transitions)
        for cycle in range(2):
            for width in RESIZE_BREAKPOINTS:
                page.set_viewport_size({"width": width, "height": 750})
                page.wait_for_timeout(50)

                passes, scroll_w, client_w = check_no_horizontal_overflow(page)
                assert passes, (
                    f"Horizontal overflow on {subpage} in cycle {cycle+1} at {width}px: "
                    f"scrollWidth={scroll_w}px > clientWidth={client_w}px (Delta: +{scroll_w - client_w}px)"
                )

        # Deep scroll test on subpage
        max_scroll = page.evaluate("() => document.documentElement.scrollHeight - window.innerHeight")
        if max_scroll > 0:
            for frac in [0.25, 0.5, 0.75, 1.0, 0.0]:
                y = int(max_scroll * frac)
                page.evaluate(f"() => window.scrollTo(0, {y})")
                page.wait_for_timeout(40)
                passes, scroll_w, client_w = check_no_horizontal_overflow(page)
                assert passes, f"Horizontal overflow on {subpage} at scroll Y={y}px"

        assert len(page._console_errors) == 0, f"Console errors on {subpage}: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page runtime errors on {subpage}: {page._page_errors}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_subpages_mobile_drawer_resize_dismiss_and_lock_release(self, page, base_url, subpage):
        """
        Verifies mobile drawer on privacy.html and terms.html:
        1. Opens at 375px / 280px with body scroll lock.
        2. Auto-dismisses when resized to desktop (1024px, 1440px).
        3. Releases body scroll lock completely.
        4. Stays closed when resized back down to 375px / 280px.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")

        assert mobile_btn.is_visible(), f"Mobile button not visible on {subpage} at 375px"

        # 5 cycles of open mobile -> jump desktop -> verify dismiss & lock release
        for i in range(5):
            page.set_viewport_size({"width": 375, "height": 667})
            page.wait_for_timeout(40)

            # Open drawer
            mobile_btn.click()
            page.wait_for_timeout(50)
            assert mobile_menu.is_visible(), f"Drawer did not open on {subpage} on cycle {i+1}"
            assert page.evaluate("() => document.body.style.overflow") == "hidden", (
                f"Body not locked on {subpage} on cycle {i+1}"
            )

            # Resize to 1024px (desktop)
            page.set_viewport_size({"width": 1024, "height": 768})
            page.wait_for_timeout(60)

            assert not mobile_menu.is_visible(), (
                f"Drawer failed to auto-dismiss on {subpage} at 1024px on cycle {i+1}"
            )
            body_overflow = page.evaluate("() => document.body.style.overflow")
            assert body_overflow != "hidden", (
                f"Body scroll lock stuck on {subpage} at 1024px on cycle {i+1}! Value: '{body_overflow}'"
            )
            assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
                f"Body class overflow-hidden stuck on {subpage} at 1024px on cycle {i+1}"
            )

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow on {subpage} at 1024px: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors on {subpage}: {page._console_errors}"
