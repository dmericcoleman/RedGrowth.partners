import time
import pytest
from playwright.sync_api import sync_playwright

INIT_SCRIPT_INSTRUMENTATION = """
(() => {
    window.__rafCalls = [];
    window.__rafHistory = [];
    const _origRAF = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = function(cb) {
        const isLenisRaf = (cb.name === 'raf');
        const entry = {
            time: performance.now(),
            name: cb.name,
            isLenisRaf: isLenisRaf
        };
        window.__rafCalls.push(entry);
        window.__rafHistory.push(entry);
        return _origRAF(cb);
    };

    // Intercept Lenis constructor to expose instance on window for deep empirical probing
    let _OrigLenis = undefined;
    Object.defineProperty(window, 'Lenis', {
        configurable: true,
        enumerable: true,
        set(cls) {
            _OrigLenis = cls;
            function LenisWrapper(...args) {
                const inst = new cls(...args);
                window.__lenis = inst;
                return inst;
            }
            LenisWrapper.prototype = cls.prototype;
            window.__LenisWrapper = LenisWrapper;
        },
        get() {
            return window.__LenisWrapper || _OrigLenis;
        }
    });

    // Helper functions to sample scroll trajectory
    window.__startTrajectoryRecording = function(sampleIntervalMs = 25) {
        window.__trajectorySamples = [];
        window.__trajectoryStartTime = performance.now();
        if (window.__trajectoryInterval) clearInterval(window.__trajectoryInterval);
        window.__trajectoryInterval = setInterval(() => {
            window.__trajectorySamples.push({
                t: Math.round(performance.now() - window.__trajectoryStartTime),
                scrollY: Math.round(window.scrollY),
                animatedScroll: window.__lenis ? Math.round(window.__lenis.animatedScroll) : null,
                isScrolling: window.__lenis ? window.__lenis.isScrolling : null,
                isRunning: window.__lenis ? (window.__lenis.animate ? window.__lenis.animate.isRunning : null) : null
            });
        }, sampleIntervalMs);
    };

    window.__stopTrajectoryRecording = function() {
        if (window.__trajectoryInterval) {
            clearInterval(window.__trajectoryInterval);
            window.__trajectoryInterval = null;
        }
        return window.__trajectorySamples;
    };
})();
"""


@pytest.fixture
def instrumented_page(page):
    """Page fixture with mock routes for external analytics and deep RAF/Lenis instrumentation."""
    # Fulfill external analytics to avoid network hangs or connection refused errors in headless test env
    page.route("**/clarity.ms/**", lambda route: route.fulfill(status=200, body="// mock clarity", content_type="application/javascript"))
    page.route("**/googletagmanager.com/**", lambda route: route.fulfill(status=200, body="// mock gtm", content_type="application/javascript"))
    page.route("**/google-analytics.com/**", lambda route: route.fulfill(status=200, body="// mock ga", content_type="application/javascript"))
    page.add_init_script(INIT_SCRIPT_INSTRUMENTATION)
    return page


