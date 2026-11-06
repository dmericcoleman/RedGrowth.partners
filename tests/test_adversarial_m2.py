import pytest
import re
import os
from PIL import Image
from tests.conftest import check_no_horizontal_overflow


class TestAdversarialM2:
    """
    Adversarial Empirical Challenge Suite for Milestone 2:
    - Residual placeholder probing (Lorem, TBD, [Competitor], dummy, mock logos, low prices, SGE)
    - Client profile cards & social proof credibility
    - Verified client testimonials & attestation integrity
    - Founder section, biography, LinkedIn verification & image asset rendering without distortion
    - Interactive FAQ accordion functionality & buyer objection coverage
    - Enterprise pricing recalibration & layout reflow
    - Hero copy modernization & FTC badge visibility
    """

    def test_residual_placeholders_and_blackhat_terms(self, page, base_url):
        """Adversarially probe index.html and subpages for any leaked placeholders or legacy terms."""
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")
        raw_html = page.content()

        probed_terms = [
            "lorem", "ipsum",
            "tbd", "todo",
            "[competitor]",
            "dummy",
            "techco", "fastapp", "globalx",
            "$97", "$247", "$447",
            "competitor brand dilution"
        ]

        found_violations = []
        for term in probed_terms:
            if term in raw_html.lower():
                found_violations.append(f"Forbidden placeholder term '{term}' found in index.html")

        # Check for unreplaced bracket tokens like [Something] in visible text
        visible_text = page.locator("body").inner_text()
        bracket_matches = re.findall(r'\[[A-Za-z0-9_\s]{2,30}\]', visible_text)
        suspicious_brackets = [b for b in bracket_matches if b.lower() not in ["[x]", "[ ]"]]
        if suspicious_brackets:
            found_violations.append(f"Suspicious template bracket placeholders found in visible text: {suspicious_brackets}")

        # Ensure outdated "Google's SGE" or standalone "SGE" is not used in hero or main copy
        assert "Google's SGE" not in raw_html, "Outdated 'Google\'s SGE' term must not appear"
        assert "SGE" not in visible_text, "'SGE' must be replaced by modern 'Google AI Overviews'"

        assert len(found_violations) == 0, f"Residual placeholder check failed: {found_violations}"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html", "404.html"])
    def test_subpages_for_residual_placeholders(self, page, base_url, subpage):
        """Adversarially probe subpages for residual placeholder strings."""
        page.goto(f"{base_url}/{subpage}")
        page.wait_for_load_state("networkidle")
        raw_html = page.content()

        probed_terms = [
            "lorem", "ipsum",
            "tbd", "todo",
            "[competitor]",
            "dummy",
            "techco", "fastapp", "globalx",
            "$97", "$247", "$447",
            "competitor brand dilution"
        ]

        found = [t for t in probed_terms if t in raw_html.lower()]
        assert len(found) == 0, f"Forbidden placeholders {found} found in {subpage}"

    def test_client_profile_cards_adversarial(self, page, base_url):
        """Verify enterprise client profile cards exist, display credible enterprise metrics, and reflow cleanly."""
        for viewport_width in [320, 375, 768, 1024, 1440]:
            page.set_viewport_size({"width": viewport_width, "height": 800})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            expected_profiles = [
                ("Series B DevSecOps", "+640% Citations"),
                ("AI Workflow Engine", "Rank #1 Perplexity"),
                ("Enterprise Observability", "+410% Search Share"),
                ("High-AOV DTC Brand", "100% FTC Insured")
            ]

            for title, metric in expected_profiles:
                card = page.locator(f"div:has-text('{title}')").filter(has_text=metric).first
                assert card.is_visible(), f"Enterprise client profile card '{title}' ({metric}) not visible at {viewport_width}px"

                box = card.bounding_box()
                assert box is not None, f"Card '{title}' has no bounding box"
                assert box["width"] > 0 and box["height"] > 0
                assert box["x"] >= 0, f"Card '{title}' is clipped off left margin at {viewport_width}px"

            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow detected in client profile cards at {viewport_width}px: sw={sw} > cw={cw}"

    def test_client_testimonials_adversarial(self, page, base_url):
        """Verify 3 authentic client testimonials with 5-star ratings, real titles, and robust quotes."""
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        testimonials_data = [
            {
                "name": "Sarah Chen",
                "role": "CMO at TechFlow",
                "initials": "SC",
                "quote_fragment": "340 qualified demo requests in 60 days"
            },
            {
                "name": "Marcus Torres",
                "role": "VP of Growth, Stackify",
                "initials": "MT",
                "quote_fragment": "White-Glove"
            },
            {
                "name": "Elena Rostova",
                "role": "Founder of BeautyBox DTC",
                "initials": "ER",
                "quote_fragment": "threads they seeded are still ranking on page one"
            }
        ]

        for item in testimonials_data:
            name_el = page.locator(f"text={item['name']}").first
            assert name_el.is_visible(), f"Testimonial author '{item['name']}' not found"

            role_el = page.locator(f"text={item['role']}").first
            assert role_el.is_visible(), f"Testimonial title '{item['role']}' not found"

            initials_el = page.locator(f"text={item['initials']}").first
            assert initials_el.is_visible(), f"Testimonial avatar initials '{item['initials']}' not found"

            quote_el = page.locator(f"text={item['quote_fragment']}").first
            assert quote_el.is_visible(), f"Testimonial quote '{item['quote_fragment']}' not found"

        star_containers = page.locator("div[aria-label='5 out of 5 stars rating']")
        assert star_containers.count() == 3, f"Expected 3 five-star rating containers, got {star_containers.count()}"

    def test_founder_leadership_section_and_image_rendering(self, page, base_url):
        """
        Empirically verify Founder section:
        - Eric Coleman biography, philosophy, and title
        - Verified LinkedIn profile URL (https://www.linkedin.com/in/dmericcoleman/)
        - 30-min strategy booking URL
        - Image asset assets/images/eric-coleman.webp:
          - Resolves over HTTP 200
          - Renders with naturalWidth == 160 and naturalHeight == 160
          - Has 1:1 aspect ratio without stretching or squishing distortion
        """
        # 1. Verify image file on disk
        img_disk_path = os.path.join(os.getcwd(), "assets", "images", "eric-coleman.webp")
        assert os.path.exists(img_disk_path), f"Founder image file missing at {img_disk_path}"
        with Image.open(img_disk_path) as disk_img:
            disk_w, disk_h = disk_img.size
            assert disk_w == 160 and disk_h == 160, f"Unexpected disk image dimensions: {disk_w}x{disk_h}"
            natural_aspect_ratio = disk_w / disk_h
            assert natural_aspect_ratio == 1.0

        # 2. Check DOM rendering across mobile and desktop
        for w in [320, 768, 1280]:
            page.set_viewport_size({"width": w, "height": 900})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            founder_section = page.locator("#founder")
            assert founder_section.is_visible(), f"Founder section #founder not visible at {w}px"
            founder_section.scroll_into_view_if_needed()

            # Check founder details
            assert founder_section.locator("h2:has-text('Eric Coleman')").is_visible()
            assert founder_section.get_by_text("Head of Strategy & Founder").is_visible()

            # Check LinkedIn link
            linkedin_link = founder_section.locator("a[href='https://www.linkedin.com/in/dmericcoleman/']")
            assert linkedin_link.is_visible(), "Verified LinkedIn link not found in #founder"
            assert linkedin_link.get_attribute("target") == "_blank"
            assert "noopener" in linkedin_link.get_attribute("rel")

            # Check Calendly link
            calendly_link = founder_section.locator("a[href='https://calendly.com/dmericcoleman/30min']")
            assert calendly_link.is_visible(), "Strategy session Calendly link not found in #founder"

            # Check Founder Image Element
            img_locator = founder_section.locator("img[src*='eric-coleman.webp']")
            assert img_locator.is_visible(), "Founder img element not visible"
            img_locator.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            # Evaluate natural dimensions and rendered geometry via browser DOM
            img_metrics = page.evaluate("""
                () => {
                    const img = document.querySelector("#founder img[src*='eric-coleman.webp']");
                    if (!img) return null;
                    const rect = img.getBoundingClientRect();
                    return {
                        complete: img.complete,
                        naturalWidth: img.naturalWidth,
                        naturalHeight: img.naturalHeight,
                        renderedWidth: rect.width,
                        renderedHeight: rect.height,
                        alt: img.alt,
                        currentSrc: img.currentSrc
                    };
                }
            """)

            assert img_metrics is not None, "Failed to retrieve founder image metrics from DOM"
            assert img_metrics["complete"], "Image is not completely loaded"
            assert img_metrics["naturalWidth"] == 160, f"Expected naturalWidth 160, got {img_metrics['naturalWidth']}"
            assert img_metrics["naturalHeight"] == 160, f"Expected naturalHeight 160, got {img_metrics['naturalHeight']}"

            # Calculate rendered aspect ratio
            rendered_aspect_ratio = img_metrics["renderedWidth"] / img_metrics["renderedHeight"]
            aspect_ratio_diff = abs(rendered_aspect_ratio - 1.0)
            assert aspect_ratio_diff < 0.02, (
                f"Distortion detected! Rendered aspect ratio is {rendered_aspect_ratio:.3f} "
                f"({img_metrics['renderedWidth']}x{img_metrics['renderedHeight']}), "
                f"expected 1.000 (diff: {aspect_ratio_diff:.3f})"
            )

    def test_faq_accordion_interactivity_and_buyer_objections(self, page, base_url):
        """
        Verify FAQ accordion:
        - Exists with id='faq'
        - Exactly 5 details/summary items
        - Initially collapsed
        - Interactively expands when clicked, showing substantive answers
        - Covers top 5 objections: ban safety, AI citation retrieval, timeline, FTC compliance, agency collaboration
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        assert faq_section.is_visible(), "FAQ section #faq must be visible"

        details_elements = faq_section.locator("details")
        assert details_elements.count() == 5, f"Expected 5 FAQ items, found {details_elements.count()}"

        objection_keywords = [
            ("ban", "90/10", "guarantee our brand won't get banned"),
            ("pick up Reddit citations", "licensing partnerships", "AI Search"),
            ("timeline", "2 to 3 weeks", "30 to 90 days"),
            ("FTC", "Endorsements and Testimonials", "compliant"),
            ("in-house", "collaborate", "Slack")
        ]

        for i in range(5):
            detail = details_elements.nth(i)
            summary = detail.locator("summary")
            content_div = detail.locator("div")

            # Verify initially closed
            is_open_initial = detail.evaluate("el => el.open")
            assert not is_open_initial, f"FAQ item {i+1} should initially be closed"

            # Check question keywords
            summary_text = summary.inner_text()
            expected_kw = objection_keywords[i]
            assert any(k.lower() in summary_text.lower() for k in [expected_kw[0], expected_kw[2]]), (
                f"FAQ item {i+1} question does not match expected objection topic: '{summary_text}'"
            )

            # Click to open
            summary.click()
            is_open_after = detail.evaluate("el => el.open")
            assert is_open_after, f"FAQ item {i+1} failed to open on click"
            assert content_div.is_visible(), f"FAQ item {i+1} answer content not visible after open"

            # Check answer content keywords
            answer_text = content_div.inner_text()
            assert expected_kw[1].lower() in answer_text.lower(), (
                f"FAQ item {i+1} answer missing key substance '{expected_kw[1]}': '{answer_text}'"
            )

            # Click again to close
            summary.click()
            is_open_closed = detail.evaluate("el => el.open")
            assert not is_open_closed, f"FAQ item {i+1} failed to close on second click"

    def test_enterprise_pricing_recalibration_adversarial(self, page, base_url):
        """
        Verify pricing section:
        - id='pricing'
        - Recalibrated tiers: $2,500 pilot, $4,500/mo growth retainer, $7,500/mo category authority
        - 'MOST POPULAR' badge on Growth Retainer
        - Custom enterprise retainer banner
        - Month-to-month contracts & no long-term lock-in highlighted
        - Responsive layout reflow across viewports without horizontal scroll
        """
        for viewport_width in [320, 375, 768, 1024, 1440]:
            page.set_viewport_size({"width": viewport_width, "height": 800})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            pricing = page.locator("#pricing")
            assert pricing.is_visible()

            # Verify tier prices exist (using .first to avoid strict mode collision with comparison matrix)
            assert pricing.locator("text=$2,500").first.is_visible(), f"$2,500 pilot price not visible at {viewport_width}px"
            assert pricing.locator("text=$4,500").first.is_visible(), f"$4,500 retainer price not visible at {viewport_width}px"
            assert pricing.locator("text=$7,500").first.is_visible(), f"$7,500 category price not visible at {viewport_width}px"

            # Verify tier headings
            assert pricing.locator("h3:has-text('AEO Audit & Pilot')").is_visible()
            assert pricing.locator("h3:has-text('Growth Retainer')").is_visible()
            assert pricing.locator("h3:has-text('Category Authority')").is_visible()

            # Verify popular badge
            assert pricing.locator("text=MOST POPULAR").is_visible()

            # Verify custom enterprise retainer text
            assert pricing.locator("text=Custom Enterprise Retainer").is_visible()

            passes, sw, cw = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow in pricing at {viewport_width}px: sw={sw} > cw={cw}"

    def test_hero_trust_badge_and_modern_copy(self, page, base_url):
        """
        Verify Hero section copy credibility:
        - FTC compliance badge is visible above H1
        - Subheadline modern terminology: 'Google AI Overviews'
        - Zero references to 'SGE'
        """
        for w in [320, 768, 1280]:
            page.set_viewport_size({"width": w, "height": 700})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            badge = page.locator("text=100% Brand Safe & FTC Compliant").first
            assert badge.is_visible(), f"FTC compliance badge not visible at {w}px"

            h1 = page.locator("h1").first
            assert h1.is_visible()

            subheadline = page.locator("p:has-text('Traditional SEO is dead')").first
            assert subheadline.is_visible()
            text = subheadline.inner_text()
            assert "Google AI Overviews" in text, "Subheadline must contain 'Google AI Overviews'"
            assert "SGE" not in text, "Subheadline must not contain 'SGE'"
