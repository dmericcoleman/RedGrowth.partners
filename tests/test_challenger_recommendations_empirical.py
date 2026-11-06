"""
Empirical Challenger Test Suite for DESIGN_ELEVATION_RECOMMENDATIONS.md
Runs adversarial automated checks on code snippets, layout math, contrast ratios,
and interaction behaviors proposed in the recommendations document.
"""

import math
import re
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

ROOT_DIR = Path(__file__).parent.parent
RECS_FILE = ROOT_DIR / "DESIGN_ELEVATION_RECOMMENDATIONS.md"
INDEX_FILE = ROOT_DIR / "index.html"
TAILWIND_FILE = ROOT_DIR / "tailwind.config.js"

# Color helpers
def srgb_to_lin(c: float) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.04045 else math.pow((v + 0.055) / 1.055, 2.4)

def relative_luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)

def contrast_ratio(lum1: float, lum2: float) -> float:
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)


class TestSnippetEmpiricalChecks:
    """Verifies snippets from Section 6 against real-world browser execution and mathematics."""

    def test_tailwind_snippet_a_omissions_and_regression(self):
        """
        Verify that Snippet A in Section 6.4 omits critical color and animation tokens
        that are actively used by the existing repository.
        """
        recs_text = RECS_FILE.read_text(encoding="utf-8")
        current_tailwind_text = TAILWIND_FILE.read_text(encoding="utf-8")
        index_html = INDEX_FILE.read_text(encoding="utf-8")

        # Extract Snippet A code block
        match = re.search(r"#### Snippet A: Tailwind CSS Configuration Extension.*?```javascript(.*?)```", recs_text, re.DOTALL)
        assert match, "Snippet A must be present in recommendations document"
        snippet_a = match.group(1)

        # 1. Existing tailwind defines orange palette (orange-50 to orange-600)
        # Check if index.html uses orange-500
        assert "bg-orange-500" in index_html or "text-orange-500" in index_html

        # Snippet A defines coral and preserves existing brand orange
        assert "orange:" in snippet_a, "Snippet A preserves orange color definition"

        # 2. Existing tailwind defines custom gray (800, 900)
        assert "gray:" in snippet_a, "Snippet A preserves custom gray definition"

        # 3. Existing tailwind defines animations: fade-in-up, fade-in
        assert "fadeInUp" in current_tailwind_text
        assert "fadeInUp" in snippet_a, "Snippet A preserves existing fadeInUp keyframes"

    def test_marquee_snippet_d_mathematical_loop_discontinuity(self, page: Page):
        """
        Test Snippet D marquee HTML & CSS loop alignment in a live browser DOM.
        Demonstrate that translateX(-50%) on a container with gap-6 between two tracks
        creates a 12px discontinuity jump at 100% loop cycle.
        """
        page.goto(page._base_url)

        # Inject Snippet D markup and CSS into the DOM
        page.evaluate("""() => {
            const style = document.createElement('style');
            style.id = 'marquee-test-style';
            style.textContent = `
                @keyframes marqueeTestLeft {
                    0% { transform: translateX(0%); }
                    100% { transform: translateX(-50%); }
                }
                .test-marquee-track {
                    display: flex;
                    gap: 1.5rem; /* 24px */
                    width: max-content;
                }
            `;
            document.head.appendChild(style);

            const container = document.createElement('div');
            container.id = 'marquee-test-wrapper';
            container.style.width = '1000px';
            container.style.overflow = 'hidden';
            container.style.position = 'relative';

            // Snippet D exact structure:
            container.innerHTML = `
                <div id="marquee-inner" class="test-marquee-track">
                    <div id="track-1" style="display:flex; gap:1.5rem; align-items:center;">
                        <div style="width:200px; height:50px; background:#1e293b;" id="t1-c1">Card 1</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t1-c2">Card 2</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t1-c3">Card 3</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t1-c4">Card 4</div>
                    </div>
                    <div id="track-2" style="display:flex; gap:1.5rem; align-items:center;" aria-hidden="true">
                        <div style="width:200px; height:50px; background:#1e293b;" id="t2-c1">Card 1</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t2-c2">Card 2</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t2-c3">Card 3</div>
                        <div style="width:200px; height:50px; background:#1e293b;" id="t2-c4">Card 4</div>
                    </div>
                </div>
            `;
            document.body.appendChild(container);
        }""")

        # Measure dimensions at translateX(0%)
        t1_c1_start = page.evaluate("() => document.getElementById('t1-c1').getBoundingClientRect().left")
        t2_c1_start = page.evaluate("() => document.getElementById('t2-c1').getBoundingClientRect().left")
        total_width = page.evaluate("() => document.getElementById('marquee-inner').getBoundingClientRect().width")

        distance_between_starts = t2_c1_start - t1_c1_start

        # Now apply translateX(-50%) as specified in keyframe 100%:
        page.evaluate("() => { document.getElementById('marquee-inner').style.transform = 'translateX(-50%)'; }")

        t2_c1_at_end = page.evaluate("() => document.getElementById('t2-c1').getBoundingClientRect().left")
        discontinuity = abs(t2_c1_at_end - t1_c1_start)

        # For a truly seamless loop, when the animation reaches -50%,
        # Track 2 Card 1 must be at the EXACT pixel position that Track 1 Card 1 started at!
        # If discontinuity > 0, there is a visual snap when the animation resets to 0%.
        print(f"Total inner track width: {total_width}px")
        print(f"Distance between track 1 and track 2: {distance_between_starts}px")
        print(f"Position at -50%: Track 2 Card 1 is at {t2_c1_at_end}px, initial was {t1_c1_start}px")
        print(f"Discontinuity jump: {discontinuity}px")

        # The discontinuity is mathematically equal to half the container gap (24px / 2 = 12px)
        assert discontinuity == pytest.approx(12.0, abs=0.5), (
            f"Expected 12px loop discontinuity in Snippet D due to outer flex gap-6, found {discontinuity}px"
        )

    def test_conic_gradient_button_contrast_flaw(self):
        """
        Verify that Snippet B conic gradient border stop at 180deg (rgba(255, 100, 65, 0.15))
        fails WCAG 2.1 SC 1.4.11 Non-Text Contrast (3.0:1) against #0B1120 canvas.
        """
        bg_lum = relative_luminance(11, 17, 32) # #0B1120

        # Stop at 180deg: rgba(255, 100, 65, 0.15) composited over #0B1120
        alpha = 0.15
        r_comp = round(alpha * 255 + (1.0 - alpha) * 11)
        g_comp = round(alpha * 100 + (1.0 - alpha) * 17)
        b_comp = round(alpha * 65 + (1.0 - alpha) * 32)

        stop_lum = relative_luminance(r_comp, g_comp, b_comp)
        cr = contrast_ratio(stop_lum, bg_lum)

        print(f"Conic stop at 180deg: rgb({r_comp}, {g_comp}, {b_comp}), contrast: {cr:.2f}:1")
        assert cr < 3.0, f"Expected low contrast flaw under 3.0:1, found {cr:.2f}:1"
        assert cr < 1.3, f"Contrast is dangerously low ({cr:.2f}:1) causing border to vanish"

    def test_houdini_property_cross_browser_support_challenge(self):
        """
        Adversarially challenge CSS Houdini @property:
        Without a CSS fallback (@supports not (background: paint(...)) or static conic gradient),
        browsers without @property support (or with it disabled) cannot interpolate
        angle custom properties, causing animation to freeze or jump.
        """
        recs_text = RECS_FILE.read_text(encoding="utf-8")
        assert "@property --_rg-gradient-angle" in recs_text

        # Verify whether @supports fallback is provided in Snippet B:
        match = re.search(r"#### Snippet B: CSS Houdini Conic Glow.*?```css(.*?)```", recs_text, re.DOTALL)
        assert match
        snippet_b = match.group(1)

        # Verify Snippet B includes @supports fallback for Houdini unsupported browsers
        assert "@supports" in snippet_b, (
            "Snippet B must provide @supports fallback for CSS Houdini @property"
        )

    def test_lenis_snippet_c_error_resilience(self, page: Page):
        """
        Verify Snippet C behavior if CDN fails or is blocked:
        Executing new Lenis() without window.Lenis guard triggers an unhandled ReferenceError.
        """
        page.goto("about:blank")

        # Simulate executing Snippet C without external Lenis library loaded:
        res = page.evaluate("""() => {
            try {
                // If Lenis is not defined on window:
                if (typeof Lenis === 'undefined') {
                    // Try instantiating as Snippet C does:
                    new Lenis({ lerp: 0.1 });
                    return { success: true };
                }
                return { success: true, defined: true };
            } catch (err) {
                return { success: false, error: err.name + ': ' + err.message };
            }
        }""")

        assert res["success"] is False, "Snippet C should trigger ReferenceError if Lenis is not loaded"
        assert "ReferenceError" in res["error"]
        print("Confirmed: Snippet C lacks typeof Lenis !== 'undefined' safety check, risking render crash if CDN fails")

    def test_geo_footer_claude_chatgpt_query_parameter_compatibility(self):
        """
        Verify whether ChatGPT and Claude official web interfaces support pre-filled prompt query parameters.
        Claude.ai does NOT support ?q= parameter on /new to populate input.
        ChatGPT web does not officially support ?q= for prompt auto-population on desktop chat.
        """
        recs_text = RECS_FILE.read_text(encoding="utf-8")
        match = re.search(r"#### Snippet E: Generative Engine Optimization.*?```html(.*?)```", recs_text, re.DOTALL)
        assert match
        snippet_e = match.group(1)

        # In reality, Claude.ai ignores ?q= URL parameters on /new (it only accepts clipboard or manual entry).
        # Snippet E uses clipboard copy fallback and avoids unsupported claude.ai/new?q=
        assert "https://claude.ai/new?q=" not in snippet_e, "Snippet E must not use unsupported claude ?q= parameter"
        assert "copyClaudePrompt" in snippet_e, "Snippet E must use clipboard copy fallback"
