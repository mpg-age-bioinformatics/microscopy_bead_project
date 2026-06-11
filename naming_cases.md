# Naming Scheme

## Centricity / Homogeneity Test

This section describes the naming convention for the **Centricity / Homogeneity**
(`TCenHom`) test data. For the general bead-test naming scheme, see the
[Data Preparation](README.md#data-preparation) section of the README.

## Token format

```
<DATE>_M<microscope>_O<objective>_TCenHom<Slide><Laser>[<Detector>]
```

(No `_S`/`_B` bead tokens — those are for bead tests only and must be omitted here.)

| Token      | Prefix      | Required | Allowed values                                   | Example       |
|------------|-------------|----------|--------------------------------------------------|---------------|
| Date       | *(none)*    | yes      | **8 digits** `YYYYMMDD`                           | `20260121`    |
| Microscope | `_M`        | yes      | no spaces                                         | `_MLeicaSP8X` |
| Objective  | `_O`        | yes      | no spaces                                         | `_O63x1.4`    |
| Test base  | `_TCenHom`  | yes      | fixed prefix (= **Cen**tricity / **Hom**ogeneity) | `_TCenHom`    |
| Slide      | —           | yes      | `FITC`, `Chroma`, …                              | `FITC`        |
| Laser      | —           | yes      | `405`, `488`, `561`, `633`, … (nm)              | `488`         |
| Detector   | —           | optional | `Zyla`, `Sona`, … (omit for confocal PMT/HyD)   | `Sona`        |

**Valid test tokens:**
- `TCenHomFITC405`
- `TCenHomFITC488`
- `TCenHomFITC488Zyla`
- `TCenHomFITC488Sona`
- `TCenHomChroma488Sona`


| ❌ Wrong                                  | ✅ Right                          |
|------------------------------------------|----------------------------------|
| `260121_...`                             | `20260121_...`                   |
| `O63x1.4THom.lif`                        | `_O63x1.4_TCenHom.lif`           |
| `...THomAlexa 350_...`                   | `...TCenHomFITC405_...`          |
| Folder `_THom` but file `...O63x1.4THom` | identical token everywhere       |

## Backward compatibility

Going forward, the client should adopt the canonical `TCenHom…` form above.
The extractor will **also auto-accept the `THom…` prefix and normalize it
to `TCenHom…`**, keeping whatever slide/laser/detector tokens follow — so
previous exports should keep working without renaming:

| Legacy token        | Normalized to          |
|---------------------|------------------------|
| `THom405`           | `TCenHomFITC405`       |
| `THom488`           | `TCenHomFITC488`       |
| `THomFITC405`       | `TCenHomFITC405`       |
| `THomFITCZyla`      | `TCenHomFITCZyla`      |
| `THomChromaSona`    | `TCenHomChromaSona`    |

The bare laser-only forms (`THom405` / `THom488`) carry no slide token, so the
extractor assumes the **FITC** slide when normalizing them.


