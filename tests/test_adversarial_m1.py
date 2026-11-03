import pytest
import time
from tests.conftest import check_no_horizontal_overflow

PROBED_VIEWPORTS = [
    (280, 653, "Galaxy Z Fold / Extreme Compact Outer"),
    (320, 568, "iPhone SE 1st Gen / Minimum Mobile"),
    (340, 700, "Odd Compact Mobile"),
    (360, 640, "Compact Android Standard"),
    (375, 667, "iPhone 6/7/8/SE2"),
    (390, 844, "iPhone 12/13/14"),
    (400, 800, "Mid-range Android"),
    (412, 915, "Samsung Galaxy S20+ / Pixel 7"),
    (428, 926, "iPhone 13/14 Pro Max"),
    (540, 720, "Surface Duo Single Screen"),
    (600, 960, "7-inch Small Tablet"),
    (768, 1024, "iPad Portrait / Standard Tablet"),
    (820, 1180, "iPad Air Portrait"),
    (912, 1368, "Surface Pro Portrait"),
    (1024, 768, "iPad Landscape / Small Desktop"),
    (1280, 800, "13-inch Laptop / WXGA"),
    (1440, 900, "Desktop / WXGA+"),
    (1920, 1080, "Full HD Desktop Widescreen"),
]

DYNAMIC_RESIZE_SEQUENCE = [
    (1920, 1080),
    (1440, 900),
    (1280, 800),
    (1024, 768),
    (912, 1368),
    (820, 1180),
    (768, 1024),
    (600, 960),
    (540, 720),
    (428, 926),
    (412, 915),
    (400, 800),
    (390, 844),
    (375, 667),
    (360, 640),
    (340, 700),
    (320, 568),
    (280, 653),
    (320, 568),
    (768, 1024),
    (1280, 800),
    (1920, 1080),
]


