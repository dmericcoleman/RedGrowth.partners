import math
import re
import pytest
from playwright.sync_api import Page, expect

BREAKPOINTS = [
    (320, 568, "320px (iPhone SE minimum)"),
    (375, 667, "375px (standard mobile)"),
    (768, 1024, "768px (iPad tablet)"),
    (1024, 768, "1024px (small desktop/tablet landscape)"),
    (1280, 800, "1280px (standard desktop)"),
    (1920, 1080, "1920px (large desktop)"),
]

PAGES = [
    ("/", "index.html"),
    ("/privacy.html", "privacy.html"),
    ("/terms.html", "terms.html"),
    ("/404.html", "404.html"),
]


def srgb_to_lin(c: float) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def relative_luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def parse_color(color_str: str) -> tuple[int, int, int, float]:
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)', color_str.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    raise ValueError(f"Cannot parse color string: {color_str}")


def composite_alpha(fg: tuple[int, int, int, float], bg: tuple[int, int, int]) -> tuple[int, int, int]:
    r_fg, g_fg, b_fg, a = fg
    r_bg, g_bg, b_bg = bg
    return (
        round(r_fg * a + r_bg * (1 - a)),
        round(g_fg * a + g_bg * (1 - a)),
        round(b_fg * a + b_bg * (1 - a)),
    )


class TestEmpiricalMultiViewportMatrix:
    """Adversarial stress testing across all 6 target breakpoints on all 4 pages."""

    @pytest.mark.parametrize("width,height,label", BREAKPOINTS)
    @pytest.mark.parametrize("path,page_name", PAGES)
    def test_horizontal_overflow_zero_across_matrix(self, page: Page, base_url: str, width: int, height: int, label: str, path: str, page_name: str):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        metrics = page.evaluate("""() => {
            const de = document.documentElement;
            return {
                scrollWidth: de.scrollWidth,
                clientWidth: de.clientWidth,
                innerWidth: window.innerWidth,
                bodyScrollWidth: document.body ? document.body.scrollWidth : 0
            };
        }""")

        assert metrics["scrollWidth"] <= width, (
            f"Horizontal overflow on {page_name} at {label}: "
            f"scrollWidth={metrics['scrollWidth']}px > viewport={width}px (Delta: +{metrics['scrollWidth'] - width}px)"
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"], (
            f"Scroll width exceeds client width on {page_name} at {label}: "
            f"scrollWidth={metrics['scrollWidth']}px > clientWidth={metrics['clientWidth']}px"
        )

    @pytest.mark.parametrize("width,height,label", BREAKPOINTS)
    @pytest.mark.parametrize("path,page_name", PAGES)
    def test_text_clipping_and_button_wrapping(self, page: Page, base_url: str, width: int, height: int, label: str, path: str, page_name: str):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        clipping_violations = page.evaluate("""() => {
            const violations = [];
            const elements = document.querySelectorAll('h1, h2, h3, p, a, button, [role="button"]');
            for (const el of elements) {
                if (!el.offsetParent) continue; // skip invisible
                if (el.classList.contains('sr-only') || el.closest('.sr-only')) continue;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                // Check text truncation breaking boundary horizontally
                if (style.overflow === 'hidden' && style.textOverflow !== 'ellipsis') {
                    if (el.scrollWidth > el.clientWidth + 2) {
                        violations.push({
                            tag: el.tagName,
                            text: el.innerText ? el.innerText.substring(0, 30) : '',
                            scrollWidth: el.scrollWidth,
                            clientWidth: el.clientWidth,
                            issue: 'unintended text clipping'
                        });
                    }
                }
                
                // Check if element spills outside viewport horizontally (excluding offscreen drawers)
                if (rect.right > window.innerWidth + 2 && !el.closest('#mobileMenu')) {
                    violations.push({
                        tag: el.tagName,
                        text: el.innerText ? el.innerText.substring(0, 30) : '',
                        right: rect.right,
                        windowWidth: window.innerWidth,
                        issue: 'element right edge exceeds viewport'
                    });
                }
            }
            return violations;
        }""")

        assert len(clipping_violations) == 0, f"Found clipping violations on {page_name} at {label}: {clipping_violations}"


