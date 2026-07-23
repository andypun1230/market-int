# Stage 10.2 Atomic Analytical Screen-State Specification

## Authority

`frontend/src/features/trust/atomicScreenState.ts` owns top-level analytical request state. `useAsyncData` consumes the reducer, and Compare/Breadth History/Theme transitions apply the same exclusivity rules.

Supported phases are `idle`, `loading`, `available`, `partial`, `empty`, `unavailable`, `stale`, and `failed`.

## Transition rules

| Event | No retained data | Retained valid data |
|---|---|---|
| request | `loading` | prior phase + `refreshing=true` |
| success | supplied terminal phase and new data atomically | supplied terminal phase and replacement data |
| failure | `failed`, no data | `stale`, retained data, explicit error |
| obsolete response | ignored by request ID | ignored by request ID |
| reset | initial phase | initial phase |

`atomicRenderFlags` yields exactly one of loading/content/empty/unavailable/stale/error at a time. Background refresh is metadata on valid content and is not a second top-level state.

## Screen invariants

- Compare never shows populated output with empty/unavailable copy.
- Theme surfaces do not render a review/unavailable state before registry/snapshot loading resolves.
- Breadth History has one authoritative populated/empty/error branch.
- Failed refresh retains and labels cached content.
- Rapid request replacement cannot publish an obsolete response.

