# Stage 9.2A Dead-End Interaction Report

## Result

Zero known enabled tappable dead ends remain in the audited interaction registry.

| Interaction family | Outcome | Cleanup / disposition |
|---|---|---|
| Home cards and rows | Navigate | Entity rows use canonical entity destinations |
| Market tabs and controls | Filter / expand | Existing behavior preserved |
| Sectors Search | Filter then navigate | Reads test repository in explicit test mode; reads canonical Sector/Theme snapshots otherwise |
| Sectors Compare | Expand | Enabled only when its deterministic repository exists; disabled in live mode instead of opening an empty view |
| Sectors top-level Filter | Filter | Enabled only where its repository is available; disabled in live mode instead of presenting a no-op panel |
| Sector/Theme heatmap tiles | Navigate / intentionally static | Accessibility role is removed when no callback exists |
| Saved Sector/Theme cards | Navigate | Both hand off to canonical Sectors detail |
| Stock cards | Expand | Existing canonical Watchlist Stock Detail preserved |
| Report history/actions | Expand / download / share / delete | Existing behavior preserved |
| Copilot actions | Navigate | Resolved through Navigation Registry |
| Context-intelligence rows | Intentionally static | No press role or handler; evidence is presented as read-only context |
| Settings rows | Navigate / update / static | Inert update controls removed; static capability/status rows have no press role |

## Alert interactions

Raw alert JSON was not an interaction but created an information dead end. Sector and Theme snapshot alerts now pass through `sectorAlertPresenter` and the shared `AlertList`, exposing entity, transition/reason, and timestamp where present.
