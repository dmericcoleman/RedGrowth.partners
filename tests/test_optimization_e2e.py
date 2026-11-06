"""
Comprehensive End-to-End Verification Test Suite for RedGrowth.partners
Authoritative M4 Victory Verification covering Features 1-16:
- Asset preloading, compression, lazy loading, and script deferral
- Multi-platform caching and security headers (_headers, vercel.json, .htaccess)
- Semantic landmarks (<main id="main-content">), skip links, and WCAG accessibility
- Full JSON-LD knowledge graph validation (Organization, WebSite, FAQPage, Services)
- Subpage SEO metadata, canonicals, Open Graph, and sitemap crawlability
- Window resize RAF debouncing and zero inline styles
- Strict HTML5 syntax validation across all 4 production pages
- Zero console errors and unhandled exceptions during execution
"""

import os
import json
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import pytest
from PIL import Image
from bs4 import BeautifulSoup

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAGES = ["index.html", "404.html", "privacy.html", "terms.html"]


# ==============================================================================
# Helper: Strict HTML Syntax Validator
# ==============================================================================
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


class StrictHTMLValidator(HTMLParser):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.tag_stack = []
        self.errors = []
        self.ids = set()
        self.duplicate_ids = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        el_id = attr_dict.get("id")
        if el_id:
            if el_id in self.ids:
                self.duplicate_ids.append((el_id, self.getpos()))
            else:
                self.ids.add(el_id)
        if tag.lower() not in VOID_ELEMENTS:
            self.tag_stack.append((tag.lower(), self.getpos()))

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_ELEMENTS:
            return
        if not self.tag_stack:
            self.errors.append(f"Unexpected closing tag </{tag}> at line {self.getpos()[0]}")
            return
        last_tag, pos = self.tag_stack.pop()
        if last_tag != tag_lower:
            self.errors.append(
                f"Mismatched closing tag </{tag}> at line {self.getpos()[0]}, "
                f"expected </{last_tag}> opened at line {pos[0]}"
            )

    def check_remaining(self):
        while self.tag_stack:
            last_tag, pos = self.tag_stack.pop()
            self.errors.append(f"Unclosed tag <{last_tag}> opened at line {pos[0]}")


