import pytest
import time


def is_third_party_analytics(msg_text: str) -> bool:
    """Filter out expected 3rd-party tracking/analytics network errors in headless test environment."""
    return any(domain in msg_text for domain in [
        "google-analytics", "clarity.ms", "googletagmanager", "doubleclick", "analytics"
    ])


@pytest.mark.tier3
class TestM1RapidInteractionInterruption:
    """
    Stress-tests rapid interactive edge cases on Milestone 1:
    - Rapid anchor switching across #framework, #compliance, #results, #pricing, #faq at 50ms intervals.
    - Asserting zero unhandled JS exceptions, Lenis scroll lock prevention, and final destination accuracy.
    - Reverse rapid anchor clicks, wheel interruptions mid-animation, and repeated rapid clicks.
    """

    def test_rapid_anchor_click_forward_chain(self, page, base_url):
        """
        Rapidly click anchors (#framework, #compliance, #results, #pricing, #faq) at 50ms intervals.
        Assert:
        - No unhandled JS errors / page errors.
        - Lenis does not lock scrolling.
        - Final destination (#faq) settles accurately with proper offset.
        - Subsequent manual/programmatic scrolling remains functional.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        anchors = ["#framework", "#compliance", "#results", "#pricing", "#faq"]

        # Ensure starting at top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)

        # Rapidly click through each anchor at 50ms intervals
        for anchor in anchors:
            link = page.locator(f"header nav a[href='{anchor}']").first
            assert link.is_visible(), f"Nav anchor link {anchor} must be visible in desktop nav"
            link.click()
            page.wait_for_timeout(50)

        # Allow final animation (duration 1.0s) to settle fully
        page.wait_for_timeout(1500)

        # 1. Assert zero unhandled JS exceptions
        assert len(page_errors) == 0, f"Unhandled page exceptions occurred during rapid clicks: {page_errors}"
        assert len(console_errors) == 0, f"Unexpected console errors occurred during rapid clicks: {console_errors}"

        # 2. Assert final target (#faq) settles accurately
        faq_target = page.locator("#faq")
        assert faq_target.count() >= 1, "Target section #faq must exist in DOM"
        faq_box = faq_target.bounding_box()
        assert faq_box is not None, "Target #faq must have a bounding box"

        # The anchor click handler applies offset: -80
        # Check that top of #faq is approximately at or near header height (around 60px to 100px from top)
        assert -10 <= faq_box["y"] <= 120, (
            f"Final anchor #faq target settled at unexpected y={faq_box['y']} (expected ~80px offset under header)"
        )

        # 3. Assert Lenis does not lock scrolling:
        # Check Lenis state (isScrolling should be false after settling)
        is_scrolling = page.evaluate("() => typeof window.lenis !== 'undefined' ? window.lenis.isScrolling : false")
        assert not is_scrolling, "Lenis must not remain stuck in isScrolling state after animation completes"

        # Verify scroll is not locked: issue programmatic scroll and verify scrollY updates
        pre_scroll_y = page.evaluate("window.scrollY")
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(200)
        post_scroll_y = page.evaluate("window.scrollY")
        assert post_scroll_y != pre_scroll_y, f"Scrolling is locked! Pre: {pre_scroll_y}, Post: {post_scroll_y}"

    def test_rapid_anchor_click_reverse_chain(self, page, base_url):
        """
        Rapidly click anchors in reverse order (#faq -> #pricing -> #results -> #compliance -> #framework) at 50ms intervals.
        Assert clean settlement at #framework with zero unhandled exceptions and no scroll lock.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        anchors_reverse = ["#faq", "#pricing", "#results", "#compliance", "#framework"]

        # Rapidly click reverse sequence
        for anchor in anchors_reverse:
            link = page.locator(f"header nav a[href='{anchor}']").first
            link.click()
            page.wait_for_timeout(50)

        # Wait for 1.0s glide to finish
        page.wait_for_timeout(1500)

        assert len(page_errors) == 0, f"Page errors: {page_errors}"
        assert len(console_errors) == 0, f"Console errors: {console_errors}"

        framework_target = page.locator("#framework")
        f_box = framework_target.bounding_box()
        assert f_box is not None, "#framework target bounding box missing"
        assert -10 <= f_box["y"] <= 120, (
            f"Final anchor #framework settled at unexpected y={f_box['y']} (expected ~80px offset)"
        )

        # Assert Lenis unlocked
        page.evaluate("window.scrollBy(0, 200)")
        page.wait_for_timeout(150)
        final_y = page.evaluate("window.scrollY")
        assert final_y > 0, "Window scroll did not respond after rapid reverse clicks"

    def test_rapid_anchor_click_interrupted_by_user_wheel(self, page, base_url):
        """
        Verify that a user mousewheel event fired mid-animation cleanly interrupts the glide
        without throwing unhandled errors or locking Lenis momentum.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Click #pricing
        page.locator("header nav a[href='#pricing']").first.click()
        # Wait 100ms mid-animation
        page.wait_for_timeout(100)

        # Simulate user wheel in opposite direction
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(500)

        assert len(page_errors) == 0, f"Page errors upon wheel interruption: {page_errors}"
        assert len(console_errors) == 0, f"Console errors upon wheel interruption: {console_errors}"

        # Assert page can still scroll down
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(300)
        y = page.evaluate("window.scrollY")
        assert y > 0, "Scroll position is locked after wheel interruption"

    def test_repeated_rapid_clicks_same_anchor(self, page, base_url):
        """
        Stress-test spam clicking the same anchor 10 times in 25ms intervals.
        Asserts no NaN values in Lenis scroll coordinates, no crashes, and clean settling.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        link = page.locator("header nav a[href='#results']").first
        for _ in range(10):
            link.click()
            page.wait_for_timeout(25)

        page.wait_for_timeout(1500)

        assert len(page_errors) == 0, f"Errors on repeated clicks: {page_errors}"
        assert len(console_errors) == 0, f"Console errors on repeated clicks: {console_errors}"

        scroll_y = page.evaluate("window.scrollY")
        assert scroll_y is not None and not page.evaluate("isNaN(window.scrollY)"), "scrollY is NaN or corrupted"
        assert scroll_y > 500, f"Expected scrollY > 500 for #results, got {scroll_y}"


@pytest.mark.tier2
class TestM1MultiViewportStress:
    """
    Stress-tests scroll performance and layout stability across viewports:
    - 320px (iPhone SE 1st gen / ultra-narrow mobile)
    - 375px (iPhone standard mobile)
    - 768px (iPad portrait / tablet)
    - 1024px (iPad landscape / small desktop)
    - 1440px (Standard desktop / widescreen)
    Asserts zero horizontal overflow and zero layout breakage.
    """

    VIEWPORTS = [
        {"name": "320px ultra-narrow", "width": 320, "height": 568},
        {"name": "375px standard-mobile", "width": 375, "height": 667},
        {"name": "768px tablet", "width": 768, "height": 1024},
        {"name": "1024px desktop-small", "width": 1024, "height": 768},
        {"name": "1440px desktop-wide", "width": 1440, "height": 900},
    ]

    @pytest.mark.parametrize("vp", VIEWPORTS, ids=lambda v: v["name"])
    def test_viewport_zero_horizontal_overflow_and_scroll_stress(self, page, base_url, vp):
        """
        Verify zero horizontal overflow during static load and active multi-step scroll stress.
        Asserts documentElement.scrollWidth <= window.innerWidth at every step.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Static check
        overflow_info = page.evaluate("""() => {
            const docWidth = document.documentElement.scrollWidth;
            const innerWidth = window.innerWidth;
            const bodyWidth = document.body.scrollWidth;
            return {
                docWidth,
                innerWidth,
                bodyWidth,
                hasOverflow: docWidth > innerWidth + 1 || bodyWidth > innerWidth + 1
            };
        }""")
        assert not overflow_info["hasOverflow"], (
            f"Horizontal overflow detected at {vp['name']}! "
            f"docWidth={overflow_info['docWidth']}, innerWidth={overflow_info['innerWidth']}"
        )

        # Dynamic scroll stress: scroll incrementally down the entire page
        total_height = page.evaluate("document.body.scrollHeight")
        step = max(300, vp["height"] // 2)
        current_y = 0

        while current_y < total_height:
            current_y += step
            page.evaluate(f"window.scrollTo(0, {current_y})")
            page.wait_for_timeout(30)

            # Assert zero horizontal overflow during scroll
            is_overflowing = page.evaluate("""() => {
                return document.documentElement.scrollWidth > window.innerWidth + 1;
            }""")
            assert not is_overflowing, (
                f"Horizontal overflow triggered during dynamic scroll at scrollY={current_y} in {vp['name']}"
            )

        # Rapid flick to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # Assert no page errors or console errors occurred during the stress scroll
        assert len(page_errors) == 0, f"Page errors during scroll stress at {vp['name']}: {page_errors}"
        assert len(console_errors) == 0, f"Console errors during scroll stress at {vp['name']}: {console_errors}"

    @pytest.mark.parametrize("vp", VIEWPORTS, ids=lambda v: v["name"])
    def test_viewport_layout_integrity_and_visibility(self, page, base_url, vp):
        """
        Verify key landmarks and sections retain structural integrity and non-zero layout dimensions
        across all target viewports.
        """
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Verify header is rendered and fits within viewport
        header = page.locator("header").first
        assert header.is_visible(), f"Header not visible at {vp['name']}"
        header_box = header.bounding_box()
        assert header_box is not None, "Header has no bounding box"
        assert header_box["width"] <= vp["width"] + 1, (
            f"Header width {header_box['width']} exceeds viewport width {vp['width']}"
        )

        # Verify key sections exist and have positive dimensions
        sections = ["hero", "framework", "compliance", "results", "pricing", "faq"]
        for sec_id in sections:
            sec = page.locator(f"#{sec_id}").first
            if sec.count() > 0:
                box = sec.bounding_box()
                assert box is not None, f"Section #{sec_id} has no bounding box at {vp['name']}"
                assert box["width"] > 0, f"Section #{sec_id} has width 0 at {vp['name']}"
                assert box["height"] > 0, f"Section #{sec_id} has height 0 at {vp['name']}"
                assert box["width"] <= vp["width"] + 2, (
                    f"Section #{sec_id} width {box['width']} overflows viewport {vp['width']}"
                )


@pytest.mark.tier1
class TestM1TrackingDeferralVerification:
    """
    Empirically verifies Milestone 1 Feature 8:
    Tracking Deferral via requestIdleCallback / fallback.
    Asserts:
    - scheduleTracking defers loadTracking to requestIdleCallback without executing synchronously.
    - User touch/scroll does not trigger synchronous blocking long tasks.
    - Fallback path works cleanly when requestIdleCallback is unavailable.
    """

    def test_touch_and_scroll_defer_tracking_via_request_idle_callback(self, page, base_url):
        """
        Challenge 3.1: Verify touchstart and scroll events invoke requestIdleCallback,
        and loadTracking does NOT execute synchronously during the event dispatch.
        """
        # Inject instrumentation before page loads
        page.add_init_script("""
            window.__ricCalls = [];
            const origRIC = window.requestIdleCallback ? window.requestIdleCallback.bind(window) : null;
            if (origRIC) {
                window.requestIdleCallback = function(cb, opts) {
                    window.__ricCalls.push({
                        opts: opts,
                        time: performance.now(),
                        cbName: cb.name
                    });
                    return origRIC(cb, opts);
                };
            }
        """)

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("domcontentloaded")

        # Immediately dispatch touchstart event on window
        start_time = time.perf_counter()
        res = page.evaluate("""() => {
            const preGtm = !!window.dataLayer;
            const t0 = performance.now();
            window.dispatchEvent(new Event('touchstart'));
            const t1 = performance.now();
            const synchronousDuration = t1 - t0;
            // Check if tracking scripts were injected synchronously
            const gtmScript = document.querySelector('script[src*="googletagmanager.com"]');
            const clarityScript = document.querySelector('script[src*="clarity.ms"]');
            const ricCount = window.__ricCalls.length;
            return {
                synchronousDuration,
                preGtm,
                hasGtmImmediately: !!gtmScript,
                hasClarityImmediately: !!clarityScript,
                ricCount,
                ricCalls: window.__ricCalls
            };
        }""")

        # 1. Assert synchronous execution time of event handler was fast (< 10ms, no long task)
        assert res["synchronousDuration"] < 15.0, (
            f"Event handler took {res['synchronousDuration']}ms synchronously, which blocks the main thread!"
        )

        # 2. Assert requestIdleCallback was scheduled
        assert res["ricCount"] >= 1, f"Expected requestIdleCallback to be called upon touchstart, got {res['ricCount']}"
        assert res["ricCalls"][0]["opts"]["timeout"] == 3000, (
            f"Expected requestIdleCallback timeout: 3000, got {res['ricCalls'][0]['opts']}"
        )

        # 3. Assert tracking was NOT injected synchronously in the same frame
        assert not res["hasGtmImmediately"], "GTM script was injected synchronously during touchstart handler!"
        assert not res["hasClarityImmediately"], "Clarity script was injected synchronously during touchstart handler!"

        # Allow idle callback to execute
        page.wait_for_timeout(1000)

        # After idle callback executes, verify tracking scripts are properly injected
        post_state = page.evaluate("""() => {
            const gtmScript = document.querySelector('script[src*="googletagmanager.com"]');
            const clarityScript = document.querySelector('script[src*="clarity.ms"]');
            return {
                hasGtm: !!gtmScript,
                hasClarity: !!clarityScript,
                hasDataLayer: typeof window.dataLayer !== 'undefined'
            };
        }""")
        assert post_state["hasGtm"], "GTM script was not injected after idle callback fired"
        assert post_state["hasClarity"], "Clarity script was not injected after idle callback fired"

    def test_tracking_deferral_fallback_without_request_idle_callback(self, page, base_url):
        """
        Challenge 3.2: Verify fallback path when requestIdleCallback is not supported
        (e.g., Safari or legacy browsers). Uses setTimeout(loadTracking, 1500) rather
        than synchronous blocking injection.
        """
        # Inject script removing requestIdleCallback to test fallback
        page.add_init_script("""
            delete window.requestIdleCallback;
            window.__setTimeoutCalls = [];
            const origSetTimeout = window.setTimeout.bind(window);
            window.setTimeout = function(cb, delay, ...args) {
                if (typeof cb === 'function' && cb.name === 'loadTracking') {
                    window.__setTimeoutCalls.push({ delay, time: performance.now() });
                }
                return origSetTimeout(cb, delay, ...args);
            };
        """)

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("domcontentloaded")

        res = page.evaluate("""() => {
            const t0 = performance.now();
            window.dispatchEvent(new Event('scroll'));
            const t1 = performance.now();
            const gtmScript = document.querySelector('script[src*="googletagmanager.com"]');
            return {
                duration: t1 - t0,
                hasGtmImmediately: !!gtmScript,
                timeoutCalls: window.__setTimeoutCalls
            };
        }""")

        assert res["duration"] < 15.0, f"Fallback scroll handler took {res['duration']}ms synchronously"
        assert not res["hasGtmImmediately"], "GTM script was injected synchronously on scroll fallback!"
        assert len(res["timeoutCalls"]) >= 1, "Expected setTimeout fallback to be scheduled for loadTracking"
        assert res["timeoutCalls"][0]["delay"] == 1500, (
            f"Expected fallback setTimeout delay 1500ms, got {res['timeoutCalls'][0]['delay']}"
        )
