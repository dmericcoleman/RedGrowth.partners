import pytest
from playwright.sync_api import Page, expect

BREAKPOINTS = [
    (320, 568, "mobile-320", False),
    (360, 640, "mobile-360", False),
    (375, 667, "mobile-375", False),
    (414, 896, "mobile-414", False),
    (640, 900, "mobile-640", False),
    (767, 1024, "mobile-767-boundary", False),
    (768, 1024, "desktop-768-boundary", True),
    (820, 1180, "desktop-820", True),
    (1024, 768, "desktop-1024", True),
    (1280, 800, "desktop-1280", True),
    (1440, 900, "desktop-1440", True),
    (1920, 1080, "desktop-1920", True),
]


class TestTimelineTrackGradientComputedStyles:
    """Empirically challenge timeline gradient display, width, and background across breakpoints."""

    @pytest.mark.parametrize("width,height,label,is_desktop", BREAKPOINTS)
    def test_timeline_gradient_visibility_and_dimensions(self, page: Page, base_url: str, width: int, height: int, label: str, is_desktop: bool):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{base_url}/#engine")
        page.wait_for_timeout(100)

        # Inspect the timeline track gradient
        metrics = page.evaluate("""() => {
            const el = document.querySelector('.timeline-track-gradient');
            if (!el) return null;
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            const parent = el.parentElement;
            const parentRect = parent ? parent.getBoundingClientRect() : null;

            return {
                display: style.display,
                width: style.width,
                rectWidth: rect.width,
                rectHeight: rect.height,
                rectLeft: rect.left,
                position: style.position,
                backgroundImage: style.backgroundImage,
                background: style.background,
                parentWidth: parentRect ? parentRect.width : 0,
                parentLeft: parentRect ? parentRect.left : 0,
            };
        }""")

        assert metrics is not None, "Element with class .timeline-track-gradient not found in DOM!"

        if not is_desktop:
            # On mobile (<768px), timeline track central gradient line MUST be hidden
            assert metrics["display"] == "none", (
                f"On mobile {label} ({width}px), expected display: 'none', but got '{metrics['display']}'"
            )
            assert metrics["rectWidth"] == 0, (
                f"On mobile {label} ({width}px), expected rectWidth 0, got {metrics['rectWidth']}"
            )
        else:
            # On desktop (>=768px), timeline track central gradient line MUST be display: block and 2px wide
            assert metrics["display"] == "block", (
                f"On desktop {label} ({width}px), expected display: 'block', but got '{metrics['display']}'"
            )
            assert metrics["width"] == "2px", (
                f"On desktop {label} ({width}px), expected computed width: '2px', but got '{metrics['width']}'"
            )
            assert abs(metrics["rectWidth"] - 2.0) <= 0.1, (
                f"On desktop {label} ({width}px), expected rendered bounding rect width ~2.0px, got {metrics['rectWidth']}"
            )
            assert metrics["rectHeight"] > 50, (
                f"On desktop {label} ({width}px), expected track height > 50px, got {metrics['rectHeight']}"
            )
            # Check linear-gradient presence in background
            bg_info = metrics["backgroundImage"] + " " + metrics["background"]
            assert "linear-gradient" in bg_info, (
                f"On desktop {label} ({width}px), expected linear-gradient in background, got: {bg_info}"
            )
            # Check center positioning: parent center vs line center
            line_center = metrics["rectLeft"] + (metrics["rectWidth"] / 2.0)
            parent_center = metrics["parentLeft"] + (metrics["parentWidth"] / 2.0)
            assert abs(line_center - parent_center) <= 2.0, (
                f"On desktop {label} ({width}px), expected centered line (diff <= 2px), line_center={line_center}, parent_center={parent_center}"
            )
