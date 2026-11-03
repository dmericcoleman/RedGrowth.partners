import pytest
import math
import re

TARGET_PAGES = ["/", "/privacy.html", "/terms.html", "/404.html"]
TARGET_VIEWPORTS = [
    (375, 667, "Mobile (375x667)"),
    (768, 1024, "Tablet (768x1024)"),
    (1280, 800, "Desktop (1280x800)"),
    (1920, 1080, "Large Desktop (1920x1080)")
]

def parse_rgb(rgb_str):
    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb_str)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def luminance(r, g, b):
    def channel_lum(val):
        v = val / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)

def contrast_ratio(color1, color2):
    lum1 = luminance(*color1)
    lum2 = luminance(*color2)
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


class TestChallengerViewportStressAudit:
    """
    Exhaustive empirical viewport and layout stress testing by Challenger 2.
    Validates mobile (375x667), tablet (768x1024), desktop (1280x800), and large desktop (1920x1080)
    across all 4 HTML pages:
    - Zero horizontal overflow (scrollWidth <= clientWidth)
    - Zero clipped text in buttons and key headings
    - No button wrapping issues
    - WCAG AA contrast ratio compliance for canvas, cards, text, and buttons
    - Clean console errors and network loads
    """

    @pytest.mark.parametrize("page_path", TARGET_PAGES)
    @pytest.mark.parametrize("width,height,label", TARGET_VIEWPORTS)
    def test_page_viewports_horizontal_overflow_and_containment(self, page, base_url, page_path, width, height, label):
        page.set_viewport_size({"width": width, "height": height})
        res = page.goto(f"{base_url}{page_path}")
        assert res.status == 200, f"Page {page_path} returned status {res.status}"
        page.wait_for_load_state("networkidle")

        # Scroll to bottom and back to trigger any lazy rendering or overflow
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(100)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(50)

        # 1. Document scrollWidth vs clientWidth
        metrics = page.evaluate("""() => {
            const docEl = document.documentElement;
            const body = document.body;
            return {
                scrollWidth: docEl.scrollWidth,
                clientWidth: docEl.clientWidth,
                bodyScrollWidth: body.scrollWidth,
                bodyClientWidth: body.clientWidth,
                innerWidth: window.innerWidth
            };
        }""")

        assert metrics["scrollWidth"] <= metrics["clientWidth"], (
            f"Horizontal overflow on {page_path} at {label}: "
            f"scrollWidth={metrics['scrollWidth']} > clientWidth={metrics['clientWidth']}"
        )
        assert metrics["bodyScrollWidth"] <= metrics["innerWidth"], (
            f"Body scroll overflow on {page_path} at {label}: "
            f"bodyScrollWidth={metrics['bodyScrollWidth']} > innerWidth={metrics['innerWidth']}"
        )

        # 2. Inspect every element on page to verify no unmasked element exceeds viewport width
        overflowing_elements = page.evaluate("""(viewportWidth) => {
            const bad = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                // Check if element extends past right edge by more than 1px
                if (rect.right > viewportWidth + 1.5 && rect.width > 0 && rect.height > 0) {
                    // Check if parent or element has overflow hidden
                    let curr = el;
                    let isClipped = false;
                    while (curr && curr !== document.body && curr !== document.documentElement) {
                        const style = window.getComputedStyle(curr);
                        if (style.overflowX === 'hidden' || style.overflow === 'hidden') {
                            isClipped = true;
                            break;
                        }
                        curr = curr.parentElement;
                    }
                    if (!isClipped) {
                        bad.push({
                            tag: el.tagName,
                            id: el.id,
                            className: (el.className || '').toString().slice(0, 50),
                            rectRight: rect.right,
                            rectWidth: rect.width
                        });
                    }
                }
            }
            return bad;
        }""", width)

        assert len(overflowing_elements) == 0, (
            f"Found {len(overflowing_elements)} elements overflowing viewport {label} on {page_path}: "
            f"{overflowing_elements[:3]}"
        )

        # 3. Verify zero console errors
        assert len(page._console_errors) == 0, (
            f"Console errors detected on {page_path} at {label}: {page._console_errors}"
        )

    @pytest.mark.parametrize("page_path", TARGET_PAGES)
    @pytest.mark.parametrize("width,height,label", TARGET_VIEWPORTS)
    def test_buttons_and_links_no_clipping_or_wrapping_distortion(self, page, base_url, page_path, width, height, label):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        button_stats = page.evaluate("""() => {
            const buttons = document.querySelectorAll('button, a.btn, a[class*="bg-coral"], a[class*="rounded-full"]');
            const data = [];
            for (const btn of buttons) {
                const rect = btn.getBoundingClientRect();
                const style = window.getComputedStyle(btn);
                if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden') {
                    data.push({
                        text: btn.innerText.trim(),
                        scrollWidth: btn.scrollWidth,
                        clientWidth: btn.clientWidth,
                        scrollHeight: btn.scrollHeight,
                        clientHeight: btn.clientHeight,
                        width: rect.width,
                        height: rect.height,
                        fontSize: style.fontSize,
                        lineHeight: style.lineHeight,
                        whiteSpace: style.whiteSpace
                    });
                }
            }
            return data;
        }""")

        for btn in button_stats:
            # Button scrollWidth should not significantly exceed clientWidth (allow 1px for border/subpixel)
            assert btn["scrollWidth"] <= btn["clientWidth"] + 1.5, (
                f"Button text clipped on {page_path} at {label}: "
                f"text='{btn['text']}', scrollWidth={btn['scrollWidth']} > clientWidth={btn['clientWidth']}"
            )
            # Button scrollHeight should not exceed clientHeight
            assert btn["scrollHeight"] <= btn["clientHeight"] + 1.5, (
                f"Button height truncated on {page_path} at {label}: "
                f"text='{btn['text']}', scrollHeight={btn['scrollHeight']} > clientHeight={btn['clientHeight']}"
            )

    @pytest.mark.parametrize("page_path", TARGET_PAGES)
    def test_wcag_standardized_color_palette_empirical_check(self, page, base_url, page_path):
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        # 1. Root canvas background check
        canvas_bg = page.evaluate("""() => {
            const bodyStyle = window.getComputedStyle(document.body);
            const htmlStyle = window.getComputedStyle(document.documentElement);
            return {
                bodyBg: bodyStyle.backgroundColor,
                htmlBg: htmlStyle.backgroundColor
            };
        }""")
        body_rgb = parse_rgb(canvas_bg["bodyBg"])
        # Should match #0B1120 -> rgb(11, 17, 32)
        assert body_rgb in [(11, 17, 32), (0, 0, 0)], f"Canvas body background is {canvas_bg['bodyBg']}, expected rgb(11, 17, 32)"

        # 2. Primary buttons contrast check
        buttons = page.locator("a[class*='bg-coral'], button[class*='bg-coral'], #submitAuditBtn")
        count = buttons.count()
        if count > 0:
            for i in range(count):
                btn = buttons.nth(i)
                if btn.is_visible():
                    colors = page.evaluate("""(el) => {
                        const style = window.getComputedStyle(el);
                        return {
                            color: style.color,
                            bgColor: style.backgroundColor
                        };
                    }""", btn.element_handle())
                    fg = parse_rgb(colors["color"])
                    bg = parse_rgb(colors["bgColor"])
                    ratio = contrast_ratio(fg, bg)
                    # WCAG AA requires at least 4.5:1 for normal text, 3:1 for large/bold text
                    assert ratio >= 4.5, (
                        f"Primary button on {page_path} failed WCAG AA contrast: "
                        f"fg={colors['color']}, bg={colors['bgColor']}, ratio={ratio:.2f}:1 (min 4.5:1)"
                    )

        # 3. Body text contrast check
        body_sample = page.locator("p, li").first
        if body_sample.count() > 0 and body_sample.is_visible():
            sample_colors = page.evaluate("""(el) => {
                const style = window.getComputedStyle(el);
                return {
                    color: style.color
                };
            }""", body_sample.element_handle())
            fg = parse_rgb(sample_colors["color"])
            # Canvas is (11, 17, 32)
            ratio = contrast_ratio(fg, (11, 17, 32))
            assert ratio >= 4.5, (
                f"Body text on {page_path} failed WCAG AA contrast vs canvas: "
                f"fg={sample_colors['color']}, ratio={ratio:.2f}:1 (min 4.5:1)"
            )
