"""
Empirical Challenger Test Suite for Milestone 2: GPU Rendering & Layout Reflow Stress Testing
Target: RedGrowth.partners (index.html, assets/css/input.css, assets/css/style.css)
Author: Teamwork Challenger (critic/specialist)
Parent Dispatch ID: d3abd61a-7f99-4fdd-966e-fae9e8a78b8b

Challenge Verifications:
1. Backdrop-Blur Count & Stationary Card Verification:
   - Query all elements with computed backdropFilter != 'none'.
   - Confirm stationary cards have backdropFilter == 'none'.
   - Confirm only designated elements (sticky header) have backdrop blur.
2. GPU Composited Layer Promotion:
   - Verify that .ambient-blur-blob elements have computed transform containing matrix3d or translateZ and willChange == 'transform'.
3. Soundwave Zero-Layout Reflow:
   - Inspect .soundwave-bar computed animation properties:
     confirm keyframe animates transform: scaleY() with transform-origin: bottom, and does NOT animate height.
4. Execution Performance & Scroll Smoothness:
   - Verify scroll smoothness in headless browser without GPU thrashing (monitoring long frames >33ms, >50ms, and average FPS).
"""

import re
import pytest
from playwright.sync_api import Page, expect

def test_backdrop_blur_count_and_stationary_cards(page: Page, base_url: str):
    """
    Challenge 1: Backdrop-Blur Count Verification
    - Query all elements with computed backdropFilter != 'none'
    - Verify that stationary cards have backdropFilter == 'none'
    - Verify that only designated elements (sticky header) have backdrop blur
    """
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    
    # Query all elements in DOM with computed backdropFilter != 'none'
    backdrop_elements = page.evaluate("""() => {
        const all = Array.from(document.querySelectorAll('*'));
        return all.filter(el => {
            const cs = window.getComputedStyle(el);
            const bf = cs.backdropFilter || cs.webkitBackdropFilter || 'none';
            return bf !== 'none' && bf !== '';
        }).map(el => {
            const cs = window.getComputedStyle(el);
            return {
                tagName: el.tagName,
                id: el.id || '',
                className: (el.className && typeof el.className === 'string') ? el.className : '',
                backdropFilter: cs.backdropFilter || cs.webkitBackdropFilter,
                isStationaryCard: (
                    el.classList.contains('card') ||
                    el.classList.contains('proof-card') ||
                    el.classList.contains('glass-card') ||
                    el.classList.contains('glass-card-elevated')
                )
            };
        });
    }""")
    
    # Print discovered backdrop elements for empirical diagnostic logs
    print(f"\n[Backdrop Audit] Found {len(backdrop_elements)} elements with backdrop-filter:")
    for idx, item in enumerate(backdrop_elements):
        print(f"  {idx+1}. <{item['tagName']} id='{item['id']}' class='{item['className'][:60]}...'> -> {item['backdropFilter']}")

    # 1. Designated element check: Sticky <header> must have backdrop blur
    header_blurs = [e for e in backdrop_elements if e['tagName'] == 'HEADER']
    assert len(header_blurs) >= 1, "Expected sticky <header> to have backdrop-blur"
    assert "blur" in header_blurs[0]['backdropFilter'], f"Expected header backdropFilter to contain blur, got {header_blurs[0]['backdropFilter']}"

    # 2. Stationary cards check: Proof cards and bento cards MUST NOT have backdrop blur
    stationary_cards_with_blur = [e for e in backdrop_elements if e['isStationaryCard'] and ('proof-card' in e['className'] or 'card' in e['className'])]
    assert len(stationary_cards_with_blur) == 0, (
        f"VIOLATION: Found {len(stationary_cards_with_blur)} stationary card(s) with backdrop-filter! "
        f"Offending elements: {stationary_cards_with_blur}"
    )

    # 3. Marquee ticker items: moving glass cards MUST NOT have backdrop blur
    marquee_cards_with_blur = [e for e in backdrop_elements if 'glass-card-elevated' in e['className']]
    assert len(marquee_cards_with_blur) == 0, (
        f"VIOLATION: Found {len(marquee_cards_with_blur)} element(s) with .glass-card-elevated applying backdrop-filter! "
        f"Offending elements: {marquee_cards_with_blur}"
    )

    # 4. Strict backdrop count: ONLY sticky header (and optional mobile menu overlay when opened)
    # Stationary and scrolling elements should not bloat the count
    non_nav_backdrop_elements = [
        e for e in backdrop_elements
        if e['tagName'] != 'HEADER' and e['id'] not in ('mobileMenu', 'mobileMenuBackdrop')
    ]
    assert len(non_nav_backdrop_elements) == 0, (
        f"VIOLATION: Found {len(non_nav_backdrop_elements)} unexpected non-header elements with backdrop-filter: "
        f"{non_nav_backdrop_elements}"
    )


