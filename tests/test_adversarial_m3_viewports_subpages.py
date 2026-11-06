import pytest
import re
from tests.conftest import check_no_horizontal_overflow

PROBED_VIEWPORTS_M3 = [
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

SUBPAGES_TO_TEST = ["privacy.html", "terms.html", "404.html"]


class TestAdversarialM3ViewportsGeometry:
    """
    Adversarial Challenge Suite 1: Extreme Viewport Geometry (280px to 3840px).
    Evaluates:
    - Zero horizontal overflow across all 13 viewports.
    - Component bounding box containment for Header, Founder card, Pricing cards,
      Section 8 (#fit), and Footer.
    - Zero clipped text across critical conversion containers.
    """

    @pytest.mark.parametrize("width,height,label", PROBED_VIEWPORTS_M3)
    def test_extreme_viewport_horizontal_overflow_zero(self, page, base_url, width, height, label):
        """Verify document.documentElement.scrollWidth <= document.documentElement.clientWidth across all 13 viewports."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        passes, scroll_width, client_width = check_no_horizontal_overflow(page)
        assert passes, (
            f"Horizontal overflow detected at {label} ({width}x{height}): "
            f"scrollWidth={scroll_width}px > clientWidth={client_width}px (Delta: +{scroll_width - client_width}px)"
        )

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
        (1280, 800, "1280px"),
        (1920, 1080, "1920px"),
        (3840, 2160, "3840px"),
    ])
    def test_header_geometry_and_no_overflow(self, page, base_url, width, height, label):
        """Verify header remains fully contained within clientWidth without horizontal overflow."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        header = page.locator("header")
        assert header.is_visible(), f"Header must be visible at {label}"

        box = header.bounding_box()
        assert box is not None, f"Header must have bounding box at {label}"
        assert box["x"] >= -1, f"Header left edge ({box['x']}px) is off-screen at {label}"
        assert box["width"] <= width + 1, f"Header width ({box['width']}px) exceeds viewport width ({width}px) at {label}"

        # Check logo is visible and within bounds
        logo = page.locator("header a[aria-label='RedGrowth.partners Home']").first
        assert logo.is_visible(), f"Logo must be visible at {label}"
        logo_box = logo.bounding_box()
        assert logo_box["x"] >= 0 and logo_box["x"] + logo_box["width"] <= width, (
            f"Logo overflows viewport at {label}"
        )

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
        (1440, 900, "1440px"),
        (3840, 2160, "3840px"),
    ])
    def test_founder_card_geometry_and_no_clipping(self, page, base_url, width, height, label):
        """Verify Founder card (#founder) fits within bounds and text is not clipped."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/#founder")
        page.wait_for_load_state("networkidle")

        founder_section = page.locator("#founder")
        assert founder_section.is_visible(), f"Founder section must be visible at {label}"

        # Evaluate founder card inner container
        card = founder_section.locator(".rounded-3xl").first
        card_box = card.bounding_box()
        assert card_box is not None
        assert card_box["x"] >= -1, f"Founder card left edge ({card_box['x']}px) off-screen at {label}"
        assert card_box["x"] + card_box["width"] <= width + 1, (
            f"Founder card right edge ({card_box['x'] + card_box['width']}px) exceeds viewport width ({width}px) at {label}"
        )

        # Verify founder image loads and is within container
        img = founder_section.locator("img[src*='eric-coleman.webp']")
        assert img.is_visible(), f"Founder image must be visible at {label}"
        img_box = img.bounding_box()
        assert img_box["width"] > 0 and img_box["height"] > 0
        assert img_box["x"] >= 0 and img_box["x"] + img_box["width"] <= width, (
            f"Founder image overflows viewport at {label}"
        )

        # Verify founder heading text does not clip horizontally
        h2 = founder_section.locator("h2:has-text('Eric Coleman')")
        assert h2.is_visible()
        h2_box = h2.bounding_box()
        assert h2_box["x"] + h2_box["width"] <= width, f"Founder H2 overflows viewport at {label}"

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
        (1024, 768, "1024px"),
        (1440, 900, "1440px"),
        (3840, 2160, "3840px"),
    ])
    def test_pricing_cards_geometry_and_no_clipping(self, page, base_url, width, height, label):
        """Verify all 3 pricing cards in #pricing fit within bounds and text does not overflow."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/#pricing")
        page.wait_for_load_state("networkidle")

        pricing_section = page.locator("#pricing")
        assert pricing_section.is_visible()

        cards = pricing_section.locator(".rounded-3xl")
        card_count = cards.count()
        assert card_count >= 3, f"Expected at least 3 pricing cards, found {card_count}"

        for i in range(card_count):
            card = cards.nth(i)
            box = card.bounding_box()
            assert box is not None, f"Pricing card {i} bounding box is None at {label}"
            assert box["x"] >= -1, f"Pricing card {i} left edge ({box['x']}px) is off-screen at {label}"
            assert box["x"] + box["width"] <= width + 1, (
                f"Pricing card {i} right edge ({box['x'] + box['width']}px) exceeds viewport width ({width}px) at {label}"
            )

            # Verify price figures are rendered and not clipped
            price_text = card.locator(".font-black").first
            assert price_text.is_visible(), f"Price figure must be visible in card {i} at {label}"
            price_box = price_text.bounding_box()
            assert price_box["x"] + price_box["width"] <= width, (
                f"Price figure in card {i} overflows viewport at {label}"
            )

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
        (1440, 900, "1440px"),
        (3840, 2160, "3840px"),
    ])
    def test_section_8_fit_geometry_and_no_clipping(self, page, base_url, width, height, label):
        """Verify Section 8 (#fit) and its cards do not cause horizontal scrolling or text clipping."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/#fit")
        page.wait_for_load_state("networkidle")

        fit_section = page.locator("#fit")
        assert fit_section.is_visible(), f"Section 8 (#fit) must be visible at {label}"

        # Check anti-agency standard card and custom enterprise retainer card
        cards = fit_section.locator(".rounded-2xl")
        assert cards.count() >= 2, f"Section 8 should have at least 2 cards, found {cards.count()}"

        for i in range(cards.count()):
            card = cards.nth(i)
            box = card.bounding_box()
            assert box is not None
            assert box["x"] >= -1, f"Section 8 card {i} left edge ({box['x']}px) is off-screen at {label}"
            assert box["x"] + box["width"] <= width + 1, (
                f"Section 8 card {i} right edge ({box['x'] + box['width']}px) exceeds viewport ({width}px) at {label}"
            )

        # Check CTA in Section 8
        cta = fit_section.locator("a[href='#audit']").first
        assert cta.is_visible(), f"Section 8 CTA must be visible at {label}"
        cta_box = cta.bounding_box()
        assert cta_box["x"] >= 0 and cta_box["x"] + cta_box["width"] <= width, (
            f"Section 8 CTA overflows viewport at {label}"
        )

    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
        (375, 667, "375px"),
        (768, 1024, "768px"),
        (1440, 900, "1440px"),
        (3840, 2160, "3840px"),
    ])
    def test_footer_geometry_and_no_overflow(self, page, base_url, width, height, label):
        """Verify footer and links fit within viewport bounds without horizontal scrolling."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        footer = page.locator("footer")
        assert footer.is_visible()
        fbox = footer.bounding_box()
        assert fbox is not None
        assert fbox["x"] >= -1
        assert fbox["x"] + fbox["width"] <= width + 1, f"Footer overflows viewport width at {label}"

        # Verify all links inside footer are within viewport width
        links = footer.locator("a")
        for i in range(links.count()):
            link = links.nth(i)
            if link.is_visible():
                lbox = link.bounding_box()
                assert lbox["x"] >= 0 and lbox["x"] + lbox["width"] <= width + 1, (
                    f"Footer link '{link.inner_text()}' overflows viewport at {label}"
                )


