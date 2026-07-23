# Stage 11.2A Typography Report

## Result

**PASS**

The frontend now uses one semantic typography registry in `frontend/src/constants/theme.ts`. All 134 TSX files are free of literal `fontSize` and numeric `fontWeight` declarations.

## Semantic scale

| Family | Roles | Intended use |
|---|---|---|
| Analytical annotation | `chartMicro` 8/11, `chartAxis` 9/12 | Non-interactive chart marks with an equivalent accessibility summary |
| Supporting text | `chartLabel` 11/14, `caption` 11/16, `small` 12/18 | Chart labels, captions, metadata, secondary copy |
| Product text | `control` 13/18, `body` 14/20, `bodyLarge` 15/22 | Controls, body copy, primary supporting copy |
| Titles | `supportTitle` 16/21 through `sectionTitle` 18/24 and `detailTitle` 20/26 | Card, section, and detail headings |
| Decision and entity emphasis | `scoreTitle` 21/27 through `entityTitle` 28/34 | Scores, decision states, report and entity titles |
| Screen and hero emphasis | `screenTitle` 29/35 through `displayHero` 48/56 | Screen titles and primary hero values |

Weights are semantic: `medium` 600, `emphasis` 700, `strong` 800, and `heavy` 900.

## Heavy-weight policy

Weight 900 was reduced to five approved owners:

- `AppScreen`: screen titles
- `UniversalCommandHeader`: screen title
- `StockDetailHeader`: entity title
- `DecisionSummaryCard`: primary decision state
- `HeroDecisionCard`: hero decision value

All other former 900-weight declarations now use `strong` or another semantic weight. The automated registry rejects unregistered heavy-weight owners.

## Accessibility

- Interactive and product text starts at 11px; the browser audit found no essential interactive text below that minimum.
- `chartMicro` and `chartAxis` are the only sub-11px exceptions. They are non-interactive annotations whose chart containers expose accessible summaries.
- `chartLabel` was normalized from 10px to the 11px caption minimum.
- Desktop, tablet, and mobile checks found no clipping or horizontal overflow after token migration.

## Scope controls

No font family, color, layout hierarchy, content, route, or financial output changed. Line-height differences that carry deliberate report/chart density were retained unless a semantic token already provided the exact value.