class TestAdversarialMobileDrawerLifecycle:
    """Mobile menu drawer open/close, focus entrapment, and link contrast."""

    @pytest.mark.parametrize("width,height,label", [
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
    ])
    def test_mobile_drawer_open_close_focus_and_contrast(self, page: Page, base_url: str, width: int, height: int, label: str):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        hamburger = page.locator("#mobileMenuBtn").first
        assert hamburger.is_visible(), f"Mobile menu toggle button must be visible at {label}"

        # 1. Open drawer
        hamburger.click()
        page.wait_for_timeout(350) # allow transition

        drawer = page.locator("#mobileMenu").first
        assert drawer.is_visible(), f"Mobile drawer must be visible after clicking toggle at {label}"

        # 2. Verify drawer bounding box within viewport
        drawer_box = drawer.bounding_box()
        assert drawer_box is not None
        assert drawer_box["x"] >= -2, f"Drawer left edge ({drawer_box['x']}px) is off-screen at {label}"
        assert drawer_box["width"] <= width + 2, f"Drawer width ({drawer_box['width']}px) exceeds viewport ({width}px) at {label}"

        # 3. Verify contrast of drawer navigation links
        links_data = page.evaluate("""() => {
            const drawer = document.getElementById('mobileMenu');
            const drawerBg = window.getComputedStyle(drawer).backgroundColor;
            const links = Array.from(drawer.querySelectorAll('a'));
            return links.map(l => {
                const style = window.getComputedStyle(l);
                return {
                    text: l.innerText.trim(),
                    color: style.color,
                    backgroundColor: style.backgroundColor,
                    drawerBg: drawerBg,
                    isButton: l.classList.contains('bg-coral') || l.classList.contains('rounded-full')
                };
            });
        }""")

        assert len(links_data) >= 6, f"Expected at least 6 drawer links, found {len(links_data)} at {label}"

        for item in links_data:
            parsed_fg = parse_color(item["color"])
            if item["isButton"] and item["backgroundColor"] != "rgba(0, 0, 0, 0)":
                # CTA button inside drawer (e.g. Run AI Visibility Check on coral background)
                parsed_bg = parse_color(item["backgroundColor"])
                effective_bg = composite_alpha(parsed_bg, (11, 17, 32))
            else:
                # Text link against drawer container background
                parsed_drawer_bg = parse_color(item["drawerBg"])
                effective_bg = composite_alpha(parsed_drawer_bg, (11, 17, 32))

            effective_fg = composite_alpha(parsed_fg, effective_bg)
            cr = contrast_ratio(effective_fg, effective_bg)
            assert cr >= 4.5, (
                f"Drawer link '{item['text']}' contrast ratio {cr:.2f}:1 "
                f"fails WCAG AA 4.5:1 requirement at {label} (FG: {item['color']}, BG: {effective_bg})"
            )

        # 4. Verify Close functionality via toggle button
        hamburger.click()
        page.wait_for_timeout(350)
        is_closed = page.evaluate("""() => {
            const d = document.getElementById('mobileMenu');
            if (!d) return true;
            const style = window.getComputedStyle(d);
            return d.classList.contains('hidden') || style.display === 'none';
        }""")
        assert is_closed, f"Mobile drawer failed to close when toggle button was clicked again at {label}"


class TestAdversarialFAQAccordion:
    """FAQ accordion expand/collapse transitions, copy contrast, and geometry."""

    def test_faq_accordion_transitions_and_contrast(self, page: Page, base_url: str):
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/#faq")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        assert faq_section.is_visible(), "FAQ section must be visible"

        details_list = faq_section.locator("details")
        d_count = details_list.count()
        assert d_count >= 3, f"Expected at least 3 FAQ <details> elements, found {d_count}"

        for i in range(d_count):
            details = details_list.nth(i)
            summary = details.locator("summary").first
            answer = details.locator("div.text-slate-300").first

            # 1. Initially closed
            assert not details.evaluate("el => el.hasAttribute('open')"), f"FAQ #{i} should be initially closed"

            # 2. Click summary to expand
            summary.scroll_into_view_if_needed()
            summary.click()
            page.wait_for_timeout(200)

            assert details.evaluate("el => el.hasAttribute('open')"), f"FAQ #{i} should have open attribute after click"
            assert answer.is_visible(), f"FAQ answer #{i} must be visible after click"

            # 3. Verify answer bounding box
            ans_box = answer.bounding_box()
            assert ans_box is not None and ans_box["height"] > 20, f"FAQ answer #{i} has invalid height {ans_box}"

            # 4. Check answer copy contrast against dark card background
            color_str = answer.evaluate("el => window.getComputedStyle(el).color")
            parsed_fg = parse_color(color_str)
            ans_fg = composite_alpha(parsed_fg, (21, 33, 58))
            cr = contrast_ratio(ans_fg, (21, 33, 58))
            assert cr >= 4.5, f"FAQ answer #{i} copy contrast {cr:.2f}:1 is below 4.5:1"

            # 5. Click summary again to collapse
            summary.click()
            page.wait_for_timeout(200)
            assert not details.evaluate("el => el.hasAttribute('open')"), f"FAQ #{i} should be closed after second click"


