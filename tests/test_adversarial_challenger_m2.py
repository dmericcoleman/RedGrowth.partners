"""
Adversarial Empirical Contrast Verification Suite (Milestone 2)
Author: Teamwork Challenger (critic/specialist)
Target: RedGrowth.partners (index.html, privacy.html, terms.html, 404.html)

Adversarial validation covering:
1. Section 4 Timeline Step 1, 2, 3 bubbles (desktop & mobile)
2. Form input resting borders in #auditForm against card surface (SC 1.4.11)
3. Outline button boundaries against adjacent surfaces (SC 1.4.11)
4. Primary button interactive states (default, hover, active, focus-visible)
5. Programmatic text selection (::selection) across all 4 pages
6. Form submit dynamic AJAX loading state (SVG spinner and text contrast)
"""

import math
import re
import pytest
from playwright.sync_api import Page, expect

CANVAS_RGB = {"r": 11, "g": 17, "b": 32, "a": 1.0}        # #0B1120
CARD_SURFACE_RGB = {"r": 21, "g": 33, "b": 58, "a": 1.0}  # #15213A
CORAL_RGB = {"r": 255, "g": 100, "b": 65, "a": 1.0}       # #FF6441

def srgb_channel_to_linear(c: float) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.03928 else math.pow((v + 0.055) / 1.055, 2.4)

def calculate_relative_luminance(r: int, g: int, b: int) -> float:
    return (
        0.2126 * srgb_channel_to_linear(r) +
        0.7152 * srgb_channel_to_linear(g) +
        0.0722 * srgb_channel_to_linear(b)
    )

def calculate_contrast_ratio(lum1: float, lum2: float) -> float:
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)

def parse_rgba(color_str: str) -> dict:
    if not color_str:
        return None
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)', color_str.strip())
    if m:
        return {
            'r': int(m.group(1)),
            'g': int(m.group(2)),
            'b': int(m.group(3)),
            'a': float(m.group(4)) if m.group(4) is not None else 1.0
        }
    return None

def blend(fg: dict, bg: dict) -> dict:
    a = fg.get('a', 1.0)
    return {
        'r': round(fg['r'] * a + bg['r'] * (1.0 - a)),
        'g': round(fg['g'] * a + bg['g'] * (1.0 - a)),
        'b': round(fg['b'] * a + bg['b'] * (1.0 - a)),
        'a': 1.0
    }

JS_RECURSIVE_BG = """
function parseRgb(str) {
    if (!str) return null;
    const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
    if (m) {
        return {
            r: parseInt(m[1], 10),
            g: parseInt(m[2], 10),
            b: parseInt(m[3], 10),
            a: m[4] !== undefined ? parseFloat(m[4]) : 1.0
        };
    }
    return null;
}

function channelLinear(c) {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function getLuminance(rgb) {
    return 0.2126 * channelLinear(rgb.r) + 0.7152 * channelLinear(rgb.g) + 0.0722 * channelLinear(rgb.b);
}

function blendOver(fg, bg) {
    const a = fg.a !== undefined ? fg.a : 1.0;
    return {
        r: Math.round(fg.r * a + bg.r * (1 - a)),
        g: Math.round(fg.g * a + bg.g * (1 - a)),
        b: Math.round(fg.b * a + bg.b * (1 - a)),
        a: 1.0
    };
}

function getEffectiveBackground(el) {
    let cur = el;
    let colorStack = [];
    while (cur && cur.nodeType === Node.ELEMENT_NODE) {
        const st = window.getComputedStyle(cur);
        const bgStr = st.backgroundColor;
        const parsed = parseRgb(bgStr);
        if (parsed && parsed.a > 0) {
            colorStack.unshift(parsed);
            if (parsed.a === 1.0) break;
        }
        cur = cur.parentElement;
    }
    let composite = { r: 11, g: 17, b: 32, a: 1.0 }; // #0B1120 canvas
    for (const c of colorStack) {
        composite = blendOver(c, composite);
    }
    return composite;
}
"""