class TestAdversarialM3SubpagesConsistencyAndInteractivity:
    """
    Adversarial Challenge Suite 2: Subpage Consistency & Interactivity.
    Evaluates:
    - Zero mentions of 'Reddit Growth Partners' across privacy.html, terms.html, 404.html.
    - Rebranded to RedGrowth.partners.
    - Mobile hamburger menu drawer opens and closes properly (backdrop click, Escape, link click).
    - Body scroll lock toggled correctly.
    - Stylesheets point to /assets/css/style.css and return HTTP 200.
    - Footer links responsive wrapping without overflow.
    """

    @pytest.mark.parametrize("subpage", SUBPAGES_TO_TEST)
    def test_subpages_rebranding_zero_reddit_growth_partners(self, page, base_url, subpage):
        """Verify subpages have ZERO mentions of 'Reddit Growth Partners' and cite 'RedGrowth.partners'."""
        response = page.goto(f"{base_url}/{subpage}")
        assert response.status == 200, f"{subpage} must return HTTP 200"
        page.wait_for_load_state("networkidle")

        raw_content = page.content()
        title = page.title()
        body_text = page.locator("body").inner_text()

        # Adversarially search for legacy brand string
        assert "reddit growth partners" not in raw_content.lower(), (
            f"Legacy brand string 'Reddit Growth Partners' found in raw HTML of {subpage}"
        )
        assert "reddit growth partners" not in title.lower(), (
            f"Legacy brand string 'Reddit Growth Partners' found in title of {subpage}"
        )
        assert "reddit growth partners" not in body_text.lower(), (
            f"Legacy brand string 'Reddit Growth Partners' found in body text of {subpage}"
        )

        # Verify current brand name is present
        assert "redgrowth.partners" in raw_content.lower() or "redgrowth" in raw_content.lower(), (
            f"Subpage {subpage} must reference 'RedGrowth.partners'"
        )

    @pytest.mark.parametrize("subpage", SUBPAGES_TO_TEST)
    def test_subpages_stylesheet_links_and_http_status(self, page, base_url, subpage):
        """Verify stylesheet links point to style.css and load with HTTP 200."""
        css_responses = []

        def handle_response(resp):
            if "assets/css/style.css" in resp.url:
                css_responses.append(resp)

        page.on("response", handle_response)
        response = page.goto(f"{base_url}/{subpage}")
        assert response.status == 200
        page.wait_for_load_state("networkidle")

        # Check DOM link element
        css_links = page.locator("link[rel='stylesheet']")
        hrefs = [css_links.nth(i).get_attribute("href") for i in range(css_links.count())]
        matching_hrefs = [h for h in hrefs if h and "assets/css/style.css" in h]

        assert len(matching_hrefs) >= 1, (
            f"{subpage} must contain a stylesheet link to 'assets/css/style.css', found: {hrefs}"
        )

        # Verify HTTP response was 200
        assert len(css_responses) >= 1, f"No HTTP response captured for style.css on {subpage}"
        for resp in css_responses:
            assert resp.status == 200, f"style.css returned HTTP {resp.status} on {subpage}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_subpages_mobile_menu_drawer_lifecycle(self, page, base_url, subpage):
        """Verify mobile drawer opens, closes via backdrop, Escape key, and link click, with scroll locking."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        backdrop = page.locator("#mobileMenuBackdrop")

        assert btn.is_visible(), f"Mobile menu button must be visible at 375px on {subpage}"
        assert not menu.is_visible(), f"Mobile menu must be closed initially on {subpage}"

        # 1. Open drawer via button click
        btn.click()
        page.wait_for_timeout(100)
        assert menu.is_visible(), f"Mobile menu must be visible after click on {subpage}"
        assert backdrop.is_visible(), f"Mobile menu backdrop must be visible after click on {subpage}"
        body_overflow = page.evaluate("() => document.body.style.overflow")
        assert body_overflow == "hidden", f"Body overflow must be 'hidden' when menu is open on {subpage}"

        # 2. Close drawer via clicking outside (backdrop area below menu drawer)
        # Menu drawer reaches down to ~450px on 375x667 screen; click exposed backdrop at y=550
        page.mouse.click(180, 550)
        page.wait_for_timeout(150)
        assert not menu.is_visible(), f"Mobile menu must close after clicking outside on backdrop on {subpage}"
        body_overflow = page.evaluate("() => document.body.style.overflow")
        assert body_overflow != "hidden", f"Body overflow lock must be released after backdrop click on {subpage}"

        # 3. Re-open and close via Escape key
        btn.click()
        page.wait_for_timeout(150)
        assert menu.is_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        assert not menu.is_visible(), f"Mobile menu must close on Escape key press on {subpage}"
        body_overflow = page.evaluate("() => document.body.style.overflow")
        assert body_overflow != "hidden", f"Body overflow lock must be released after Escape key on {subpage}"

        # 4. Re-open and close via navigation link click
        btn.click()
        page.wait_for_timeout(150)
        assert menu.is_visible()
        # Intercept navigation default action so we verify closeDrawer DOM transition on this page
        page.evaluate("""() => {
            const firstLink = document.querySelector('#mobileMenu a');
            if (firstLink) firstLink.addEventListener('click', (e) => e.preventDefault(), true);
        }""")
        nav_link = menu.locator("a").first
        nav_link.click()
        page.wait_for_timeout(150)
        assert not menu.is_visible(), f"Mobile menu must close when link is clicked on {subpage}"
        body_overflow = page.evaluate("() => document.body.style.overflow")
        assert body_overflow != "hidden", f"Body overflow lock must be released after link click on {subpage}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    @pytest.mark.parametrize("width,height,label", [
        (280, 653, "280px"),
        (320, 568, "320px"),
    ])
    def test_subpages_footer_links_and_responsive_wrapping(self, page, base_url, subpage, width, height, label):
        """Verify legal page footer links wrap responsively without horizontal overflow at 280px and 320px."""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")

        passes, sw, cw = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow on {subpage} at {label}: scrollWidth={sw}px > clientWidth={cw}px"

        footer = page.locator("footer")
        assert footer.is_visible()

        # Check footer links container uses flex-wrap
        links_container = footer.locator(".flex-wrap").first
        assert links_container.is_visible(), f"Footer links container on {subpage} must have flex-wrap"

        # Check individual links are within bounds
        links = footer.locator("a")
        assert links.count() >= 2
        for i in range(links.count()):
            l = links.nth(i)
            if l.is_visible():
                lbox = l.bounding_box()
                assert lbox["x"] >= 0 and lbox["x"] + lbox["width"] <= width + 1, (
                    f"Footer link '{l.inner_text()}' overflows viewport at {label} on {subpage}"
                )


class TestAdversarialM3OverflowAndConsoleIntegrity:
    """
    Adversarial Challenge Suite 3: DOM Mutation, Overflow Cheating & Console Integrity.
    Evaluates:
    - True unmasked overflow: removing overflow-x: hidden from body and evaluating
      whether any elements cause horizontal scrollWidth > clientWidth.
    - Zero uncaught console errors, page errors, or failed requests across all pages.
    """

    @pytest.mark.parametrize("width,height,label", PROBED_VIEWPORTS_M3)
    def test_unmasked_overflow_when_body_overflow_x_visible(self, page, base_url, width, height, label):
        """
        Adversarially removes overflow-x: hidden / overflow-x-hidden from body and root.
        Verifies that document.documentElement.scrollWidth <= document.documentElement.clientWidth
        STILL holds with zero horizontal overflow, proving overflow-x: hidden is NOT masking rogue elements.
        """
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Dynamically unmask overflow
        page.evaluate("""() => {
            document.body.style.overflowX = 'visible';
            document.body.classList.remove('overflow-x-hidden');
            document.documentElement.style.overflowX = 'visible';
        }""")
        page.wait_for_timeout(100)

        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")

        assert scroll_width <= client_width, (
            f"Unmasked horizontal overflow detected at {label} ({width}x{height}) when body overflow-x: visible! "
            f"scrollWidth={scroll_width}px > clientWidth={client_width}px (Delta: +{scroll_width - client_width}px)"
        )

    def test_no_elements_overflow_document_bounds_when_unmasked(self, page, base_url):
        """
        Deep DOM scan across all visible elements at 320px mobile viewport to ensure
        no element extends outside the viewport bounds unless clipped by an explicit container.
        """
        page.set_viewport_size({"width": 320, "height": 568})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        offenders = page.evaluate("""() => {
            const cw = document.documentElement.clientWidth;
            const res = [];
            document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                // Check if element extends outside right boundary (with 1px tolerance)
                if (r.right > cw + 1 || r.left < -1) {
                    const s = window.getComputedStyle(el);
                    if (s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && r.width > 0 && r.height > 0) {
                        // Check if clipped by an ancestor with overflow: hidden
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
                                className: (typeof el.className === 'string') ? el.className.slice(0, 50) : '',
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

        assert len(offenders) == 0, (
            f"Found {len(offenders)} unclipped overflowing elements at 320px: {offenders}"
        )

    @pytest.mark.parametrize("page_path", ["/", "/privacy.html", "/terms.html", "/404.html"])
    def test_clean_console_with_zero_uncaught_errors(self, page, base_url, page_path):
        """Verify that visiting any page results in zero console errors or uncaught page exceptions."""
        console_errors = []
        page_errors = []

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        response = page.goto(f"{base_url}{page_path}")
        assert response.status == 200
        page.wait_for_load_state("networkidle")

        assert len(page_errors) == 0, f"Uncaught JavaScript exceptions on {page_path}: {page_errors}"
        assert len(console_errors) == 0, f"Console error logs detected on {page_path}: {console_errors}"
