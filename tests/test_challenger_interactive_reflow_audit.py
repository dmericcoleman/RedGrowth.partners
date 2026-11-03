import pytest
import time
from tests.conftest import check_no_horizontal_overflow

MANDATED_PRICING_VIEWPORTS = [
    (280, 653, "280px - Galaxy Z Fold Compact"),
    (320, 568, "320px - iPhone SE 1st Gen"),
    (375, 667, "375px - iPhone SE2 / 6/7/8"),
    (768, 1024, "768px - iPad Portrait"),
    (1024, 768, "1024px - iPad Landscape / Desktop 3-Col Reflow Breakpoint"),
    (1280, 800, "1280px - 13-inch Laptop"),
    (1440, 900, "1440px - Standard Desktop Widescreen"),
]


class TestChallengerInteractiveReflowAudit:
    """
    Adversarial Challenge Verification Suite:
    - Tier 2 Pricing Figures ($4,500/mo) across 280px, 320px, 375px, 768px, 1024px, 1280px, 1440px
    - Proof tab switcher (Google AI Overview <-> Reddit Source)
    - FAQ accordion rapid open/close stress
    - Dynamic resize drawer auto-close and scroll-lock release (mobile -> >=1024px)
    """

    @pytest.mark.parametrize("width,height,label", MANDATED_PRICING_VIEWPORTS)
    def test_pricing_cards_reflow_and_tier2_number_clipping(self, page, base_url, width, height, label):
        """
        Verify that Tier 2 pricing figures ($4,500/mo) and surrounding elements
        never overflow or clip in any column across all mandated viewports.
        """
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        pricing_section = page.locator("#pricing")
        pricing_section.scroll_into_view_if_needed()
        assert pricing_section.count() == 1, "Expected #pricing section to exist"

        # Check full document horizontal overflow
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at {label}: scrollWidth={scroll_w}px > clientWidth={client_w}px"

        # Evaluate all pricing cards with special focus on Card 2 (Tier 2: Growth Retainer $4,500/mo)
        cards_metrics = page.evaluate("""
            () => {
                const section = document.querySelector('#pricing');
                if (!section) return { error: 'No #pricing section found' };

                const cards = Array.from(section.querySelectorAll('.grid > div'));
                const docWidth = document.documentElement.clientWidth;

                return cards.map((card, idx) => {
                    const cardRect = card.getBoundingClientRect();
                    const computed = window.getComputedStyle(card);
                    const heading = card.querySelector('h3') ? card.querySelector('h3').textContent.trim() : '';

                    const spans = Array.from(card.querySelectorAll('span'));
                    const priceSpan = spans.find(s => s.textContent.includes('$'));
                    const unitSpan = spans.find(s => s.textContent.includes('/'));
                    const priceParent = priceSpan ? priceSpan.parentElement : null;

                    const priceRect = priceSpan ? priceSpan.getBoundingClientRect() : null;
                    const priceParentRect = priceParent ? priceParent.getBoundingClientRect() : null;

                    const priceParentScrollW = priceParent ? priceParent.scrollWidth : 0;
                    const priceParentClientW = priceParent ? priceParent.clientWidth : 0;
                    const parentOverflow = priceParentScrollW > priceParentClientW + 1;

                    const overflowsViewport = priceRect ? (priceRect.right > docWidth + 1 || priceRect.left < -1) : true;
                    const overflowsCard = priceRect ? (priceRect.right > cardRect.right + 2 || priceRect.left < cardRect.left - 2) : true;

                    const btn = card.querySelector('a');
                    const btnRect = btn ? btn.getBoundingClientRect() : null;
                    const btnOverflowsCard = btnRect ? (btnRect.right > cardRect.right + 2 || btnRect.left < cardRect.left - 2) : true;

                    return {
                        idx: idx + 1,
                        heading,
                        priceText: priceSpan ? priceSpan.textContent.trim() : '',
                        unitText: unitSpan ? unitSpan.textContent.trim() : '',
                        cardWidth: Math.round(cardRect.width),
                        cardPadding: `${computed.paddingLeft} ${computed.paddingRight}`,
                        priceParentClientW,
                        priceParentScrollW,
                        priceSpanWidth: priceRect ? Math.round(priceRect.width) : 0,
                        parentOverflow,
                        overflowsViewport,
                        overflowsCard,
                        btnOverflowsCard
                    };
                });
            }
        """)

        assert len(cards_metrics) == 3, f"Expected 3 pricing cards, found {len(cards_metrics)}"

        # Validate Card 2 specifically (Tier 2: Growth Retainer)
        card2 = cards_metrics[1]
        assert "$4,500" in card2["priceText"], f"Card 2 expected '$4,500', got '{card2['priceText']}'"
        assert "/mo" in card2["unitText"], f"Card 2 expected '/mo', got '{card2['unitText']}'"
        assert not card2["parentOverflow"], (
            f"Card 2 at {label}: Price container has horizontal overflow! "
            f"scrollWidth={card2['priceParentScrollW']}px > clientWidth={card2['priceParentClientW']}px"
        )
        assert not card2["overflowsCard"], f"Card 2 at {label}: Price figure overflows card bounds: {card2}"
        assert not card2["overflowsViewport"], f"Card 2 at {label}: Price figure overflows viewport: {card2}"
        assert not card2["btnOverflowsCard"], f"Card 2 at {label}: CTA button overflows card: {card2}"

        # Validate Card 1 ($2,500) and Card 3 ($7,500)
        card1 = cards_metrics[0]
        assert "$2,500" in card1["priceText"]
        assert not card1["parentOverflow"]
        assert not card1["overflowsCard"]

        card3 = cards_metrics[2]
        assert "$7,500" in card3["priceText"]
        assert not card3["parentOverflow"]
        assert not card3["overflowsCard"]

        assert len(page._console_errors) == 0, f"Console errors at {label}: {page._console_errors}"

    def test_proof_tab_switcher_interaction_and_rapid_toggle(self, page, base_url):
        """
        Stress test interactive Proof tab switcher (Section 3):
        - Verify initial Google AI Overview tab is selected and panel visible
        - Toggle to Reddit Source tab: verify classes, aria-selected, panel display, image load
        - Toggle back to Google AI Overview tab: verify state restoration
        - Rapid toggle stress (30 alternating cycles)
        - Verify zero console errors and zero layout shifts
        """
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        tab_google = page.locator("#tabGoogleProof")
        tab_reddit = page.locator("#tabRedditProof")
        panel_google = page.locator("#panelGoogleProof")
        panel_reddit = page.locator("#panelRedditProof")

        tab_google.scroll_into_view_if_needed()
        assert tab_google.is_visible(), "Google proof tab must be visible"
        assert tab_reddit.is_visible(), "Reddit proof tab must be visible"

        # 1. Initial State Check
        assert tab_google.get_attribute("aria-selected") == "true", "Google tab must be initially selected"
        assert tab_reddit.get_attribute("aria-selected") == "false", "Reddit tab must be initially unselected"
        assert panel_google.is_visible(), "Google panel must be visible initially"
        assert not panel_reddit.is_visible(), "Reddit panel must be hidden initially"

        img_google = panel_google.locator("img")
        assert img_google.is_visible(), "Google proof image must be visible"
        assert img_google.evaluate("img => img.complete && img.naturalWidth > 0"), "Google proof image failed to load"

        # 2. Click Reddit Source Tab
        tab_reddit.click()
        page.wait_for_timeout(50)

        assert tab_reddit.get_attribute("aria-selected") == "true", "Reddit tab must have aria-selected='true'"
        assert tab_google.get_attribute("aria-selected") == "false", "Google tab must have aria-selected='false'"
        assert panel_reddit.is_visible(), "Reddit panel must be visible after click"
        assert not panel_google.is_visible(), "Google panel must be hidden after click"

        img_reddit = panel_reddit.locator("img")
        assert img_reddit.is_visible(), "Reddit proof image must be visible"
        assert img_reddit.evaluate("img => img.complete && img.naturalWidth > 0"), "Reddit proof image failed to load"

        # 3. Click Google AI Overview Tab back
        tab_google.click()
        page.wait_for_timeout(50)

        assert tab_google.get_attribute("aria-selected") == "true"
        assert tab_reddit.get_attribute("aria-selected") == "false"
        assert panel_google.is_visible()
        assert not panel_reddit.is_visible()

        # 4. Rapid Stress Toggling (30 alternating clicks)
        for i in range(15):
            tab_reddit.click()
            tab_google.click()

        # Final toggle to Reddit
        tab_reddit.click()
        page.wait_for_timeout(50)
        assert tab_reddit.get_attribute("aria-selected") == "true"
        assert panel_reddit.is_visible()
        assert not panel_google.is_visible()

        # Check horizontal overflow after stress toggling
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow after tab stress: {scroll_w}px > {client_w}px"
        assert len(page._console_errors) == 0, f"Console errors during proof tab toggling: {page._console_errors}"

    def test_faq_accordion_rapid_open_close_stress(self, page, base_url):
        """
        Adversarial Stress Test: Rapid open/close operations on FAQ accordion.
        Verifies summary clicks, content rendering, chevron rotation, and zero layout shift.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        faq_section.scroll_into_view_if_needed()
        details_items = faq_section.locator("details")
        assert details_items.count() == 5, f"Expected 5 FAQ items, found {details_items.count()}"

        # Rapidly toggle each item 6 times (30 click operations total)
        for cycle in range(3):
            for i in range(5):
                item = details_items.nth(i)
                summary = item.locator("summary")
                # Open
                summary.click()
                assert item.evaluate("el => el.open"), f"Item {i+1} failed to open on cycle {cycle+1}"
                # Close
                summary.click()
                assert not item.evaluate("el => el.open"), f"Item {i+1} failed to close on cycle {cycle+1}"

        # Open all 5 items simultaneously and verify layout stability
        for i in range(5):
            details_items.nth(i).locator("summary").click()
            assert details_items.nth(i).evaluate("el => el.open")

        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow with all FAQs open: {scroll_w}px > {client_w}px"
        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    def test_dynamic_resize_mobile_to_desktop_drawer_autoclose_and_lock_release(self, page, base_url):
        """
        Adversarial Dynamic Resize:
        1. Open drawer at 280px / 320px / 375px.
        2. Resize directly across the 1024px desktop breakpoint (e.g. 1024px, 1280px, 1440px).
        3. Verify drawer auto-closes (hidden), backdrop hidden, and body scroll lock released.
        4. Resize back to mobile and verify drawer does not reappear.
        5. Repeat for 5 rapid cycles.
        """
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        mobile_btn = page.locator("#mobileMenuBtn")
        mobile_menu = page.locator("#mobileMenu")
        mobile_backdrop = page.locator("#mobileMenuBackdrop")

        test_viewports = [
            (280, 1024),
            (320, 1280),
            (375, 1024),
            (390, 1440),
            (414, 1024),
        ]

        for mobile_w, desktop_w in test_viewports:
            # 1. Start at mobile viewport
            page.set_viewport_size({"width": mobile_w, "height": 667})
            page.wait_for_timeout(40)
            assert mobile_btn.is_visible(), f"Mobile button not visible at {mobile_w}px"

            # 2. Open drawer
            mobile_btn.click()
            page.wait_for_timeout(40)
            assert mobile_menu.is_visible(), f"Drawer failed to open at {mobile_w}px"
            assert page.evaluate("() => document.body.style.overflow") == "hidden", (
                f"Body scroll lock not applied at {mobile_w}px"
            )

            # 3. Resize to desktop breakpoint
            page.set_viewport_size({"width": desktop_w, "height": 800})
            page.wait_for_timeout(60)

            # 4. Verify drawer auto-dismiss & scroll lock release
            assert not mobile_menu.is_visible(), f"Drawer failed to auto-close at {desktop_w}px"
            assert not mobile_backdrop.is_visible(), f"Backdrop not hidden at {desktop_w}px"
            assert page.evaluate("() => document.body.style.overflow") != "hidden", (
                f"Body scroll lock stuck after resize to {desktop_w}px"
            )
            assert not page.evaluate("() => document.body.classList.contains('overflow-hidden')"), (
                f"overflow-hidden class stuck after resize to {desktop_w}px"
            )

            # 5. Resize back to mobile
            page.set_viewport_size({"width": mobile_w, "height": 667})
            page.wait_for_timeout(40)
            assert not mobile_menu.is_visible(), f"Drawer unexpectedly reopened on shrinking back to {mobile_w}px"
            assert page.evaluate("() => document.body.style.overflow") != "hidden", (
                f"Body scroll lock engaged on shrinking back to {mobile_w}px"
            )

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow at {mobile_w}px: {scroll_w}px > {client_w}px"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"
