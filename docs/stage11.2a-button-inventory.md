# Stage 11.2A Button Inventory

## Result

**PASS**

`AppButton` is the canonical reusable button family. It preserves the existing accent, neutral, danger, and Copilot color semantics.

## Contract

| Variant | Intended use | Current examples |
|---|---|---|
| Primary | Main forward action | Empty-state recovery, Generate Updated Research, add ticker, Copilot send |
| Secondary | Alternate forward action | Read Research |
| Neutral | Non-destructive utility | Modal close, small Copilot actions |
| Danger | Error recovery or destructive emphasis | Error-state retry |
| Icon | Labelled icon-only utility | Back, header actions, search/compare/filter, add, refresh |
| Compact | Dense labelled utility with a full touch target | Ask Copilot and conversation context actions |

The family owns:

- minimum 44px height and 44px icon width
- shared horizontal spacing and small-radius default
- loading indicator and busy state
- disabled state
- pressed feedback
- keyboard focus outline
- accessible label, role, and state composition
- default and Copilot tones using existing theme colors

## Adoption

There are 15 `AppButton` render sites in 11 source files. Migrated families include:

- application back and command-header actions
- modal close, empty-state action, and error retry
- report generation and report reading
- Watchlist add/refresh and add-panel controls
- Sectors search/compare/filter utilities
- Copilot launch, send, and compact context actions

`QuickActionChip` and `SegmentedControl` remain specialized selection primitives, now with 44px minimum targets. Analytical chart scrubbers, rows, radio groups, and disclosure surfaces remain `Pressable` because substituting a button would change their behavior or structure; they are not duplicate button implementations.

## Validation

At 1280×720, 768×1024, and 390×844, the seven audited major routes had zero visible interactive targets with both dimensions below 44px. No nested interactive controls or unlabeled buttons were found.