class TestAdversarialM1Viewports:
    """
    Adversarial Empirical Challenge Suite for Milestone 1.
    Evaluates 18 viewports, horizontal overflow, text clipping, element collision,
    dynamic resize reflow, and console stability.
    """

    @pytest.mark.parametrize("width,height,label", PROBED_VIEWPORTS)
    def test_horizontal_overflow_across_all_18_viewports(self, page, base_url, width, height, label):
        """Probes every specified viewport for horizontal overflow."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        passes, scroll_width, client_width = check_no_horizontal_overflow(page)
        
        overflow_elements = []
        if not passes:
            overflow_elements = page.evaluate("""
                () => {
                    const docWidth = document.documentElement.clientWidth;
                    const offending = [];
                    document.querySelectorAll('*').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.right > docWidth + 1 || rect.left < -1) {
                            offending.push({
                                tag: el.tagName,
                                id: el.id,
                                class: (el.className || '').toString().slice(0, 60),
                                right: Math.round(rect.right),
                                width: Math.round(rect.width),
                                docWidth: docWidth
                            });
                        }
                    });
                    return offending.slice(0, 5);
                }
            """)

        assert passes, (
            f"Horizontal overflow at {label} ({width}x{height}): "
            f"scrollWidth={scroll_width}px > clientWidth={client_width}px. "
            f"Offenders: {overflow_elements}"
        )

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "Galaxy Z Fold (280px)"),
        (320, 568, "iPhone SE (320px)"),
        (375, 667, "iPhone 8 (375px)"),
        (768, 1024, "iPad Portrait (768px)"),
        (1440, 900, "Desktop (1440px)"),
    ])
    def test_text_clipping_and_wrapping_adversarial(self, page, base_url, width, height, label):
        """Verifies headings and text elements wrap cleanly without clipping or container breach."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        clipping_issues = page.evaluate("""
            () => {
                const results = [];
                const headings = Array.from(document.querySelectorAll('h1, h2, h3, .proof-tab-btn, button, nav a'));
                const docWidth = document.documentElement.clientWidth;
                
                for (const el of headings) {
                    const rect = el.getBoundingClientRect();
                    // Check if element box extends beyond document width
                    if (rect.right > docWidth + 1.5) {
                        results.push({
                            type: 'overflows_viewport',
                            tag: el.tagName,
                            text: (el.innerText || '').slice(0, 30),
                            rect_right: Math.round(rect.right),
                            docWidth: docWidth
                        });
                    }
                    // Check if element has unhandled horizontal scroll inside itself
                    if (el.scrollWidth > el.clientWidth + 2 && window.getComputedStyle(el).overflowX !== 'visible') {
                        // Exclude intentional scrollable containers if any
                        results.push({
                            type: 'internal_text_clip',
                            tag: el.tagName,
                            text: (el.innerText || '').slice(0, 30),
                            scrollWidth: el.scrollWidth,
                            clientWidth: el.clientWidth
                        });
                    }
                }
                return results;
            }
        """)

        assert len(clipping_issues) == 0, f"Text clipping/breach detected at {label}: {clipping_issues}"

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "Galaxy Z Fold (280px)"),
        (320, 568, "iPhone SE (320px)"),
        (375, 667, "iPhone 8 (375px)"),
        (768, 1024, "iPad (768px)"),
        (1280, 800, "Desktop (1280px)"),
    ])
    def test_element_geometry_and_no_unwanted_overlap(self, page, base_url, width, height, label):
        """Verifies no destructive element overlaps between critical layout components."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        overlaps = page.evaluate("""
            () => {
                const issues = [];
                // Check Growth Engine cards vertical sequence (they shouldn't overlap vertically on mobile)
                const engineCards = document.querySelectorAll('#engine .bg-white.rounded-\\\\[20px\\\\]');
                if (engineCards.length >= 3) {
                    const rect0 = engineCards[0].getBoundingClientRect();
                    const rect1 = engineCards[1].getBoundingClientRect();
                    const rect2 = engineCards[2].getBoundingClientRect();
                    
                    // Card 1 and Card 2 vertical overlap
                    if (rect1.top < rect0.bottom - 5) {
                        issues.push({
                            pair: 'engine_card_0_1_overlap',
                            card0_bottom: rect0.bottom,
                            card1_top: rect1.top
                        });
                    }
                    // Card 2 and Card 3 vertical overlap
                    if (rect2.top < rect1.bottom - 5) {
                        issues.push({
                            pair: 'engine_card_1_2_overlap',
                            card1_bottom: rect1.bottom,
                            card2_top: rect2.top
                        });
                    }
                }
                return issues;
            }
        """)

        assert len(overlaps) == 0, f"Element overlap detected at {label}: {overlaps}"

    def test_section3_proof_tab_switcher_across_standard_and_extreme(self, page, base_url):
        """Tests Section 3 proof card tab switching at standard viewports (320px to 1440px)."""
        for w, h in [(320, 568), (375, 667), (768, 1024), (1024, 768), (1440, 900)]:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            # Check initial state: Google tab selected
            tab_google = page.locator("#tabGoogleProof")
            tab_reddit = page.locator("#tabRedditProof")
            panel_google = page.locator("#panelGoogleProof")
            panel_reddit = page.locator("#panelRedditProof")

            assert tab_google.is_visible()
            assert tab_reddit.is_visible()
            assert panel_google.is_visible()
            assert not panel_reddit.is_visible()

            # Click Reddit tab
            tab_reddit.click()
            time.sleep(0.1)
            assert not panel_google.is_visible()
            assert panel_reddit.is_visible()
            assert tab_reddit.get_attribute("aria-selected") == "true"

            # Check bounds of proof card
            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow triggered after clicking Reddit tab at {w}px: {sw} > {cw}"

            # Click Google tab back
            tab_google.click()
            time.sleep(0.1)
            assert panel_google.is_visible()
            assert not panel_reddit.is_visible()
            assert tab_google.get_attribute("aria-selected") == "true"

    def test_m1_components_fit_within_280px(self, page, base_url):
        """
        Adversarial evaluation of M1 components specifically at 280px extreme viewport.
        Verifies Hero H1, Section 3 H2, Growth Engine cards, and Proof panel do not exceed 280px.
        """
        page.set_viewport_size({"width": 280, "height": 653})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        h1_box = page.locator("h1").first.bounding_box()
        assert h1_box["width"] <= 280, f"Hero H1 overflows 280px: {h1_box['width']}px"

        s3_h2 = page.locator("section#framework h2").first.bounding_box()
        assert s3_h2["width"] <= 280, f"Section 3 H2 overflows 280px: {s3_h2['width']}px"

        proof_panel = page.locator("#panelGoogleProof").bounding_box()
        assert proof_panel["width"] <= 280, f"Proof panel overflows 280px: {proof_panel['width']}px"

        engine_section = page.locator("#engine").bounding_box()
        assert engine_section["width"] <= 280, f"Engine section overflows 280px: {engine_section['width']}px"

    def test_dynamic_resize_standard_range_stress(self, page, base_url):
        """
        Adversarially resizes the page through all 17 standard viewports (1920 down to 320 and back)
        without reloading to test CSS reflow and dynamic layout stability.
        """
        standard_sequence = [v for v in DYNAMIC_RESIZE_SEQUENCE if v[0] >= 320]
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        resize_failures = []
        for width, height in standard_sequence:
            page.set_viewport_size({"width": width, "height": height})
            time.sleep(0.04)
            passes, sw, cw = check_no_horizontal_overflow(page)
            if not passes:
                resize_failures.append({
                    "width": width,
                    "height": height,
                    "scrollWidth": sw,
                    "clientWidth": cw,
                    "delta": sw - cw
                })

        assert len(resize_failures) == 0, f"Dynamic resize standard range failures: {resize_failures}"

    def test_dynamic_resize_rapid_oscillation_stress(self, page, base_url):
        """
        Adversarially oscillates viewport rapidly between 320px and 1280px (10 cycles)
        to stress responsive recalculation and detect reflow memory/DOM lockups.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        for i in range(10):
            # Compact mobile
            page.set_viewport_size({"width": 320, "height": 568})
            time.sleep(0.03)
            passes_mobile, sw_m, cw_m = check_no_horizontal_overflow(page)
            assert passes_mobile, f"Oscillation cycle {i+1} failed at 320px: sw={sw_m}, cw={cw_m}"

            # Desktop
            page.set_viewport_size({"width": 1280, "height": 800})
            time.sleep(0.03)
            passes_desk, sw_d, cw_d = check_no_horizontal_overflow(page)
            assert passes_desk, f"Oscillation cycle {i+1} failed at 1280px: sw={sw_d}, cw={cw_d}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html", "404.html"])
    def test_subpages_extreme_viewport_responsiveness(self, page, base_url, subpage):
        """Verifies legal and error subpages at extreme 280px and 1920px viewports."""
        for width, height in [(280, 653), (320, 568), (1920, 1080)]:
            page.set_viewport_size({"width": width, "height": height})
            page.goto(f"{base_url}/{subpage}")
            page.wait_for_load_state("networkidle")

            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Subpage {subpage} overflowed at {width}px: scrollWidth={sw} > clientWidth={cw}"
