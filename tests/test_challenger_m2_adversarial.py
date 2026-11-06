import pytest
from tests.conftest import check_no_horizontal_overflow

PROBED_VIEWPORTS = [
    (280, 653, "Galaxy Z Fold (280px)"),
    (320, 568, "iPhone SE (320px)"),
    (360, 640, "Compact Android (360px)"),
    (375, 667, "iPhone SE2/8 (375px)"),
    (390, 844, "iPhone 12/13/14 (390px)"),
    (414, 896, "iPhone XR/11 (414px)"),
    (768, 1024, "iPad Portrait (768px)"),
    (1024, 768, "iPad Landscape (1024px)"),
    (1280, 800, "13-inch Laptop (1280px)"),
    (1440, 900, "Desktop Widescreen (1440px)"),
    (1920, 1080, "Full HD Desktop (1920px)"),
    (2560, 1440, "2K QHD Display (2560px)"),
    (3840, 2160, "4K UHD Display (3840px)"),
]

PAGES = ["/", "/privacy.html", "/terms.html", "/404.html"]
CONTAINMENT_VIEWPORTS = [
    (280, 653, "280px"),
    (320, 568, "320px"),
    (375, 667, "375px"),
    (768, 1024, "768px"),
    (1024, 768, "1024px"),
    (1440, 900, "1440px"),
]


