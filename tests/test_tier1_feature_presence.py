import re
import pytest


@pytest.mark.tier1
class TestTier1FeaturePresence:
    """
    Tier 1: Feature Coverage & Presence.
    Verifies that all core features cataloged in PROJECT.md (F1 to F16)
    are present in the DOM with authoritative expected content.
    """

    def test_hero_section_presence_and_structure(self, page, base_url):
        """F1/F2: Verify hero headline, subheadline, CTAs, and dashboard visual."""
        page.goto(f"{base_url}/")
        
        # Verify page title
        assert "RedGrowth.partners" in page.title()
        
        # Verify H1 presence
        h1 = page.locator("h1")
        assert h1.count() >= 1
        h1_text = h1.first.inner_text()
        assert len(h1_text.strip()) > 10, "H1 text must be substantial"
        assert "AI" in h1_text or "Search" in h1_text or "Reddit" in h1_text
        
        # Primary CTA button in hero
        hero_cta = page.locator("a[href='#audit']").first
        assert hero_cta.is_visible()
        
        # Hero dashboard preview image
        hero_img = page.locator("img[src*='dashboard'], img[src*='visibility']")
        assert hero_img.count() >= 1

    def test_hero_copy_modernization_and_ftc_badge(self, page, base_url):
        """F5: Subheadline must reference 'Google AI Overviews' (not outdated 'Google's SGE') and show FTC compliance badge."""
        page.goto(f"{base_url}/")
        page_content = page.content()
        
        # Verify legacy 'SGE' is not used in hero copy
        assert "Google's SGE" not in page_content, "Outdated 'Google\'s SGE' should be modernized to 'Google AI Overviews'"
        
        # Verify modern AI search terminology is present
        assert "AI Overviews" in page_content or "Google AI" in page_content
        
        # Verify FTC compliance trust badge is visible
        badge = page.locator("text=100% Brand Safe & FTC Compliant").or_(page.locator("text=FTC Compliant"))
        assert badge.count() >= 1, "Visible FTC compliance trust badge must be present"

    def test_section3_proof_card_integrated(self, page, base_url):
        """F4: Section 3 must have integrated proof cards and citations (no empty void comment/column)."""
        page.goto(f"{base_url}/")
        page_content = page.content()
        
        # Must not contain placeholder comment indicating blank void
        assert "<!-- Blank space as requested -->" not in page_content, "Section 3 empty void placeholder must be replaced with proof content"
        
        # Proof citations or cards must exist in Section 3 / Framework
        proof_cards = page.locator("section#framework, section:has-text('Framework')").locator("img, .proof-card, [class*='card']")
        assert proof_cards.count() >= 1, "Section 3 must integrate visual proof cards showing AI/Reddit citations"

    def test_credible_social_proof_no_dummy_logos(self, page, base_url):
        """F6: Mock dummy logos (TECHCO, FASTAPP, STACKIFY, GLOBALX) must be replaced with credible enterprise profiles."""
        page.goto(f"{base_url}/")
        page_content = page.content()
        
        dummy_logos = ["TECHCO", "FASTAPP", "STACKIFY", "GLOBALX"]
        for dummy in dummy_logos:
            assert dummy not in page_content, f"Mock placeholder logo '{dummy}' must not appear on the production site"
            
        # Verify presence of credible enterprise profile badges or client references
        proof_section = page.locator("section:has-text('Trusted by'), section:has-text('Enterprise'), div:has-text('Series')").first
        assert proof_section.is_visible()

    def test_client_testimonials_and_no_bracket_placeholders(self, page, base_url):
        """F7: Testimonials must be present and unreplaced bracket placeholder '[Competitor]' must be eliminated."""
        page.goto(f"{base_url}/")
        page_content = page.content()
        
        # Must not contain unreplaced bracket token
        assert "[Competitor]" not in page_content, "Unreplaced template placeholder '[Competitor]' must be fixed"
        
        # Verified testimonials should be present
        testimonials = page.locator("text=Sarah Chen").or_(page.locator("text=Marcus Torres")).or_(page.locator("text=Elena Rostova"))
        assert testimonials.count() >= 1, "Authoritative client testimonials must be present"

    def test_enterprise_pricing_structure(self, page, base_url):
        """F8: Pricing section must reflect enterprise agency models and eliminate low-barrier dissonance ($97/kw, $247/mo)."""
        page.goto(f"{base_url}/")
        pricing_section = page.locator("#pricing")
        assert pricing_section.count() >= 1, "Pricing section with id='pricing' must exist"
        
        pricing_text = pricing_section.inner_text()
        
        # Verify elimination of low-barrier dissonance
        assert "$97" not in pricing_text, "Low-ticket $97/kw dissonance must be removed from enterprise pricing"
        assert "$247" not in pricing_text, "Low-ticket $247/mo dissonance must be removed from enterprise pricing"
        assert "Competitor Brand Dilution" not in pricing_text, "Dissonant low-end feature title must be removed"
        
        # Verify enterprise agency tiers (e.g. Audit & Pilot, Growth Retainer, Enterprise Category Authority)
        assert ("Audit" in pricing_text or "Pilot" in pricing_text)
        assert ("Retainer" in pricing_text or "Growth" in pricing_text)

    def test_founder_leadership_section_presence(self, page, base_url):
        """F9: Founder section must feature Eric Coleman with image eric-coleman.webp and verified LinkedIn link."""
        page.goto(f"{base_url}/")
        
        # Founder section locator
        founder_section = page.locator("section:has-text('Eric Coleman')").or_(page.locator("#founder"))
        assert founder_section.count() >= 1, "Dedicated Founder section highlighting Eric Coleman must exist"
        
        # Founder image eric-coleman.webp
        founder_img = page.locator("img[src*='eric-coleman.webp']")
        assert founder_img.count() >= 1, "Founder image 'eric-coleman.webp' must be present"
        assert founder_img.first.is_visible()
        
        # Founder LinkedIn profile link
        linkedin_link = page.locator("a[href*='linkedin.com/in/dmericcoleman']")
        assert linkedin_link.count() >= 1, "Verified LinkedIn link for Eric Coleman must exist"

    def test_comprehensive_faq_accordion_presence(self, page, base_url):
        """F10: Interactive FAQ accordion (#faq) addressing top objections (Reddit safety, FTC compliance, etc.)."""
        page.goto(f"{base_url}/")
        
        # FAQ section locator
        faq_section = page.locator("#faq")
        assert faq_section.count() >= 1, "FAQ section with id='faq' must exist"
        
        faq_text = faq_section.inner_text()
        # Verify coverage of core buyer objections
        assert ("Reddit" in faq_text or "ban" in faq_text.lower()), "FAQ must address Reddit safety"
        assert ("FTC" in faq_text or "compliance" in faq_text.lower()), "FAQ must address FTC compliance"

    def test_navigation_header_links_presence(self, page, base_url):
        """F11: Top navigation header must contain all essential navigation anchors."""
        page.goto(f"{base_url}/")
        
        header = page.locator("header").first
        assert header.is_visible()
        
        # Core navigation anchor links
        nav_anchors = ["#framework", "#compliance", "#results", "#pricing", "#audit"]
        for anchor in nav_anchors:
            link = page.locator(f"header a[href='{anchor}']").or_(page.locator(f"header a[href*='{anchor}']"))
            assert link.count() >= 1, f"Header navigation must contain link to '{anchor}'"

    def test_clickable_contact_info(self, page, base_url):
        """F13: Direct access email and phone must be clickable mailto: and tel: links."""
        page.goto(f"{base_url}/")
        
        # Email mailto link
        email_link = page.locator("a[href='mailto:eric@redgrowth.partners']")
        assert email_link.count() >= 1, "Email 'eric@redgrowth.partners' must be a clickable mailto: link"
        
        # Phone tel link
        phone_link = page.locator("a[href^='tel:']")
        assert phone_link.count() >= 1, "Phone '+1 (916) 907-6120' must be a clickable tel: link"

    def test_audit_form_fields_and_status_elements(self, page, base_url):
        """F14: Audit form must contain required input fields (name, domain, email) and status containers."""
        page.goto(f"{base_url}/")
        
        # Form element
        form = page.locator("#auditForm")
        assert form.count() >= 1, "Audit form with id='auditForm' must exist"
        
        # Required input fields
        assert form.locator("input[name='domain']").count() >= 1, "Input name='domain' is required"
        assert form.locator("input[name='email']").count() >= 1, "Input name='email' is required"
        assert form.locator("input[name='name']").count() >= 1, "Input name='name' (Full Name) is required"
        
        # Status containers
        assert page.locator("#auditSuccess").count() >= 1, "Status element id='auditSuccess' must exist"
        assert page.locator("#auditError").count() >= 1, "Status element id='auditError' must exist"
