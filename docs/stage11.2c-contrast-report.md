# Stage 11.2C Contrast Report

## Result

**PASS**

| Pair | Before | Final | Requirement |
|---|---:|---:|---:|
| Purple on purple-soft | 3.97:1 | 4.51:1 | 4.5:1 |
| Danger on danger-soft | 4.22:1 | 4.71:1 | 4.5:1 |
| Muted text on elevated card | 5.71:1 | 5.71:1 | 4.5:1 |
| Cyan focus on background | browser-default amber | 8.33:1 | 3:1 non-text |

Purple remains owned by Copilot/AI, red by danger/failure, amber by partial/stale/warning, green by positive/live, and cyan by selection/action/focus. The fixes darken existing soft-background pairings; no new semantic color family was introduced.

Automated validation checks the four pairs above. Browser acceptance additionally covered badges, tabs, disabled controls, empty/error/loading states, modal overlays, inline actions, confidence/freshness, and focus.

Chart-only micro labels remain an exception where needed for density. Every accepted chart exposes a concise accessible region summary, so chart interpretation does not depend on the small label or color alone.