# ==============================================================================
# Feature 1: LCP Hero Image Preload
# ==============================================================================
class TestFeature1HeroPreload:
    def test_hero_image_preload_in_head(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        head = soup.find("head")
        assert head is not None, "index.html must contain a <head> element"

        preload = head.find(
            "link",
            rel="preload",
            attrs={"as": "image", "href": "assets/images/ai-visibility-dashboard.webp"}
        )
        assert preload is not None, "Hero preload link missing from <head>"
        assert preload.get("type") == "image/webp"
        assert preload.get("fetchpriority") == "high"


# ==============================================================================
# Feature 2: Below-Fold Image Eager Fix
# ==============================================================================
class TestFeature2BelowFoldFounderImage:
    def test_founder_portrait_lazy_and_dimensions(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        founder_img = soup.find("img", src=lambda s: s and "eric-coleman.webp" in s)
        assert founder_img is not None, "Founder image eric-coleman.webp not found in index.html"

        assert founder_img.get("loading") == "lazy", "Founder image must have loading='lazy'"
        assert founder_img.get("decoding") == "async", "Founder image must have decoding='async'"
        assert founder_img.get("width") == "160", "Founder image must have explicit width='160'"
        assert founder_img.get("height") == "160", "Founder image must have explicit height='160'"
        assert founder_img.get("loading") != "eager", "Founder image must not have loading='eager'"


# ==============================================================================
# Feature 3: Offscreen Image Async Decoding
# ==============================================================================
class TestFeature3OffscreenAsyncDecoding:
    def test_proof_card_images_async_decoding(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        google_img = soup.find("img", src=lambda s: s and "google-rank-ai-overview-desktop.webp" in s)
        reddit_img = soup.find("img", src=lambda s: s and "reddit-post-ai-overview-desktop.webp" in s)

        assert google_img is not None, "Google rank proof image not found"
        assert reddit_img is not None, "Reddit post proof image not found"

        assert google_img.get("decoding") == "async"
        assert google_img.get("loading") == "lazy"
        assert reddit_img.get("decoding") == "async"
        assert reddit_img.get("loading") == "lazy"


# ==============================================================================
# Feature 4: Active Image Compression Integrity
# ==============================================================================
class TestFeature4ActiveImageCompression:
    IMAGE_TARGETS = [
        ("assets/images/ai-visibility-dashboard.webp", (1454, 1082), 125000),
        ("assets/images/google-rank-ai-overview-desktop.webp", (1208, 690), 65000),
        ("assets/images/reddit-post-ai-overview-desktop.webp", (1208, 675), 55000),
        ("assets/images/eric-coleman.webp", (160, 160), 8000),
        ("og-image.jpg", (1200, 630), 25000),
        ("apple-touch-icon.png", (180, 180), 15000),
        ("favicon-32x32.png", (32, 32), 2000),
    ]

    @pytest.mark.parametrize("rel_path,expected_dims,max_bytes", IMAGE_TARGETS)
    def test_compressed_asset_dimensions_and_budget(self, rel_path, expected_dims, max_bytes):
        full_path = os.path.join(WORKSPACE_ROOT, rel_path)
        assert os.path.exists(full_path), f"Asset {rel_path} does not exist"

        file_size = os.path.getsize(full_path)
        assert file_size < max_bytes, f"{rel_path} size {file_size} B exceeds threshold {max_bytes} B"
        assert file_size > 100, f"{rel_path} size {file_size} B is suspiciously small"

        with Image.open(full_path) as im:
            assert im.size == expected_dims, f"{rel_path} dimensions {im.size} != {expected_dims}"


# ==============================================================================
# Feature 5: Google Fonts Pruning & DNS Hints
# ==============================================================================
class TestFeature5FontPruningAndDNSHints:
    def test_font_weights_pruned_in_index(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "1,600;1,700" not in content, "Unused Playfair Display italic 600/700 must be pruned"
        assert "Playfair+Display:ital,wght@1,400" in content, "Required Playfair Display 400 italic must be present"

    @pytest.mark.parametrize("page_name", PAGES)
    def test_dns_prefetch_hints_on_all_pages(self, page_name):
        page_path = os.path.join(WORKSPACE_ROOT, page_name)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        dns_hints = [
            link.get("href")
            for link in soup.find_all("link", rel=lambda r: r and "dns-prefetch" in r)
        ]
        assert "https://fonts.googleapis.com" in dns_hints, f"Missing googleapis dns-prefetch on {page_name}"
        assert "https://fonts.gstatic.com" in dns_hints, f"Missing gstatic dns-prefetch on {page_name}"


# ==============================================================================
# Feature 6: Lenis Script Deferral
# ==============================================================================
class TestFeature6LenisScriptDeferral:
    def test_lenis_script_tag_deferred(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        lenis_script = soup.find("script", src=lambda s: s and "lenis.min.js" in s)
        assert lenis_script is not None, "Lenis script tag missing from index.html"
        assert lenis_script.has_attr("defer"), "Lenis script tag must have 'defer' attribute"

    def test_lenis_runtime_initialization(self, page, base_url):
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        is_lenis_defined = page.evaluate("typeof Lenis !== 'undefined'")
        assert is_lenis_defined, "Lenis should be defined in browser execution environment"
        assert len(page._console_errors) == 0, f"Console errors observed: {page._console_errors}"


# ==============================================================================
# Feature 7: Production Caching & Security Headers Configurations
# ==============================================================================
class TestFeature7ProductionCachingHeaders:
    def test_cloudflare_headers_file(self):
        headers_path = os.path.join(WORKSPACE_ROOT, "_headers")
        assert os.path.exists(headers_path), "_headers file missing"

        with open(headers_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "/*" in content
        assert "X-Content-Type-Options: nosniff" in content
        assert "X-Frame-Options: DENY" in content
        assert "Referrer-Policy: strict-origin-when-cross-origin" in content
        assert "Permissions-Policy: camera=(), microphone=(), geolocation=()" in content
        assert "Cache-Control: public, max-age=0, must-revalidate" in content
        assert "/assets/*" in content
        assert "Cache-Control: public, max-age=31536000, immutable" in content
        assert "/sitemap.xml" in content
        assert "/robots.txt" in content

    def test_vercel_json_file(self):
        vercel_path = os.path.join(WORKSPACE_ROOT, "vercel.json")
        assert os.path.exists(vercel_path), "vercel.json file missing"

        with open(vercel_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("cleanUrls") is True
        headers_rules = data.get("headers", [])
        assert len(headers_rules) >= 3

        # Check global security headers rule
        global_rule = next((r for r in headers_rules if r.get("source") == "/(.*)"), None)
        assert global_rule is not None
        global_headers = {h["key"]: h["value"] for h in global_rule["headers"]}
        assert global_headers.get("X-Frame-Options") == "DENY"
        assert global_headers.get("X-Content-Type-Options") == "nosniff"

        # Check static asset immutable cache rule
        assets_rule = next((r for r in headers_rules if r.get("source") == "/assets/(.*)"), None)
        assert assets_rule is not None
        assets_headers = {h["key"]: h["value"] for h in assets_rule["headers"]}
        assert assets_headers.get("Cache-Control") == "public, max-age=31536000, immutable"

    def test_htaccess_file(self):
        htaccess_path = os.path.join(WORKSPACE_ROOT, ".htaccess")
        assert os.path.exists(htaccess_path), ".htaccess file missing"

        with open(htaccess_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "mod_mime.c" in content
        assert "mod_headers.c" in content
        assert "mod_expires.c" in content
        assert "mod_deflate.c" in content
        assert "mod_rewrite.c" in content
        assert 'Header always set X-Frame-Options "DENY"' in content
        assert 'Header set Cache-Control "public, max-age=31536000, immutable"' in content


# ==============================================================================
# Feature 8: Semantic <main> Landmark Remediation
# ==============================================================================
class TestFeature8SemanticMainLandmark:
    def test_main_content_wraps_sections(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        main = soup.find("main", id="main-content")
        assert main is not None, "<main id='main-content'> landmark missing"

        # Verify key sections are children/descendants of <main>
        sections_in_main = [s.get("id") for s in main.find_all("section") if s.get("id")]
        expected_sections = ["hero", "framework", "search", "compliance", "engine", "results", "pricing", "fit", "founder", "faq", "audit"]
        for expected in expected_sections:
            assert expected in sections_in_main, f"Section #{expected} must be enclosed within <main id='main-content'>"

        # Verify footer is AFTER </main>
        footer = soup.find("footer")
        assert footer is not None, "<footer> missing"
        assert footer not in main.descendants, "<footer> must not be inside <main>"


# ==============================================================================
# Feature 9: Skip-to-Content Navigation Links
# ==============================================================================
class TestFeature9SkipLinks:
    @pytest.mark.parametrize("page_name", PAGES)
    def test_skip_link_markup_presence(self, page_name):
        page_path = os.path.join(WORKSPACE_ROOT, page_name)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        skip_link = soup.find("a", href="#main-content")
        assert skip_link is not None, f"Skip link <a href='#main-content'> missing from {page_name}"
        classes = skip_link.get("class", [])
        assert "sr-only" in classes, f"Skip link in {page_name} must have 'sr-only' class"

        main_el = soup.find(id="main-content")
        assert main_el is not None, f"Target <main id='main-content'> missing from {page_name}"

    @pytest.mark.parametrize("page_name", ["", "404.html", "privacy.html", "terms.html"])
    def test_skip_link_keyboard_navigation(self, page, base_url, page_name):
        page.goto(f"{base_url}/{page_name}")
        page.wait_for_load_state("networkidle")

        # Press Tab to focus skip link
        page.keyboard.press("Tab")
        page.wait_for_timeout(50)

        focused_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName.toLowerCase() : ''")
        focused_href = page.evaluate("() => document.activeElement ? document.activeElement.getAttribute('href') : ''")

        assert focused_tag == "a", f"First tab stop on '{page_name}' must be an anchor link"
        assert focused_href == "#main-content", f"First tab stop on '{page_name}' must be skip link to #main-content"

        # Press Enter to activate skip link
        page.keyboard.press("Enter")
        page.wait_for_timeout(50)

        active_id = page.evaluate("() => document.activeElement ? document.activeElement.id : ''")
        assert active_id == "main-content", f"Activating skip link must move focus to #main-content on '{page_name}'"


# ==============================================================================
# Feature 10: Structured Data (JSON-LD) Expansion
# ==============================================================================
class TestFeature10StructuredDataExpansion:
    def test_jsonld_schemas_validity_and_graph(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        schema_scripts = soup.find_all("script", type="application/ld+json")
        assert len(schema_scripts) >= 1, "No JSON-LD scripts found in index.html"

        all_types = set()
        faq_entity = None
        service_entity = None

        for script in schema_scripts:
            data = json.loads(script.string)
            if "@graph" in data:
                for entity in data["@graph"]:
                    e_type = entity.get("@type")
                    all_types.add(e_type)
                    if e_type == "FAQPage":
                        faq_entity = entity
                    elif e_type == "ProfessionalService":
                        service_entity = entity
            else:
                all_types.add(data.get("@type"))

        required_types = {"Organization", "WebSite", "WebPage", "BreadcrumbList", "ProfessionalService", "FAQPage"}
        assert required_types.issubset(all_types), f"Missing required schemas. Found: {all_types}"

        # Verify FAQPage has exactly 5 Q&A pairs matching landing page objections
        assert faq_entity is not None, "FAQPage entity missing from schema graph"
        main_entities = faq_entity.get("mainEntity", [])
        assert len(main_entities) == 5, f"Expected 5 FAQ entities, got {len(main_entities)}"

        # Verify ProfessionalService has price catalog
        assert service_entity is not None
        catalog = service_entity.get("hasOfferCatalog")
        assert catalog is not None
        items = catalog.get("itemListElement", [])
        assert len(items) == 3, f"Expected 3 service tiers in catalog, found {len(items)}"


# ==============================================================================
# Feature 11: Subpage SEO Metadata & Social Cards
# ==============================================================================
class TestFeature11SubpageSEOMetadata:
    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_subpage_meta_tags(self, subpage):
        page_path = os.path.join(WORKSPACE_ROOT, subpage)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # Canonical
        canonical = soup.find("link", rel="canonical")
        assert canonical is not None, f"Canonical link missing in {subpage}"
        assert f"redgrowth.partners/{subpage}" in canonical.get("href")

        # Meta description
        desc = soup.find("meta", attrs={"name": "description"})
        assert desc is not None, f"Meta description missing in {subpage}"
        assert len(desc.get("content", "")) > 30

        # OpenGraph
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        assert og_title is not None and og_desc is not None and og_image is not None

        # Twitter card
        tw_card = soup.find("meta", attrs={"name": "twitter:card"})
        assert tw_card is not None and tw_card.get("content") == "summary_large_image"


# ==============================================================================
# Feature 12: Subpage Crawlability & Sitemap Update
# ==============================================================================
class TestFeature12CrawlabilityAndSitemap:
    def test_sitemap_xml_structure_and_subpages(self):
        sitemap_path = os.path.join(WORKSPACE_ROOT, "sitemap.xml")
        assert os.path.exists(sitemap_path), "sitemap.xml missing"

        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        locs = [el.text for el in root.findall(".//sm:loc", namespace)]
        assert "https://redgrowth.partners/" in locs
        assert "https://redgrowth.partners/privacy.html" in locs
        assert "https://redgrowth.partners/terms.html" in locs

        # Verify lastmod tags exist and follow ISO YYYY-MM-DD
        lastmods = [el.text for el in root.findall(".//sm:lastmod", namespace)]
        assert len(lastmods) >= 3
        for lm in lastmods:
            assert len(lm) == 10 and lm[4] == "-" and lm[7] == "-"

    @pytest.mark.parametrize("subpage", ["privacy.html", "terms.html"])
    def test_no_noindex_on_production_subpages(self, subpage):
        page_path = os.path.join(WORKSPACE_ROOT, subpage)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        if robots_meta:
            assert "noindex" not in robots_meta.get("content", "").lower(), f"noindex found in {subpage}"


# ==============================================================================
# Feature 13: Window Resize Debounce Optimization
# ==============================================================================
class TestFeature13WindowResizeDebounce:
    @pytest.mark.parametrize("page_name", ["index.html", "privacy.html", "terms.html"])
    def test_resize_handler_uses_request_animation_frame(self, page_name):
        page_path = os.path.join(WORKSPACE_ROOT, page_name)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "requestAnimationFrame" in content, f"requestAnimationFrame missing in {page_name}"
        assert "resize" in content, f"Resize listener missing in {page_name}"
        assert "resizeRaf" in content, f"RAF debounce guard variable 'resizeRaf' missing in {page_name}"


# ==============================================================================
# Feature 14: CSS & Zero Inline Styles Refinement
# ==============================================================================
class TestFeature14ZeroInlineStyles:
    @pytest.mark.parametrize("page_name", PAGES)
    def test_zero_inline_style_attributes(self, page_name):
        page_path = os.path.join(WORKSPACE_ROOT, page_name)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        elements_with_style = soup.find_all(lambda el: el.has_attr("style"))
        assert len(elements_with_style) == 0, (
            f"Found {len(elements_with_style)} element(s) with inline style attribute in {page_name}: "
            f"{[el.name for el in elements_with_style]}"
        )

    def test_timeline_track_gradient_in_css(self):
        css_path = os.path.join(WORKSPACE_ROOT, "assets", "css", "style.css")
        assert os.path.exists(css_path), "style.css missing"

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        assert ".timeline-track-gradient" in css_content, "Class .timeline-track-gradient missing from style.css"


# ==============================================================================
# Feature 15: Baseline Test Harmonization & Robustness
# ==============================================================================
class TestFeature15BaselineHarmonization:
    def test_modernized_hero_copy_present(self):
        index_path = os.path.join(WORKSPACE_ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Google AI Overviews" in content
        assert "SGE" not in content


# ==============================================================================
# Feature 16: Strict HTML Validation & Zero Console Errors
# ==============================================================================
class TestFeature16ComprehensiveE2E:
    @pytest.mark.parametrize("page_name", PAGES)
    def test_strict_html_syntax_validation(self, page_name):
        page_path = os.path.join(WORKSPACE_ROOT, page_name)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        validator = StrictHTMLValidator(page_name)
        validator.feed(content)
        validator.check_remaining()

        assert len(validator.errors) == 0, f"HTML syntax errors in {page_name}: {validator.errors}"
        assert len(validator.duplicate_ids) == 0, f"Duplicate IDs in {page_name}: {validator.duplicate_ids}"

    @pytest.mark.parametrize("page_name", ["", "404.html", "privacy.html", "terms.html"])
    def test_zero_console_errors_and_http_200(self, page, base_url, page_name):
        response = page.goto(f"{base_url}/{page_name}")
        assert response.status == 200, f"Page '{page_name}' returned status {response.status}"
        page.wait_for_load_state("networkidle")

        assert len(page._console_errors) == 0, f"Console errors on '{page_name}': {page._console_errors}"
        assert len(page._page_errors) == 0, f"Page runtime errors on '{page_name}': {page._page_errors}"
