import os
import re
import json
import subprocess
import pytest
from PIL import Image
import numpy as np
from bs4 import BeautifulSoup
from skimage.metrics import structural_similarity as ssim

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUP_DIR = os.path.join(WORKSPACE_ROOT, ".agents", "teamwork", "explorer_m1_1", "image_backups")

ACTIVE_IMAGES = [
    {
        "rel_path": "assets/images/ai-visibility-dashboard.webp",
        "backup_name": "ai-visibility-dashboard.webp.orig",
        "dims": (1454, 1082),
        "format": "WEBP",
        "mode": "RGBA",
    },
    {
        "rel_path": "assets/images/google-rank-ai-overview-desktop.webp",
        "backup_name": "google-rank-ai-overview-desktop.webp.orig",
        "dims": (1208, 690),
        "format": "WEBP",
        "mode": "RGB",
    },
    {
        "rel_path": "assets/images/reddit-post-ai-overview-desktop.webp",
        "backup_name": "reddit-post-ai-overview-desktop.webp.orig",
        "dims": (1208, 675),
        "format": "WEBP",
        "mode": "RGB",
    },
    {
        "rel_path": "assets/images/eric-coleman.webp",
        "backup_name": "eric-coleman.webp.orig",
        "dims": (160, 160),
        "format": "WEBP",
        "mode": "RGB",
    },
    {
        "rel_path": "og-image.jpg",
        "backup_name": "og-image.jpg.orig",
        "dims": (1200, 630),
        "format": "JPEG",
        "mode": "RGB",
    },
    {
        "rel_path": "apple-touch-icon.png",
        "backup_name": "apple-touch-icon.png.orig",
        "dims": (180, 180),
        "format": "PNG",
        "mode": "RGBA",
    },
    {
        "rel_path": "favicon-32x32.png",
        "backup_name": "favicon-32x32.png.orig",
        "dims": (32, 32),
        "format": "PNG",
        "mode": "RGBA",
    },
]

def test_backup_images_match_git_head():
    """Verify that backup originals in image_backups are bit-for-bit identical to git HEAD."""
    for img in ACTIVE_IMAGES:
        backup_file = os.path.join(BACKUP_DIR, img["backup_name"])
        assert os.path.exists(backup_file), f"Backup file missing: {backup_file}"
        with open(backup_file, "rb") as f:
            backup_bytes = f.read()
        
        git_bytes = subprocess.check_output(["git", "show", f"HEAD:{img['rel_path']}"])
        assert backup_bytes == git_bytes, f"Backup {img['backup_name']} diverges from git HEAD!"

def test_exact_pixel_dimensions_strictly_preserved():
    """Verify that every compressed image preserves exact width and height."""
    for img in ACTIVE_IMAGES:
        curr_path = os.path.join(WORKSPACE_ROOT, img["rel_path"])
        backup_path = os.path.join(BACKUP_DIR, img["backup_name"])
        
        with Image.open(backup_path) as im_orig, Image.open(curr_path) as im_curr:
            assert im_curr.size == img["dims"], f"{img['rel_path']} size {im_curr.size} != expected {img['dims']}"
            assert im_curr.size == im_orig.size, f"{img['rel_path']} size {im_curr.size} != backup {im_orig.size}"