class TestEmpiricalChallengerM1:
    """
    Empirical Challenger Suite: Milestone 1 Script Engine & Scroll Performance.
    Conducts adversarial stress-testing, RAF lifecycle verification, trajectory measurement,
    CDP listener inspection, and mobile touch violation validation.
    """

    # =========================================================================
    # CRITERION 1: RAF Loop Idle Sleeping & Awakening
    # =========================================================================

    def test_raf_idle_sleeping_when_stationary(self, instrumented_page, base_url):
        """
        Empirically verify that when the page is stationary, requestAnimationFrame
        calls cease (rafId == null, 0 new Lenis RAF invocations over 500ms).
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Allow initial page load momentum / settling to complete (1 second)
        page.wait_for_timeout(1000)

        # Clear RAF calls buffer
        page.evaluate("() => { window.__rafCalls = []; }")

        # Wait stationary for 600ms
        page.wait_for_timeout(600)

        # Read RAF stats during stationary window
        raf_stats = page.evaluate("""
            () => {
                const lenisCalls = window.__rafCalls.filter(c => c.isLenisRaf);
                const isScrolling = window.__lenis ? window.__lenis.isScrolling : 'NO_LENIS';
                const isRunning = (window.__lenis && window.__lenis.animate) ? window.__lenis.animate.isRunning : 'NO_LENIS';
                return {
                    totalCalls: window.__rafCalls.length,
                    lenisCallsCount: lenisCalls.length,
                    isScrolling: isScrolling,
                    isRunning: isRunning
                };
            }
        """)

        # If loop was continuously spinning at 60Hz-120Hz, lenisCallsCount would be ~36-72.
        # Under adaptive scheduler, it MUST be 0!
        assert raf_stats["lenisCallsCount"] == 0, (
            f"FAIL: RAF loop did NOT sleep when page was stationary! "
            f"Observed {raf_stats['lenisCallsCount']} Lenis RAF calls during 600ms stationary period. "
            f"isScrolling={raf_stats['isScrolling']}, isRunning={raf_stats['isRunning']}"
        )
        assert not raf_stats["isScrolling"], f"Expected isScrolling to be false, got {raf_stats['isScrolling']}"
        assert not raf_stats["isRunning"], f"Expected animate.isRunning to be false, got {raf_stats['isRunning']}"

    def test_raf_awakens_immediately_on_wheel_event(self, instrumented_page, base_url):
        """
        Empirically verify that dispatching a wheel event immediately awakens
        the sleeping RAF loop and executes interpolation frames.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Verify loop is asleep
        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(400)
        asleep_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert asleep_calls == 0, "Loop was not asleep before wheel test"

        # Dispatch wheel event on window
        page.evaluate("""
            () => {
                window.__rafCalls = [];
                const wheelEvt = new WheelEvent('wheel', {
                    deltaY: 150,
                    deltaMode: 0,
                    bubbles: true,
                    cancelable: true
                });
                window.dispatchEvent(wheelEvt);
            }
        """)

        # Wait 100ms for RAF wake and frame processing
        page.wait_for_timeout(100)

        awake_stats = page.evaluate("""
            () => {
                const lenisCalls = window.__rafCalls.filter(c => c.isLenisRaf);
                return {
                    lenisCallsCount: lenisCalls.length,
                    firstCallDeltaMs: lenisCalls.length > 0 ? (lenisCalls[0].time - performance.now()) : null
                };
            }
        """)

        assert awake_stats["lenisCallsCount"] > 0, (
            "FAIL: RAF loop failed to awaken upon wheel event dispatch! "
            f"Lenis RAF calls: {awake_stats['lenisCallsCount']}"
        )

        # Allow wheel momentum to settle (1.2s) and confirm return to sleep
        page.wait_for_timeout(1200)
        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(500)
        settled_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert settled_calls == 0, (
            f"FAIL: RAF loop failed to return to sleep after wheel scroll settled! "
            f"Observed {settled_calls} calls during stationary window."
        )

    def test_raf_awakens_immediately_on_touchstart_event(self, instrumented_page, base_url):
        """
        Empirically verify that dispatching a touchstart event immediately awakens
        the sleeping RAF loop.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Clear RAF buffer
        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(400)
        assert page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length") == 0

        # Dispatch touchstart event
        page.evaluate("""
            () => {
                window.__rafCalls = [];
                const touchObj = new Touch({
                    identifier: 1,
                    target: document.body,
                    clientX: 200,
                    clientY: 300
                });
                const touchEvt = new TouchEvent('touchstart', {
                    touches: [touchObj],
                    targetTouches: [touchObj],
                    changedTouches: [touchObj],
                    bubbles: true,
                    cancelable: true
                });
                window.dispatchEvent(touchEvt);
            }
        """)

        page.wait_for_timeout(100)
        awake_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert awake_calls > 0, (
            f"FAIL: RAF loop failed to awaken upon touchstart event dispatch! "
            f"Lenis RAF calls: {awake_calls}"
        )

    def test_raf_awakens_and_sleeps_on_programmatic_scroll_to(self, instrumented_page, base_url):
        """
        Empirically verify that lenis.scrollTo() awakens RAF, runs animation frames,
        and sleeps when target is reached.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(300)
        assert page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length") == 0

        # Programmatic scrollTo 500px over 0.4s
        page.evaluate("""
            () => {
                window.__rafCalls = [];
                window.__lenis.scrollTo(500, { duration: 0.4 });
            }
        """)

        # Check immediate awakening
        page.wait_for_timeout(100)
        active_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert active_calls > 0, "lenis.scrollTo() failed to awaken RAF loop"

        # Wait for animation to finish and settle (total 1000ms)
        page.wait_for_timeout(1000)
        final_y = page.evaluate("() => Math.round(window.scrollY)")
        assert 490 <= final_y <= 510, f"Expected scrollY near 500, got {final_y}"

        # Confirm return to idle sleep
        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(500)
        sleeping_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert sleeping_calls == 0, (
            f"RAF loop failed to sleep after lenis.scrollTo() completed! Observed {sleeping_calls} calls."
        )

    # =========================================================================
    # CRITERION 2: Anchor Smooth Scroll Glide (1.0s vs 40ms Snap)
    # =========================================================================

    def test_anchor_pricing_smooth_scroll_trajectory(self, instrumented_page, base_url):
        """
        Empirically measure scroll trajectory when #pricing anchor is clicked.
        Confirm smooth 1.0s glide rather than 40ms snap.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        # Initial scroll should be 0
        assert page.evaluate("() => window.scrollY") == 0

        # Start sampling trajectory at 25ms intervals
        page.evaluate("() => window.__startTrajectoryRecording(25)")

        # Programmatically click #pricing anchor via DOM click
        pricing_anchor = page.locator("header nav a[href='#pricing']").first
        assert pricing_anchor.is_visible()
        pricing_anchor.click()

        # Allow trajectory to record across the 1.4s window
        page.wait_for_timeout(1400)

        # Stop and retrieve samples
        samples = page.evaluate("() => window.__stopTrajectoryRecording()")

        # Empirical analysis of trajectory
        # 1. Start position: samples[0] scrollY should be near 0
        start_y = samples[0]["scrollY"]
        assert start_y == 0, f"Initial trajectory scroll was {start_y}, expected 0"

        # 2. Final position: should be target position (>5000px)
        final_y = samples[-1]["scrollY"]
        assert final_y > 5000, f"Expected final scrollY > 5000, got {final_y}"

        # 3. Check snap vs glide:
        # If it was a 40ms snap, at t=100ms the scroll would already be >= 95% of target!
        sample_at_100ms = next((s for s in samples if s["t"] >= 100), None)
        assert sample_at_100ms is not None
        pct_at_100ms = sample_at_100ms["scrollY"] / final_y
        assert pct_at_100ms < 0.80, (
            f"FAIL: Scroll snapped too quickly! At t={sample_at_100ms['t']}ms, "
            f"scrollY was already {pct_at_100ms:.1%} of final destination. (Indicates 40ms snap)"
        )

        # 4. Check smooth progression across intermediate timestamps
        sample_at_300ms = next((s for s in samples if s["t"] >= 300), None)
        sample_at_600ms = next((s for s in samples if s["t"] >= 600), None)
        assert sample_at_300ms is not None and sample_at_600ms is not None
        assert sample_at_100ms["scrollY"] < sample_at_300ms["scrollY"] < sample_at_600ms["scrollY"] <= final_y, (
            f"Trajectory not monotonically increasing: "
            f"100ms: {sample_at_100ms['scrollY']}, 300ms: {sample_at_300ms['scrollY']}, "
            f"600ms: {sample_at_600ms['scrollY']}, final: {final_y}"
        )

        # 5. Measure settling time (when scroll reaches 98% of final value)
        settled_sample = next((s for s in samples if s["scrollY"] >= 0.98 * final_y), None)
        assert settled_sample is not None
        settling_time_ms = settled_sample["t"]
        assert 700 <= settling_time_ms <= 1300, (
            f"FAIL: Settling time {settling_time_ms}ms outside expected 1.0s window [700ms, 1300ms]! "
            f"(40ms snap would be <100ms; overly sluggish would be >1300ms)"
        )

        # 6. Verify distinct intermediate positions count (smooth gradation)
        distinct_positions = len(set(s["scrollY"] for s in samples))
        assert distinct_positions >= 20, (
            f"Expected smooth gradation with >= 20 distinct positions, got {distinct_positions}"
        )

    def test_anchor_faq_smooth_scroll_trajectory(self, instrumented_page, base_url):
        """
        Empirically measure scroll trajectory when #faq anchor is clicked.
        Confirm smooth 1.0s glide rather than 40ms snap.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        # Start sampling trajectory at 25ms intervals
        page.evaluate("() => window.__startTrajectoryRecording(25)")

        # Click #faq anchor
        faq_anchor = page.locator("header nav a[href='#faq']").first
        assert faq_anchor.is_visible()
        faq_anchor.click()

        # Allow trajectory to record across the 1.4s window
        page.wait_for_timeout(1400)

        # Stop and retrieve samples
        samples = page.evaluate("() => window.__stopTrajectoryRecording()")

        start_y = samples[0]["scrollY"]
        final_y = samples[-1]["scrollY"]
        assert start_y == 0
        assert final_y > 6000, f"Expected final scrollY for FAQ > 6000, got {final_y}"

        # Verify not snapped at 100ms
        sample_at_100ms = next((s for s in samples if s["t"] >= 100), None)
        pct_at_100ms = sample_at_100ms["scrollY"] / final_y
        assert pct_at_100ms < 0.80, f"FAQ snapped too quickly at 100ms: {pct_at_100ms:.1%}"

        # Settling time in 1.0s range
        settled_sample = next((s for s in samples if s["scrollY"] >= 0.98 * final_y), None)
        assert settled_sample is not None
        assert 700 <= settled_sample["t"] <= 1300, (
            f"FAQ settling time {settled_sample['t']}ms outside expected 1.0s range"
        )

    # =========================================================================
    # CRITERION 3: Passive Touch Event Verification via CDP
    # =========================================================================

    def test_passive_touch_listeners_via_cdp(self, instrumented_page, base_url):
        """
        Query registered event listeners on window using Chrome DevTools Protocol (CDP).
        Empirically verify that touchstart, touchmove, and touchend are registered with passive: true.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        cdp = page.context.new_cdp_session(page)

        # Evaluate window object to get its RemoteObjectId
        eval_res = cdp.send("Runtime.evaluate", {"expression": "window", "returnByValue": False})
        window_obj_id = eval_res["result"]["objectId"]

        # Get all registered event listeners on window
        listeners_res = cdp.send("DOMDebugger.getEventListeners", {"objectId": window_obj_id})
        listeners = listeners_res.get("listeners", [])

        # Filter for touch events
        touch_listeners = [
            l for l in listeners
            if l.get("type") in ("touchstart", "touchmove", "touchend")
        ]

        assert len(touch_listeners) > 0, "No touch event listeners found on window object"

        non_passive_touch = [
            l for l in touch_listeners
            if l.get("passive") is not True
        ]

        assert len(non_passive_touch) == 0, (
            f"FAIL: Found {len(non_passive_touch)} non-passive touch listeners on window: {non_passive_touch}"
        )

        # Specific audit: verify at least one touchstart and one touchmove are registered with passive: true
        has_passive_touchstart = any(l.get("type") == "touchstart" and l.get("passive") is True for l in touch_listeners)
        has_passive_touchmove = any(l.get("type") == "touchmove" and l.get("passive") is True for l in touch_listeners)

        assert has_passive_touchstart, "Expected at least one passive touchstart listener"
        assert has_passive_touchmove, "Expected at least one passive touchmove listener"

    # =========================================================================
    # CRITERION 4: Zero Console Errors / Violations During Mobile Touch Simulation
    # =========================================================================

    def test_mobile_touch_simulation_zero_violations_and_errors(self, browser_instance, base_url):
        """
        Simulate mobile touch interactions in a genuine mobile viewport with touch enabled.
        Empirically verify zero [Violation] Added non-passive event listener warnings
        and zero console errors.
        """
        # Create mobile touch context
        context = browser_instance.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        # Fulfill analytics mock
        page.route("**/clarity.ms/**", lambda route: route.fulfill(status=200, body="// mock", content_type="application/javascript"))
        page.route("**/googletagmanager.com/**", lambda route: route.fulfill(status=200, body="// mock", content_type="application/javascript"))

        console_violations = []
        console_errors = []
        page_errors = []

        page.on("console", lambda msg: (
            console_violations.append(msg.text)
            if ("violation" in msg.text.lower() or "passive" in msg.text.lower())
            else (console_errors.append(msg.text) if msg.type == "error" else None)
        ))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Simulate mobile touch gestures (touch tap, drag/swipe up and down)
        touch = page.touchscreen
        # Tap hero
        touch.tap(200, 300)
        page.wait_for_timeout(100)

        # Perform touch drag gestures to trigger touchmove and VirtualScroll
        for _ in range(3):
            # Swipe up (scroll down)
            page.mouse.move(200, 500)
            page.mouse.down()
            page.mouse.move(200, 200, steps=10)
            page.mouse.up()
            page.wait_for_timeout(150)

        # Verify no violations
        non_passive_violations = [
            v for v in console_violations
            if "non-passive" in v.lower() or "scroll-blocking" in v.lower()
        ]

        assert len(non_passive_violations) == 0, (
            f"FAIL: Chrome emitted non-passive touch listener violations during mobile simulation: {non_passive_violations}"
        )
        assert len(console_errors) == 0, f"Console errors observed: {console_errors}"
        assert len(page_errors) == 0, f"Unhandled page errors: {page_errors}"

        context.close()

    # =========================================================================
    # CRITERION 5: Stress & Adversarial Hardening
    # =========================================================================

    def test_root_class_thrashing_eliminated(self, instrumented_page, base_url):
        """
        Adversarial Test: Monitor documentElement attribute mutations during scrolling.
        Verify that documentElement.className is NOT repeatedly mutated on every scroll frame.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Attach MutationObserver to document.documentElement watching attribute 'class'
        page.evaluate("""
            () => {
                window.__classMutationCount = 0;
                const observer = new MutationObserver(mutations => {
                    for (const m of mutations) {
                        if (m.attributeName === 'class') {
                            window.__classMutationCount++;
                        }
                    }
                });
                observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
            }
        """)

        # Execute 5 programmatic scroll operations with momentum
        for i in range(1, 6):
            page.evaluate(f"() => window.__lenis.scrollTo({i * 600}, {{ duration: 0.2 }})")
            page.wait_for_timeout(250)

        mutation_count = page.evaluate("() => window.__classMutationCount")

        # Under the old code, updateClassName() ran regex replace and re-assigned className on every tick (~100+ times).
        # Under the patched code with classList.contains guard, mutations during active scroll should be 0!
        assert mutation_count == 0, (
            f"FAIL: Class thrashing detected! documentElement.className was mutated {mutation_count} times "
            f"during active scroll transitions."
        )

    def test_rapid_anchor_interruptions_stress(self, instrumented_page, base_url):
        """
        Stress Test: Rapidly click alternating anchors (#pricing -> #faq -> #pricing)
        at high frequency (30ms intervals) to verify RAF scheduler and Lenis handle
        animation cancellations gracefully without exceptions or permanently frozen RAF loop.
        """
        page = instrumented_page
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        pricing = page.locator("header nav a[href='#pricing']").first
        faq = page.locator("header nav a[href='#faq']").first

        for _ in range(8):
            pricing.click()
            page.wait_for_timeout(30)
            faq.click()
            page.wait_for_timeout(30)

        # Allow animation to settle
        page.wait_for_timeout(1500)

        # Verify page is still responsive
        final_y = page.evaluate("() => window.scrollY")
        assert final_y > 0, "Page should have scrolled"

        # Verify RAF returns to sleep after rapid interruptions
        page.evaluate("() => { window.__rafCalls = []; }")
        page.wait_for_timeout(500)
        settled_calls = page.evaluate("() => window.__rafCalls.filter(c => c.isLenisRaf).length")
        assert settled_calls == 0, (
            f"RAF loop failed to return to sleep after rapid interruptions! Calls: {settled_calls}"
        )
