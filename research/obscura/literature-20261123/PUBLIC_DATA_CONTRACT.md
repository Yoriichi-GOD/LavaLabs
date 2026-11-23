# Paper applicability: organizer specification checked live

23 November 2026. Read the public competition Data description and bundled README in the signed-in browser; no competition arrays downloaded. [Official source](https://www.kaggle.com/competitions/obscura/data)

Inputs are facility-framed384x384chips:12Sentinel-2 **Level-2A surface-reflectance** bands B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12, scaled10000, plus SCL and cloud probability. No B10, coordinates, georeferencing or physical pixel size. Facility framing varies. The description states0–1reflectance; actual clipped/saturated-value support must be checked privately before any physics-based feature is implemented.

Samples span a few days. Targets refer to a fixed10kmwindow. Gas values are coarse Sentinel-5P site-window means minus the median of a30–75kmbackground ring; all are standardized with training statistics. Fire/flare intensity is derived from FIRMS detections; the minimum represents no detection, not missingness. No facility emission-rate interpretation is authorized by these labels.

Weather includes wind speed and **meteorological wind direction FROM**, plus temperature,humidity,precipitation,solar radiation. Only cyclic month is supplied. Dates, geography and external environmental acquisitions cannot be recovered or added.

Implications: no calibrated TOA radiance/temperature/FRP/flux retrieval; no temporal-reference method requiring another pass; no known-metre hotspot-size thresholds. A small chip need not cover the full target window, so no detected chip hotspot cannot imply a zero/floor target. Hypotheses may use dimensionless relative-pixel spectral/spatial statistics or an official-input-trained image model, subject to held-out-site validation. These are applicability conclusions, not measured error causes or improvements.