def test_preload_link_validity_and_attributes():
    """Verify index.html head contains valid preload tags pointing to existing files with correct attributes."""
    index_path = os.path.join(WORKSPACE_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    preloads = soup.find_all("link", rel=lambda r: r and "preload" in r)
    assert len(preloads) > 0, "No preload links found in index.html"
    
    for p in preloads:
        href = p.get("href")
        as_attr = p.get("as")
        type_attr = p.get("type")
        fetchpriority = p.get("fetchpriority")
        
        assert href, "Preload link missing href"
        target_path = os.path.join(WORKSPACE_ROOT, href.lstrip("/"))
        assert os.path.exists(target_path), f"Preload href '{href}' points to non-existent file: {target_path}"
        
        assert as_attr in ["image", "style", "script", "font"], f"Unexpected 'as' attribute: {as_attr}"
        if as_attr == "image":
            assert type_attr in ["image/webp", "image/png", "image/jpeg", "image/svg+xml"], f"Invalid type attribute: {type_attr}"
            assert fetchpriority in ["high", "low", "auto", None], f"Invalid fetchpriority: {fetchpriority}"

def test_cloudflare_headers_structure():
    """Verify _headers syntax, non-conflicting rules, and proper cache headers."""
    headers_file = os.path.join(WORKSPACE_ROOT, "_headers")
    assert os.path.exists(headers_file), "_headers file missing"
    
    with open(headers_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    routes = {}
    current_route = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and not line.startswith("\t"):
            current_route = stripped
            routes[current_route] = {}
        else:
            assert current_route is not None, f"Header without route: {line}"
            parts = stripped.split(":", 1)
            assert len(parts) == 2, f"Malformed header in _headers: {line}"
            k, v = parts[0].strip(), parts[1].strip()
            routes[current_route][k] = v
            
    assert "/*" in routes
    assert "/assets/*" in routes
    assert "/robots.txt" in routes
    assert "/sitemap.xml" in routes
    
    # Global security headers
    assert routes["/*"]["X-Content-Type-Options"] == "nosniff"
    assert routes["/*"]["X-Frame-Options"] == "DENY"
    assert routes["/*"]["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert routes["/*"]["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "max-age=0" in routes["/*"]["Cache-Control"]
    
    # Static asset 1-year caching
    assert "max-age=31536000" in routes["/assets/*"]["Cache-Control"]
    assert "immutable" in routes["/assets/*"]["Cache-Control"]
    assert routes["/assets/*"]["Access-Control-Allow-Origin"] == "*"

def test_vercel_json_regex_resolution():
    """Verify vercel.json headers regex patterns correctly match and resolve target URLs."""
    vercel_file = os.path.join(WORKSPACE_ROOT, "vercel.json")
    assert os.path.exists(vercel_file), "vercel.json missing"
    
    with open(vercel_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data.get("cleanUrls") is True
    headers_rules = data.get("headers", [])
    
    test_cases = [
        ("/", {"X-Frame-Options": "DENY", "Cache-Control": "public, max-age=0, must-revalidate"}),
        ("/index.html", {"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=0, must-revalidate"}),
        ("/assets/images/ai-visibility-dashboard.webp", {"Cache-Control": "public, max-age=31536000, immutable", "Access-Control-Allow-Origin": "*"}),
        ("/assets/css/style.css", {"Cache-Control": "public, max-age=31536000, immutable"}),
        ("/favicon-32x32.png", {"Cache-Control": "public, max-age=31536000, immutable", "Access-Control-Allow-Origin": "*"}),
        ("/robots.txt", {"Cache-Control": "public, max-age=86400, stale-while-revalidate=86400"}),
        ("/sitemap.xml", {"Cache-Control": "public, max-age=86400, stale-while-revalidate=86400"}),
    ]
    
    for url, expected_headers in test_cases:
        effective = {}
        for rule in headers_rules:
            pattern = "^" + rule["source"] + "$"
            if re.match(pattern, url):
                for h in rule["headers"]:
                    effective[h["key"]] = h["value"]
        for ek, ev in expected_headers.items():
            assert ek in effective, f"URL {url} missing expected header {ek}"
            assert effective[ek] == ev, f"URL {url} header {ek}='{effective[ek]}' != expected '{ev}'"

def test_apache_htaccess_syntax():
    """Verify .htaccess module blocks, rewrite rules, and security headers."""
    htaccess_file = os.path.join(WORKSPACE_ROOT, ".htaccess")
    assert os.path.exists(htaccess_file), ".htaccess missing"
    
    with open(htaccess_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "<IfModule mod_mime.c>" in content
    assert "<IfModule mod_headers.c>" in content
    assert "<IfModule mod_expires.c>" in content
    assert "<IfModule mod_deflate.c>" in content
    assert "<IfModule mod_rewrite.c>" in content
    
    # Confirm rewrite regexes
    assert "RewriteCond %{THE_REQUEST} ^[A-Z]{3,}\\s([^.]+)\\.html" in content or "RewriteCond %{THE_REQUEST} ^[A-Z]{3,}\\s([^.]+)\\.html [NC]" in content
    assert "RewriteRule ^(.*?)/?$ $1.html [L]" in content

def test_ssim_all_active_images():
    """Adversarially challenge SSIM quality: verify whether SSIM >= 0.99 under standard Wang et al. 2004 skimage metric."""
    results = {}
    failures = []
    
    for img in ACTIVE_IMAGES:
        curr_path = os.path.join(WORKSPACE_ROOT, img["rel_path"])
        backup_path = os.path.join(BACKUP_DIR, img["backup_name"])
        
        with Image.open(backup_path) as im_orig, Image.open(curr_path) as im_curr:
            gray_orig = np.array(im_orig.convert("L"))
            gray_curr = np.array(im_curr.convert("L"))
            s_gray = ssim(gray_orig, gray_curr, data_range=255)
            
            if im_orig.mode in ["RGB", "RGBA"]:
                rgb_orig = np.array(im_orig.convert("RGB"))
                rgb_curr = np.array(im_curr.convert("RGB"))
                s_rgb = ssim(rgb_orig, rgb_curr, channel_axis=2, data_range=255)
            else:
                s_rgb = s_gray
                
            results[img["rel_path"]] = {"ssim_gray": s_gray, "ssim_rgb": s_rgb}
            
            # The prompt requires: "Confirm SSIM >= 0.99 for all active WebP and JPEG images."
            if s_gray < 0.99:
                failures.append(f"{img['rel_path']}: SSIM(gray)={s_gray:.6f} < 0.99 threshold!")
    
    assert not failures, f"SSIM threshold violations detected:\n" + "\n".join(failures)
