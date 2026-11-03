# TEST_READY.md — WCAG AA Contrast Remediation Verification Gate

## 1. Executive Summary & Readiness Declaration

A comprehensive, opaque-box, requirement-driven automated E2E test suite for **WCAG 2.1 / 2.2 Level AA Contrast Remediation** has been designed, authored, and verified in `tests/test_wcag_contrast_full_suite.py`. This suite serves as the authoritative quality assurance gate for all pages of **RedGrowth.partners** (`index.html`, `privacy.html`, `terms.html`, and `404.html`).

- **Test Module**: `tests/test_wcag_contrast_full_suite.py`
- **Framework**: Python 3.14 + Pytest 9.1.1 + Playwright 1.62.0 (Headless Chromium)
- **Target Standard**: WCAG 2.1 & 2.2 Level AA (Criteria 1.4.3 Contrast Minimum & 1.4.11 Non-text Contrast)
- **Mathematical Engine**: Exact sRGB gamma decompression, relative luminance calculation, and recursive alpha compositing over base canvas `#0B1120` (`rgb(11, 17, 32)`).
- **Total Test Cases**: **18 distinct test executions** structured across 4 rigorous tiers.

---

## 2. Authoritative Mathematical Specifications & Thresholds

Every test case derives its expected values directly from the official W3C WCAG 2.1 / 2.2 mathematical specifications:

### 2.1 Relative Luminance ($L$)
For any sRGB color channel $C \in \{R, G, B\}$ normalized to $V = C / 255.0$:
$$C_{\text{linear}} = \begin{cases} \frac{V}{12.92} & \text{if } V \le 0.03928 \\ \left(\frac{V + 0.055}{1.055}\right)^{2.4} & \text{if } V > 0.03928 \end{cases}$$
$$L = 0.2126 \times R_{\text{linear}} + 0.7152 \times G_{\text{linear}} + 0.0722 \times B_{\text{linear}}$$

### 2.2 Contrast Ratio ($CR$)
For any two luminances $L_1$ and $L_2$ (where $L_1 \ge L_2$):
$$CR = \frac{L_1 + 0.05}{L_2 + 0.05}$$

### 2.3 Recursive Alpha Compositing
For translucent elements (`rgba(...)`) stacked in the DOM, effective backgrounds are calculated recursively from the target element up the DOM tree down to the base canvas `#0B1120`:
$$C_{\text{composite}} = \text{round}\left(C_{\text{fg}} \times \alpha + C_{\text{bg}} \times (1 - \alpha)\right)$$

### 2.4 WCAG Level AA Compliance Thresholds
- **Normal Text** (< 24px / 18pt regular, or < 18.66px / 14pt bold): $CR \ge \mathbf{4.50:1}$
- **Large Text** ($\ge 24\text{px}$ / 18pt regular, or $\ge 18.66\text{px}$ / 14pt bold with weight $\ge 700$): $CR \ge \mathbf{3.00:1}$
- **Non-Text UI Components & Graphical Objects** (SC 1.4.11 — control borders, active state boundaries, SVG icons): $CR \ge \mathbf{3.00:1}$

---

## 3. Test Suite Architecture & 4-Tier Inventory

| Tier | Focus Area | Test Method | Target Scope | Criteria |
|---|---|---|---|---|
| **Tier 1** | Feature Coverage | `test_tier1_pages_load_cleanly_no_console_errors` (4 runs) | `/`, `/privacy.html`, `/terms.html`, `/404.html` | HTTP 200/304, zero JS console errors, zero page crashes, active stylesheet loaded, body canvas `#0B1120`. |
| **Tier 1** | Feature Coverage | `test_tier1_core_typography_hierarchy_index` | `index.html` (14 section selectors) | Headings (H1, H2), subheadings, body text, form labels, footer copyright meet AA threshold. |
| **Tier 1** | Feature Coverage | `test_tier1_core_typography_hierarchy_subpages` | `privacy.html`, `terms.html`, `404.html` | Headings, body copy, "Last Updated" metadata stamp, footer text meet AA threshold. |
| **Tier 2** | Boundary Cases | `test_tier2_form_input_resting_borders_contrast` | `#auditForm` (`#fullName`, `#companyDomain`, `#workEmail`, `#brandNotes`) | Resting input borders against card `#15213A` achieve $CR \ge 3.0:1$ (SC 1.4.11). |
| **Tier 2** | Boundary Cases | `test_tier2_outline_buttons_boundary_contrast` | Hero CTA, Pricing 1 & 3, Founder CTA, 404 CTA & Return | Outline button borders against adjacent surfaces achieve $CR \ge 3.0:1$ (SC 1.4.11). |
| **Tier 2** | Boundary Cases | `test_tier2_section4_timeline_bubbles_contrast` | `#engine` Timeline Step 1, 2, 3 Bubbles | Step 3 achieves $\ge 4.5:1$ (or $\ge 3.0:1$ large); Steps 1 & 2 achieve $\ge 3.0:1$ (Large Text $\ge 18.66\text{px}$ bold) or $\ge 4.5:1$. |
| **Tier 3** | Interactive States | `test_tier3_primary_button_interactive_states` | Primary Coral Buttons | Default ($CR \ge 4.5:1$), Hover ($CR \ge 4.5:1$), Focus Ring ($CR \ge 3.0:1$ vs offset canvas). |
| **Tier 3** | Interactive States | `test_tier3_selection_pseudo_element_contrast` | All 4 Pages (`::selection`) | Highlighted text foreground on Coral background achieves $CR \ge 4.5:1$. |
| **Tier 3** | Interactive States | `test_tier3_ajax_form_loading_state_contrast` | `#submitAuditBtn` dynamic submit | Loading spinner SVG and "Submitting..." text achieve $CR \ge 4.5:1$ on Coral. |
| **Tier 3** | Interactive States | `test_tier3_mobile_drawer_and_accordion_expanded_contrast` | Mobile Drawer (375px) & FAQ Accordion | Newly revealed mobile drawer links and expanded FAQ answer copy achieve $CR \ge 4.5:1$. |
| **Tier 3** | Subpage Polish | `test_tier3_subpage_consistency_404_footer_and_logo` | `404.html` consistency | Mobile logo font size matches 17px standard; footer contains 4 standard links with $CR \ge 4.5:1$. |
| **Tier 4** | Full DOM Scan | `test_tier4_full_dom_unrestricted_contrast_index` | `index.html` (> 100 text nodes + SVGs) | Unrestricted recursive alpha-blended walk of ALL visible text nodes ($\ge 4.5:1$ / $\ge 3.0:1$) and SVGs ($\ge 3.0:1$). |
| **Tier 4** | Full DOM Scan | `test_tier4_full_dom_unrestricted_contrast_subpages` (3 runs) | `/privacy.html`, `/terms.html`, `/404.html` | Unrestricted recursive alpha-blended walk of ALL visible text nodes and SVGs. |