def test_ambient_blur_blob_gpu_promotion(page: Page, base_url: str):
    """
    Challenge 2: GPU Composited Layer Promotion
    - Verify that .ambient-blur-blob elements have computed transform containing matrix3d or translateZ
      and willChange == 'transform'.
    """
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    
    blob_data = page.evaluate("""() => {
        const blobs = Array.from(document.querySelectorAll('.ambient-blur-blob'));
        return blobs.map((el, i) => {
            const cs = window.getComputedStyle(el);
            return {
                index: i,
                inlineTransform: el.style.transform || '',
                computedTransform: cs.transform || '',
                computedWillChange: cs.willChange || '',
                computedContain: cs.contain || '',
                computedFilter: cs.filter || ''
            };
        });
    }""")
    
    assert len(blob_data) == 11, f"Expected 11 .ambient-blur-blob elements, found {len(blob_data)}"
    
    for b in blob_data:
        # Check willChange promotion
        assert b['computedWillChange'] == 'transform', (
            f"Blob #{b['index']} expected willChange == 'transform', got '{b['computedWillChange']}'"
        )
        
        # Check contain property
        assert 'strict' in b['computedContain'], (
            f"Blob #{b['index']} expected contain: strict, got '{b['computedContain']}'"
        )
        
        # Verify 3D Composited Layer Promotion
        # Note: Chromium resolves translateZ(0) to 2D matrix(...) unless Z has non-zero coordinate or matrix3d
        # We test both computed transform and inline transform
        has_3d_computed = ('matrix3d' in b['computedTransform'] or 'translateZ' in b['computedTransform'])
        has_3d_inline = ('translateZ' in b['inlineTransform'] or 'matrix3d' in b['inlineTransform'] or 'translate3d' in b['inlineTransform'])
        
        print(f"Blob #{b['index']}: inline='{b['inlineTransform']}', computed='{b['computedTransform']}'")
        
        # Dispatch Requirement: "computed transform containing matrix3d or translateZ"
        assert has_3d_computed or has_3d_inline, (
            f"Blob #{b['index']} lacks 3D GPU layer promotion! "
            f"computedTransform='{b['computedTransform']}', inlineTransform='{b['inlineTransform']}'"
        )
        assert has_3d_computed, (
            f"STRICT COMPUTED CHECK: Blob #{b['index']} computedTransform is '{b['computedTransform']}', "
            f"which is serialized as 2D matrix and does not contain 'matrix3d' or 'translateZ'!"
        )


def test_soundwave_zero_layout_reflow(page: Page, base_url: str):
    """
    Challenge 3: Soundwave Zero-Layout Reflow
    - Inspect .soundwave-bar computed animation properties:
      confirm keyframe animates transform: scaleY() with transform-origin: bottom,
      and does NOT animate height.
    """
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    
    soundwave_info = page.evaluate("""() => {
        const bars = Array.from(document.querySelectorAll('.soundwave-bar'));
        const barData = bars.map((b, i) => {
            const cs = window.getComputedStyle(b);
            return {
                index: i,
                animationName: cs.animationName,
                transformOrigin: cs.transformOrigin,
                willChange: cs.willChange,
                height: cs.height
            };
        });
        
        // Inspect stylesheet keyframe rules for soundwave-pulse
        let keyframeRules = [];
        for (const sheet of Array.from(document.styleSheets)) {
            try {
                for (const rule of Array.from(sheet.cssRules || [])) {
                    if (rule.type === CSSRule.KEYFRAMES_RULE && rule.name === 'soundwave-pulse') {
                        for (const kf of Array.from(rule.cssRules)) {
                            keyframeRules.push({
                                keyText: kf.keyText,
                                cssText: kf.cssText
                            });
                        }
                    }
                }
            } catch(e) {}
        }
        
        return { barCount: bars.length, barData, keyframeRules };
    }""")
    
    # 1. Confirm exactly 5 soundwave bars present
    assert soundwave_info['barCount'] == 5, f"Expected 5 soundwave bars, found {soundwave_info['barCount']}"
    
    # 2. Confirm each bar has willChange: transform and animationName: soundwave-pulse
    for b in soundwave_info['barData']:
        assert b['animationName'] == 'soundwave-pulse', f"Bar #{b['index']} unexpected animationName {b['animationName']}"
        assert b['willChange'] == 'transform', f"Bar #{b['index']} unexpected willChange {b['willChange']}"
        assert b['height'] == '20px', f"Bar #{b['index']} expected fixed height 20px, got {b['height']}"
        # transformOrigin bottom on 4px wide, 20px high element resolves to "2px 20px" or "bottom"
        assert b['transformOrigin'] in ('2px 20px', '50% 100%', 'bottom'), (
            f"Bar #{b['index']} transformOrigin should be bottom, got {b['transformOrigin']}"
        )
    
    # 3. Confirm keyframe animates transform: scaleY() and does NOT animate height
    assert len(soundwave_info['keyframeRules']) > 0, "No keyframe rules found for @keyframes soundwave-pulse"
    for kf in soundwave_info['keyframeRules']:
        css_text = kf['cssText'].lower()
        print(f"Keyframe [{kf['keyText']}]: {css_text}")
        assert "transform" in css_text and "scaley" in css_text, (
            f"Keyframe {kf['keyText']} must animate transform: scaleY(), got: {css_text}"
        )
        assert "height" not in css_text, (
            f"VIOLATION: Keyframe {kf['keyText']} animates height, causing layout reflow! {css_text}"
        )