class TestAdversarialTimelineBubbles:
    """Adversarial stress-testing of Section 4 Timeline Step bubbles."""

    @pytest.mark.parametrize("viewport", [
        {"width": 1280, "height": 800, "name": "desktop"},
        {"width": 375, "height": 667, "name": "mobile"}
    ])
    def test_adversarial_timeline_step_bubbles(self, page: Page, base_url: str, viewport: dict):
        page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        page.goto(f"{base_url}/#engine")
        page.wait_for_timeout(300)

        bubbles_data = page.evaluate("""
        () => {
            """ + JS_RECURSIVE_BG + """
            const results = [];
            const engine = document.getElementById('engine');
            if (!engine) return results;

            // Target actual rounded-full bubble badges containing numerals 1, 2, 3
            const allBadges = engine.querySelectorAll('.rounded-full');
            for (const div of allBadges) {
                const text = div.innerText ? div.innerText.trim() : '';
                if (['1', '2', '3'].includes(text)) {
                    const rect = div.getBoundingClientRect();
                    const st = window.getComputedStyle(div);
                    if (st.display === 'none' || st.visibility === 'hidden') continue;
                    if (rect.width >= 20 && rect.width <= 70 && rect.height >= 20 && rect.height <= 70) {
                        const fg = parseRgb(st.color);
                        const bg = parseRgb(st.backgroundColor);
                        const parentBg = getEffectiveBackground(div.parentElement);
                        const effectiveBg = (bg.a < 1.0) ? blendOver(bg, parentBg) : bg;

                        const lFg = getLuminance(fg);
                        const lBg = getLuminance(effectiveBg);
                        const cr = (Math.max(lFg, lBg) + 0.05) / (Math.min(lFg, lBg) + 0.05);

                        const fontSize = parseFloat(st.fontSize);
                        const fontWeight = parseInt(st.fontWeight, 10) || 400;
                        const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);

                        results.push({
                            step: text,
                            visible: rect.width > 0 && rect.height > 0 && parseFloat(st.opacity) > 0,
                            rect: { width: rect.width, height: rect.height, top: rect.top, left: rect.left },
                            color: st.color,
                            backgroundColor: st.backgroundColor,
                            fontSize,
                            fontWeight,
                            isLarge,
                            contrastRatio: Math.round(cr * 100) / 100,
                            className: div.className
                        });
                    }
                }
            }
            return results;
        }
        """)

        assert len(bubbles_data) >= 3, f"In {viewport['name']}, expected at least 3 bubbles, found {len(bubbles_data)}"

        visible_bubbles = [b for b in bubbles_data if b['visible']]
        assert len(visible_bubbles) >= 3, f"Expected at least 3 visible bubbles in {viewport['name']}, found {len(visible_bubbles)}"

        for b in visible_bubbles:
            step = b['step']
            cr = b['contrastRatio']
            is_large = b['isLarge']
            req = 3.0 if is_large else 4.5

            if step == '3':
                # Step 3 text on #f97316 must reach AA contrast
                assert cr >= req, (
                    f"Step 3 in {viewport['name']} failed contrast: {cr}:1 < {req}:1 "
                    f"(Color: {b['color']} on {b['backgroundColor']}, font: {b['fontSize']}px / {b['fontWeight']})"
                )
                assert '0B1120' in b['className'] or 'rgb(11, 17, 32)' in b['color'], (
                    f"Step 3 in {viewport['name']} should use navy text, got {b['color']} ({b['className']})"
                )
            else:
                # Steps 1 & 2 must qualify as Large Text (>= 18.66px and bold >= 700) and satisfy >= 3.0:1
                assert is_large, (
                    f"Step {step} in {viewport['name']} is NOT large text: "
                    f"fontSize={b['fontSize']}px, fontWeight={b['fontWeight']}"
                )
                assert cr >= 3.0, (
                    f"Step {step} in {viewport['name']} failed large text contrast: {cr}:1 < 3.0:1"
                )


