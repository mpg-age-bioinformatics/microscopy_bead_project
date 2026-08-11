# Naming Scheme — Centricity / Homogeneity Test

This document describes the naming convention for the **Centricity / Homogeneity**
(`TCenHom`) test data. For the general bead-test naming scheme, see the
[Data Preparation](README.md#data-preparation) section of the README.

## Token format

```
<DATE>_M<microscope>_O<objective>_TCenHom<Slide><Laser>[<Detector>][SD<Pinhole>]
```

(No `_S`/`_B` bead tokens — those are for bead tests only and must be omitted here.)

| Token           | Prefix      | Required | Allowed values                                       | Example       |
|-----------------|-------------|----------|------------------------------------------------------|---------------|
| Date            | *(none)*    | yes      | **8 digits** `YYYYMMDD`                               | `20260121`    |
| Microscope      | `_M`        | yes      | no spaces                                             | `_MLeicaSP8X` |
| Objective       | `_O`        | yes      | no spaces                                             | `_O63x1.4`    |
| Test base       | `_TCenHom`  | yes      | fixed prefix (= **Cen**tricity / **Hom**ogeneity)     | `_TCenHom`    |
| Slide           | —           | yes      | `FITC`, `Chroma`, …                                  | `FITC`        |
| Laser           | —           | yes      | `405`, `488`, `561`, `633`, … (nm)                  | `488`         |
| Detector        | —           | optional | `Zyla`, `Sona`, … (omit for confocal PMT/HyD)       | `Sona`        |
| Spinning disk   | `SD`        | optional | pinhole size in µm as a bare number (`25`, `40`, `50`, …) or `SoRa` | `SD40`, `SDSoRa` |

The **spinning-disk / pinhole** token records which disk/pinhole was used. Write
the pinhole size as a plain number **without the `µm` unit** (`SD40`, not
`SD40µm`), or `SDSoRa` for SoRa. Place it **at the end**, after the detector.

**Valid test tokens:**
- `TCenHomFITC405`
- `TCenHomFITC488`
- `TCenHomFITC488Zyla`
- `TCenHomFITC488Sona`
- `TCenHomChroma488Sona`
- `TCenHomChroma488SonaSD40`
- `TCenHomChroma488ZylaSD25`
- `TCenHomChroma488SD50`
- `TCenHomFITC488SDSoRa`

## Hard rules

1. **Date = exactly 8 digits** `YYYYMMDD` at the start. `20260121` ✅ — `260121` ❌.
2. **Underscore is the delimiter — never inside a value.**
3. **No spaces anywhere.** `Alexa 350` ❌ → use the canonical channel token.
4. **Keep the `_` before each prefix.** `O63x1.4TCenHom` ❌ → `_O63x1.4_TCenHom` ✅.
5. **Same metadata at every level** — session folder, channel subfolder, and every
   output file must match.

## Folder/file layout

```
20260121_MLeicaSP8X_O63x1.4_TCenHom/                         <- session folder (channel-agnostic)
├── 20260121_MLeicaSP8X_O63x1.4_TCenHom.lif
└── Processed/
    ├── 20260121_MLeicaSP8X_O63x1.4_TCenHomFITC405/          <- per-channel (full token)
    │   └── 20260121_MLeicaSP8X_O63x1.4_TCenHomFITC405_..._stats.xls
    └── 20260121_MLeicaSP8X_O63x1.4_TCenHomFITC488/
        └── 20260121_MLeicaSP8X_O63x1.4_TCenHomFITC488_..._stats.xls
```

- **Parent session folder:** `_TCenHom` (no channel).
- **Channel subfolders + their files:** full token with slide+laser (+detector) —
  this is what gets recorded.

## Mistakes to avoid (from sample data)

| ❌ Wrong                                  | ✅ Right                          |
|------------------------------------------|----------------------------------|
| `260121_...`                             | `20260121_...`                   |
| `O63x1.4THom.lif`                        | `_O63x1.4_TCenHom.lif`           |
| `...THomAlexa 350_...`                   | `...TCenHomFITC405_...`          |
| Folder `_THom` but file `...O63x1.4THom` | identical token everywhere       |

## Backward compatibility

Going forward, canonical `TCenHom…` form above should be adopted.
The extractor will **also auto-accept the legacy `THom…` prefix and normalize it
to `TCenHom…`**, keeping whatever slide/laser/detector tokens follow — so
historical exports keep working without renaming:

| Legacy token        | Normalized to          |
|---------------------|------------------------|
| `THom405`           | `TCenHomFITC405`       |
| `THom488`           | `TCenHomFITC488`       |
| `THomFITC405`       | `TCenHomFITC405`       |
| `THomFITCZyla`      | `TCenHomFITCZyla`      |
| `THomChromaSona`    | `TCenHomChromaSona`    |

The bare laser-only forms (`THom405` / `THom488`) carry no slide token, so the
extractor assumes the **FITC** slide when normalizing them.
