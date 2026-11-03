import random
import time
import pytest
from tests.conftest import check_no_horizontal_overflow

# Viewports strictly mandated by task prompt: 320px, 360px, 375px, 768px, 1024px, 1440px (plus 390px, 414px standard mobile)
REQUIRED_PRICING_VIEWPORTS = [
    (320, 568, "iPhone SE 1st Gen (320px)"),
    (360, 640, "Compact Android Standard (360px)"),
    (375, 667, "iPhone 6/7/8/SE2 (375px)"),
    (390, 844, "iPhone 12/13/14 (390px)"),
    (414, 896, "iPhone Plus/Max (414px)"),
    (768, 1024, "iPad Portrait / Tablet (768px)"),
    (1024, 768, "iPad Landscape / Small Desktop (1024px)"),
    (1440, 900, "Standard Desktop (1440px)"),
]

REQUIRED_FOUNDER_MOBILE_VIEWPORTS = [
    (320, 568, "320px"),
    (360, 640, "360px"),
    (375, 667, "375px"),
    (390, 844, "390px"),
    (414, 896, "414px"),
    (768, 1024, "768px"),
]


class TestAdversarialM2FaqInteractivity:
    """
    Empirical Stress Testing for FAQ Accordion Interactivity.
    Validates rapid toggling (50 cycles), full expansion, text overflow,
    layout stability, and zero runtime console errors.
    """

    def test_faq_presence_and_initial_contract(self, page, base_url):
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        assert faq_section.count() == 1, "Expected section#faq to exist."

        details_items = faq_section.locator("details")
        assert details_items.count() == 5, f"Expected exactly 5 FAQ details items, found {details_items.count()}."

        # Verify all start closed
        for i in range(5):
            item = details_items.nth(i)
            is_open = item.evaluate("el => el.open")
            assert not is_open, f"FAQ item {i+1} was expected to be closed initially."
            summary = item.locator("summary")
            assert summary.is_visible(), f"FAQ item {i+1} summary should be visible."

        # Verify zero console errors
        assert len(page._console_errors) == 0, f"Console errors on load: {page._console_errors}"

    def test_faq_rapid_sequence_toggle_50_toggles(self, page, base_url):
        """
        Interactivity stress test:
        50 rapid sequence toggles across all 5 FAQ <details> items (10 full cycles).
        Verifies smooth toggle transitions, zero layout breaking, and zero console errors.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        faq_section = page.locator("#faq")
        details_items = faq_section.locator("details")
        assert details_items.count() == 5

        # Execute 50 rapid sequential clicks (10 rounds across 5 items)
        for round_idx in range(10):
            for i in range(5):
                summary = details_items.nth(i).locator("summary")
                summary.scroll_into_view_if_needed()
                summary.click()

            # Check horizontal overflow after each 5-item burst
            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow during rapid toggle round {round_idx+1}: {scroll_w}px > {client_w}px"

        # After 10 toggles per item (even count), all items should return to closed
        for i in range(5):
            is_open = details_items.nth(i).evaluate("el => el.open")
            assert not is_open, f"FAQ item {i+1} expected to be closed after even number of toggles."

        # Zero console errors and zero page errors
        assert len(page._console_errors) == 0, f"Console errors after 50 rapid toggles: {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page runtime errors: {page._page_errors}"

    def test_faq_all_open_layout_and_text_overflow(self, page, base_url):
        """
        Opens all 5 FAQ panels simultaneously across both mobile (360px) and desktop (1280px).
        Verifies that no text overflows container, summary/content wrap cleanly,
        and scrollWidth <= clientWidth.
        """
        for vp_width, vp_height in [(320, 568), (360, 640), (375, 667), (768, 1024), (1280, 800)]:
            page.set_viewport_size({"width": vp_width, "height": vp_height})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            faq_section = page.locator("#faq")
            details_items = faq_section.locator("details")

            # Open all 5 items
            for i in range(5):
                item = details_items.nth(i)
                if not item.evaluate("el => el.open"):
                    item.locator("summary").click()

            # Verify all 5 are open
            for i in range(5):
                assert details_items.nth(i).evaluate("el => el.open"), f"Item {i+1} failed to open at {vp_width}px."

            # Verify document horizontal overflow
            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow at {vp_width}px with all FAQs open: {scroll_w}px > {client_w}px"

            # Check each details item container and text content for overflow
            overflow_report = page.evaluate("""
                () => {
                    const results = [];
                    const details = document.querySelectorAll('#faq details');
                    details.forEach((det, idx) => {
                        const detRect = det.getBoundingClientRect();
                        const summary = det.querySelector('summary');
                        const sumRect = summary ? summary.getBoundingClientRect() : null;
                        const contentDiv = det.querySelector('div');
                        const contentRect = contentDiv ? contentDiv.getBoundingClientRect() : null;
                        
                        const detOverflow = det.scrollWidth > det.clientWidth + 1;
                        const sumOverflow = summary ? summary.scrollWidth > summary.clientWidth + 1 : false;
                        const contentOverflow = contentDiv ? contentDiv.scrollWidth > contentDiv.clientWidth + 1 : false;
                        
                        if (detOverflow || sumOverflow || contentOverflow) {
                            results.push({
                                index: idx + 1,
                                detOverflow,
                                sumOverflow,
                                contentOverflow,
                                detScrollW: det.scrollWidth,
                                detClientW: det.clientWidth
                            });
                        }
                    });
                    return results;
                }
            """)
            assert len(overflow_report) == 0, f"FAQ item text overflow detected at {vp_width}px: {overflow_report}"

        assert len(page._console_errors) == 0, f"Console errors: {page._console_errors}"

    def test_faq_random_hammering_stress(self, page, base_url):
        """
        Aggressive random rapid clicks simulating impatient mobile user.
        50 clicks in non-uniform pattern with 0ms delay.
        """
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        random.seed(42)
        faq_section = page.locator("#faq")
        summaries = [faq_section.locator("details").nth(i).locator("summary") for i in range(5)]

        for _ in range(50):
            target_summary = random.choice(summaries)
            target_summary.click()

        # Check document layout integrity after hammering
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Layout broken after random hammering: {scroll_w}px > {client_w}px"
        assert len(page._console_errors) == 0, f"Console errors after random hammering: {page._console_errors}"


class TestAdversarialM2PricingReflow:
    """
    Empirical Stress Testing for Pricing Card Responsive Reflow.
    Tests across 320px, 360px, 375px, 768px, 1024px, 1440px.
    Verifies $2,500, $4,500 /mo, $7,500 /mo numbers never clip, truncate, or cause horizontal overflow.
    """

    @pytest.mark.parametrize("width,height,label", REQUIRED_PRICING_VIEWPORTS)
    def test_pricing_cards_reflow_and_number_clipping(self, page, base_url, width, height, label):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        pricing_section = page.locator("#pricing")
        pricing_section.scroll_into_view_if_needed()
        assert pricing_section.count() == 1, "Expected #pricing section to exist."

        # Verify document horizontal overflow
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at {label}: {scroll_w}px > {client_w}px"

        # Check each of the 3 price cards and their price values
        expected_tiers = [
            {"name": "AEO Audit & Pilot", "price_str": "$2,500", "unit": "/ one-time pilot"},
            {"name": "Growth Retainer", "price_str": "$4,500", "unit": "/mo"},
            {"name": "Category Authority", "price_str": "$7,500", "unit": "/mo"},
        ]

        # Evaluate cards inside the pricing section
        evaluation = page.evaluate("""
            () => {
                const results = [];
                const section = document.querySelector('#pricing');
                if (!section) return { error: 'No #pricing section' };

                const cards = section.querySelectorAll('.grid > div');
                cards.forEach((card, idx) => {
                    const cardRect = card.getBoundingClientRect();
                    const heading = card.querySelector('h3') ? card.querySelector('h3').textContent.trim() : '';
                    
                    // Find the price span
                    const spans = Array.from(card.querySelectorAll('span'));
                    const priceSpan = spans.find(s => s.textContent.includes('$'));
                    const priceRect = priceSpan ? priceSpan.getBoundingClientRect() : null;
                    const priceText = priceSpan ? priceSpan.textContent.trim() : '';
                    
                    // Find unit span
                    const unitSpan = spans.find(s => s.textContent.includes('/'));
                    const unitRect = unitSpan ? unitSpan.getBoundingClientRect() : null;
                    const unitText = unitSpan ? unitSpan.textContent.trim() : '';

                    // Check clipping
                    const priceParent = priceSpan ? priceSpan.parentElement : null;
                    const priceParentScrollW = priceParent ? priceParent.scrollWidth : 0;
                    const priceParentClientW = priceParent ? priceParent.clientWidth : 0;
                    const parentOverflow = priceParentScrollW > priceParentClientW + 1;

                    // Check bounds within viewport
                    const docWidth = document.documentElement.clientWidth;
                    const overflowsViewport = priceRect ? (priceRect.right > docWidth || priceRect.left < 0) : true;
                    
                    // Check bounds within card
                    const overflowsCard = priceRect ? (priceRect.right > cardRect.right + 2 || priceRect.left < cardRect.left - 2) : true;

                    // Button
                    const btn = card.querySelector('a');
                    const btnRect = btn ? btn.getBoundingClientRect() : null;
                    const btnOverflowsCard = btnRect ? (btnRect.right > cardRect.right + 2 || btnRect.left < cardRect.left - 2) : true;

                    results.push({
                        idx,
                        heading,
                        priceText,
                        unitText,
                        priceRect: priceRect ? { left: priceRect.left, right: priceRect.right, width: priceRect.width } : null,
                        cardRect: { left: cardRect.left, right: cardRect.right, width: cardRect.width },
                        parentOverflow,
                        overflowsViewport,
                        overflowsCard,
                        btnOverflowsCard
                    });
                });
                return results;
            }
        """)

        assert len(evaluation) == 3, f"Expected 3 pricing cards, found {len(evaluation)}: {evaluation}"

        for idx, expected in enumerate(expected_tiers):
            card_data = evaluation[idx]
            assert expected["price_str"] in card_data["priceText"], (
                f"Card {idx+1} ({expected['name']}) at {label}: Expected price {expected['price_str']}, got '{card_data['priceText']}'"
            )
            assert not card_data["parentOverflow"], (
                f"Card {idx+1} at {label}: Price container has horizontal overflow!"
            )
            assert not card_data["overflowsViewport"], (
                f"Card {idx+1} at {label}: Price number overflows viewport bounds: {card_data}"
            )
            assert not card_data["overflowsCard"], (
                f"Card {idx+1} at {label}: Price number overflows card bounds: {card_data}"
            )
            assert not card_data["btnOverflowsCard"], (
                f"Card {idx+1} at {label}: CTA button overflows card bounds: {card_data}"
            )

        assert len(page._console_errors) == 0, f"Console errors at {label}: {page._console_errors}"

    def test_pricing_section_extreme_compact_280px_integrity(self, page, base_url):
        """
        Adversarial edge test: Probes pricing section internal scrollWidth at 280px (Galaxy Fold).
        Verifies that the pricing section itself has zero horizontal overflow and cards fit 280px.
        """
        page.set_viewport_size({"width": 280, "height": 653})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        pricing_section = page.locator("#pricing")
        metrics = pricing_section.evaluate("el => ({ scrollWidth: el.scrollWidth, clientWidth: el.clientWidth })")
        assert metrics["scrollWidth"] <= metrics["clientWidth"], (
            f"Pricing section internally overflows at 280px: {metrics}"
        )


class TestAdversarialM2FounderLayout:
    """
    Empirical Stress Testing for Founder Card Layout.
    Verifies that on mobile viewports (320px, 360px, 375px, 390px, 414px, 768px):
    - Image and text stack cleanly without overlapping.
    - Image loads correctly (complete and naturalWidth > 0).
    - Image and text containers do not horizontally or vertically collide.
    - Buttons and links are fully functional and within bounds.
    """

    @pytest.mark.parametrize("width,height,label", REQUIRED_FOUNDER_MOBILE_VIEWPORTS)
    def test_founder_card_mobile_stacking_no_overlap(self, page, base_url, width, height, label):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        founder_section = page.locator("#founder")
        founder_section.scroll_into_view_if_needed()
        assert founder_section.count() == 1, "Expected #founder section to exist."

        # Document horizontal overflow check
        passes, scroll_w, client_w = check_no_horizontal_overflow(page)
        assert passes, f"Horizontal overflow at {label} in #founder: {scroll_w}px > {client_w}px"

        # Check founder image loading
        img_locator = founder_section.locator("img[src*='eric-coleman']")
        assert img_locator.count() == 1, "Expected Eric Coleman founder image."
        img_loaded = img_locator.evaluate("img => img.complete && img.naturalWidth > 0")
        assert img_loaded, "Founder image failed to load or has naturalWidth == 0."

        # Evaluate geometric stacking and overlap
        layout_metrics = page.evaluate("""
            () => {
                const section = document.querySelector('#founder');
                const imgContainer = section.querySelector('.w-48, .w-56, .w-64') || section.querySelector('img').parentElement;
                const textContainer = section.querySelector('.flex-1');
                
                const imgRect = imgContainer.getBoundingClientRect();
                const textRect = textContainer.getBoundingClientRect();
                
                // Check 2D bounding box intersection (AABB overlap test)
                const horizontalOverlap = !(imgRect.right <= textRect.left || imgRect.left >= textRect.right);
                const verticalOverlap = !(imgRect.bottom <= textRect.top || imgRect.top >= textRect.bottom);
                const overlaps = horizontalOverlap && verticalOverlap;
                
                // Check vertical stacking order (image should be above text on mobile)
                const isStackedVertically = imgRect.bottom <= textRect.top + 2; // allowance for subpixel
                
                // Check viewport bounds
                const docWidth = document.documentElement.clientWidth;
                const imgWithinViewport = imgRect.left >= 0 && imgRect.right <= docWidth;
                const textWithinViewport = textRect.left >= 0 && textRect.right <= docWidth;

                // Check action buttons
                const buttons = Array.from(textContainer.querySelectorAll('a'));
                const buttonsMetrics = buttons.map(b => {
                    const bRect = b.getBoundingClientRect();
                    return {
                        href: b.href,
                        text: b.textContent.trim().slice(0, 30),
                        withinViewport: bRect.left >= 0 && bRect.right <= docWidth,
                        rect: { left: Math.round(bRect.left), right: Math.round(bRect.right), width: Math.round(bRect.width) }
                    };
                });

                return {
                    imgRect: { top: Math.round(imgRect.top), bottom: Math.round(imgRect.bottom), left: Math.round(imgRect.left), right: Math.round(imgRect.right), width: Math.round(imgRect.width), height: Math.round(imgRect.height) },
                    textRect: { top: Math.round(textRect.top), bottom: Math.round(textRect.bottom), left: Math.round(textRect.left), right: Math.round(textRect.right), width: Math.round(textRect.width), height: Math.round(textRect.height) },
                    overlaps,
                    horizontalOverlap,
                    verticalOverlap,
                    isStackedVertically,
                    imgWithinViewport,
                    textWithinViewport,
                    buttonsMetrics
                };
            }
        """)

        assert not layout_metrics["overlaps"], (
            f"Founder image and text OVERLAP at {label}! "
            f"ImageRect: {layout_metrics['imgRect']}, TextRect: {layout_metrics['textRect']}"
        )
        assert layout_metrics["isStackedVertically"], (
            f"Founder image is not stacked above text on {label}! "
            f"Image bottom: {layout_metrics['imgRect']['bottom']}, Text top: {layout_metrics['textRect']['top']}"
        )
        assert layout_metrics["textWithinViewport"], (
            f"Founder text container overflows viewport at {label}: {layout_metrics['textRect']}"
        )
        for btn in layout_metrics["buttonsMetrics"]:
            assert btn["withinViewport"], (
                f"Founder button '{btn['text']}' overflows viewport at {label}: {btn}"
            )

        assert len(page._console_errors) == 0, f"Console errors at {label}: {page._console_errors}"

    def test_founder_card_desktop_side_by_side(self, page, base_url):
        """Verify on desktop viewports (1024px, 1440px) that layout cleanly transitions to side-by-side without overlap."""
        for vp_w, vp_h in [(1024, 768), (1440, 900)]:
            page.set_viewport_size({"width": vp_w, "height": vp_h})
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")

            founder_section = page.locator("#founder")
            founder_section.scroll_into_view_if_needed()

            passes, scroll_w, client_w = check_no_horizontal_overflow(page)
            assert passes, f"Horizontal overflow at {vp_w}px in #founder"

            layout_metrics = page.evaluate("""
                () => {
                    const section = document.querySelector('#founder');
                    const imgContainer = section.querySelector('.w-48, .w-56, .w-64') || section.querySelector('img').parentElement;
                    const textContainer = section.querySelector('.flex-1');
                    
                    const imgRect = imgContainer.getBoundingClientRect();
                    const textRect = textContainer.getBoundingClientRect();
                    
                    const horizontalOverlap = !(imgRect.right <= textRect.left || imgRect.left >= textRect.right);
                    const verticalOverlap = !(imgRect.bottom <= textRect.top || imgRect.top >= textRect.bottom);
                    const overlaps = horizontalOverlap && verticalOverlap;
                    const isSideBySide = imgRect.right <= textRect.left + 5; // image to the left of text

                    return {
                        imgRect,
                        textRect,
                        overlaps,
                        isSideBySide
                    };
                }
            """)

            assert not layout_metrics["overlaps"], f"Founder card overlap at {vp_w}px!"
            assert layout_metrics["isSideBySide"], f"Founder card expected side-by-side layout at {vp_w}px!"

        assert len(page._console_errors) == 0

    def test_founder_section_extreme_compact_280px_integrity(self, page, base_url):
        """
        Adversarial edge test: Probes founder section internal scrollWidth at 280px (Galaxy Fold).
        Verifies that the founder section itself has zero horizontal overflow.
        """
        page.set_viewport_size({"width": 280, "height": 653})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        founder_section = page.locator("#founder")
        metrics = founder_section.evaluate("el => ({ scrollWidth: el.scrollWidth, clientWidth: el.clientWidth })")
        assert metrics["scrollWidth"] <= metrics["clientWidth"], (
            f"Founder section internally overflows at 280px: {metrics}"
        )
