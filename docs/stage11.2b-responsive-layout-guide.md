# Stage 11.2B Responsive Layout Guide

## Viewport classes

| Class | Range | Horizontal gutter | Behavior |
|---|---:|---:|---|
| Mobile | `<600px` | 16px | Single-column narrative flow; horizontal controls scroll when required |
| Tablet / split screen | `600–1023px` | 24px | Semantic max width remains active; charts retain available analytical width |
| Desktop | `≥1024px` | 32px | Content centers within its semantic maximum |

Landscape and split-screen changes are handled from the current window width. No device-name assumptions are used.

## Rules

- Use `AppScreen`; do not add route-local page gutters or bottom-tab padding.
- Select a semantic width only when the route default is not correct.
- Wide charts and tables remain inside `full_width_analytical`; narrative copy does not become edge-to-edge.
- Existing table and chart horizontal scrolling remains authoritative when columns cannot fit.
- Modal content uses `modal_content` and owns its safe bottom independently of the tab bar.

## Validated classes

Browser validation covered 320, 390, 640, 768, 1024, and the in-app browser's practical wide maximum of 1476px, in portrait and landscape shapes. The 35-check responsive matrix found zero overflow, clipped/unnamed controls, hidden selected tabs, nested controls, or scoped console errors.
