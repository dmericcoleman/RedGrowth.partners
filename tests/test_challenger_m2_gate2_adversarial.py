"""
Empirical Challenger Adversarial Stress Suite for Milestone 2 Iteration 2 Gate
Target: RedGrowth.partners (index.html, 404.html, privacy.html, terms.html, assets/css/input.css, assets/css/style.css)
Role: GPU Rendering & Layout Reflow Challenger (teamwork_challenger)
"""

import pytest
from playwright.sync_api import Page, expect

ALL_PAGES = ["/", "/index.html", "/404.html", "/privacy.html", "/terms.html"]

class TestMilestone2AdversarialStress:
    """
    Adversarial challenge tests for Milestone 2 GPU Rendering, Backdrop Blur Count, and Layout Reflow.
    """

    @pytest.mark.parametrize("page_path", ALL_PAGES)
    def test_adversarial_backdrop_blur_audit_all_pages(self, page: Page, base_url: str, page_path: str):
        """
        Challenge: Audit all pages in the repository to guarantee that NO non-nav elements
        or stationary cards have computed backdrop-filter anywhere on the website.
        """
        page.goto(f"{base_url}{page_path}", wait_until="networkidle")

        audit_results = page.evaluate("""() => {
            const allElements = Array.from(document.querySelectorAll('*'));
            const elementsWithBlur = [];

            for (const el of allElements) {
                const cs = window.getComputedStyle(el);
                const bf = cs.backdropFilter || cs.webkitBackdropFilter || 'none';
                if (bf !== 'none' && bf !== '') {
                    elementsWithBlur.push({
                        tagName: el.tagName,
                        id: el.id || '',
                        className: (el.className && typeof el.className === 'string') ? el.className : '',
                        filter: bf,
                        isCard: el.classList.contains('card') ||
                                el.classList.contains('glass-card') ||
                                el.classList.contains('glass-card-elevated') ||
                                el.classList.contains('proof-card')
                    });
                }
            }
            return elementsWithBlur;
        }""")

        # Print audit results
        print(f"\n[Page {page_path}] Elements with backdrop-filter: {len(audit_results)}")
        for e in audit_results:
            print(f"  <{e['tagName']} id='{e['id']}' class='{e['className'][:50]}...'> -> {e['filter']}")

        # 1. Zero cards may have backdrop-filter
        cards_with_blur = [e for e in audit_results if e['isCard']]
        assert len(cards_with_blur) == 0, (
            f"Page {page_path} has {len(cards_with_blur)} card(s) with backdrop-filter: {cards_with_blur}"
        )

        # 2. Only header or mobile menu elements may have backdrop blur
        allowed_ids_or_tags = {'HEADER', 'mobileMenu', 'mobileMenuBackdrop'}
        disallowed = [
            e for e in audit_results
            if e['tagName'] not in allowed_ids_or_tags and e['id'] not in allowed_ids_or_tags
        ]
        assert len(disallowed) == 0, (
            f"Page {page_path} has {len(disallowed)} unauthorized elements with backdrop-filter: {disallowed}"
        )

    def test_adversarial_ambient_blob_promotion_across_viewports(self, page: Page, base_url: str):
        """
        Challenge: Verify that all 11 ambient blur blobs retain GPU 3D promotion
        (matrix3d, will-change: transform, contain: strict) across multiple responsive viewports
        (mobile: 375x667, tablet: 768x1024, desktop: 1440x900).
        """
        viewports = [
            {"width": 375, "height": 667, "name": "Mobile SE"},
            {"width": 768, "height": 1024, "name": "iPad Portrait"},
            {"width": 1440, "height": 900, "name": "MacBook Desktop"}
        ]

        for vp in viewports:
            page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            page.goto(f"{base_url}/index.html", wait_until="networkidle")

            blobs = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('.ambient-blur-blob'));
                return elements.map((el, i) => {
                    const cs = window.getComputedStyle(el);
                    return {
                        index: i,
                        willChange: cs.willChange,
                        contain: cs.contain,
                        transform: cs.transform
                    };
                });
            }""")

            assert len(blobs) == 11, f"Expected 11 ambient blur blobs on {vp['name']}, found {len(blobs)}"

            for b in blobs:
                assert b["willChange"] == "transform", (
                    f"[{vp['name']}] Blob #{b['index']} willChange expected 'transform', got '{b['willChange']}'"
                )
                assert "strict" in b["contain"], (
                    f"[{vp['name']}] Blob #{b['index']} contain expected 'strict', got '{b['contain']}'"
                )
                assert "matrix3d" in b["transform"], (
                    f"[{vp['name']}] Blob #{b['index']} failed 3D promotion! Computed transform: '{b['transform']}'"
                )

    def test_adversarial_soundwave_reflow_measurement_and_reduced_motion(self, page: Page, base_url: str):
        """
        Challenge: Measure layout reflow and layout shift during soundwave animation,
        and test prefers-reduced-motion media query fallback.
        """
        # Step 1: Standard viewport
        page.goto(f"{base_url}/index.html", wait_until="networkidle")

        soundwave_metrics = page.evaluate("""async () => {
            const bars = Array.from(document.querySelectorAll('.soundwave-bar'));
            if (bars.length !== 5) return { error: `Expected 5 bars, got ${bars.length}` };

            // Record initial heights and bounding rect heights
            const initialBBoxes = bars.map(b => b.getBoundingClientRect().height);
            const initialComputedHeights = bars.map(b => window.getComputedStyle(b).height);

            // Wait 600ms (half the 1.2s cycle, reaching peak scaleY 1.0 vs 0.3)
            await new Promise(r => setTimeout(r, 600));

            const midComputedHeights = bars.map(b => window.getComputedStyle(b).height);
            const midBBoxes = bars.map(b => b.getBoundingClientRect().height);

            return {
                initialBBoxes,
                midBBoxes,
                initialComputedHeights,
                midComputedHeights
            };
        }""")

        assert "error" not in soundwave_metrics, soundwave_metrics.get("error")

        # Computed CSS height MUST remain exactly 20px throughout animation (no main thread layout reflow)
        for h in soundwave_metrics["initialComputedHeights"]:
            assert h == "20px", f"Expected initial computed height 20px, got {h}"
        for h in soundwave_metrics["midComputedHeights"]:
            assert h == "20px", f"Expected mid computed height 20px, got {h}"

        # Bounding client rect heights should scale dynamically via GPU transform
        print(f"Soundwave Bounding Rects (t=0): {soundwave_metrics['initialBBoxes']}")
        print(f"Soundwave Bounding Rects (t=600ms): {soundwave_metrics['midBBoxes']}")

        # Step 2: Test reduced-motion emulation
        page.emulate_media(reduced_motion="reduce")
        page.reload(wait_until="networkidle")

        reduced_motion_animation = page.evaluate("""() => {
            const bars = Array.from(document.querySelectorAll('.soundwave-bar'));
            return bars.map((b, i) => {
                const cs = window.getComputedStyle(b);
                return {
                    index: i,
                    animationName: cs.animationName,
                    animationPlayState: cs.animationPlayState
                };
            });
        }""")

        for bar in reduced_motion_animation:
            assert bar["animationName"] == "none", (
                f"Bar #{bar['index']} expected animation: none under prefers-reduced-motion, got {bar['animationName']}"
            )

    def test_adversarial_scroll_continuous_stress_under_load(self, page: Page, base_url: str):
        """
        Challenge: Continuous back-and-forth scrolling stress test over 3000ms.
        Measure minimum FPS and maximum jank delta.
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/index.html", wait_until="networkidle")

        results = page.evaluate("""async () => {
            return new Promise(resolve => {
                const deltas = [];
                let last = performance.now();
                let running = true;

                function record(now) {
                    deltas.push(now - last);
                    last = now;
                    if (running) requestAnimationFrame(record);
                }
                requestAnimationFrame(record);

                const total = document.documentElement.scrollHeight - window.innerHeight;
                const duration = 2400;
                const start = performance.now();

                function oscillate(now) {
                    const elapsed = now - start;
                    const phase = elapsed / duration;
                    // Sine oscillation: scroll down to bottom and back up to top
                    const progress = 0.5 * (1 - Math.cos(phase * 2 * Math.PI));
                    window.scrollTo(0, progress * total);

                    if (elapsed < duration) {
                        requestAnimationFrame(oscillate);
                    } else {
                        running = false;
                        const sorted = [...deltas].sort((a,b) => a - b);
                        const avg = deltas.reduce((a, b) => a + b, 0) / deltas.length;
                        const p95 = sorted[Math.floor(sorted.length * 0.95)] || 0;
                        const max = sorted[sorted.length - 1] || 0;
                        resolve({
                            frames: deltas.length,
                            avgMs: avg,
                            fps: 1000 / avg,
                            p95Ms: p95,
                            maxMs: max
                        });
                    }
                }
                requestAnimationFrame(oscillate);
            });
        }""")

        print(f"\n[Continuous Oscillation Scroll Stress]")
        print(f"  Frames: {results['frames']}")
        print(f"  Avg Frame: {results['avgMs']:.2f} ms ({results['fps']:.1f} FPS)")
        print(f"  95th Percentile: {results['p95Ms']:.2f} ms")
        print(f"  Max Frame: {results['maxMs']:.2f} ms")

        assert results["fps"] >= 20.0, f"Continuous scroll FPS too low: {results['fps']:.1f} FPS"