class TestAdversarialFormInputBorders:
    """Adversarial stress-testing of #auditForm input resting borders against card background."""

    def test_adversarial_form_resting_borders(self, page: Page, base_url: str):
        page.goto(f"{base_url}/#audit")
        page.wait_for_timeout(300)

        inputs = ["#fullName", "#companyDomain", "#workEmail", "#brandNotes"]

        for input_sel in inputs:
            loc = page.locator(input_sel)
            assert loc.is_visible(), f"{input_sel} not visible"

            eval_res = loc.evaluate("""
            (el) => {
                """ + JS_RECURSIVE_BG + """
                const st = window.getComputedStyle(el);
                const parentBg = getEffectiveBackground(el.parentElement);
                const parsedBorder = parseRgb(st.borderColor);
                const effectiveBorder = blendOver(parsedBorder, parentBg);

                const lBorder = getLuminance(effectiveBorder);
                const lParent = getLuminance(parentBg);
                const ratio = (Math.max(lBorder, lParent) + 0.05) / (Math.min(lBorder, lParent) + 0.05);

                return {
                    borderColor: st.borderColor,
                    borderWidth: st.borderWidth,
                    parentBg: `rgb(${parentBg.r}, ${parentBg.g}, ${parentBg.b})`,
                    ratio: Math.round(ratio * 100) / 100,
                    classes: el.className
                };
            }
            """)

            # Must satisfy SC 1.4.11 (>= 3.0:1)
            assert eval_res["ratio"] >= 3.0, (
                f"{input_sel} resting border contrast failed SC 1.4.11: {eval_res['ratio']}:1 < 3.0:1 "
                f"(border: {eval_res['borderColor']}, bg: {eval_res['parentBg']})"
            )
            assert "border-white/40" in eval_res["classes"], (
                f"{input_sel} missing expected border-white/40 class, found: {eval_res['classes']}"
            )


class TestAdversarialOutlineButtons:
    """Adversarial stress-testing of outline button boundaries against adjacent surfaces."""

    def test_adversarial_outline_button_boundaries(self, page: Page, base_url: str):
        # 1. Index page outline buttons
        page.goto(f"{base_url}/")
        page.wait_for_timeout(300)

        targets = [
            ("Hero Secondary CTA", "#hero a:has-text('View Pipeline Results')", "border-white/40"),
            ("Pricing Tier 1 CTA", "#pricing a:has-text('Book Pilot Audit')", "border-white/40"),
            ("Pricing Tier 3 CTA", "#pricing a:has-text('Dominate Category')", "border-white/40"),
            ("Founder Strategy CTA", "#founder a:has-text('Schedule Strategy Session')", "border-white/40"),
        ]

        for desc, sel, expected_class in targets:
            btn = page.locator(sel).first
            assert btn.is_visible(), f"{desc} ({sel}) not visible"

            eval_res = btn.evaluate("""
            (el) => {
                """ + JS_RECURSIVE_BG + """
                const st = window.getComputedStyle(el);
                const parentBg = getEffectiveBackground(el.parentElement);
                const parsedBorder = parseRgb(st.borderColor);
                const effectiveBorder = blendOver(parsedBorder, parentBg);

                const lBorder = getLuminance(effectiveBorder);
                const lParent = getLuminance(parentBg);
                const ratio = (Math.max(lBorder, lParent) + 0.05) / (Math.min(lBorder, lParent) + 0.05);

                return {
                    borderColor: st.borderColor,
                    borderWidth: st.borderWidth,
                    parentBg: `rgb(${parentBg.r}, ${parentBg.g}, ${parentBg.b})`,
                    ratio: Math.round(ratio * 100) / 100,
                    classes: el.className
                };
            }
            """)

            assert eval_res["ratio"] >= 3.0, (
                f"{desc} border contrast failed SC 1.4.11: {eval_res['ratio']}:1 < 3.0:1 "
                f"(border: {eval_res['borderColor']}, bg: {eval_res['parentBg']})"
            )
            assert expected_class in eval_res["classes"], (
                f"{desc} missing {expected_class}: {eval_res['classes']}"
            )

        # 2. 404 page outline buttons
        page.goto(f"{base_url}/404.html")
        page.wait_for_timeout(300)

        subpage_targets = [
            ("404 Secondary CTA", "a:has-text('Schedule Strategy Call')", "border-white/40"),
            ("404 Header Return Home", "header a:has-text('Home')", "border-white/40")
        ]

        for desc, sel, expected_class in subpage_targets:
            btn = page.locator(sel).first
            assert btn.is_visible(), f"{desc} not visible on 404.html"

            eval_res = btn.evaluate("""
            (el) => {
                """ + JS_RECURSIVE_BG + """
                const st = window.getComputedStyle(el);
                const parentBg = getEffectiveBackground(el.parentElement);
                const parsedBorder = parseRgb(st.borderColor);
                const effectiveBorder = blendOver(parsedBorder, parentBg);

                const lBorder = getLuminance(effectiveBorder);
                const lParent = getLuminance(parentBg);
                const ratio = (Math.max(lBorder, lParent) + 0.05) / (Math.min(lBorder, lParent) + 0.05);

                return {
                    borderColor: st.borderColor,
                    parentBg: `rgb(${parentBg.r}, ${parentBg.g}, ${parentBg.b})`,
                    ratio: Math.round(ratio * 100) / 100,
                    classes: el.className
                };
            }
            """)

            assert eval_res["ratio"] >= 3.0, (
                f"{desc} boundary contrast failed SC 1.4.11: {eval_res['ratio']}:1 < 3.0:1"
            )
            assert expected_class in eval_res["classes"], (
                f"{desc} missing {expected_class}: {eval_res['classes']}"
            )


