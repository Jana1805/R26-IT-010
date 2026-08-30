# Electricity Demand Intelligence System — Design Specification

Status: Final project-specific direction  
Scope: React/Vite frontend for Sri Lankan electricity-demand forecasting and model comparison  
Audience: Engineers, researchers, supervisors, and project evaluators  
Theme: Light-first. No dark theme is specified for this release.

This is the permanent visual and interaction contract for the frontend. It may take structural cues from rigorous enterprise systems, but it is not IBM-branded and must not reproduce an IBM marketing site. Where the implementation and this document differ, this document is the target for future frontend work.

## 1. Product visual direction

The product is a research instrument, not a marketing surface or real-time utility control room. It must feel analytical, calm, precise, and credible under academic review.

- Use a cool-white canvas, restrained blue-gray surfaces, near-black navy text, and one blue interaction accent.
- Prefer compact, aligned information structures over oversized headings or decorative whitespace.
- Make data provenance, timestamps, units, model status, and unavailable evidence visually explicit.
- Use color only for model identity, data meaning, semantic state, or interaction.
- Keep a visible historical-dataset/research-mode notice. Never imply live national-grid connectivity when the source is historical.
- Use factual, specific, sentence-case language.

## 2. Design principles

1. **Evidence before decoration.** Metrics, scope, timestamps, uncertainty method, and availability lead.
2. **Consistent encodings.** A model keeps one color, pattern, marker, label, and legend position everywhere.
3. **Dense, not cramped.** Support comparison while retaining readable rhythm and adequate targets.
4. **Honest uncertainty.** Show intervals only when the backend provides genuine, documented bounds.
5. **Accessible by construction.** Shape, pattern, text, focus, and descriptions supplement color.
6. **Progressive detail.** Summaries lead to charts and tables without decorative card nesting.
7. **Stable layout.** Loading, missing data, long names, and responsive changes avoid layout jumps.

## 3. Background and surface hierarchy

| Token | Value | Required use |
|---|---:|---|
| `canvas` | `#F7F9FC` | Page background and chart surroundings |
| `surface-primary` | `#FFFFFF` | Panels, tables, controls, navigation |
| `surface-secondary` | `#F1F4F8` | Table headers, grouped controls, section bands |
| `surface-selected` | `#E8F1FB` | Selected navigation and rows |
| `surface-hover` | `#F4F7FA` | Hovered neutral rows and controls |
| `surface-disabled` | `#E9EDF2` | Disabled controls only |
| `surface-info` | `#EEF5FC` | Research-mode and information notices |
| `surface-success` | `#EAF6F0` | Success status background |
| `surface-warning` | `#FFF5D9` | Warning and partial-data background |
| `surface-danger` | `#FCECEE` | Error background |

Create hierarchy with surface contrast and dividers. A panel may contain an unboxed chart, table, form group, or status row. Do not put a card inside a card solely for decoration.

## 4. Primary, accent, and semantic colors

### Core palette

| Token | Value | Use |
|---|---:|---|
| `ink-strong` | `#17212B` | Headings, values, actual demand |
| `ink` | `#263746` | Body and control text |
| `ink-muted` | `#5F6F7E` | Supporting descriptions and metadata |
| `ink-subtle` | `#778695` | Placeholders and disabled text only |
| `primary` | `#1F5A94` | Primary actions, links, focus, active navigation |
| `primary-hover` | `#174A7B` | Primary hover |
| `primary-pressed` | `#10395F` | Primary pressed |
| `primary-subtle` | `#D9E8F6` | Selection and information emphasis |

### Semantic palette

| Meaning | Foreground | Background | Border |
|---|---:|---:|---:|
| Positive / available | `#176B45` | `#EAF6F0` | `#9ACDB4` |
| Warning / partial | `#7A5700` | `#FFF5D9` | `#E4C76A` |
| Negative / error | `#B4232F` | `#FCECEE` | `#E5A4AA` |
| Informational | `#1F5A94` | `#EEF5FC` | `#A9C8E5` |

Semantic colors are reserved for meaning. If a model color resembles a semantic color, pattern, marker, and text must prevent confusion. All pairs must meet section 24 contrast rules.

