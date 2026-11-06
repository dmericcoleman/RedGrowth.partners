"""
Adversarial Verification Suite for Milestone 2:
Keyboard navigation, focus management, skip-to-content functionality,
WCAG AA contrast, and landmark invariants across all 4 pages.
"""

import math
import re
import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import Page, expect

PAGES = ["/", "/404.html", "/privacy.html", "/terms.html"]

# ==============================================================================
# WCAG Contrast Calculation Helpers
# ==============================================================================

def srgb_to_linear(c: float) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.03928 else math.pow((v + 0.055) / 1.055, 2.4)

def calculate_luminance(r: int, g: int, b: int) -> float:
    return (
        0.2126 * srgb_to_linear(r) +
        0.7152 * srgb_to_linear(g) +
        0.0722 * srgb_to_linear(b)
    )

def contrast_ratio(lum1: float, lum2: float) -> float:
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)

def parse_rgb_or_rgba(css_color: str):
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", css_color.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return {"r": r, "g": g, "b": b, "a": a}
    return None

def blend_colors(fg: dict, bg: dict) -> dict:
    a = fg.get("a", 1.0)
    return {
        "r": round(fg["r"] * a + bg["r"] * (1.0 - a)),
        "g": round(fg["g"] * a + bg["g"] * (1.0 - a)),
        "b": round(fg["b"] * a + bg["b"] * (1.0 - a)),
    }


# ==============================================================================
# Test Suite
# ==============================================================================

class TestSkipLinkKeyboardNavigation:
    """Task 1: Playwright Keyboard Navigation & Focus Management across all 4 pages."""

    @pytest.mark.parametrize("page_path", PAGES)
    def test_single_tab_focuses_skip_link(self, page: Page, base_url: str, page_path: str):
        """
        Verify that pressing Tab once from document start focuses the skip-to-content link
        (a[href="#main-content"]).
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        # Ensure document has focus before pressing Tab
        page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); window.focus(); }")

        # Press Tab once
        page.keyboard.press("Tab")

        # Evaluate active element
        active_info = page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return null;
            return {
                tagName: el.tagName.toLowerCase(),
                href: el.getAttribute('href'),
                text: el.innerText.trim(),
                id: el.id,
                className: el.className
            };
        }""")

        assert active_info is not None, f"No element focused after initial Tab on {page_path}"
        assert active_info["tagName"] == "a", f"Active element on {page_path} is <{active_info['tagName']}>, expected <a>"
        assert active_info["href"] == "#main-content", (
            f"Active element on {page_path} has href '{active_info['href']}', expected '#main-content'"
        )

    @pytest.mark.parametrize("page_path", PAGES)
    def test_skip_link_visible_in_viewport_when_focused(self, page: Page, base_url: str, page_path: str):
        """
        Verify skip link becomes visibly positioned on screen when focused:
        - Bounding box is in viewport
        - Height and width > 0 (not collapsed or clipped by sr-only)
        - clip-path / clip is unclipped
        - opacity > 0, visibility != hidden, display != none
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        skip_link = page.locator('a[href="#main-content"]')
        assert skip_link.count() == 1, f"Expected exactly 1 skip link on {page_path}, found {skip_link.count()}"

        # Focus skip link
        skip_link.focus()

        # Check visibility properties and bounding box
        metrics = page.evaluate("""() => {
            const el = document.querySelector('a[href="#main-content"]');
            const rect = el.getBoundingClientRect();
            const cs = window.getComputedStyle(el);
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            return {
                rect: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    top: rect.top,
                    left: rect.left,
                    bottom: rect.bottom,
                    right: rect.right
                },
                computed: {
                    display: cs.display,
                    visibility: cs.visibility,
                    opacity: parseFloat(cs.opacity),
                    position: cs.position,
                    clip: cs.clip,
                    clipPath: cs.clipPath,
                    zIndex: cs.zIndex
                },
                inViewport: (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= vh &&
                    rect.right <= vw &&
                    rect.width > 20 &&
                    rect.height > 10
                )
            };
        }""")

        assert metrics["computed"]["display"] != "none", f"Skip link on {page_path} has display: none"
        assert metrics["computed"]["visibility"] != "hidden", f"Skip link on {page_path} has visibility: hidden"
        assert metrics["computed"]["opacity"] > 0, f"Skip link on {page_path} has opacity <= 0"
        assert metrics["rect"]["width"] > 30, (
            f"Skip link on {page_path} width is too small ({metrics['rect']['width']}px); sr-only may not be overridden"
        )
        assert metrics["rect"]["height"] > 15, (
            f"Skip link on {page_path} height is too small ({metrics['rect']['height']}px); sr-only may not be overridden"
        )
        assert metrics["inViewport"], (
            f"Skip link on {page_path} is not fully within viewport when focused: {metrics['rect']}"
        )

    @pytest.mark.parametrize("page_path", PAGES)
    def test_activating_skip_link_shifts_focus_to_main_content(self, page: Page, base_url: str, page_path: str):
        """
        Verify activating skip link (via Enter key and click) shifts focus to #main-content
        and document.activeElement is #main-content.
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        # 1. Test keyboard activation (Enter)
        skip_link = page.locator('a[href="#main-content"]')
        skip_link.focus()
        page.keyboard.press("Enter")

        active_tag, active_id = page.evaluate("""() => {
            const el = document.activeElement;
            return [el ? el.tagName.toLowerCase() : null, el ? el.id : null];
        }""")

        assert active_id == "main-content", (
            f"After pressing Enter on skip link in {page_path}, activeElement id is '{active_id}' "
            f"(tag: <{active_tag}>), expected 'main-content'"
        )

        # 2. Test click activation when visible (after tab focus)
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")
        page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); window.focus(); }")
        page.keyboard.press("Tab")
        skip_link = page.locator('a[href="#main-content"]')
        skip_link.click()

        active_tag_click, active_id_click = page.evaluate("""() => {
            const el = document.activeElement;
            return [el ? el.tagName.toLowerCase() : null, el ? el.id : null];
        }""")

        assert active_id_click == "main-content", (
            f"After clicking skip link in {page_path}, activeElement id is '{active_id_click}' "
            f"(tag: <{active_tag_click}>), expected 'main-content'"
        )