class TestChallengerMilestone2Audit:
    """
    Adversarial verification harness created by challenger_gen2_m2_1:
    - Exhaustive 13-viewport cross-product on ALL 4 pages.
    - Deep element overflow detection (DOM scan).
    - Sticky header containment and scroll persistence on all 4 pages.
    - Legal card containment across 6 key viewports.
    - 404 card containment and button scaling.
    - Zero console errors or uncaught exceptions.
    """

    @pytest.mark.parametrize("page_path", PAGES)
    @pytest.mark.parametrize("width,height,label", PROBED_VIEWPORTS)
    def test_all_pages_13_viewports_no_horizontal_overflow(self, page, base_url, page_path, width, height, label):
        """Verify zero horizontal overflow (scrollWidth <= clientWidth) across all 4 pages and 13 viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        passes, scroll_width, client_width = check_no_horizontal_overflow(page)
        assert passes, (
            f"Horizontal overflow detected on {page_path} at {label} ({width}x{height}): "
            f"scrollWidth={scroll_width}px > clientWidth={client_width}px (Delta: +{scroll_width - client_width}px)"
        )

    @pytest.mark.parametrize("page_path", PAGES)
    @pytest.mark.parametrize("width,height,label", [(280, 653, "280px"), (320, 568, "320px"), (375, 667, "375px")])
    def test_all_pages_deep_element_overflow_scan(self, page, base_url, page_path, width, height, label):
        """Deep DOM scan on all pages at mobile viewports to ensure no unclipped element extends outside viewport."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        offenders = page.evaluate("""() => {
            const cw = document.documentElement.clientWidth;
            const res = [];
            document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.right > cw + 1 || r.left < -1) {
                    const s = window.getComputedStyle(el);
                    if (s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && r.width > 0 && r.height > 0) {
                        let parent = el.parentElement;
                        let isClipped = false;
                        while (parent && parent !== document.body && parent !== document.documentElement) {
                            const ps = window.getComputedStyle(parent);
                            if (['hidden', 'auto', 'scroll'].includes(ps.overflowX) || ['hidden', 'auto', 'scroll'].includes(ps.overflow)) {
                                isClipped = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        if (!isClipped) {
                            res.push({
                                tag: el.tagName,
                                id: el.id,
                                className: (typeof el.className === 'string') ? el.className.slice(0, 60) : '',
                                left: Math.round(r.left),
                                right: Math.round(r.right),
                                width: Math.round(r.width)
                            });
                        }
                    }
                }
            });
            return res;
        }""")
        assert len(offenders) == 0, f"Found unclipped overflowing elements on {page_path} at {label}: {offenders}"

    @pytest.mark.parametrize("page_path", PAGES)
    @pytest.mark.parametrize("width,height,label", [(280, 653, "280px"), (375, 667, "375px"), (1024, 768, "1024px"), (1440, 900, "1440px")])
    def test_sticky_header_containment_and_scroll_persistence(self, page, base_url, page_path, width, height, label):
        """Check sticky headers on all pages: visibility, width within clientWidth, and persistence on scroll."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        header = page.locator("header")
        assert header.is_visible(), f"Header not visible on {page_path} at {label}"

        box = header.bounding_box()
        assert box is not None
        assert box["x"] >= -1, f"Header left edge offscreen on {page_path} at {label}"
        assert box["x"] + box["width"] <= width + 2, f"Header right edge exceeds viewport on {page_path} at {label}"

        # Scroll down and check persistence
        page.evaluate("() => window.scrollTo(0, 400)")
        page.wait_for_timeout(50)

        box_scrolled = header.bounding_box()
        assert box_scrolled is not None
        assert box_scrolled["y"] <= 1, f"Header is not sticky at top after scrolling on {page_path} at {label}: y={box_scrolled['y']}"

    @pytest.mark.parametrize("page_path", ["/privacy.html", "/terms.html"])
    @pytest.mark.parametrize("width,height,label", CONTAINMENT_VIEWPORTS)
    def test_legal_card_containment(self, page, base_url, page_path, width, height, label):
        """Check legal page main card containment on 280px, 320px, 375px, 768px, 1024px, 1440px."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        card = page.locator("main .rounded-2xl").first
        assert card.is_visible(), f"Main content card not visible on {page_path} at {label}"

        box = card.bounding_box()
        assert box is not None
        assert box["x"] >= 0, f"Card left edge ({box['x']}px) is offscreen on {page_path} at {label}"
        assert box["x"] + box["width"] <= width + 1, (
            f"Card right edge ({box['x'] + box['width']}px) exceeds viewport width ({width}px) on {page_path} at {label}"
        )

        # Check heading containment
        h1 = card.locator("h1").first
        assert h1.is_visible()
        h1_box = h1.bounding_box()
        assert h1_box["x"] >= box["x"] and h1_box["x"] + h1_box["width"] <= box["x"] + box["width"] + 1

    @pytest.mark.parametrize("width,height,label", CONTAINMENT_VIEWPORTS)
    def test_404_card_and_button_scaling(self, page, base_url, width, height, label):
        """Check 404 card containment and button scaling across viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/404.html")
        page.wait_for_load_state("networkidle")

        card = page.locator("main .rounded-2xl").first
        assert card.is_visible(), f"404 card not visible at {label}"

        box = card.bounding_box()
        assert box is not None
        assert box["x"] >= 0, f"404 card left edge ({box['x']}px) offscreen at {label}"
        assert box["x"] + box["width"] <= width + 1, f"404 card right edge exceeds viewport width at {label}"

        # Check buttons inside 404 card
        buttons = card.locator("a")
        assert buttons.count() >= 2, f"Expected at least 2 CTA links on 404 card, found {buttons.count()}"

        for i in range(buttons.count()):
            btn = buttons.nth(i)
            assert btn.is_visible()
            bbox = btn.bounding_box()
            assert bbox["x"] >= box["x"] - 1, f"Button {i} overflows card left on 404 at {label}"
            assert bbox["x"] + bbox["width"] <= box["x"] + box["width"] + 1, (
                f"Button {i} overflows card right on 404 at {label}"
            )
            # Ensure button is comfortably tall enough to be clickable
            assert bbox["height"] >= 36, f"Button {i} height ({bbox['height']}px) too small at {label}"

    @pytest.mark.parametrize("page_path", PAGES)
    def test_zero_console_errors_and_exceptions(self, page, base_url, page_path):
        """Confirm zero console errors or unhandled exceptions across all test runs."""
        console_errors = []
        page_errors = []

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        response = page.goto(f"{base_url}{page_path}")
        assert response.status == 200
        page.wait_for_load_state("networkidle")

        assert len(page_errors) == 0, f"Page errors on {page_path}: {page_errors}"
        assert len(console_errors) == 0, f"Console errors on {page_path}: {console_errors}"
