# Stage 12.1 Bundle Profile

**Classification:** PASS WITH CONDITIONS

## Production export

| Item | Size |
|---|---:|
| Total web export | 5,848 KiB (5.71 MiB) |
| JavaScript | 3,594,300 bytes raw / **908,888 bytes gzip** |
| Material Symbols font | 956,416 bytes raw / **425,122 bytes gzip** |
| Static assets | 21 files / 1,311,618 bytes |
| HTML | 25 files / 937,128 bytes |
| Logo glow image | 331,624 bytes |
| Source asset directory | 23 files / 1,405,094 bytes |

The web export contains one JavaScript chunk. Lighthouse reports 2,174,355 bytes of unused JavaScript on Home, or **60.49%** of the raw bundle. The duplicated-JavaScript audit found no duplicate modules; the issue is broad eager delivery rather than module duplication.

## Asset composition

| Type | Files |
|---|---:|
| JavaScript | 1 |
| CSS | 2 |
| HTML | 25 |
| PNG | 20 |
| TTF | 1 |
| JSON | 1 |
| ICO | 1 |

The largest source assets are the 799 KB application icon, 332 KB logo glow, 79 KB Android foreground image, and 59 KB tutorial image. Some template/badge assets are not emitted in the web export; native package use should be verified before removal is considered.

## Duplication

Five route aliases emit byte-identical HTML pairs:

- `index` and `(tabs)/index`
- `market` and `(tabs)/market`
- `sectors` and `(tabs)/sectors`
- `watchlist` and `(tabs)/watchlist`
- `more` and `(tabs)/more`

One copy of each pair totals approximately **230,896 raw bytes**. This is deployment duplication and does not duplicate a single navigation's runtime transfer. No duplicate JavaScript modules were reported.

## Budget status

| Budget | Current | Status |
|---|---:|---|
| JavaScript gzip <= 750 KB | 909 KB | Fail |
| Icon/font gzip <= 150 KB | 425 KB | Fail |
| Total web export <= 5 MB | 5.71 MB | Fail |
| Home unused JavaScript <= 35% | 60.49% | Fail |
| Duplicate runtime modules | None detected | Pass |

## Opportunities

1. **Route-level code splitting — High.** Lazy-load analytical modules that Home does not use. Based on Lighthouse's unused-JS audit, the upper-bound raw reduction is about 2.17 MB; a practical first-load target is 450–600 KB less gzip and 40–90 ms less JS initialization.
2. **Icon subset — Medium.** Replace the full Material Symbols font payload with an application-used subset or existing local icon mappings. Expected gzip saving: 300–400 KB.
3. **Asset/package pruning — Low.** Verify and remove unused template assets from platform packages. This improves install/export size but has little effect on current web navigation.
4. **Static route alias deduplication — Low.** Consolidate deployment output only if the hosting contract permits it; expected export saving is about 231 KB raw with no runtime effect.

These are profiling recommendations only. No bundle, dependency, asset, or route configuration was changed.