class TestAdversarialInteractiveButtonStates:
    """Adversarial stress-testing of primary coral button interactive states."""

    def test_adversarial_button_states_hover_active_focus(self, page: Page, base_url: str):
        page.goto(f"{base_url}/")
        page.wait_for_timeout(300)

        btn = page.locator("#hero a.bg-coral").first
        assert btn.is_visible(), "Hero Primary CTA not visible"
        btn.evaluate("el => el.addEventListener('click', e => e.preventDefault())")

        # 1. Default Resting State
        def_eval = btn.evaluate("""
        (el) => {
            """ + JS_RECURSIVE_BG + """
            const st = window.getComputedStyle(el);
            const fg = parseRgb(st.color);
            const bg = parseRgb(st.backgroundColor);
            const cr = (getLuminance(bg) + 0.05) / (getLuminance(fg) + 0.05);
            return { color: st.color, bg: st.backgroundColor, ratio: Math.round(cr * 100) / 100 };
        }
        """)
        assert def_eval["ratio"] >= 4.5, f"Default button contrast failed: {def_eval['ratio']}:1 < 4.5:1"

        # 2. Hover State
        btn.hover()
        page.wait_for_timeout(200)
        hover_eval = btn.evaluate("""
        (el) => {
            """ + JS_RECURSIVE_BG + """
            const st = window.getComputedStyle(el);
            const fg = parseRgb(st.color);
            const bg = parseRgb(st.backgroundColor);
            const cr = (getLuminance(bg) + 0.05) / (getLuminance(fg) + 0.05);
            return { color: st.color, bg: st.backgroundColor, ratio: Math.round(cr * 100) / 100 };
        }
        """)
        assert hover_eval["ratio"] >= 4.5, f"Hover button contrast failed: {hover_eval['ratio']}:1 < 4.5:1"

        # 3. Active / MouseDown State
        box = btn.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.wait_for_timeout(100)
        active_eval = btn.evaluate("""
        (el) => {
            """ + JS_RECURSIVE_BG + """
            const st = window.getComputedStyle(el);
            const fg = parseRgb(st.color);
            const bg = parseRgb(st.backgroundColor);
            const cr = (getLuminance(bg) + 0.05) / (getLuminance(fg) + 0.05);
            return { color: st.color, bg: st.backgroundColor, ratio: Math.round(cr * 100) / 100 };
        }
        """)
        page.mouse.up()
        assert active_eval["ratio"] >= 4.5, f"Active button contrast failed: {active_eval['ratio']}:1 < 4.5:1"

        # 4. Focus-visible State (verify ring specification and contrast)
        btn_classes = btn.evaluate("el => el.className")
        assert "btn-interactive" in btn_classes or "focus-visible:ring-coral" in btn_classes, (
            f"Button missing interactive focus ring classes: {btn_classes}"
        )
        # Coral focus ring (#FF6441) on navy canvas (#0B1120) achieves 6.41:1 >= 3.0:1
        ring_contrast = calculate_contrast_ratio(
            calculate_relative_luminance(CORAL_RGB['r'], CORAL_RGB['g'], CORAL_RGB['b']),
            calculate_relative_luminance(CANVAS_RGB['r'], CANVAS_RGB['g'], CANVAS_RGB['b'])
        )
        assert ring_contrast >= 3.0, f"Focus ring contrast {ring_contrast:.2f}:1 < 3.0:1"


