# Automated E2E Test Infrastructure

## Overview

RedGrowth.partners uses an automated, opaque-box, requirement-driven E2E test harness built on **Python 3.14**, **Playwright 1.62.0** (headless Chromium), and **Pytest 9.1.1**.

The test suite acts as an authoritative, independent quality gate derived from `PROJECT.md` and `ORIGINAL_REQUEST.md`. It validates the site across 4 rigorous tiers of functional, boundary, cross-feature, and real-world executive user journeys.

---

## Architecture & Layout

```
RedGrowth.partners/
├── pytest.ini                            # Pytest configuration, pythonpath, markers
├── TEST_INFRA.md                         # Test architecture and runner documentation
├── TEST_READY.md                         # Test suite readiness and baseline report
└── tests/
    ├── __init__.py
    ├── conftest.py                       # Fixtures: auto-server spawn, browser, console/error capture
    ├── test_tier1_feature_presence.py    # Tier 1: Core features presence (F1 - F14)
    ├── test_tier1_subpages.py            # Tier 1: Legal & error subpages (F15)
    ├── test_tier2_responsiveness.py      # Tier 2: 8 viewports (320px-1440px) zero horizontal overflow
    ├── test_tier2_forms_boundary.py      # Tier 2: Form validation constraints & rapid UI interaction
    ├── test_tier3_navigation_anchors.py  # Tier 3: Sticky nav, anchor offsets, drawer backdrop/escape
    ├── test_tier3_ux_contrast_console.py # Tier 3: Zero console errors, inline form UX, WCAG contrast
    └── test_tier4_executive_journey.py   # Tier 4: Unfamiliar executive buyer end-to-end journey
```

---

## 4-Tier Test Taxonomy

