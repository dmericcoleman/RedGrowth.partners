from playwright.sync_api import sync_playwright

def test_wake_all_frames():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

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
                                currentTime: this.animate ? this.animate.currentTime : 0,
                                value: this.animate ? this.animate.value : 0,
                                scrollY: window.scrollY
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
        page.wait_for_timeout(2000)

        page.evaluate("() => { window.__rafHistory = []; }")
        page.evaluate("() => { window.__lenis.time = 0; }")

        page.locator("header nav a[href='#pricing']").first.click()
        page.wait_for_timeout(400)

        history = page.evaluate("() => window.__rafHistory")
        print(f"Total frames recorded: {len(history)}")
        for i, f in enumerate(history):
            print(f"  Frame {i}: t={f['t']:.1f}, delta={f['deltaMs']:.1f}ms, isRunning={f['isRunning']}, isScrolling={f['isScrolling']}, currentTime={f['currentTime']:.3f}, animVal={f['value']:.1f}, scrollY={f['scrollY']}")

        browser.close()

if __name__ == "__main__":
    test_wake_all_frames()
