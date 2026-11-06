from playwright.sync_api import sync_playwright

def test_reproduce():
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
        
        # Let the page idle for 2 seconds so the RAF loop sleeps
        page.wait_for_timeout(2000)

        # Clear history to isolate the wake-up event
        page.evaluate("() => { window.__rafHistory = []; }")

        # Now click #pricing anchor
        print("Clicking #pricing anchor after 2s idle sleep...")
        page.locator("header nav a[href='#pricing']").first.click()

        # Wait 100ms
        page.wait_for_timeout(100)

        # Inspect the recorded frames
        history = page.evaluate("() => window.__rafHistory")
        print(f"Recorded {len(history)} frames on wake-up:")
        for i, frame in enumerate(history[:5]):
            print(f"  Frame {i}: t={frame['t']:.1f}, prevTime={frame['prevTime']}, deltaMs={frame['deltaMs']:.1f}ms, isRunning={frame['isRunning']}, currentTime={frame['currentTime']}")

        scrollY = page.evaluate("() => window.scrollY")
        print(f"Current scrollY: {scrollY}")

        browser.close()

if __name__ == "__main__":
    test_reproduce()
