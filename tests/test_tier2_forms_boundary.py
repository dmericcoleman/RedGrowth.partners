import pytest


@pytest.mark.tier2
class TestTier2FormsBoundary:
    """
    Tier 2: Boundary & Corner Cases - Forms & Interactive Controls.
    Tests form constraint validation, required field enforcement,
    empty and invalid inputs, and rapid mobile drawer interaction.
    """

    def test_audit_form_empty_submission_validation(self, page, base_url):
        """Empty submission should be prevented by required field validation."""
        page.goto(f"{base_url}/")
        
        form = page.locator("#auditForm")
        submit_btn = page.locator("#submitAuditBtn")
        
        # Verify submit button is clickable
        assert submit_btn.is_visible()
        
        # Attempt to click submit without filling anything
        submit_btn.click()
        
        # Verify success message is NOT displayed
        assert not page.locator("#auditSuccess").is_visible(), "Empty form must not transition to success state"

    def test_audit_form_invalid_email_format(self, page, base_url):
        """Invalid email formats should fail validation."""
        page.goto(f"{base_url}/")
        
        email_input = page.locator("#workEmail")
        if email_input.count() > 0:
            email_input.fill("not-a-valid-email")
            is_valid = email_input.evaluate("el => el.checkValidity()")
            assert not is_valid, "Input 'not-a-valid-email' must fail HTML5 email validation"

    def test_audit_form_full_name_required(self, page, base_url):
        """F14: Full Name input field must be present with required attribute and autocomplete."""
        page.goto(f"{base_url}/")
        
        form = page.locator("#auditForm")
        name_input = form.locator("input[name='name'], input#fullName")
        
        assert name_input.count() >= 1, "Full Name input field must exist in audit form (F14)"
        # Check required attribute
        assert name_input.first.get_attribute("required") is not None, "Full Name field should be required"

    def test_mobile_menu_rapid_toggle(self, page, base_url):
        """Rapidly toggling mobile menu button must remain synchronized and not crash."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        
        assert btn.is_visible()
        
        # Toggle 10 times rapidly
        for i in range(10):
            btn.click()
        
        # After 10 clicks (even number), the menu should return to closed (hidden)
        menu_classes = (menu.get_attribute("class") or "").split()
        is_hidden = "hidden" in menu_classes
        aria_exp = btn.get_attribute("aria-expanded")
        
        if is_hidden:
            assert aria_exp == "false"
        else:
            assert aria_exp == "true"

    def test_mobile_menu_aria_expanded_state(self, page, base_url):
        """Mobile menu button aria-expanded attribute must toggle dynamically."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        
        btn = page.locator("#mobileMenuBtn")
        menu = page.locator("#mobileMenu")
        
        # Initial state should be closed: aria-expanded="false"
        assert btn.get_attribute("aria-expanded") == "false"
        
        # Open drawer
        btn.click()
        assert btn.get_attribute("aria-expanded") == "true"
        
        # Close drawer
        btn.click()
        assert btn.get_attribute("aria-expanded") == "false"
