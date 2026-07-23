# Stage 11.2B Secondary Navigation Standard

Owner: `selectedItemScrollOffset`; renderer: `HorizontalSelectionBar`. `SegmentedControl` consumes the same calculation when it can overflow.

## Contract

- Measure viewport, content, and every item.
- On initial/deep-linked selection, item-width change, or viewport change, center the selected item when practical.
- Clamp first to zero and last to the maximum content offset.
- Do not recenter during vertical scrolling.
- Preserve DOM/screen-reader order.
- Expose `tablist`, `tab`, an explicit clean label, and `aria-selected`/selected accessibility state.
- Visible icons are decorative to the parent control's accessible name.

Focused tests cover first, middle, last, deep-link geometry, non-overflowing content, and resize. Browser checks covered rapid item changes, a deep-linked Macro tab at 320px, and a resize to 768px; the selected item remained visible and announced selected.