## 5. Typography hierarchy

Use `Source Sans 3`, then `Segoe UI`, `Arial`, `sans-serif`. Use `Source Code Pro`, `Consolas`, `monospace` only for identifiers or raw technical values. Normal metrics use the primary family with tabular figures.

| Token | Size / line height | Weight | Use |
|---|---:|---:|---|
| `page-title` | `32px / 40px` | 600 | One h1; `28px / 36px` below 768px |
| `section-title` | `20px / 28px` | 600 | Major panel h2 |
| `subsection-title` | `16px / 24px` | 600 | Chart/table h3 |
| `metric-value` | `26px / 32px` | 600 | Summary values |
| `body` | `15px / 23px` | 400 | Prose and controls |
| `body-strong` | `15px / 23px` | 600 | Emphasis and row names |
| `body-small` | `13px / 19px` | 400 | Detail and table cells |
| `label` | `12px / 16px` | 600 | Field labels and compact headings |
| `caption` | `12px / 16px` | 400 | Provenance and chart captions |

Use sentence case, including table headers and eyebrows. Eyebrows are optional 12px semibold labels, not slogans. Keep explanatory paragraphs near 70 characters per line. Do not use marketing-scale display type or weights below 400.

## 6. Numeric formatting and tabular-number rules

Apply `font-variant-numeric: tabular-nums lining-nums` to metrics, times, axes, tooltips, numeric table cells, counts, ranks, and heatmap values. Right-align comparable numeric columns.

| Value | UI display |
|---|---|
| MAE | `1,234.56 kW` |
| RMSE | `1,234.56 kW` |
| MAPE | `12.34%` |
| R² | `0.9876` |
| Demand | `12,345 kW` |
| Dataset rows / parameters | `1,234,567` |
| Timestamp | `25 Aug 2026, 14:30` with timezone context when ambiguous |
| Horizon | `6 hours · 24 × 15 min` |

- Use `R²`, not user-facing `R2`, and an en dash for ranges.
- Full precision belongs only in downloads or an explicit detail view.
- Null, undefined, non-finite, unavailable, not measured, and inapplicable values display `—`. Explain why nearby or in a tooltip.
- Zero remains `0`; never convert it to `—`.
- Never interpolate, backfill, or invent missing presentation values.

## 7. Spacing scale

Use a 4px base grid: `4, 8, 12, 16, 24, 32, 48px`. Desktop panel padding is 24px; compact/mobile panel padding is 16px. Use 16px between related controls, 24px between related sections, and 32px between major groups. Do not create marketing-hero whitespace.

## 8. Border-radius rules

| Token | Value | Use |
|---|---:|---|
| `radius-none` | 0 | Tables, dividers, plot areas |
| `radius-small` | 3px | Tags, indicators, heatmap cells |
| `radius-control` | 4px | Buttons, inputs, selects |
| `radius-panel` | 6px | Panels and metric summaries |

Do not exceed 6px on normal surfaces. Pills are allowed only for compact status/taxonomy indicators; buttons, cards, navigation, and selectors are not pills.

## 9. Border and divider rules

- Default border: `1px solid #D6DEE6`.
- Strong divider: `1px solid #BAC6D1`.
- Input border: `1px solid #AEBBC7`; focus retains it and adds the focus ring.
- Error border: `1px solid #B4232F` plus inline error text.
- Table row divider: `1px solid #E3E8ED`.
- Avoid double borders between adjacent cells. Dashed borders are only for empty/unavailable placeholders.

## 10. Shadow and elevation rules

The interface is predominantly flat.

| Level | Treatment | Use |
|---|---|---|
| 0 | None | Pages, panels, cards, tables, charts |
| 1 | `0 1px 2px rgba(23,33,43,.08)` | Sticky top bar if needed |
| 2 | `0 4px 12px rgba(23,33,43,.12)` | Tooltips, popovers, menus |
| 3 | `0 8px 24px rgba(23,33,43,.16)` | Future modal only |

Never use colored shadows, glow, inset lighting, or a shadow on every card.

## 11. Page-width and layout rules