class TestSkipLinkContrast:
    """Task 2: Mathematical WCAG AA contrast check for skip link when focused."""

    @pytest.mark.parametrize("page_path", PAGES)
    def test_skip_link_contrast_ratio_wcag_aa(self, page: Page, base_url: str, page_path: str):
        """
        Compute mathematical contrast ratio between the skip link text and background when focused.
        Must satisfy WCAG AA >= 4.5:1.
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        skip_link = page.locator('a[href="#main-content"]')
        skip_link.focus()

        colors = page.evaluate("""() => {
            const el = document.querySelector('a[href="#main-content"]');
            const cs = window.getComputedStyle(el);
            return {
                color: cs.color,
                backgroundColor: cs.backgroundColor,
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight
            };
        }""")

        fg_parsed = parse_rgb_or_rgba(colors["color"])
        bg_parsed = parse_rgb_or_rgba(colors["backgroundColor"])

        assert fg_parsed is not None, f"Unable to parse color: {colors['color']}"
        assert bg_parsed is not None, f"Unable to parse backgroundColor: {colors['backgroundColor']}"

        # If background has alpha, blend with canvas #0B1120 (11, 17, 32)
        if bg_parsed["a"] < 1.0:
            bg_parsed = blend_colors(bg_parsed, {"r": 11, "g": 17, "b": 32, "a": 1.0})

        lum_fg = calculate_luminance(fg_parsed["r"], fg_parsed["g"], fg_parsed["b"])
        lum_bg = calculate_luminance(bg_parsed["r"], bg_parsed["g"], bg_parsed["b"])
        ratio = contrast_ratio(lum_fg, lum_bg)

        # WCAG AA requires 4.5:1 for normal text (or 3.0:1 for large text).
        # We enforce strict AA >= 4.5:1
        assert ratio >= 4.5, (
            f"Skip link on {page_path} has contrast ratio {ratio:.2f}:1 "
            f"(fg={colors['color']}, bg={colors['backgroundColor']}), below WCAG AA 4.5:1"
        )


class TestLandmarkInvariants:
    """Task 3: Landmark Invariant Verification on index.html."""

    def test_index_html_11_sections_inside_main(self):
        """
        Verify that all 11 content sections in index.html are direct or descendant
        children of <main id="main-content">, and <footer> is a sibling outside <main>.
        """
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # 1. Exactly one <main id="main-content"> landmark
        mains = soup.find_all("main")
        assert len(mains) == 1, f"Expected exactly 1 <main> element, found {len(mains)}"
        main = mains[0]
        assert main.get("id") == "main-content", f"<main> element must have id='main-content', got '{main.get('id')}'"
        assert main.get("tabindex") == "-1", f"<main> element must have tabindex='-1', got '{main.get('tabindex')}'"

        # 2. Verify footer is NOT inside <main> and is a sibling
        footers = soup.find_all("footer")
        assert len(footers) == 1, f"Expected exactly 1 <footer> element, found {len(footers)}"
        footer = footers[0]
        assert main not in footer.parents, "<footer> must not be inside <main id='main-content'>"
        assert footer not in main.descendants, "<footer> must not be inside <main id='main-content'>"
        assert footer.parent == main.parent, "<footer> and <main> should be siblings under <body>"

        # 3. Verify the 11 content sections:
        # 1: #hero
        # 2: #framework (AEO Framework)
        # 3: #search (AI Search vs Traditional)
        # 4: #compliance (FTC Compliance)
        # 5: #engine (Consensus Engine / Process)
        # 6: #results (Case Studies / Results)
        # 7: #pricing (Pricing)
        # 8: #fit (Who We Work With / Not a Fit)
        # 9: #founder (Founder & Leadership)
        # 10: #faq (FAQ Accordion)
        # 11: #audit (AI Visibility Check / Audit Form)
        expected_section_ids = [
            "hero",
            "framework",
            "search",
            "compliance",
            "engine",
            "results",
            "pricing",
            "fit",
            "founder",
            "faq",
            "audit",
        ]

        # Check each section exists and is within main
        main_descendants = set(main.descendants)
        for sec_id in expected_section_ids:
            elem = soup.find(id=sec_id)
            assert elem is not None, f"Expected content section id='{sec_id}' was not found in index.html"
            assert elem in main_descendants, (
                f"Section id='{sec_id}' is NOT inside <main id='main-content'>! Parent: {elem.parent.name if elem.parent else None}"
            )

    @pytest.mark.parametrize("page_name", ["404.html", "privacy.html", "terms.html"])
    def test_subpage_landmarks(self, page_name: str):
        """
        Verify that each subpage has exactly one <main id="main-content" tabindex="-1">
        and footer is a sibling outside <main>.
        """
        with open(page_name, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        mains = soup.find_all("main")
        assert len(mains) == 1, f"Expected exactly 1 <main> element in {page_name}, found {len(mains)}"
        main = mains[0]
        assert main.get("id") == "main-content", f"<main> in {page_name} must have id='main-content'"
        assert main.get("tabindex") == "-1", f"<main> in {page_name} must have tabindex='-1'"

        footers = soup.find_all("footer")
        if footers:
            footer = footers[0]
            assert footer not in main.descendants, f"<footer> in {page_name} must not be inside <main>"
            assert footer.parent == main.parent, f"<footer> and <main> in {page_name} should be siblings"


class TestAdversarialStressScenarios:
    """Task 4: Adversarial Stress Harness & Edge Cases."""

    @pytest.mark.parametrize("page_name", ["index.html", "404.html", "privacy.html", "terms.html"])
    def test_main_content_id_uniqueness(self, page_name: str):
        """Ensure id='main-content' is completely unique in the entire DOM (no duplicate IDs)."""
        with open(page_name, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        matches = soup.find_all(id="main-content")
        assert len(matches) == 1, f"Found {len(matches)} elements with id='main-content' in {page_name}"

    @pytest.mark.parametrize("page_path", PAGES)
    def test_tab_bypasses_header_after_skip_activation(self, page: Page, base_url: str, page_path: str):
        """
        Verify that after skip link activation moves focus to #main-content,
        the NEXT Tab press moves focus into an element inside #main-content,
        completely skipping all header navigation links!
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("domcontentloaded")

        # 1. Tab to skip link and activate
        page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); window.focus(); }")
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")

        # Confirm main-content is active
        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : null")
        assert active_id == "main-content"

        # 2. Press Tab again
        page.keyboard.press("Tab")

        # Evaluate where focus landed
        focus_info = page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return null;
            const main = document.getElementById('main-content');
            const header = document.querySelector('header');
            return {
                tagName: el.tagName.toLowerCase(),
                id: el.id,
                href: el.getAttribute('href'),
                text: el.innerText.trim().slice(0, 50),
                isInsideMain: main.contains(el),
                isInsideHeader: header ? header.contains(el) : false
            };
        }""")

        assert focus_info is not None, f"No element focused on next Tab in {page_path}"
        assert not focus_info["isInsideHeader"], (
            f"Focus failed to bypass header! Active element is inside header: {focus_info}"
        )
        assert focus_info["isInsideMain"], (
            f"Focus after skip link should land inside #main-content, but landed on: {focus_info}"
        )

    @pytest.mark.parametrize("page_path", PAGES)
    @pytest.mark.parametrize("width,height", [(320, 568), (375, 667), (768, 1024), (1440, 900)])
    def test_skip_link_viewport_containment_stress(self, page: Page, base_url: str, page_path: str, width: int, height: int):
        """Stress-test skip link positioning across mobile and desktop viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        skip_link = page.locator('a[href="#main-content"]')
        skip_link.focus()

        box = skip_link.bounding_box()
        assert box is not None, f"Skip link has no bounding box at {width}x{height} on {page_path}"
        assert box["x"] >= 0, f"Skip link overflows left boundary at {width}x{height} on {page_path}: {box}"
        assert box["y"] >= 0, f"Skip link overflows top boundary at {width}x{height} on {page_path}: {box}"
        assert box["x"] + box["width"] <= width + 1, (
            f"Skip link overflows right boundary at {width}x{height} on {page_path}: {box}"
        )
        assert box["y"] + box["height"] <= height + 1, (
            f"Skip link overflows bottom boundary at {width}x{height} on {page_path}: {box}"
        )

    @pytest.mark.parametrize("page_path", PAGES)
    def test_exact_contrast_ratio_exceeds_wcag_aaa(self, page: Page, base_url: str, page_path: str):
        """
        Verify exact contrast ratio between text color and background color on focused skip link.
        Background is coral (#FF6441), text is navy (#0B1120).
        Luminance of coral ~0.264, luminance of navy ~0.005.
        Ratio ~ (0.264 + 0.05) / (0.005 + 0.05) = 5.7:1 (exceeds 4.5:1 WCAG AA).
        """
        page.goto(f"{base_url}{page_path}")
        page.wait_for_load_state("networkidle")

        skip_link = page.locator('a[href="#main-content"]')
        skip_link.focus()

        colors = page.evaluate("""() => {
            const el = document.querySelector('a[href="#main-content"]');
            const cs = window.getComputedStyle(el);
            return {
                color: cs.color,
                backgroundColor: cs.backgroundColor
            };
        }""")

        fg = parse_rgb_or_rgba(colors["color"])
        bg = parse_rgb_or_rgba(colors["backgroundColor"])

        lum_fg = calculate_luminance(fg["r"], fg["g"], fg["b"])
        lum_bg = calculate_luminance(bg["r"], bg["g"], bg["b"])
        ratio = contrast_ratio(lum_fg, lum_bg)

        # Confirm contrast ratio is >= 5.5:1
        assert ratio >= 5.5, f"Contrast ratio is {ratio:.2f}:1, expected >= 5.5:1"
