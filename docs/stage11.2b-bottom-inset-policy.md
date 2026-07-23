# Stage 11.2B Bottom Inset Policy

Owner: `pageBottomInset` in `frontend/src/architecture/layoutPolicy.ts`; application owner: `AppScreen`.

## Formula

- Web primary tab: 70px tab-bar footprint + 16px breathing space = **86px**.
- Native primary tab: 58px bar + current bottom safe area + 16px breathing space.
- Stack/non-primary screen: current bottom safe area + 16px breathing space.
- Modal: current bottom safe area + 16px breathing space, owned inside the modal scroll content.

Safe-area bottom is deliberately excluded from `SafeAreaView` edges where scroll content owns it. This prevents double padding. Modal content never inherits the tab-bar footprint.

## Validation

Home, Market, Sectors, Watchlist, and More each exposed exactly 86px of web content padding, reached their scroll end, and had zero horizontal overflow at 390px. The Home final card ended 25px above the navigation surface in the measured browser frame.