- Support 320px minimum; cap main content at 1440px and center it.
- Gutters: 32px at ≥1200px, 24px at 768–1199px, 16px below 768px.
- Desktop shell uses a 224px navigation column and fluid main column; collapse navigation below 900px.
- Page headers are compact: h1, one explanation, at most one page-level action. They are not heroes.
- Forms and prose occupy only the columns they need.

## 12. Dashboard grid

Use 12 desktop columns with 24px gutters, 8 tablet columns with 16px gutters, and 4 mobile columns.

- Metrics: four across at ≥1200px, two at 768–1199px, one below 560px.
- Overview: primary chart 8 columns, operational summary 4.
- Two analysis charts use 6 + 6 only while each remains at least 420px wide; otherwise stack.
- Forecast controls: model 4, timestamp 3, horizon 2, action 3 columns.
- Model library: list 5, detail 7; stack below 960px.
- Do not force unrelated panels to equal height. Align headings/baselines in shared rows.

## 13. Cards and metric summaries

- Use cards only for independently meaningful summaries or grouped controls.
- Metric cards: white, 1px border, 6px radius, 16px padding; no colored top stripe.
- Structure: label, value, provenance/context. Avoid wrapping values where abbreviated units solve it.
- Help icons are proper described controls, not `title`-only targets.
- A “best model” summary states the metric and aligned-test basis and never ranks unavailable evidence.
- Avoid nested metric cards unless the parent provides a necessary semantic group.

## 14. Buttons and action hierarchy

- **Primary:** filled primary with white text; one per local task, such as Run forecast.
- **Secondary:** white, neutral border, ink text; export, reset, navigation.
- **Tertiary:** primary text/icon, background only on hover; disclosure.
- **Danger:** red only for genuinely destructive actions; none are currently needed.
- Minimum height is 40px desktop and 44px touch. Icon-only targets are 44×44px with accessible names.
- Hover changes color/border without movement; pressed darkens. Disabled uses disabled tokens and `not-allowed`.
- Loading buttons retain width, show a progress indicator, and use labels such as `Running forecast…`.

## 15. Forms and input controls

- Keep a persistent label above every field; placeholders are not labels.
- Controls are 40px desktop, 44px mobile, white, 4px radius, with 12px horizontal padding.
- Put timestamp limits, lookback constraints, availability, and horizon semantics in helper text.
- Errors appear beneath fields and connect with `aria-describedby`; color is supplementary.
- Disabled model options include `— unavailable`.
- Date/time groups state timezone and enforce a valid 15-minute interval.
- Checkbox targets include their labels. Model selectors show line swatch, marker, short label, and full name.
- Preserve configuration after forecast failure for retry.

## 16. Navigation and active states

- Desktop uses left workspace navigation; mobile uses a drawer from the top bar.
- Active items use selected surface, strong ink, 600 weight, a 3px primary leading rule, and `aria-current="page"`.
- Hover uses hover surface; focus uses the global ring. Color alone never indicates active state.
- Top bar may show product name, research status, API state, and latest observation as space permits.
- Mobile drawer traps focus, closes on Escape, has an explicit close control, restores focus, and makes background content inert.
- Preserve the skip link and move focus to main content or h1 after navigation.

## 17. Tables and comparison leaderboards

- Use semantic tables with a caption or accessible name. Sticky headers are allowed.
- Header: secondary surface, 12px semibold sentence case.
- Text/model names align left; metrics, rank, counts, and durations align right with tabular figures.
- Default leaderboard order is ascending MAE on the common aligned test set. Only comparable rows receive a rank; unavailable rows show `—` and follow ranked rows.
- Sort buttons show direction icons; apply `aria-sort` only to the active header.
- Identify models by line pattern plus marker and label, never a colored dot alone.
- Best values can use semibold and hidden `Best` text; color is optional and supplementary.
- Availability status and explanatory reason are separate. Notes wrap.
- Mobile keeps one horizontally scrollable comparison table; do not convert it to disconnected cards. Freeze model column where feasible.
- CSV retains raw precision, stable IDs, unit-bearing headers, and blank unavailable fields.

## 18. Badges and status indicators

