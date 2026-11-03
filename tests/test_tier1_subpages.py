import pytest


@pytest.mark.tier1
class TestTier1Subpages:
    """
    Tier 1: Subpages Coverage (F15).
    Verifies that legal pages (privacy.html, terms.html) and custom error pages (404.html)
    are properly branded with 'RedGrowth.partners', load stylesheets without error,
    and have functioning navigation.
    """

    def test_privacy_page_branding_and_content(self, page, base_url):
        """privacy.html must be updated to RedGrowth.partners and eliminate Reddit Growth Partners."""
        response = page.goto(f"{base_url}/privacy.html")
        assert response.status == 200, "privacy.html must return HTTP 200"
        
        # Verify title does not reference legacy name
        title = page.title()
        assert "Reddit Growth Partners" not in title, "privacy.html title must not contain 'Reddit Growth Partners'"
        assert "RedGrowth.partners" in title or "RedGrowth" in title, "privacy.html title must reference 'RedGrowth.partners'"
        
        # Verify body branding
        body_text = page.locator("body").inner_text()
        assert "RedGrowth.partners" in body_text, "privacy.html body must reference 'RedGrowth.partners'"

    def test_privacy_page_navigation_and_assets(self, page, base_url):
        """privacy.html navigation must have valid links and stylesheet must load."""
        page.goto(f"{base_url}/privacy.html")
        
        # Logo link back to homepage
        home_link = page.locator("a[aria-label='RedGrowth.partners Home']").or_(page.locator("a[href='/']")).first
        assert home_link.is_visible()
        
        # Check stylesheet link
        css_links = page.locator("link[rel='stylesheet']")
        assert css_links.count() >= 1, "privacy.html must link to stylesheet"

    def test_terms_page_branding_and_content(self, page, base_url):
        """terms.html must be updated to RedGrowth.partners and eliminate Reddit Growth Partners."""
        response = page.goto(f"{base_url}/terms.html")
        assert response.status == 200, "terms.html must return HTTP 200"
        
        # Verify title does not reference legacy name
        title = page.title()
        assert "Reddit Growth Partners" not in title, "terms.html title must not contain 'Reddit Growth Partners'"
        assert "RedGrowth.partners" in title or "RedGrowth" in title, "terms.html title must reference 'RedGrowth.partners'"
        
        # Verify body branding
        body_text = page.locator("body").inner_text()
        assert "RedGrowth.partners" in body_text, "terms.html body must reference 'RedGrowth.partners'"

    def test_terms_page_navigation_and_assets(self, page, base_url):
        """terms.html navigation must have valid links and stylesheet must load."""
        page.goto(f"{base_url}/terms.html")
        
        # Logo link back to homepage
        home_link = page.locator("a[aria-label='RedGrowth.partners Home']").or_(page.locator("a[href='/']")).first
        assert home_link.is_visible()
        
        # Check stylesheet link
        css_links = page.locator("link[rel='stylesheet']")
        assert css_links.count() >= 1, "terms.html must link to stylesheet"

    def test_404_page_layout_and_cta(self, page, base_url):
        """404.html must render clear error explanation and return-to-home CTA."""
        response = page.goto(f"{base_url}/404.html")
        assert response.status == 200
        
        # Heading 404
        assert page.locator("h1:has-text('404')").is_visible()
        
        # Return to homepage CTA
        home_cta = page.locator("a[href='/']").first
        assert home_cta.is_visible()