**Total Tests**: **18 Test Executions**.

---

## 4. Baseline Execution Results & Failure Registry

Prior to the completion of Milestone 1 worker remediations, initial execution of `tests/test_wcag_contrast_full_suite.py` yielded:
- **Passed**: **12 tests** (66.7%)
- **Failed**: **6 tests** (33.3%)

### Failure Mapping to Planned Remediations:
All 6 failures accurately pinpoint the exact contrast remediation points:

1. **`test_tier2_form_input_resting_borders_contrast`**:
   - *Current State*: `#fullName` resting border uses `border-white/30`, yielding $2.68:1$ (< 3.0:1).
   - *Remediation Target*: Upgrade to `border-white/40` to achieve **3.81:1** ($CR \ge 3.0:1$).
2. **`test_tier2_outline_buttons_boundary_contrast`**:
   - *Current State*: Pricing Tier 1 CTA button uses `border-white/20`, yielding $1.88:1$ (< 3.0:1).
   - *Remediation Target*: Upgrade to `border-2 border-white/40` to achieve **3.85:1** ($CR \ge 3.0:1$).
3. **`test_tier2_section4_timeline_bubbles_contrast`**:
   - *Current State*: Step 3 bubble uses `bg-[#f97316] text-white`, yielding $2.80:1$ (< 4.5:1).
   - *Remediation Target*: Change text to `text-[#0B1120]` on `#f97316` to achieve **6.79:1** ($CR \ge 4.5:1$).
4. **`test_tier3_selection_pseudo_element_contrast`**:
   - *Current State*: `selection:text-[#0B1120]` was missing from compiled `assets/css/style.css`, causing browser fallback to `text-slate-100` ($2.68:1$ on Coral).
   - *Remediation Target*: Recompile Tailwind CSS so `selection:text-[#0B1120]` compiles to `::selection { color: #0B1120; }` (**6.41:1**).
5. **`test_tier3_ajax_form_loading_state_contrast`**:
   - *Current State*: Dynamic AJAX loading state in `#submitAuditBtn` handler injected `<svg class="text-white ...">` ($3.02:1$).
   - *Remediation Target*: Update script to inject `text-[#0B1120]` for both spinner and text (**6.31:1**).
6. **`test_tier3_subpage_consistency_404_footer_and_logo`**:
   - *Current State*: `404.html` mobile logo was `text-[15px]` and lacked the 4 standard footer navigation links.
   - *Remediation Target*: Upgrade mobile logo to `text-[17px]` and inject standard 4 footer links.

---

## 5. Execution Instructions

### 5.1 Run the Full WCAG Contrast Suite
To run all 18 tests across all 4 tiers with detailed output:
```powershell
pytest tests/test_wcag_contrast_full_suite.py -v
```

*Note: The built-in fixture in `tests/conftest.py` automatically detects whether a local HTTP server is active on port 8000; if not, it spawns `python -m http.server 8000` in the repository root and cleanly terminates it upon test completion.*

### 5.2 Run Individual Tiers
```powershell
# Tier 1: Feature Coverage (Page load & typography)
pytest tests/test_wcag_contrast_full_suite.py -k "TestTier1" -v

# Tier 2: Boundary & Corner Cases (SC 1.4.11 & step bubbles)
pytest tests/test_wcag_contrast_full_suite.py -k "TestTier2" -v

# Tier 3: Interactive States & Subpage Consistency
pytest tests/test_wcag_contrast_full_suite.py -k "TestTier3" -v

# Tier 4: Full DOM Unrestricted Scan
pytest tests/test_wcag_contrast_full_suite.py -k "TestTier4" -v
```

---

## 6. Acceptance & Gate Sign-Off Criteria

To achieve Milestone 2 sign-off:
1. **Zero Failures**: All 18 tests in `tests/test_wcag_contrast_full_suite.py` must pass ($100\%$ pass rate).
2. **Zero Regressions**: All 22 pre-existing tests in `tests/` must remain passing.
3. **Deterministic Unrestricted Scan**: Tier 4 full DOM scan across all 4 pages must report $0$ text contrast violations and $0$ SVG icon violations.
4. **No Console Errors**: Zero JavaScript runtime exceptions or unhandled promise rejections on any page.