Use badges sparingly for Deterministic, Probabilistic, Ready, Unavailable, Partial, and API state. Use 3px radius, 1px border, 4px 8px padding, and 12px semibold text. Ready has a check icon; unavailable and partial have appropriate icon plus text. Model type is neutral taxonomy, not success. Probabilistic never implies better.

## 19. Tooltips and popovers

- Tooltip = one term/datum; popover = interactive or multiline support.
- Open on pointer hover and keyboard focus; Escape dismisses. Noninteractive tooltips do not trap focus.
- Use white, `#BAC6D1` border, 6px radius, level-2 shadow, strong primary text, muted metadata, 12px padding, 320px maximum width.
- Keep within the viewport and avoid covering the focused mark when possible.
- Native `title` attributes are not the primary help mechanism, and tooltips never contain the only copy of essential facts.

## 20. Loading, error, empty, and unavailable-data states

- **Initial loading:** geometry-matched skeletons, stable headings/panel height, `aria-busy`, one concise live message.
- **Action loading:** preserve valid previous results, mark updating/stale, show progress beside the action.
- **Error:** specific message, affected scope, retry when possible. API failure does not erase navigation/source context.
- **Empty:** explain why and state the next action. Never show synthetic preview data.
- **Unavailable:** use `—` plus a reason such as missing artifact, not measured, unsupported interval, or outside coverage.
- **Partial:** retain valid values, label partial scope, list omitted models/points.
- Chart states retain the chart minimum height; never use zero or fake points as placeholders.

## 21. Responsive breakpoints

| Name | Range | Behaviour |
|---|---:|---|
| Compact mobile | `320–479px` | One column; scroll tables/charts |
| Mobile | `480–767px` | One column; limited two-up summaries |
| Tablet | `768–899px` | Eight-column grid; drawer navigation |
| Compact desktop | `900–1199px` | Sidebar; stack charts below minimum width |
| Desktop | `1200–1599px` | Full 12-column dashboard |
| Wide | `1600px+` | Content remains capped at 1440px |

Breakpoints follow content constraints. Move or scroll a chart before ticks overlap.

## 22. Mobile behaviour

- Preserve order: context, controls, primary results, supporting evidence.
- Page actions move below titles and become full width only when useful.
- Forecast controls stack model → timestamp → horizon → action.
- Metrics become one column below 560px.
- Tables scroll with an edge cue and label; never shrink text below 12px.
- Comparison defaults to actual plus one selected model; selector stays above.
- Touch targets are at least 44×44px with 8px separation where practical.
- Never hide units, provenance, reasons, or uncertainty notes to save space.

## 23. Keyboard and focus behaviour

- Actions, navigation, selectors, sortable headers, heatmap cells, and interactive chart marks are keyboard reachable in logical DOM order.
- Focus: `2px solid #1F5A94`, 2px offset; add a 1px white gap over colored surfaces.
- Enter/Space activates. Escape closes. Arrow navigation is preferred inside heatmap and chart groups.
- Never use positive `tabindex`. Dense visualizations use roving tabindex, not hundreds of tab stops.
- Announce async success/failure without unexpected focus movement. Focus main/h1 after route changes.

## 24. Accessibility requirements

- Meet WCAG 2.2 AA: 4.5:1 normal text; 3:1 large text, meaningful graphics, focus, and control boundaries.
- Use landmarks, one h1, ordered headings, real buttons, labels, semantic tables, and a skip link.
- Icon-only controls have names; decorative icons use `aria-hidden="true"`.
- Status updates use concise live regions.
- Never communicate model identity, selection, rank, availability, or error by color alone.
- Charts have concise descriptions and an underlying data table or download.
- Heatmap cells expose weekday, hour, demand, and missing status in the same reading order as the matrix.
- Support 200% zoom and 320 CSS px reflow except labelled scrolling for intrinsically two-dimensional data.
- Use `lang="en"`; accessible names pronounce `kW` as kilowatts and `R²` as R squared.

## 25. Reduced-motion behaviour

- Respect `prefers-reduced-motion: reduce`.
- Disable spinner rotation, animated chart drawing, line morphing, count-ups, smooth scrolling, and drawer sliding; use static progress and instant state changes.
- Otherwise limit transitions to 120–180ms for color, border, and opacity. Do not animate position/scale for routine feedback.
- Motion is never required to understand a data change.

