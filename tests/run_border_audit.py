import math
import re
from playwright.sync_api import sync_playwright

def channel_linear(c):
    v = c / 255.0
    return v / 12.92 if v <= 0.03928 else math.pow((v + 0.055) / 1.055, 2.4)

def get_lum(r, g, b):
    return 0.2126 * channel_linear(r) + 0.7152 * channel_linear(g) + 0.0722 * channel_linear(b)

def parse_rgba(s):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)', s)
    return [int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)) if m.group(4) else 1.0]

def blend(fg, bg):
    a = fg[3]
    return [round(fg[0]*a + bg[0]*(1-a)), round(fg[1]*a + bg[1]*(1-a)), round(fg[2]*a + bg[2]*(1-a)), 1.0]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.goto('http://127.0.0.1:8000/#audit')
        data = page.evaluate('''() => {
            const inp = document.querySelector("#companyDomain");
            const card = inp.closest('.bg-\\\\[\\\\#15213A\\\\]\\\\/95');
            const inpSt = window.getComputedStyle(inp);
            const cardSt = window.getComputedStyle(card);
            return {
                inpBorder: inpSt.borderColor,
                inpBg: inpSt.backgroundColor,
                cardBg: cardSt.backgroundColor
            };
        }''')
        print('DOM styles:', data)
        canvas = [11, 17, 32, 1.0]
        card_raw = parse_rgba(data['cardBg'])
        card_effective = blend(card_raw, canvas)
        
        inp_bg_raw = parse_rgba(data['inpBg'])
        inp_bg_effective = blend(inp_bg_raw, card_effective)
        
        border_raw = parse_rgba(data['inpBorder'])
        border_on_card = blend(border_raw, card_effective)
        border_on_inp = blend(border_raw, inp_bg_effective)
        
        lum_card = get_lum(*card_effective[:3])
        lum_inp = get_lum(*inp_bg_effective[:3])
        lum_border_card = get_lum(*border_on_card[:3])
        lum_border_inp = get_lum(*border_on_inp[:3])
        
        ratio_card = (max(lum_border_card, lum_card) + 0.05) / (min(lum_border_card, lum_card) + 0.05)
        ratio_inp = (max(lum_border_inp, lum_inp) + 0.05) / (min(lum_border_inp, lum_inp) + 0.05)
        
        print(f'Card Effective: {card_effective}, Lum: {lum_card:.5f}')
        print(f'Inp Effective: {inp_bg_effective}, Lum: {lum_inp:.5f}')
        print(f'Border on Card: {border_on_card}, Lum: {lum_border_card:.5f}, Ratio vs Card: {ratio_card:.2f}:1')
        print(f'Border on Inp: {border_on_inp}, Lum: {lum_border_inp:.5f}, Ratio vs Inp: {ratio_inp:.2f}:1')
        browser.close()

if __name__ == '__main__':
    main()
