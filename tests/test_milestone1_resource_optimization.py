import os
import json
import pytest
from PIL import Image

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_feature1_lcp_hero_preload():
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    assert '<link rel="preload" as="image" href="assets/images/ai-visibility-dashboard.webp" type="image/webp" fetchpriority="high"/>' in html, (
        "Feature 1: LCP hero preload link missing or improperly configured in index.html"
    )

def test_feature2_founder_portrait_attributes():
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    assert 'assets/images/eric-coleman.webp' in html
    assert 'loading="lazy" decoding="async" width="160" height="160"' in html, (
        "Feature 2: Founder portrait attributes (loading=lazy, decoding=async, 160x160) missing in index.html"
    )
    assert 'loading="eager"' not in html, "Feature 2: loading=eager should be removed from founder portrait"

def test_feature3_offscreen_images_async_decoding():
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    assert 'assets/images/google-rank-ai-overview-desktop.webp' in html
    assert 'assets/images/reddit-post-ai-overview-desktop.webp' in html
    
    # Check decoding="async" on both images
    assert 'loading="lazy" decoding="async" width="1208" height="690"' in html
    assert 'loading="lazy" decoding="async" width="1208" height="675"' in html

def test_feature4_compressed_images_integrity():
    targets = [
        ("assets/images/ai-visibility-dashboard.webp", (1454, 1082), 125000),
        ("assets/images/google-rank-ai-overview-desktop.webp", (1208, 690), 65000),
        ("assets/images/reddit-post-ai-overview-desktop.webp", (1208, 675), 55000),
        ("assets/images/eric-coleman.webp", (160, 160), 8000),
        ("og-image.jpg", (1200, 630), 25000),
        ("apple-touch-icon.png", (180, 180), 15000),
        ("favicon-32x32.png", (32, 32), 2000),
    ]
    for rel_path, expected_dims, max_bytes in targets:
        full_path = os.path.join(WORKSPACE_ROOT, rel_path)
        assert os.path.exists(full_path), f"File {rel_path} does not exist"
        sz = os.path.getsize(full_path)
        assert sz < max_bytes, f"{rel_path} size {sz} B exceeds threshold {max_bytes} B"
        with Image.open(full_path) as im:
            assert im.size == expected_dims, f"{rel_path} dimensions {im.size} != {expected_dims}"

def test_feature5_font_pruning_and_dns_hints():
    # Verify index.html font URL pruned of unused weights 600/700
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    assert "Playfair+Display:ital,wght@1,400&amp;family=Plus+Jakarta+Sans" in html or "Playfair+Display:ital,wght@1,400&family=Plus+Jakarta+Sans" in html
    assert "1,600;1,700" not in html, "Unused Playfair Display weights 600/700 should be pruned"
    
    # Verify DNS prefetch hints across all pages
    for page in ["index.html", "404.html", "privacy.html", "terms.html"]:
        page_path = os.path.join(WORKSPACE_ROOT, page)
        with open(page_path, "r", encoding="utf-8") as f:
            c = f.read()
        assert '<link rel="dns-prefetch" href="https://fonts.googleapis.com"' in c or '<link rel="dns-prefetch" href="https://fonts.googleapis.com">' in c
        assert '<link rel="dns-prefetch" href="https://fonts.gstatic.com"' in c or '<link rel="dns-prefetch" href="https://fonts.gstatic.com">' in c

def test_feature6_lenis_defer_and_lifecycle_guard(page, base_url):
    # Verify DOM contains defer and lifecycle hook
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    assert '<script src="assets/js/vendor/lenis.min.js" defer></script>' in html
    assert "document.addEventListener('DOMContentLoaded', initLenis)" in html
    
    # Test live in browser with base_url fixture
    warnings = []
    errors = []
    page.on("console", lambda msg: warnings.append(msg.text) if msg.type == "warning" else (errors.append(msg.text) if msg.type == "error" else None))
    
    page.goto(f"{base_url}/index.html")
    page.wait_for_load_state("networkidle")
    
    is_lenis_defined = page.evaluate("typeof Lenis !== 'undefined'")
    assert is_lenis_defined, "Lenis must be defined on window object"
    assert not any("Lenis smooth scroll library not detected" in w for w in warnings), f"Lenis warning observed: {warnings}"
    assert len(errors) == 0, f"Console errors observed: {errors}"

def test_feature7_server_configuration_files():
    # 1. _headers (Cloudflare Pages)
    headers_path = os.path.join(WORKSPACE_ROOT, "_headers")
    assert os.path.exists(headers_path), "_headers configuration file missing"
    with open(headers_path, "r", encoding="utf-8") as f:
        h = f.read()
    assert "/assets/*" in h
    assert "Cache-Control: public, max-age=31536000, immutable" in h
    assert "X-Frame-Options: DENY" in h
    assert "X-Content-Type-Options: nosniff" in h
    assert "Referrer-Policy: strict-origin-when-cross-origin" in h
    assert "Permissions-Policy: camera=(), microphone=(), geolocation=()" in h

    # 2. vercel.json (Vercel)
    vercel_path = os.path.join(WORKSPACE_ROOT, "vercel.json")
    assert os.path.exists(vercel_path), "vercel.json configuration file missing"
    with open(vercel_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("cleanUrls") is True
    assert any(rule["source"] == "/assets/(.*)" for rule in data["headers"])

    # 3. .htaccess (Apache)
    htaccess_path = os.path.join(WORKSPACE_ROOT, ".htaccess")
    assert os.path.exists(htaccess_path), ".htaccess configuration file missing"
    with open(htaccess_path, "r", encoding="utf-8") as f:
        a = f.read()
    assert "mod_headers.c" in a
    assert "mod_expires.c" in a
    assert "mod_deflate.c" in a
    assert "Header always set X-Frame-Options \"DENY\"" in a
