from playwright.sync_api import sync_playwright

def test_wake_reset():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Intercept Lenis and instrument raf()
        page.add_init_script("""
            window.__rafHistory = [];
            let _OrigLenis = undefined;
            Object.defineProperty(window, 'Lenis', {
                configurable: true,
                enumerable: true,
                set(cls) {
                    _OrigLenis = cls;
                    function LenisWrapper(...args) {
                        const inst = new cls(...args);
                        window.__lenis = inst;
                        
                        // Instrument inst.raf to record time delta
                        const origRaf = inst.raf.bind(inst);
                        inst.raf = function(t) {
                            const prevTime = this.time;
                            const delta = t - (prevTime || t);
                            window.__rafHistory.push({
                                t: t,
                                prevTime: prevTime,
                                deltaMs: delta,
                                isRunning: this.animate ? this.animate.isRunning : false,
                                isScrolling: this.isScrolling,
                                currentTime: this.animate ? this.animate.currentTime : 0
                            });
                            return origRaf(t);
                        };
                        return inst;
                    }
                    LenisWrapper.prototype = cls.prototype;
                    window.__LenisWrapper = LenisWrapper;
                },
                get() {
                    return window.__LenisWrapper || _OrigLenis;
                }
            });
        """)

        page.goto("http://127.0.0.1:8000/index.html")
        page.wait_for_load_state("networkidle")
        
        # Let the page idle for 2 seconds
        page.wait_for_timeout(2000)

        # Clear history
        page.evaluate("() => { window.__rafHistory = []; }")

        # Set lenis.time = 0 before clicking to simulate the proper wakeRaf reset
        page.evaluate("() => { window.__lenis.time = 0; }")

        # Now click #pricing anchor
        print("Clicking #pricing anchor with lenis.time = 0 reset...")
        page.locator("header nav a[href='#pricing']").first.click()

        # Wait 400ms
        page.wait_for_timeout(400)

        history = page.evaluate("() => window.__rafHistory")
        print(f"Recorded {len(history)} frames during first 400ms:")
        for i, frame in enumerate(history[:5]):
            print(f"  Frame {i}: t={frame['t']:.1f}, prevTime={frame['prevTime']}, deltaMs={frame['deltaMs']:.1f}ms, isRunning={frame['isRunning']}, currentTime={frame['currentTime']:.3f}")

        scrollY = page.evaluate("() => window.scrollY")
        print(f"ScrollY at 400ms: {scrollY}")

        # Wait remaining 800ms for full settle
        page.wait_for_timeout(800)
        final_y = page.evaluate("() => window.scrollY")
        print(f"Final scrollY: {final_y}")

        browser.close()

if __name__ == "__main__":
    test_wake_reset()