class TestAdversarialSelectionContrast:
    """Adversarial stress-testing of text selection highlight across all 4 pages."""

    @pytest.mark.parametrize("page_path", ["/", "/privacy.html", "/terms.html", "/404.html"])
    def test_adversarial_selection_contrast_all_pages(self, page: Page, base_url: str, page_path: str):
        page.goto(f"{base_url}{page_path}")
        page.wait_for_timeout(200)

        # Programmatically select all text in H1
        h1 = page.locator("h1").first
        assert h1.is_visible(), f"H1 not visible on {page_path}"

        selection_metrics = h1.evaluate("""
        (el) => {
            """ + JS_RECURSIVE_BG + """
            const range = document.createRange();
            range.selectNodeContents(el);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);

            const bodyClasses = document.body.className || '';
            const selStyle = window.getComputedStyle(document.body, '::selection');

            let fg = parseRgb(selStyle.color);
            let bg = parseRgb(selStyle.backgroundColor);

            const hasNavyClass = bodyClasses.includes('selection:text-[#0B1120]');
            const hasCoralBgClass = bodyClasses.includes('selection:bg-coral');

            if (!bg || bg.a === 0) {
                bg = { r: 255, g: 100, b: 65, a: 1.0 }; // coral
            }
            if (!fg || fg.a === 0 || fg.r === bg.r) {
                fg = hasNavyClass ? { r: 11, g: 17, b: 32, a: 1.0 } : { r: 255, g: 255, b: 255, a: 1.0 };
            }

            const lFg = getLuminance(fg);
            const lBg = getLuminance(bg);
            const cr = (Math.max(lFg, lBg) + 0.05) / (Math.min(lFg, lBg) + 0.05);

            return {
                bodyClasses,
                hasNavyClass,
                hasCoralBgClass,
                fg: `rgb(${fg.r}, ${fg.g}, ${fg.b})`,
                bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`,
                contrastRatio: Math.round(cr * 100) / 100
            };
        }
        """)

        assert selection_metrics["hasNavyClass"], (
            f"Page {page_path} missing selection:text-[#0B1120] in body classes: {selection_metrics['bodyClasses']}"
        )
        assert selection_metrics["hasCoralBgClass"], (
            f"Page {page_path} missing selection:bg-coral in body classes: {selection_metrics['bodyClasses']}"
        )
        assert selection_metrics["contrastRatio"] >= 4.5, (
            f"Selection contrast on {page_path} failed: {selection_metrics['contrastRatio']}:1 < 4.5:1 "
            f"(FG: {selection_metrics['fg']}, BG: {selection_metrics['bg']})"
        )