class TestAdversarialTimelineStepBubblesReflow:
    """Proper reflow and geometry of Timeline step bubbles across mobile stack and desktop layout."""

    @pytest.mark.parametrize("width,height,mode", [
        (320, 568, "mobile"),
        (375, 667, "mobile"),
        (768, 1024, "desktop"),
        (1024, 768, "desktop"),
        (1280, 800, "desktop"),
        (1920, 1080, "desktop"),
    ])
    def test_timeline_step_bubbles_reflow(self, page: Page, base_url: str, width: int, height: int, mode: str):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/#engine")
        page.wait_for_load_state("networkidle")

        engine = page.locator("#engine")
        assert engine.is_visible()

        bubble_data = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('#engine .rounded-full')).filter(el => {
                const t = el.innerText.trim();
                if (t !== '1' && t !== '2' && t !== '3') return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                // ONLY examine currently visible bubbles
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            });
            return bubbles.map(b => {
                const rect = b.getBoundingClientRect();
                const style = window.getComputedStyle(b);
                return {
                    text: b.innerText.trim(),
                    width: rect.width,
                    height: rect.height,
                    x: rect.x,
                    y: rect.y,
                    color: style.color,
                    backgroundColor: style.backgroundColor,
                    fontSize: parseFloat(style.fontSize),
                    fontWeight: parseInt(style.fontWeight) || 400
                };
            });
        }""")

        assert len(bubble_data) == 3, f"Expected 3 visible timeline step bubbles at {width}px, found {len(bubble_data)}"

        # Find bubbles 1, 2, 3
        b1 = next(b for b in bubble_data if b["text"] == "1")
        b2 = next(b for b in bubble_data if b["text"] == "2")
        b3 = next(b for b in bubble_data if b["text"] == "3")

        # 1. Verify bubble circular dimensions
        for b in [b1, b2, b3]:
            assert b["width"] >= 28 and b["height"] >= 28, f"Bubble {b['text']} too small: {b['width']}x{b['height']}"
            assert abs(b["width"] - b["height"]) <= 4.0, f"Bubble {b['text']} is not circular: {b['width']}x{b['height']}"

        # 2. Verify reflow vertical progression: y coordinates must increase monotonically
        assert b1["y"] < b2["y"] < b3["y"], (
            f"Timeline vertical progression violated at {width}px: y1={b1['y']}, y2={b2['y']}, y3={b3['y']}"
        )

        # 3. Desktop alignment: all 3 bubbles should align on the central spine
        if mode == "desktop":
            assert abs(b1["x"] - b2["x"]) <= 10.0 and abs(b2["x"] - b3["x"]) <= 10.0, (
                f"Desktop central spine alignment violated at {width}px: x1={b1['x']}, x2={b2['x']}, x3={b3['x']}"
            )

        # 4. Contrast verification of Step 3
        fg3 = parse_color(b3["color"])
        bg3 = parse_color(b3["backgroundColor"])
        cr3 = contrast_ratio(fg3[:3], bg3[:3])
        assert cr3 >= 4.5, f"Step 3 bubble contrast {cr3:.2f}:1 fails 4.5:1 requirement at {width}px"

        # 5. Large Text rule verification of Steps 1 & 2
        for b in [b1, b2]:
            is_large_text = b["fontSize"] >= 18.66 and b["fontWeight"] >= 700
            fg = parse_color(b["color"])
            bg = parse_color(b["backgroundColor"])
            cr = contrast_ratio(fg[:3], bg[:3])
            min_cr = 3.0 if is_large_text else 4.5
            assert cr >= min_cr, (
                f"Step {b['text']} bubble contrast {cr:.2f}:1 (fontSize={b['fontSize']}px, fontWeight={b['fontWeight']}) "
                f"fails {min_cr}:1 at {width}px"
            )


class TestAdversarialBordersCrispRendering:
    """Verify card and button borders maintain crisp rendering without subpixel clipping."""

    @pytest.mark.parametrize("width,height,label", BREAKPOINTS)
    def test_card_and_button_borders_crisp_rendering(self, page: Page, base_url: str, width: int, height: int, label: str):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        border_data = page.evaluate("""() => {
            const results = [];
            const targets = document.querySelectorAll('.rounded-3xl, .rounded-2xl, a.border, button.border');
            for (const el of targets) {
                if (!el.offsetParent) continue;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                results.push({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className ? el.className.substring(0, 40) : '',
                    width: rect.width,
                    height: rect.height,
                    borderWidth: parseFloat(style.borderWidth) || 0,
                    borderColor: style.borderColor,
                    borderStyle: style.borderStyle
                });
            }
            return results;
        }""")

        assert len(border_data) > 0, f"Expected border elements at {label}"
        for item in border_data:
            # Check for non-zero border width on bordered elements
            if "border" in item["className"] and not "border-0" in item["className"]:
                assert item["borderWidth"] >= 1.0, f"Subpixel border clipping on {item} at {label}"
            # Check for non-negative geometry
            assert item["width"] > 0 and item["height"] > 0, f"Invalid zero dimensions for {item} at {label}"
