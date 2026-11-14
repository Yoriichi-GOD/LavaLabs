# Road-exposure reference sources

Metadata check, 2026-11-12. The Germany and Louisiana-East public SpaceNet 8 releases expose individual native GeoJSON objects and an image-to-annotation filename index. Maxar’s legacy archive identifies the capture day for each post-event catalog ID. Independent Sentinel-2 Level-2A pre/post STAC items cover the proposed regions. Annotation bodies, flood-label values, and imagery pixels were outside this check. Scene cloud percentages describe full Sentinel tiles. Local clear-pixel support and the eligible road denominator still require verification.

## Native access and reference semantics

The benchmark paper describes hand-drawn building footprints and road centerlines from Maxar pre-event imagery, with water exposure attributed using post-event pansharpened RGB. The flood attribute indicates water covering a road segment. The annotators omitted the attribute for features hidden in the post-event image. Use an explicit supported negative value for a negative label and retain omitted/unknown features as unscored. This is an independently interpreted optical reference for a Sentinel-2 method, with timing and observability limits. It does not verify vehicle passage or structural damage. [SpaceNet 8 benchmark paper, §§2 and 5–6](https://elib.dlr.de/191307/1/Hansch_SpaceNet_8_-_The_Detection_of_Flooded_Roads_and_Buildings_CVPRW_2022_paper.pdf)

The official baseline identifies roads via non-null `properties.highway`, treats the road geometry as `LineString`, sets EPSG:4326 for export, reads `properties.flooded`, and handles both `properties.id` and `properties.@id` across AOIs. The native identifiers’ completeness and uniqueness were outside this metadata check. A row can be keyed by `AOI / annotation filename / feature ordinal` within hashed native objects. Use native IDs for cross-tile grouping after checking missingness and repeated/clipped road geometries. GeoJSON serves geometry and exposure attributes together. A staged import can allowlist geometry and identifier fields before opening the exposure attribute. [Official SpaceNet baseline schema and loader](https://github.com/SpaceNetChallenge/SpaceNet8/blob/main/baseline/data_prep/geojson_prep.py)

Anonymous `ListObjectsV2` and object `HEAD` succeeded. Use the `label` field from the mapping as the filename under the AOI’s `annotations/` prefix. Germany and Louisiana-East also publish `_reference.csv` files (2,161,947 and 5,843,764 bytes), which were not opened. Louisiana-West has a mapping but no annotation prefix. [AWS SpaceNet registry](https://registry.opendata.aws/spacenet/) · [Official native AOI index](https://spacenet-dataset.s3.amazonaws.com/?list-type=2&prefix=spacenet%2FSN8_floods%2F&delimiter=%2F) · [Germany annotation listing](https://spacenet-dataset.s3.amazonaws.com/?list-type=2&prefix=spacenet%2FSN8_floods%2FGermany_Training_Public%2Fannotations%2F) · [Louisiana-East annotation listing](https://spacenet-dataset.s3.amazonaws.com/?list-type=2&prefix=spacenet%2FSN8_floods%2FLouisiana-East_Training_Public%2Fannotations%2F)

| Split | Direct filename mapping | Sample native GeoJSON, `HEAD` verified |
| --- | --- | --- |
| Germany training | [17,450-byte mapping](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/Germany_Training_Public_label_image_mapping.csv) | [0_41_59.geojson](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/annotations/0_41_59.geojson), 55,897 bytes |
| Louisiana-East training | [44,640-byte mapping](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Louisiana-East_Training_Public/Louisiana-East_Training_Public_label_image_mapping.csv) | [1_7_88.geojson](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Louisiana-East_Training_Public/annotations/1_7_88.geojson), 14,917 bytes |

SpaceNet publishes its dataset under CC BY-SA 4.0. Credit the SpaceNet Partners and Maxar as specified by the dataset. The Universitat de València TACO card also lists CC BY-SA 4.0 and OpenStreetMap contributors among the providers. Its optional ZIP supports byte ranges and has a verified 4,933,377,810-byte size at revision `931047e7d7e0f1a79fb8012eef3c005e1497560e`. The direct native GeoJSON objects preserve the original centerlines and avoid an archive download. [Official SpaceNet challenge and license](https://www.spacenet.ai/sn8-challenge/) · [TACO dataset card](https://huggingface.co/datasets/isp-uv-es/spacenet8-taco) · [Pinned TACO ZIP](https://huggingface.co/datasets/isp-uv-es/spacenet8-taco/resolve/931047e7d7e0f1a79fb8012eef3c005e1497560e/spacenet8.zip)

## Maxar reference dates and raster bounds

Capture days were joined by exact catalog ID across SpaceNet’s filename mappings and Maxar’s dated legacy object keys. The 36-byte `.info` objects contain a delivery placeholder. Source and native TIFF metadata ranges examined supplied grid metadata but no capture clock. The envelopes below come from source TIFF dimensions, pixel scales, and tiepoints. These are EPSG:4326 outer raster rectangles in `[west,south,east,north]` order. Actual valid-image support can occupy a smaller or irregular area. [SpaceNet catalog ID and resolution table](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/resolutions.txt)

| Region / role | Catalog ID and Maxar date | Raster envelope | Source |
| --- | --- | --- | --- |
| Germany pre | `10500500C4DD7000`, 2021-02-11 | `[6.8398641001,50.4734558324,7.0617629472,50.8181656078]` | [Maxar source GeoTIFF](https://dg-opendata.s3.amazonaws.com/events/western-europe-flooding21/pre-event/2021-02-11/10500500C4DD7000/10500500C4DD7000.tif) |
| Germany post, singly mapped reference set | `10500500E6DD3C00`, 2021-07-18 | `[6.6914557970,50.2960279044,7.0844614095,50.5887635679]` | [Maxar dated catalog index](https://dg-opendata.s3.amazonaws.com/?list-type=2&prefix=events%2Fwestern-europe-flooding21%2Fpost-event%2F2021-07-18%2F10500500E6DD3C00%2F&delimiter=%2F) · [Maxar source GeoTIFF](https://dg-opendata.s3.amazonaws.com/events/western-europe-flooding21/post-event/2021-07-18/10500500E6DD3C00/10500500E6DD3C00.tif) |
| Germany overlapping post | `1040050035DC3B00`, 2021-07-21 | `[6.7938275525,50.1375032845,6.9881419789,50.5145100934]` | [Maxar source GeoTIFF](https://dg-opendata.s3.amazonaws.com/events/western-europe-flooding21/post-event/2021-07-21/1040050035DC3B00/1040050035DC3B00.tif) |
| Louisiana-East post | `10300100C46F5900`, 2021-08-31 | `[-90.1400569083,29.5353495143,-89.9341849760,30.5700709559]` | [Maxar dated catalog index](https://dg-opendata.s3.amazonaws.com/?list-type=2&prefix=events%2Fhurricane-ida21%2Fpost-event%2F2021-08-31%2F10300100C46F5900%2F&delimiter=%2F) · [Maxar source GeoTIFF](https://dg-opendata.s3.amazonaws.com/events/hurricane-ida21/post-event/2021-08-31/10300100C46F5900/10300100C46F5900.tif) |

## Germany frozen metadata cohort

The 17,450-byte mapping SHA-256 is `6eb036a70cdd19f15fb9dabc067e8c41a79d7cea8e4b3927d5188661d7e5e45e`. Select all rows where `post-event image 1` begins `10500500E6DD3C00_` and `post-event image 2` is empty. This yields 122 of 202 mapping rows and 1,871,529 total annotation bytes across exactly 122 verified keys. The 80 other rows each list both July 18 and July 21. The metadata offers no per-feature attribution to either date in those tiles. [Germany mapping](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/Germany_Training_Public_label_image_mapping.csv) · [Germany annotation listing](https://spacenet-dataset.s3.amazonaws.com/?list-type=2&prefix=spacenet%2FSN8_floods%2FGermany_Training_Public%2Fannotations%2F)

The 122-tile envelope is `[6.976108584859848,50.47268852142039,7.063694325061571,50.54567663825516]`. It comes from the extremal keys on the published regular geographic grid and the pre-tile GeoTIFF bounds for those keys. Several grid cells inside the envelope are absent from the cohort. A smaller complete window, selected by location and the single-date mapping, has columns 37–42 and rows 60–62, 18 tiles and 265,003 bytes, within `[7.019901454960709,50.5116155170656,7.049096701694618,50.52621314043255]`. [Benchmark grid specification, §2](https://elib.dlr.de/191307/1/Hansch_SpaceNet_8_-_The_Detection_of_Flooded_Roads_and_Buildings_CVPRW_2022_paper.pdf) · [Sample native grid metadata source](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/PRE-event/10500500C4DD7000_0_28_59.tif)

Each line lists a column followed by every accepted row. For column `c` and row `r`, the exact annotation filename is `0_c_r.geojson`, the exact post-image filename is `10500500E6DD3C00_0_c_r.tif`, and the pre-image filename is `10500500C4DD7000_0_c_r.tif`. The keys below are ordered numerically for readability. [Native Germany mapping](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/Germany_Training_Public_label_image_mapping.csv)

```text
28: 59,60,61
29: 59,60,61,62,63,64,65,66,67,68,69,70
30: 59,60,61,62,63,66,67,68,69,70
31: 57,59,60,61,62,63,65,66,67,68,69
32: 56,57,58,59,61,62,63,65,66,68,69
33: 56,57,61,68
34: 61,62,68
35: 59,60,61,62,63,68
36: 59,60,61,62,68
37: 59,60,61,62,67,68,69,70
38: 60,61,62,68,69
39: 60,61,62,63,66,67,69
40: 57,58,59,60,61,62,63,67,68,69
41: 58,59,60,61,62,63,69
42: 58,59,60,61,62,69
43: 58,62,63,68,69
44: 63,68,69
45: 63,64,67,68,69,70
```

## Louisiana-East metadata candidate

The 44,640-byte mapping SHA-256 is `3ab79befbb73958a36f7002db71c0390a70f3ce73d8c8cbff8336aa11ac04997`. All 599 mapping rows have the same August 31 post ID. A contiguous nine-tile pilot has filenames `1_c_r.geojson` for `c∈{6,7,8}` and `r∈{87,88,89}`. These total 118,810 annotation bytes and the native pre-tile grids give `[-90.029795154087,29.815535523225634,-90.01634198439203,29.828988692920607]`. The exact post filenames are `10300100C46F5900_1_c_r.tif`. This pilot is bounded by the native grid and verified scene coverage. Its suitability for scored evaluation remains open until the preregistered label and support gates run. [Louisiana-East mapping](https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Louisiana-East_Training_Public/Louisiana-East_Training_Public_label_image_mapping.csv) · [Louisiana-East annotation listing](https://spacenet-dataset.s3.amazonaws.com/?list-type=2&prefix=spacenet%2FSN8_floods%2FLouisiana-East_Training_Public%2Fannotations%2F)

## Sentinel-2 pairing

The four corners of each proposed envelope were inside both corresponding item geometries. All four items below use the same Sentinel-2 processing baseline `05.00`. Use the linked STAC item’s `green` (B03), `nir` (B08), `swir16` (B11) and `scl` assets. The Sentinel acquisitions are a separate data source from the Maxar inputs used to attribute SpaceNet exposure. Neither the geometry intersection nor a scene cloud statistic verifies local pixel usability.

| Region / role | Earth Search item | Capture UTC | Scene cloud |
| --- | --- | --- | --- |
| Germany pre | [S2B_32ULB_20210703_1_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_32ULB_20210703_1_L2A) | 2021-07-03T10:36:53.839Z | 27.32% |
| Germany post | [S2A_32ULB_20210718_1_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_32ULB_20210718_1_L2A) | 2021-07-18T10:36:55.733Z | 4.57% |
| Louisiana-East pre | [S2B_15RYP_20210823_1_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_15RYP_20210823_1_L2A) | 2021-08-23T16:55:11.784Z | 1.60% |
| Louisiana-East post | [S2B_15RYP_20210902_1_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_15RYP_20210902_1_L2A) | 2021-09-02T16:55:09.567Z | 4.09% |

With Maxar’s capture date interpreted as a UTC day interval, the Germany post images are within 13 h 24 min and the Louisiana-East Sentinel observation is 40 h 55 min to 64 h 55 min later than the Maxar observation, rounded to minutes. Both satisfy a 72-hour screen under that interpretation. The same-day Germany observation gives the tighter interval. Retain acquisition date precision explicitly. [Germany Maxar catalog index](https://dg-opendata.s3.amazonaws.com/?list-type=2&prefix=events%2Fwestern-europe-flooding21%2Fpost-event%2F2021-07-18%2F10500500E6DD3C00%2F&delimiter=%2F) · [Louisiana Maxar catalog index](https://dg-opendata.s3.amazonaws.com/?list-type=2&prefix=events%2Fhurricane-ida21%2Fpost-event%2F2021-08-31%2F10300100C46F5900%2F&delimiter=%2F)