## 26. Data Visualization

### Chart canvas, geometry, axes, and units

- Container, canvas, and plot area use white; no tinted or gradient plot background.
- Minimum heights: standard 320px, primary forecast/comparison 420px, small multiple 240px, mobile primary 320px. Loading/error keeps the same height.
- Container padding: 16px desktop, 12px mobile. Plot margins: top 16, right 24, bottom 44, left 64px. Expand left to prevent clipping.
- Keep 12px between ticks and axis titles, 16px between plot and legend.
- Grid: `#DDE4EA`, 1px solid. Use horizontal major lines by default; vertical only for useful time alignment; no minor grid.
- Axis: `#9EACB9`, 1px; 4px ticks. Tick labels: 12/16, 400, muted ink, tabular. Titles: 12/16, 600, ink.
- Axis titles state `Demand (kW)`, `MAE (kW)`, or `RMSE (kW)`. Compact ticks may show `12k`; tooltips/accessibility use full grouped values.
- Time axes disambiguate date boundaries and use `Asia/Colombo` unless timestamps explicitly define another zone.
- Time-series y-domains need not start at zero; bar charts do. Scatter domains use honest padding.

### Permanent series mapping

Centralize this immutable mapping. Every forecast, comparison, metric chart, scatter, selector, legend, tooltip, export, and accessible description imports it; no chart chooses local colors.

| Stable ID | Short label | Full accessible label | Color | Line pattern | Marker |
|---|---|---|---:|---|---|
| `cnn` | CNN | Convolutional neural network forecast | `#0072B2` | solid | circle |
| `lstm` | LSTM | Long short-term memory network forecast | `#D55E00` | `8 4` dashed | square |
| `transformer` | Transformer | Transformer network forecast | `#009E73` | `2 3` dotted | upward triangle |
| `cnn_lstm_b` | CNN–LSTM-B | CNN–LSTM baseline forecast | `#CC79A7` | `10 3 2 3` dash-dot | diamond |
| `cnn_transformer_b` | CNN–Transformer-B | CNN–Transformer baseline forecast | `#E69F00` | `12 4` long dash | downward triangle |
| `cnn_lstm_mc` | CNN–LSTM MC | CNN–LSTM forecast with Monte Carlo dropout | `#6F4E9C` | `5 3` short dash | cross |
| `cnn_transformer_mc` | CNN–Transformer MC | CNN–Transformer forecast with Monte Carlo dropout | `#8A5A2B` | `10 3 3 3 3 3` dash-dot-dot | hexagon |

Actual demand is separate: short label `Actual`, accessible label `Observed electricity demand`, `#17212B`, 2.75px solid, filled circle. It is always first in legends/tooltips.

Render a 28px patterned line and marker beside each legend/selector label. Scatter markers are mandatory. Monochrome print must preserve identity.

### Line, point, selection, hover, and focus rules

- Model lines: 2px. Actual: 2.75px. Selected/focused: 3px. Hovered: 2.75px.
- Unselected overlay models retain color at 20% opacity and 1.25px; actual never drops below 70%.
- Dense time-series markers are hidden until hover/focus unless ≤48 points. Visible markers are 6px; hover/focus 9px with 2px white halo. Scatter is 10px; selected scatter 14px with 2px strong-ink outline.
- Hover/focus shows a 1px dashed neutral crosshair and corresponding values for visible series.
- Pointer hit regions are at least 24px. Keyboard operates by series and nearest timestamp.
- Selection never changes a series to another color; use weight, opacity, outline, and annotation.

### Legend and tooltip rules

- Legend sits above and left of the plot, after subtitle. Wrap whole items. With >4 series, prefer a side list when space permits, otherwise above.
- Stable order: Actual, CNN, LSTM, Transformer, CNN–LSTM-B, CNN–Transformer-B, CNN–LSTM MC, CNN–Transformer MC. Filtering never reorders.
- Legend item includes pattern, marker, short label, selection state, and accessible full name.
- Tooltip: white, neutral border, 6px radius, level-2 shadow; strong timestamp, normal series text, muted metadata.
- Tooltip order matches legend. Demand/forecast/MAE/RMSE use two decimals; MAPE two; R² four; heatmap demand grouped whole. Never exceed source precision.
- Include timestamp, full series name, formatted value/unit, observed/forecast status, horizon step, and interval bounds/method when present. Null is `—` plus known reason.