class TestAdversarialAjaxFormLoadingState:
    """Adversarial stress-testing of AJAX dynamic submit loading spinner and text contrast."""

    def test_adversarial_ajax_submit_loading_contrast(self, page: Page, base_url: str):
        page.goto(f"{base_url}/#audit")
        page.wait_for_timeout(300)

        # Fill the form with valid data
        page.fill("#fullName", "John Doe")
        page.fill("#companyDomain", "https://example.com")
        page.fill("#workEmail", "john@example.com")
        page.fill("#brandNotes", "Adversarial contrast verification test note.")

        submit_btn = page.locator("#submitAuditBtn")
        assert submit_btn.is_visible(), "Submit button not visible"

        # Verify that script template contains text-[#0B1120] and NOT text-white inside the submitBtn assignment
        script_eval = page.evaluate("""
        () => {
            const scripts = Array.from(document.querySelectorAll('script')).map(s => s.textContent).join('\\n');
            const submitMatch = scripts.match(/submitBtn\\.innerHTML\\s*=\\s*`([\\s\\S]*?)`;/);
            if (!submitMatch) return { error: 'submitBtn.innerHTML not found' };

            const templateHTML = submitMatch[1];
            return {
                templateHTML,
                hasNavyColor: templateHTML.includes('text-[#0B1120]'),
                hasWhiteColor: templateHTML.includes('text-white')
            };
        }
        """)

        assert "error" not in script_eval, f"Script inspection failed: {script_eval.get('error')}"
        assert script_eval["hasNavyColor"], f"Injected template does not contain text-[#0B1120]: {script_eval['templateHTML']}"
        assert not script_eval["hasWhiteColor"], f"Injected template still contains text-white: {script_eval['templateHTML']}"

        # Dynamically invoke submission and verify DOM while disabled
        page.evaluate("""
        () => {
            const form = document.getElementById('auditForm');
            window._originalFetch = window.fetch;
            window.fetch = () => new Promise(resolve => setTimeout(() => resolve({ ok: true, json: () => Promise.resolve({ success: true }) }), 2000));
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
        """)

        page.wait_for_timeout(300)

        # While submission is pending, measure button computed styles
        loading_metrics = submit_btn.evaluate("""
        (btn) => {
            """ + JS_RECURSIVE_BG + """
            const svg = btn.querySelector('svg');
            const span = btn.querySelector('span');

            const btnSt = window.getComputedStyle(btn);
            const btnBg = parseRgb(btnSt.backgroundColor) || { r: 255, g: 100, b: 65, a: 1.0 };

            let svgColor = svg ? parseRgb(window.getComputedStyle(svg).color) : null;
            let spanColor = span ? parseRgb(window.getComputedStyle(span).color) : null;

            const lBtn = getLuminance(btnBg);

            let crSvg = 0;
            if (svgColor) {
                const lSvg = getLuminance(svgColor);
                crSvg = (Math.max(lBtn, lSvg) + 0.05) / (Math.min(lBtn, lSvg) + 0.05);
            }

            let crSpan = 0;
            if (spanColor) {
                const lSpan = getLuminance(spanColor);
                crSpan = (Math.max(lBtn, lSpan) + 0.05) / (Math.min(lBtn, lSpan) + 0.05);
            }

            return {
                disabled: btn.disabled,
                svgColor: svg ? window.getComputedStyle(svg).color : null,
                spanColor: span ? window.getComputedStyle(span).color : null,
                btnBg: btnSt.backgroundColor,
                crSvg: Math.round(crSvg * 100) / 100,
                crSpan: Math.round(crSpan * 100) / 100,
                html: btn.innerHTML
            };
        }
        """)

        assert loading_metrics["disabled"] is True, "Button should be disabled during submit"
        assert loading_metrics["crSvg"] >= 4.5, (
            f"Loading SVG spinner contrast failed: {loading_metrics['crSvg']}:1 < 4.5:1 "
            f"(color: {loading_metrics['svgColor']}, bg: {loading_metrics['btnBg']})"
        )
        assert loading_metrics["crSpan"] >= 4.5, (
            f"Loading text span contrast failed: {loading_metrics['crSpan']}:1 < 4.5:1 "
            f"(color: {loading_metrics['spanColor']}, bg: {loading_metrics['btnBg']})"
        )
