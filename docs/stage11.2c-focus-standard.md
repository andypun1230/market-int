# Stage 11.2C Canonical Focus Standard

## Owner

- Web owner: `frontend/src/global.css`
- Native/shared fallback: `frontend/src/components/ui/AppButton.tsx`
- Token owner: `Theme.colors.focus` (`#38BDF8`)

## Contract

- 3px solid cyan focus ring
- 2px offset
- At least 3:1 against adjacent dark surfaces; measured 8.33:1 against the background
- `:focus-visible` on web; ordinary pointer focus is suppressed
- No amber, red, green, or purple status color is reused as focus
- Ring is not clipped by shared controls or modal sheets

## Coverage

Buttons, icon buttons, links, cards acting as controls, search results, tabs, segmented controls, filter chips, report actions, modal close controls, settings rows, inputs, switches, Watchlist actions, compare selectors, and chart controls use the canonical behavior.

Roving selection supports Arrow Left/Right, Home, and End on horizontal tab systems. Modal focus starts on Close, remains inside the modal, supports Escape, and returns to the original trigger. If canonical routing removes the original search result, `DetailModal` returns focus to the matching visible entity control.

Disabled controls remain unfocusable. Reduced motion does not suppress the focus ring or state feedback.