### Actual demand, forecasts, prediction start, and uncertainty

- Historical actual uses the strong neutral style. Observed demand inside the forecast window uses the same identity at 2px and label `Observed in forecast window`.
- A prediction begins at its first predicted timestamp and never extends backward.
- Forecast start: 1.5px dashed muted-neutral vertical line, labelled `Forecast starts` plus full timestamp. It is not model-colored.
- Adjacent metadata states anchor, first/final prediction timestamp, cadence, steps, and human duration.
- Actual gaps remain gaps. Never connect or invent values across missing timestamps.
- Do not silently clip forecasts outside a plausible display domain; extend and warn if data validation permits them.
- Draw an interval only if finite lower/upper bounds are ordered, timestamp-aligned, and the response supports intervals.
- Interval fill uses model color at 12% opacity, no gradient. Bounds use model color at 45%, 1px `3 3`; mean stays opaque above.
- Label the actual method/level, e.g. `95% calibrated prediction interval`; not every band is a confidence interval.
- MC-dropout predictive mean is the forecast line. MC spread alone is not automatically 95%; use documented backend bounds only.
- Deterministic models show point forecasts unless separately calibrated bounds exist. Say `Point forecast; interval unavailable`; never fake a zero-width band.

### Forecast-chart rules

Z-order: valid interval band, historical actual, observed actual in forecast window, model prediction, forecast-start indicator, hover/focus annotations.

- Include at least the available lookback context plus the full horizon. If the API returns forecast-window rows only, state that instead of fabricating history.
- Actual and prediction differ in grayscale using weight, pattern, marker, and direct label.
- Tooltips identify `Historical actual`, `Observed in forecast window`, or the full model forecast.
- If future actuals are unavailable, keep prediction and show actual as `—`; never infer them.
- Always state timestamp and horizon information outside hover-only content.

### Multi-model comparison rules

- Actual is dominant, first, and cannot be removed from the primary overlay.
- Show at most three selected models plus actual. A fourth selection must replace one or open all-model view; never silently create clutter.
- Default to the three available models with lowest aligned MAE while retaining stable legend order; state this basis.
- View all seven as aligned small multiples sharing time and y-domains. Each shows faint actual plus one model, full/short name, type, and availability. Two columns desktop, one below 900px.
- Hover/focus emphasizes its model and de-emphasizes other models; actual remains dominant. Selection persists separately.
- An unavailable model retains its stable position with reason.
- Never place all seven forecast lines in the primary overlay or reorder legend by metric rank.

### Error-scatter rules

- X = `MAE (kW)`, y = `RMSE (kW)`, with two-decimal tooltips and honestly padded domains.
- Each model uses its permanent color and marker. Never use one shared fill or identical same-colored points.
- Direct short labels offset 8px. Resolve collisions in order: top-right, bottom-right, top-left, bottom-left, leader line, then hide only the visual label while keeping accessible legend/tooltip.
- Selected point: 14px, strong outline, full opacity. Unselected: 45% opacity.
- Tooltip: full model name, type, MAE, RMSE, aligned sample, defined rank, availability note.
- Exact overlaps may use ≤3px non-data visual offset with leader line and identical numeric values stated; never jitter data coordinates.

### Heatmap rules

- Exactly seven weekday columns, Monday–Sunday, and 24 hourly rows, `00:00`–`23:00`.
- First column is hour header; top row is weekday headers. Rows/columns never wrap, transpose, or vary alignment. Cells are equal size.
- Use the accessible Cividis sequential scale from `#00204C` through `#7C7B78` to `#FDE737`. This scientific ramp is the sole exception to the decorative-gradient ban. Do not use red/green or categorical thresholds.
- Legend below: continuous matching scale, `Lower average demand` / `Higher average demand`, numeric min/mid/max, `kW`.
- Tooltip/accessibility: weekday, hour range, grouped whole demand, e.g. `Monday, 14:00–14:59, 12,345 kW`.
- Missing cells: white, neutral diagonal hatch, `—`; exclude them from the color domain. Never coerce missing to zero.
- If cell values appear, select white or strong-ink text via a tested 4.5:1 contrast threshold. Omit visual values if too small but keep accessibility.
- Cell minimum: desktop 32×24px, mobile 40×32px. Narrow screens use a labelled two-axis scroll container with recommended sticky headers. Never collapse the 7×24 matrix into cards.

