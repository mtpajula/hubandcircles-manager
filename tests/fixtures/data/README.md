# Fixture source data (V1)

Synthetic `DATA_DIR` for the build golden test. The layout follows ARKKITEHTUURI.md
chapters 5.1–5.3, 5.8 and 6. Scope: no layers, no services, no media. Field names
exactly as in the architecture (English, P10).

## Contents

| File | What |
|---|---|
| `project.json` | Project settings (5.1). No `feedback`; `itrs_scales` both `null`. |
| `themes/*.json` | The five default themes of chapter 5.8 (`winter`, `mtb`, `gravel`, `road`, `touring`) with `name`, `tagline`, `order` 1–5, `colors` and `dark` (true only for `winter`). No `basemap`, `default_layers` empty. |
| `routes/test-loop/route.json` | One route card (5.3). One `text` section, no cover image, no media. |
| `routes/test-loop/track.gpx` | GPX 1.1, one `trk`/`trkseg`, 10 `trkpt` points with `ele`, no timestamps. |
| `services/manual.geojson` | Empty `FeatureCollection`. The layout is in the architecture; V2 needs it. |

## GPX points

A loop near Rovaniemi. Starts and ends ~14 m apart (points 1 and 10).

| # | lat | lon | ele (m) | distance to previous (m, haversine, R = 6371000) |
|---|---|---|---|---|
| 1 | 66.5000 | 25.7200 | 100 | – |
| 2 | 66.5010 | 25.7210 | 105 | 119.7 |
| 3 | 66.5020 | 25.7230 | 112 | 142.2 |
| 4 | 66.5025 | 25.7260 | 118 | 144.2 |
| 5 | 66.5020 | 25.7290 | 115 | 144.2 |
| 6 | 66.5010 | 25.7300 | 120 | 119.7 |
| 7 | 66.5000 | 25.7290 | 126 | 119.7 |
| 8 | 66.4990 | 25.7260 | 120 | 173.4 |
| 9 | 66.4990 | 25.7225 | 110 | 155.2 |
| 10 | 66.5001 | 25.7202 | 100 | 159.3 |

## Expected computed values

| Field | Value | How |
|---|---|---|
| `ascent_m` | **29** | Sum of the positive differences between consecutive `ele` values: 5 + 7 + 6 + 5 + 6 = 29. Descents (−3, −6, −10, −10) do not count. |
| `bbox` | **[25.7200, 66.4990, 25.7300, 66.5025]** | `[min lon, min lat, max lon, max lat]` of the points, 4 decimals. |
| `length_km` | **1.277** (1277.5 m) haversine, published rounded to **1.3** | Sum of the haversine gaps between points 1→10, 3 decimals. In the golden test ±0.01 km is enough; a different Earth radius or a geodesic formula gives 1.27–1.28 km. |

The loop is not closed in the computation: the 14 m between the last point (10) and the
first (1) is not counted, because the GPX has no closing point.

## Other expectations

- `catalog.json`: five themes ordered by `order`, one route (`test-loop`), `default_theme: "gravel"`, `languages: ["fi","en"]`, `layers: []`, no `services` or `coverage`.
- The route's `themes: ["gravel"]` points to an existing theme → no reference error.
- Every `name`, `tagline` and `content` has both `fi` and `en` → no translation warnings.
- Theme colour `#9A6414` against white: contrast ratio ≈ 4.99:1 (WCAG formula) → passes the 4.5:1 limit narrowly; if a contrast check uses a different formula or limit, check this first.
