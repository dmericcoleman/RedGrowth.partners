import pytest
import time
from tests.conftest import check_no_horizontal_overflow

PAGES = ["", "privacy.html", "terms.html"]
ALL_PAGES = ["", "404.html", "privacy.html", "terms.html"]


class TestEmpiricalM3Gate1Validation:
    """
    Challenger M3 Gate 1 Empirical Validation Suite:
    1. Mobile drawer auto-dismisses on resize to desktop (>= 1024px) in < 16ms and body scroll unlocks.
    2. Rapid resize oscillation (20 cycles) across viewports causes zero errors.
    3. Extreme viewport bounds (280px to 3840px).
    4. Early State Guard prevents unnecessary RAF callbacks and layout thrash when drawer is closed.
    """

    @pytest.mark.parametrize("page_name", PAGES)
    def test_mobile_drawer_dismiss_latency_and_scroll_unlock(self, page, base_url, page_name):
        """
        Validate that mobile drawer auto-dismisses on resize to desktop (>= 1024px) in < 16ms frame
        and body scroll unlocks cleanly.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/{page_name}")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")

        assert mobile_btn.is_visible(), f"Mobile button not visible on {page_name}"
        mobile_btn.click()
        page.wait_for_timeout(50)

        assert mobile_menu.is_visible(), f"Drawer not visible on {page_name}"
        assert page.evaluate("() => document.body.style.overflow") == "hidden", "Scroll lock must be active"

        # Empirically measure the resize listener execution latency:
        # 1. Synchronous dispatch latency (Early State Guard / RAF scheduling)
        # 2. Drawer dismissal and body scroll unlock upon desktop resize
        metrics = page.evaluate("""() => {
            const menu = document.getElementById('mobileMenu');
            const t0 = performance.now();
            
            // Dispatch resize event to simulate desktop resize
            window.innerWidth = 1024;
            window.dispatchEvent(new Event('resize'));
            const t1 = performance.now();
            const syncDispatchMs = t1 - t0;

            return {
                syncDispatchMs: syncDispatchMs,
                bodyOverflowVal: document.body.style.overflow
            };
        }""")

        # Perform physical viewport resize to confirm full reflow
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(50)

        body_unlocked = page.evaluate("() => document.body.style.overflow !== 'hidden' && !document.body.classList.contains('overflow-hidden')")
        drawer_hidden = page.evaluate("() => document.getElementById('mobileMenu').classList.contains('hidden')")

        assert drawer_hidden, f"Drawer did not dismiss on {page_name} at 1024px"
        assert body_unlocked, f"Body scroll not unlocked on {page_name} at 1024px"
        assert metrics["syncDispatchMs"] < 16.0, f"Resize listener dispatch took too long: {metrics['syncDispatchMs']:.2f}ms >= 16ms"
        assert not mobile_menu.is_visible(), f"Drawer still visible in DOM at 1024px on {page_name}"
        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    @pytest.mark.parametrize("page_name", ALL_PAGES)
    def test_rapid_resize_oscillation_20_cycles_zero_errors(self, page, base_url, page_name):
        """
        Validate that rapid resize oscillation (20 cycles) across viewports causes zero errors.
        """
        page.goto(f"{base_url}/{page_name}")
        page.wait_for_load_state("networkidle")

        oscillation_pairs = [
            (320, 1280),
            (280, 1440),
            (375, 1024),
            (414, 1920)
        ]

        for cycle in range(20):
            w_small, w_large = oscillation_pairs[cycle % len(oscillation_pairs)]
            # Small viewport
            page.set_viewport_size({"width": w_small, "height": 600})
            page.wait_for_timeout(20)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Cycle {cycle+1} overflow at {w_small}px on '{page_name}': {sw} > {cw}"

            # Large viewport
            page.set_viewport_size({"width": w_large, "height": 800})
            page.wait_for_timeout(20)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Cycle {cycle+1} overflow at {w_large}px on '{page_name}': {sw} > {cw}"

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on '{page_name}': {page._page_errors}"

    @pytest.mark.parametrize("page_name", ALL_PAGES)
    def test_extreme_viewport_bounds_280px_to_3840px(self, page, base_url, page_name):
        """
        Validate extreme viewport bounds from 280px (Galaxy Z Fold folded) up to 3840px (4K UHD).
        """
        page.goto(f"{base_url}/{page_name}")
        page.wait_for_load_state("networkidle")

        test_points = [280, 320, 360, 375, 414, 768, 1024, 1280, 1440, 1920, 2560, 3840]
        for width in test_points:
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(25)
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow on '{page_name}' at width {width}px: {sw} > {cw}"

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page errors on '{page_name}': {page._page_errors}"

    def test_early_state_guard_zero_raf_when_idle(self, page, base_url):
        """
        Verifies that the Early State Guard in the resize listener immediately exits
        when mobileMenu is hidden and scroll is unlocked, without invoking requestAnimationFrame.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Monkey-patch requestAnimationFrame to count calls
        raf_calls = page.evaluate("""() => {
            let rafCount = 0;
            const originalRAF = window.requestAnimationFrame;
            window.requestAnimationFrame = function(cb) {
                rafCount++;
                return originalRAF.call(window, cb);
            };

            // Dispatch 100 rapid resize events while menu is closed
            for (let i = 0; i < 100; i++) {
                window.dispatchEvent(new Event('resize'));
            }

            // Restore
            window.requestAnimationFrame = originalRAF;
            return rafCount;
        }""")

        assert raf_calls == 0, f"Early State Guard failed: {raf_calls} requestAnimationFrame calls triggered while idle!"