### Tier 1: Feature Coverage & Subpages (16 Tests)
- **`test_hero_section_presence_and_structure`**: H1 title, subheadline, CTAs, dashboard preview image.
- **`test_hero_copy_modernization_and_ftc_badge`**: Validates modern "Google AI Overviews" terminology, absence of legacy "Google's SGE", and visible FTC compliance trust badge.
- **`test_section3_proof_card_integrated`**: Validates absence of `<!-- Blank space as requested -->` and verifies integration of Google AI Overview and Reddit citation proof cards.
- **`test_credible_social_proof_no_dummy_logos`**: Verifies dummy placeholder logos (`TECHCO`, `FASTAPP`, `STACKIFY`, `GLOBALX`) are absent, and enterprise client profiles are present.
- **`test_client_testimonials_and_no_bracket_placeholders`**: Verifies authentic client testimonials (Sarah Chen, Marcus Torres, Elena Rostova) and absence of unreplaced `[Competitor]`.
- **`test_enterprise_pricing_structure`**: Verifies enterprise tiers (Audit & Pilot, Retainer, Enterprise Authority) and eliminates low-barrier dissonance ($97/kw, $247/mo, "Competitor Brand Dilution").
- **`test_founder_leadership_section_presence`**: Verifies dedicated Founder section featuring Eric Coleman, `assets/images/eric-coleman.webp`, and verified LinkedIn profile.
- **`test_comprehensive_faq_accordion_presence`**: Verifies `#faq` accordion addressing Reddit ban safety, AI citation tracking, and FTC compliance.
- **`test_navigation_header_links_presence`**: Verifies primary navigation links (#framework, #compliance, #results, #pricing, #audit).
- **`test_clickable_contact_info`**: Verifies email (`eric@redgrowth.partners`) is a clickable `mailto:` link and phone (`+1 (916) 907-6120`) is a clickable `tel:` link.
- **`test_audit_form_fields_and_status_elements`**: Verifies audit form contains domain, email, and full name (`name="name"`) inputs plus `#auditSuccess` and `#auditError` status containers.
- **`test_privacy_page_branding_and_content`**: Verifies `privacy.html` references "RedGrowth.partners" (zero "Reddit Growth Partners").
- **`test_privacy_page_navigation_and_assets`**: Verifies `privacy.html` navigation links, stylesheet links, and HTTP 200.
- **`test_terms_page_branding_and_content`**: Verifies `terms.html` references "RedGrowth.partners" (zero "Reddit Growth Partners").
- **`test_terms_page_navigation_and_assets`**: Verifies `terms.html` navigation links, stylesheet links, and HTTP 200.
- **`test_404_page_layout_and_cta`**: Verifies custom 404 page layout and return-to-home CTA.

### Tier 2: Boundary & Corner Cases (17 Tests)
- **`test_zero_horizontal_overflow_across_viewports`** (8 parametrized tests):
  - 320x568 (iPhone SE / compact mobile)
  - 360x640 (Compact Android)
  - 375x667 (iPhone 8 / standard mobile)
  - 390x844 (iPhone 12/13/14)
  - 414x896 (iPhone XR / Plus / Max)
  - 768x1024 (iPad portrait / Tablet)
  - 1024x768 (iPad landscape / Small Desktop)
  - 1440x900 (Desktop / Widescreen)
  - Evaluates: `document.documentElement.scrollWidth <= document.documentElement.clientWidth` with zero horizontal overflow.
- **`test_hero_h1_nowrap_elimination_on_mobile`**: Verifies H1 does not contain unconditional `whitespace-nowrap` on mobile screens and does not clip.
- **`test_section3_h2_responsive_wrapping`**: Verifies Section 3 heading wraps without overflow.
- **`test_hero_dashboard_container_mobile_spacing`**: Verifies hero preview container avoids mobile dead space.
- **`test_growth_engine_mobile_layout`**: Verifies 3-step engine cards are centered and visible on mobile.
- **`test_audit_form_empty_submission_validation`**: Verifies empty submissions are prevented by browser constraint validation.
- **`test_audit_form_invalid_email_format`**: Verifies malformed emails fail HTML5 validation.
- **`test_audit_form_full_name_required`**: Verifies Full Name field is required.
- **`test_mobile_menu_rapid_toggle`**: Stresses hamburger toggle with 10 rapid clicks to ensure synchronization without state corruptions.
- **`test_mobile_menu_aria_expanded_state`**: Verifies `aria-expanded` transitions dynamically between `"true"` and `"false"`.

### Tier 3: Cross-Feature Combinations (11 Tests)
- **`test_sticky_header_persists_on_scroll`**: Verifies header pins to top (`position: fixed` or `sticky`) when user scrolls down 1200px.
- **`test_anchor_links_scroll_targets_into_view`**: Verifies clicking navigation anchors smoothly scrolls targets into view.
- **`test_anchor_target_scroll_offset_prevents_overlap`**: Verifies anchor targets define `scroll-mt-24` (or equivalent offset) so headings are never obscured by sticky nav.
- **`test_mobile_drawer_link_click_closes_drawer`**: Verifies selecting a section from the mobile drawer dismisses the drawer.
- **`test_mobile_drawer_dismiss_on_backdrop_click`**: Verifies clicking outside the mobile drawer dismisses it.
- **`test_mobile_drawer_dismiss_on_escape_key`**: Verifies pressing `Escape` dismisses the mobile drawer.
- **`test_mobile_drawer_locks_body_scroll`**: Verifies body scroll is locked (`overflow: hidden`) when the mobile drawer is open.
- **`test_zero_console_errors_on_landing_and_scroll`**: Verifies zero unhandled JavaScript exceptions or browser console errors during full page scroll.
- **`test_audit_form_error_inline_ux_no_alert`**: Intercepts failed submission (HTTP 500) and asserts zero browser `alert()` popups and visible inline `#auditError`.
- **`test_audit_form_success_inline_ux`**: Intercepts successful submission (HTTP 200) and asserts visible inline `#auditSuccess`.
- **`test_wcag_contrast_on_key_elements`**: Evaluates WCAG AA contrast ratio standards on body and footer text.

### Tier 4: Real-World Workload Scenarios (1 Test)
- **`test_executive_buyer_end_to_end_journey`**: Simulates a complete, unfamiliar executive visitor journey:
  1. Lands on homepage.
  2. Inspects Hero value proposition and compliance badges.
  3. Scrolls through Framework and inspects Section 3 visual proof.
  4. Reviews case studies, client quotes, and verified testimonials.
  5. Verifies Founder Eric Coleman's profile, image, and LinkedIn link.
  6. Evaluates Enterprise Pricing tiers and deliverables.
  7. Checks FAQ accordion for Reddit safety and FTC compliance objection handling.
  8. Interacts with the Audit form, fills details, submits, and verifies inline confirmation.
  9. Validates legal subpages (Privacy, Terms) for uniform branding.
  10. Asserts zero browser console errors throughout the entire journey.

---

## Runner Commands

### Running All Tests
```bash
pytest
```
*Note: If no HTTP server is currently running, `conftest.py` automatically spawns a local server on port 8000 and terminates it when the test run concludes.*

### Running Against an Existing Server
If you already started `python -m http.server 8000`:
```bash
pytest
```
To point to a different port or custom host:
```bash
$env:BASE_URL="http://127.0.0.1:8080"
pytest
```

### Running by Tier
```bash
# Tier 1 only
pytest -m tier1

# Tier 2 only
pytest -m tier2

# Tier 3 only
pytest -m tier3

# Tier 4 only
pytest -m tier4
```

### Running Specific Test Modules
```bash
pytest tests/test_tier2_responsiveness.py
pytest tests/test_tier4_executive_journey.py
```

### Verbose Mode with Detailed Trace
```bash
pytest -v -s --tb=short
```

---

## Milestone Quality Gates

| Milestone | Target Features | Quality Gate Required |
|-----------|-----------------|------------------------|
| **M1** | F1, F2, F3, F4 | Tier 2 Responsiveness (8 viewports zero overflow, hero H1 nowrap removal, section 3 wrapping, dashboard spacing, growth engine alignment) + Tier 1 Section 3 proof presence pass 100%. |
| **M2** | F5, F6, F7, F8, F9, F10 | Tier 1 Hero copy modernization, FTC badge, enterprise logo profiles, client testimonials, bracket removal, enterprise pricing, founder presence, FAQ accordion pass 100%. |
| **M3** | F11, F12, F13, F14, F15, F16 | Tier 1 Contact info, audit form fields, subpages synchronization + Tier 3 sticky navigation, anchor offsets, mobile drawer accessibility, inline form error UX, zero console errors, WCAG contrast pass 100%. |
| **M4** | F17 (Final Sign-off) | **100% of all 45 tests across Tiers 1-4 pass.** Zero failures, zero warnings, zero unhandled console errors. |
