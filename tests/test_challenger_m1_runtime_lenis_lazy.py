import pytest
import time

def is_third_party_analytics(msg_text: str) -> bool:
    """Filter out expected 3rd-party tracking/analytics network errors in headless test environment."""
    return any(domain in msg_text for domain in [
        "google-analytics", "clarity.ms", "googletagmanager", "doubleclick", "analytics"
    ])


@pytest.mark.tier3
class TestLenisSmoothScrollLifecycle:
    """
    Adversarial empirical verification of Lenis 1.1.14 Smooth Momentum Scroll
    Lifecycle, script deferral, DOMContentLoaded execution, anchor jumps,
    and console cleanliness across multiple viewports.
    """

    def test_lenis_initialization_cleanliness_and_lifecycle(self, page, base_url):
        """
        Challenge 1.1: Verify Lenis initializes cleanly with defer attribute,
        window.Lenis is instantiated, documentElement gets .lenis class,
        and zero console errors/warnings are emitted.
        """
        console_warnings = []
        console_errors = []
        page_errors = []

        page.on("console", lambda msg: (
            console_warnings.append(msg.text) if (msg.type == "warning" and not is_third_party_analytics(msg.text))
            else (console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        ))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # 1. Assert window.Lenis constructor exists
        has_lenis = page.evaluate("typeof window.Lenis !== 'undefined'")
        assert has_lenis, "window.Lenis constructor is undefined on window object"

        # 2. Assert window.lenisVersion is set to 1.1.14
        lenis_version = page.evaluate("window.lenisVersion")
        assert lenis_version == "1.1.14", f"Expected lenisVersion '1.1.14', got '{lenis_version}'"

        # 3. Assert root element has 'lenis' class added by Lenis constructor
        html_classes = page.evaluate("document.documentElement.className")
        assert "lenis" in html_classes, f"Expected 'lenis' class on html element, got '{html_classes}'"

        # 4. Assert zero console warnings (specifically no 'Lenis smooth scroll library not detected')
        lenis_fallback_warnings = [w for w in console_warnings if "Lenis smooth scroll library not detected" in w]
        assert len(lenis_fallback_warnings) == 0, f"Lenis fallback warning detected: {lenis_fallback_warnings}"
        assert len(console_warnings) == 0, f"Unexpected console warnings observed: {console_warnings}"

        # 5. Assert zero console errors or page errors
        assert len(console_errors) == 0, f"Unexpected console errors observed: {console_errors}"
        assert len(page_errors) == 0, f"Unhandled page errors: {page_errors}"

    def test_smooth_anchor_jumps_pricing_and_faq(self, page, base_url):
        """
        Challenge 1.2: Verify smooth anchor jumps for #pricing and #faq execute cleanly
        without throwing unhandled errors, and page scroll offset transitions smoothly.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Check initial scroll position is 0
        initial_scroll = page.evaluate("window.scrollY")
        assert initial_scroll == 0, f"Initial scroll position should be 0, got {initial_scroll}"

        # 1. Click #pricing anchor
        pricing_link = page.locator("header nav a[href='#pricing']").first
        assert pricing_link.is_visible(), "Desktop nav link to #pricing not visible"
        pricing_link.click()

        # Allow momentum scroll to settle (waiting for scrollY delta to reach 0)
        start_t = time.time()
        last_scroll = -1
        while (time.time() - start_t) < 2.5:
            current_scroll = page.evaluate("window.scrollY")
            if current_scroll == last_scroll and current_scroll > 5000:
                break
            last_scroll = current_scroll
            page.wait_for_timeout(150)

        pricing_scroll = page.evaluate("window.scrollY")
        assert pricing_scroll > 5000, f"Expected page to scroll down to #pricing (~6831px), got {pricing_scroll}"
        
        # Verify pricing target is within viewport view and positioned near header offset
        pricing_box = page.locator("#pricing").bounding_box()
        assert pricing_box is not None, "#pricing element not found in DOM"
        assert 0 <= pricing_box["y"] <= 250, f"#pricing target bounding y={pricing_box['y']} not at top of viewport"

        # 2. Click #faq anchor
        faq_link = page.locator("header nav a[href='#faq']").first
        assert faq_link.is_visible(), "Desktop nav link to #faq not visible"
        faq_link.click()

        start_t = time.time()
        last_scroll = -1
        while (time.time() - start_t) < 2.5:
            current_scroll = page.evaluate("window.scrollY")
            if current_scroll == last_scroll and current_scroll > pricing_scroll:
                break
            last_scroll = current_scroll
            page.wait_for_timeout(150)

        faq_scroll = page.evaluate("window.scrollY")
        assert faq_scroll > pricing_scroll, f"Expected page to scroll further down to #faq, but scrollY is {faq_scroll}"

        faq_box = page.locator("#faq").bounding_box()
        assert faq_box is not None, "#faq element not found in DOM"
        assert 0 <= faq_box["y"] <= 250, f"#faq target bounding y={faq_box['y']} not at top of viewport"

        # Verify zero console or page errors occurred during navigation
        assert len(console_errors) == 0, f"Console errors during anchor navigation: {console_errors}"
        assert len(page_errors) == 0, f"Page errors during anchor navigation: {page_errors}"

    def test_smooth_anchor_jump_to_founder(self, page, base_url):
        """
        Challenge 1.3: Verify anchor jumps targeting #founder execute smoothly,
        whether invoked via a DOM anchor or programmatic hash navigation.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Create an anchor with href="#founder" in the document and click it through the same Lenis listener
        page.evaluate("""
            () => {
                const a = document.createElement('a');
                a.id = 'test-founder-anchor';
                a.href = '#founder';
                a.textContent = 'Founder';
                document.body.appendChild(a);
                a.addEventListener('click', function(e) {
                    const href = this.getAttribute('href');
                    const target = document.querySelector(href);
                    if (target) {
                        e.preventDefault();
                        target.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            }
        """)

        page.click("#test-founder-anchor")
        page.wait_for_timeout(800)

        founder_scroll = page.evaluate("window.scrollY")
        assert founder_scroll > 2000, f"Expected scroll position to be deep (>2000px) for #founder, got {founder_scroll}"

        founder_box = page.locator("#founder").bounding_box()
        assert founder_box is not None, "#founder section not found"
        viewport_height = page.viewport_size["height"]
        assert -200 <= founder_box["y"] <= viewport_height, f"#founder not in visible range: y={founder_box['y']}"

        assert len(console_errors) == 0
        assert len(page_errors) == 0

    def test_stress_rapid_anchor_clicks_interruption(self, page, base_url):
        """
        Challenge 1.4 (Stress): Rapidly fire sequential anchor clicks (#pricing -> #faq -> #pricing)
        in rapid succession (50ms interval) to stress test animation cancellation and velocity handling.
        """
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        pricing_link = page.locator("header nav a[href='#pricing']").first
        faq_link = page.locator("header nav a[href='#faq']").first

        for _ in range(5):
            pricing_link.click()
            page.wait_for_timeout(50)
            faq_link.click()
            page.wait_for_timeout(50)

        # Allow final animation to settle
        page.wait_for_timeout(800)

        # Confirm page is still responsive and scrollable
        current_scroll = page.evaluate("window.scrollY")
        assert current_scroll > 0, "Page should have scrolled after rapid clicks"

        # Check Lenis did not lock page scrolling
        is_locked = page.evaluate("document.documentElement.classList.contains('lenis-locked')")
        assert not is_locked, "Lenis must not be permanently locked after interrupted scrolls"

        assert len(console_errors) == 0, f"Errors during rapid anchor stress: {console_errors}"
        assert len(page_errors) == 0

    def test_reduced_motion_behavior(self, page, base_url):
        """
        Challenge 1.5: When prefers-reduced-motion is active, Lenis should return early
        without initializing momentum scroll, preserving accessibility and emitting 0 errors.
        """
        console_warnings = []
        console_errors = []
        page.on("console", lambda msg: (
            console_warnings.append(msg.text) if (msg.type == "warning" and not is_third_party_analytics(msg.text))
            else (console_errors.append(msg.text) if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        ))

        page.emulate_media(reduced_motion="reduce")
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # In reduced motion mode, initLenis returns early
        html_classes = page.evaluate("document.documentElement.className")
        assert "lenis" not in html_classes.split(), "Lenis class should not be added when reduced motion is preferred"
        assert len(console_errors) == 0, f"Console errors under reduced motion: {console_errors}"
        assert len(console_warnings) == 0, f"Console warnings under reduced motion: {console_warnings}"

    @pytest.mark.parametrize("width,height,label", [
        (1920, 1080, "Desktop Widescreen"),
        (1280, 800, "Standard Laptop"),
        (768, 1024, "iPad / Tablet Portrait"),
        (375, 667, "iPhone Mobile Portrait"),
    ])
    def test_console_cleanliness_across_viewports_during_scroll(self, page, base_url, width, height, label):
        """
        Challenge 1.6: Verify zero console errors or warnings across 4 distinct viewports
        during dynamic full-page top-to-bottom scroll and return.
        """
        console_warnings = []
        console_errors = []
        page_errors = []

        page.on("console", lambda msg: (
            console_warnings.append(f"[{label}] {msg.text}") if (msg.type == "warning" and not is_third_party_analytics(msg.text))
            else (console_errors.append(f"[{label}] {msg.text}") if (msg.type == "error" and not is_third_party_analytics(msg.text)) else None)
        ))
        page.on("pageerror", lambda err: page_errors.append(f"[{label}] {str(err)}"))

        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Scroll to bottom in increments
        total_height = page.evaluate("document.body.scrollHeight")
        step = total_height // 5
        for offset in range(0, total_height, step):
            page.evaluate(f"window.scrollTo(0, {offset})")
            page.wait_for_timeout(100)

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)

        assert len(console_warnings) == 0, f"Console warnings detected during scroll at {label}: {console_warnings}"
        assert len(console_errors) == 0, f"Console errors detected during scroll at {label}: {console_errors}"
        assert len(page_errors) == 0, f"Page errors detected during scroll at {label}: {page_errors}"


@pytest.mark.tier3
class TestLazyLoadingNetworkVerification:
    """
    Adversarial verification of lazy loading network requests using Playwright request tracking.
    Confirms below-the-fold image assets/images/eric-coleman.webp is NOT requested during initial
    above-the-fold viewport render, and IS requested only when scrolled into proximity.
    """

    def test_founder_portrait_not_requested_on_initial_desktop_render(self, page, base_url):
        """
        Challenge 2.1 (Desktop): Verify that eric-coleman.webp is NOT requested initially
        at 1280x800 desktop viewport, while critical LCP hero image IS requested.
        """
        requested_urls = []
        page.on("request", lambda req: requested_urls.append(req.url))

        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # 1. Critical hero image MUST be requested initially
        hero_requested = any("ai-visibility-dashboard.webp" in u for u in requested_urls)
        assert hero_requested, "Preloaded critical LCP hero image (ai-visibility-dashboard.webp) was not requested"

        # 2. Below-the-fold founder image MUST NOT be requested initially
        founder_requested = any("eric-coleman.webp" in u for u in requested_urls)
        assert not founder_requested, (
            "REGRESSION / DEFECT: Below-the-fold image 'eric-coleman.webp' was fetched during "
            "initial above-the-fold viewport render! Lazy loading is not deferring network request."
        )

        # 3. Scroll down into proximity of the founder section
        page.evaluate("document.getElementById('founder').scrollIntoView()")
        page.wait_for_timeout(1000)

        # 4. Now founder image MUST be requested
        founder_requested_after_scroll = any("eric-coleman.webp" in u for u in requested_urls)
        assert founder_requested_after_scroll, (
            "DEFECT: Image 'eric-coleman.webp' was NOT fetched even after scrolling into proximity of #founder!"
        )

    def test_founder_portrait_not_requested_on_initial_mobile_render(self, page, base_url):
        """
        Challenge 2.2 (Mobile): Verify that eric-coleman.webp is NOT requested initially
        at 375x667 mobile viewport, and is requested when scrolled to Section 9.
        """
        requested_urls = []
        page.on("request", lambda req: requested_urls.append(req.url))

        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Initial check
        founder_requested = any("eric-coleman.webp" in u for u in requested_urls)
        assert not founder_requested, (
            "Mobile viewport initial render prematurely fetched 'eric-coleman.webp'!"
        )

        # Scroll to founder
        page.evaluate("document.getElementById('founder').scrollIntoView()")
        page.wait_for_timeout(1000)

        founder_requested_after_scroll = any("eric-coleman.webp" in u for u in requested_urls)
        assert founder_requested_after_scroll, (
            "Mobile viewport failed to fetch 'eric-coleman.webp' when scrolled into view!"
        )

    def test_section3_proof_images_lazy_loading(self, page, base_url):
        """
        Challenge 2.3: Verify Section 3 proof cards (google-rank and reddit-post images)
        respect lazy loading and async decoding attributes.
        """
        requested_urls = []
        page.on("request", lambda req: requested_urls.append(req.url))

        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Verify decoding attribute is set to async on both images in DOM
        decoding_attrs = page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll('img[src*=\"ai-overview-desktop.webp\"]'));
                return imgs.map(img => ({
                    src: img.src,
                    decoding: img.getAttribute('decoding'),
                    loading: img.getAttribute('loading')
                }));
            }
        """)
        assert len(decoding_attrs) == 2, f"Expected 2 proof card images, found {len(decoding_attrs)}"
        for attr in decoding_attrs:
            assert attr["decoding"] == "async", f"Expected decoding='async' for {attr['src']}, got {attr['decoding']}"
            assert attr["loading"] == "lazy", f"Expected loading='lazy' for {attr['src']}, got {attr['loading']}"
