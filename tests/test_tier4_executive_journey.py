import pytest


@pytest.mark.tier4
class TestTier4ExecutiveJourney:
    """
    Tier 4: Real-World Workload Scenarios.
    Simulates a high-intent executive buyer evaluating RedGrowth.partners:
    landing, examining value propositions, reviewing proof and testimonials,
    verifying founder credentials, evaluating pricing models, reading FAQs,
    and submitting an audit request with clean inline feedback and zero console errors.
    """

    def test_executive_buyer_end_to_end_journey(self, page, base_url):
        # 1. Landing on Homepage
        response = page.goto(f"{base_url}/")
        assert response.status == 200, "Homepage must return HTTP 200 OK"
        assert "RedGrowth.partners" in page.title()

        # 2. Inspect Hero Value Proposition
        h1 = page.locator("h1").first
        assert h1.is_visible()
        page_text = page.content()
        assert "Google's SGE" not in page_text, "Hero must use modern AI Overview terminology"

        # 3. Explore Framework and Section 3 Visual Proof
        framework_section = page.locator("#framework, section:has-text('Framework')").first
        framework_section.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        assert "<!-- Blank space as requested -->" not in page.content(), "Void placeholder must not exist"

        # 4. Review Case Studies and Testimonials
        results_section = page.locator("#results, section:has-text('Outcomes'), section:has-text('Proof')").first
        results_section.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        assert "[Competitor]" not in page.content(), "Testimonials must have no template placeholders"

        # 5. Verify Founder Credentials
        founder_section = page.locator("section:has-text('Eric Coleman')").or_(page.locator("#founder")).first
        if founder_section.count() > 0:
            founder_section.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            founder_img = page.locator("img[src*='eric-coleman.webp']")
            assert founder_img.count() >= 1, "Founder image must be present"
            assert page.locator("a[href*='linkedin.com/in/dmericcoleman']").count() >= 1

        # 6. Evaluate Enterprise Pricing
        pricing_section = page.locator("#pricing").first
        pricing_section.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        pricing_text = pricing_section.inner_text()
        assert "$97" not in pricing_text, "Pricing should not show $97 low-ticket dissonance"
        assert "$247" not in pricing_text, "Pricing should not show $247 low-ticket dissonance"

        # 7. Check FAQ Accordion
        faq_section = page.locator("#faq").first
        if faq_section.count() > 0:
            faq_section.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            faq_text = faq_section.inner_text()
            assert "Reddit" in faq_text or "ban" in faq_text.lower()

        # 8. Submit Audit Request (with mocked backend)
        audit_section = page.locator("#audit").first
        audit_section.scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        page.route("**/formspree.io/**", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"ok": true}'
        ))

        form = page.locator("#auditForm")
        assert form.is_visible()

        if form.locator("input[name='name']").count() > 0:
            form.locator("input[name='name']").fill("Jordan Croft (VP Growth)")
        form.locator("input[name='domain']").fill("https://enterprise-saas.io")
        form.locator("input[name='email']").fill("jordan@enterprise-saas.io")
        if form.locator("textarea[name='notes']").count() > 0:
            form.locator("textarea[name='notes']").fill("Evaluating AEO readiness for Q3 budget cycle.")

        page.locator("#submitAuditBtn").click()
        page.wait_for_timeout(500)

        # Verify inline success state
        assert page.locator("#auditSuccess").is_visible()
        assert len(page._dialogs) == 0, "No disruptive alert dialogs during submission"

        # 9. Verify Subpages Branding Consistency
        page.goto(f"{base_url}/privacy.html")
        assert "Reddit Growth Partners" not in page.title()
        assert "RedGrowth.partners" in page.title()

        page.goto(f"{base_url}/terms.html")
        assert "Reddit Growth Partners" not in page.title()
        assert "RedGrowth.partners" in page.title()

        # 10. Verify Zero Console Errors
        critical_errors = [
            err for err in page._console_errors
            if "google-analytics" not in err and "clarity.ms" not in err and "googletagmanager" not in err
        ]
        assert len(page._page_errors) == 0, f"Page errors logged during journey: {page._page_errors}"
        assert len(critical_errors) == 0, f"Console errors logged during journey: {critical_errors}"
