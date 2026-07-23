# Stage 11.2B Modal Guidelines

## Shared policy

- Maximum desktop width: 760px.
- Phone/tablet presentation: bottom sheet up to 88% height with a 280px stable minimum.
- Header spacing and close location are owned by `DetailModal`.
- Close controls use `AppButton` and meet the 44px target.
- Scroll content owns one modal safe-bottom inset; no tab inset is inherited.
- `KeyboardAvoidingView` protects input content.
- Backdrop is a sibling dismissal control, avoiding nested interaction.
- `onRequestClose` handles Escape/system dismissal.
- Opening focuses Close on web; dismissal restores the invoking control.

Universal Search uses the same width and safe-bottom calculation in its full-screen overlay. Its input remains autofocus-enabled and its internal results scroll independently.

Browser validation passed close button, backdrop, Escape, focus restoration, 760px desktop cap, 44px close target, long content, and zero nested controls.