def test_scroll_execution_performance_without_gpu_thrashing(page: Page, base_url: str):
    """
    Challenge 4: Execution Performance & Scroll Smoothness
    - Verify scroll smoothness in headless browser without GPU thrashing
    - Stress-test frame budget during continuous document scroll
    """
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(f"{base_url}/index.html", wait_until="networkidle")
    page.wait_for_timeout(1000)
    
    metrics = page.evaluate("""async () => {
        return new Promise(resolve => {
            let frameDeltas = [];
            let lastTimestamp = performance.now();
            let recording = true;
            
            function onFrame(now) {
                frameDeltas.push(now - lastTimestamp);
                lastTimestamp = now;
                if (recording) requestAnimationFrame(onFrame);
            }
            requestAnimationFrame(onFrame);
            
            const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
            const duration = 2000;
            const startTime = performance.now();
            
            function step(now) {
                const elapsed = now - startTime;
                const progress = Math.min(1.0, elapsed / duration);
                window.scrollTo(0, progress * totalScroll);
                if (progress < 1.0) {
                    requestAnimationFrame(step);
                } else {
                    recording = false;
                    const sorted = [...frameDeltas].sort((a,b) => a - b);
                    const avg = frameDeltas.reduce((a, b) => a + b, 0) / frameDeltas.length;
                    const p95 = sorted[Math.floor(sorted.length * 0.95)] || 0;
                    const p99 = sorted[Math.floor(sorted.length * 0.99)] || 0;
                    const max = sorted[sorted.length - 1] || 0;
                    const framesOver33ms = frameDeltas.filter(d => d > 33.3).length;
                    const framesOver50ms = frameDeltas.filter(d => d > 50.0).length;
                    
                    resolve({
                        frameCount: frameDeltas.length,
                        avgFrameMs: avg,
                        fps: 1000 / avg,
                        p95FrameMs: p95,
                        p99FrameMs: p99,
                        maxFrameMs: max,
                        framesOver33ms,
                        framesOver50ms
                    });
                }
            }
            requestAnimationFrame(step);
        });
    }""")
    
    print("\n[Scroll Performance Metrics]")
    print(f"  Total Frames: {metrics['frameCount']}")
    print(f"  Average Frame Time: {metrics['avgFrameMs']:.2f} ms ({metrics['fps']:.1f} FPS)")
    print(f"  95th Percentile: {metrics['p95FrameMs']:.2f} ms")
    print(f"  99th Percentile: {metrics['p99FrameMs']:.2f} ms")
    print(f"  Max Frame Time: {metrics['maxFrameMs']:.2f} ms")
    print(f"  Frames > 33ms: {metrics['framesOver33ms']} ({(metrics['framesOver33ms']/metrics['frameCount']*100):.1f}%)")
    print(f"  Frames > 50ms: {metrics['framesOver50ms']} ({(metrics['framesOver50ms']/metrics['frameCount']*100):.1f}%)")
    
    # Assert acceptable baseline in headless software rasterization
    # Average FPS must not degrade below 15 FPS
    assert metrics['fps'] >= 15.0, f"Scroll FPS degraded to {metrics['fps']:.1f} FPS!"