### Missing, loading, and error chart states

- Missing time-series points create line gaps. Optional hollow neutral markers identify isolated gaps. Interpolation appears only as a separately labelled imputed series.
- Missing series remain in the legend as unavailable with muted swatch and reason.
- Loading uses neutral geometry and an accessible message, never fake data.
- Error replaces marks, not title, units, or scope; show reason and retry in the minimum-height plot region.
- Partial results retain valid series and list omitted series/timestamps in a warning.

### Export and print

- Image exports use opaque white, title, range, timezone, units, legend, interval method, and source/provenance.
- Never depend on transparency, hover-only content, or UI chrome.
- Print retains patterns/markers, ≥1.25px model lines, neutral actual, and textual/icon statuses. Test grayscale.
- Data exports use stable IDs, ISO 8601 timestamps with timezone, raw precision, unit-bearing columns, and blank missing fields.

### Mobile charts

- Keep primary charts ≥320px. Reduce tick count before rotating; prefer 0° and never exceed 45°.
- Comparison defaults to actual plus one model and permits at most three. Legend stays above and wraps whole items.
- Dense time series may pan/scroll with a visible range label; never squeeze to illegibility.
- Tap/focus tooltips persist until dismissal or new selection and stay in viewport.
- Small multiples stack. Heatmap preserves all cells using its scrolling rule.

### Accessible descriptions and non-color identification

Every chart provides:

1. Visible title/subtitle stating measure, units, time/sample scope, and comparison basis.
2. Programmatic description naming active series, purpose, interval availability, and missing data.
3. Keyboard-operable legend/selector with line pattern, marker, short label, and full accessible label.
4. Underlying data table or downloadable CSV.
5. Concise text summary of the primary finding without unsupported causality/significance claims.

No identity, selection, actual/forecast distinction, model type, status, or error is color-only.

## 27. Explicit design anti-patterns

Prohibited:

- Neon, cyberpunk, dark command-center defaults, glow, or luminous cyan-on-navy styling.
- Decorative gradients. Only scientifically appropriate continuous data scales such as Cividis are exempt.
- Glassmorphism, backdrop blur, translucent floating panels, or frosted surfaces.
- Marketing heroes, oversized display type, conversion copy, decorative illustrations, or generic AI SaaS layouts.
- Excessive pills, radius >6px, deep card nesting, or shadows on every panel.
- Decorative emoji, novelty imagery/icons, ornamental noise, and texture overlays.
- Unnecessary animation, draw-on charts, parallax, count-ups, pulsing/glowing status, or motion hover.
- Color without meaning, local model colors, color-only legends, or red/green-only comparisons.
- Seven lines in one overlay, unlabeled bands, fake uncertainty, misleading smoothing, interpolated missing data, or truncated bar axes.
- Invented metrics, synthetic previews, zero for missing, ambiguous prose in place of `—` plus reason, or false precision.
- Transposed/wrapped heatmaps, variable cells, missing legends, or mobile layouts that destroy the 7×24 matrix.
- Comparison tables converted into disconnected cards.
- Tooltips as the only source of units, identity, method, or critical findings.
- IBM names, logos, marketing patterns, or claims of Carbon conformance.

## Implementation governance

- Centralize tokens and the permanent series mapping before future implementation.
- This file is the decision source; component exceptions require an amendment here.
- Validate at 320, 768, 1024, and 1440px; 200% zoom; keyboard-only; reduced motion; common color-vision deficiencies; grayscale print; and all loading/error/empty/partial/unavailable states.
- Verify chart decisions against API responses; never assume intervals, actual coverage, sample size, or model availability.
- This specification does not authorize frontend or backend implementation changes.
