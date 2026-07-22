# PSTG to P Corporate-Action Verification

Conclusion: **VERIFIED SAME-ISSUER TICKER CHANGE**

Retrieved: `2026-07-19T18:11:25Z`  
Reviewer: `AndyPun123123` (`andypun3a224@gmail.com`)  
Review commit: `3b48aae2f371f88087cf4d09220198dfd3af7e03`

## Identities

| Field | Former | Current |
| --- | --- | --- |
| Display ticker | PSTG | P |
| Company name | Pure Storage | Everpure, Inc. |
| Exchange | NYSE | NYSE |
| SEC CIK | 0001474432 | 0001474432 |
| Polygon composite FIGI | BBG00212PVZ5 | BBG00212PVZ5 |
| Polygon share-class FIGI | BBG00212PW10 | BBG00212PW10 |

The dated Polygon reference switches from PSTG through `2026-04-16` to P on `2026-04-17`. The SEC 8-K records the same issuer's corporate name change from Pure Storage to Everpure. This is one issuer, not a replacement constituent.

## Authoritative Evidence

- SEC company tickers: CIK `1474432`, current ticker `P`, title `Everpure, Inc.`: [company_tickers.json](https://www.sec.gov/files/company_tickers.json).
- SEC submissions for CIK `0001474432`: name `Everpure, Inc.`, ticker `P`, NYSE; former names include Pure Storage: [CIK0001474432.json](https://data.sec.gov/submissions/CIK0001474432.json).
- SEC 8-K `0001474432-26-000011`, filed `2026-02-23`: reports the February 2026 Pure Storage corporate-name change to Everpure while the common shares then continued trading as PSTG: [8-K](https://www.sec.gov/Archives/edgar/data/1474432/000147443226000011/pstg-20260223.htm).
- Polygon dated reference for PSTG on `2026-04-16`: active Everpure, same CIK/FIGIs, request ID `d76e7cfd5eea33bd956c369931979451`.
- Polygon dated reference for P on `2026-04-17`: active Everpure, same CIK/FIGIs, request ID `c17c7b7675ba541bcfba01d54c7199c4`.
- Polygon current P reference on `2026-07-17`: active Everpure, same CIK/FIGIs, request ID `46af4df3adf1391cbf9f355910649`.
- Polygon adjusted aggregates: PSTG has 450 sessions from `2024-07-01` through `2026-04-16` (request ID `07a233c200415cc0ad04223c02ddafa8`); P has 63 sessions from `2026-04-17` through `2026-07-17` (request ID `97f70d7e97f9995c955e010b55b8903c`).
- Finnhub current quote supports P as the current symbol. PSTG still returned an alias quote, so it is not used as proof of current identity.

## Continuity and Boundary Audit

The provider-symbol boundary is `2026-04-17`: Polygon history uses PSTG through `2026-04-16`, then P on and after `2026-04-17`.

- Last PSTG adjusted close: `67.80` on `2026-04-16`.
- First P adjusted close: `66.97` on `2026-04-17`.
- Boundary return: `-1.2242%`.
- Provider-date overlap: `0`; missing weekday sessions caused by the alias transition: `0`; synthetic return generation: `false`.
- Polygon aggregate responses declare adjusted history. No manual smoothing, split factor, or dividend normalization was applied. The ordinary one-day move does not indicate an adjustment discontinuity.

## Conflicts

The only conflict is that a Finnhub quote still responds to PSTG. That endpoint is treated as a legacy alias response, not active-symbol identity evidence. Polygon's dated reference identity, CIK, and FIGI continuity resolve the conflict in favor of current canonical P.

## Amendment Record

`memory_storage v1` remains immutable and proposed. `memory_storage v1.1` is the human-reviewed corporate-action amendment: role `infrastructure`, purity `90`, importance `6`, equal weighting, methodology, benchmark, and inclusion rationale are unchanged. PSTG is historical provenance only; P / Everpure is the sole active member identity.
