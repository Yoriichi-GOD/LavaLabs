# Drainage validation source eligibility

12 November 2026. Primary-source access and lineage audit; no training, registration, messages, paid calls, full raster downloads, new vector feature queries, or WorldFloods reserve access. This note does not declare a successful physical validation. Existing pilot findings are in `research/results/drainage-consistency-20261112/REPORT.md`.

## Immediate decisions

1. **A bounded public quantitative MERIT-derived Asia route exists:** the distributor's `flowdir45.tif` and `accum45.tif` support exact HTTP byte ranges. They are stripped GeoTIFFs, not COGs. Their original MERIT version is not established by the inspected metadata. Use only as a named, qualified secondary baseline after freezing acquisition and scoring.
2. **Exact producer MERIT Hydro v1.0.1 remains access-gated:** producer registration/password, an existing authorized local extract, or an authenticated Earth Engine project is needed for a version-certified comparison. Do not infer credentials or register on the user's behalf.
3. **An accessible observed-vector control was found:** NERC EIDC South Saskatchewan ADCP, with a public package URL, five-column field definitions,50CSV file identities/hashes and949,009 uncompressed CSV bytes. Coordinate-zone uncertainty needs the declared companion-metadata inference/check below. USGS Sacramento/Allegheny remain physical-observation prospects with ScienceBase attachment access blocked; Sacramento is additionally source-metadata exposed.
4. **NHD vector direction is an available annotation reference, conditional on lineage.** It must remain separate from physical observed velocity. No fresh NHD feature records were read.
5. **Nepal, Varanasi, and the existing Delhi engineered units still lack an acquired, independent, co-registered interior physical direction reference and separate outlet anchor.** This is a bounded search outcome, not proof that no such records exist.

## MERIT access and quantitative eligibility

### Producer and Earth Engine

The producer now uses [Global Hydrodynamics Lab's MERIT Hydro page](https://global-hydrodynamics.github.io/MERIT_Hydro/); the previous Tokyo URL redirects. It identifies v1.0.1 (10 June 2019), 3 arc-second GeoTIFFs, 5-degree tiles bundled into 30-degree packages, registration followed by an emailed password, and CC BY-NC 4.0 / ODbL 1.0 dual licensing. It derives direction from MERIT DEM and water maps, so it is a hydrographic comparator rather than independent physical truth. **Gate:** no authorized producer password/local original was supplied to this audit. No download-page authentication was attempted.

The [Earth Engine catalog](https://developers.google.com/earth-engine/datasets/catalog/MERIT_Hydro_v1_0_1) identifies `MERIT/Hydro/v1_0_1`, including `dir`, `upa`, `upg`, `elv`, `hnd`, and width bands. It documents single-downstream-direction limitations at bifurcations and difficulties with tunnels/glaciers. Its catalog/visualization page is not an unauthenticated quantitative export API. **Gate:** parent execution found no local Windows/WSL Earth Engine credentials/project/library. An existing authorized project/export would close this access gate; a rendered map would not.

### Public distributor mosaic: Asia candidate

[Matthew Heberger's data distribution page](https://mghydro.com/watersheds/data/) directly links quantitative MERIT-derived rasters, states CC BY-NC-SA 4.0, and publishes [SHA256 entries](https://mghydro.com/watersheds/data/checksums.sha256). This is the distributor's own primary description, not an official Yamazaki release. Its [raster processing README](https://github.com/mheberger/delineator/tree/main/data_mgmt/0_raster) describes mosaicking original 5-degree tiles. The inspected source does not identify their exact original release version. The distributor's stated data license differs from the producer's dual-license wording; retain both attributions/terms and do not label the derivative as an unchanged official download.

The [tile-to-basin source table](https://github.com/mheberger/delineator/blob/main/data_mgmt/0_raster/basins_tiles.csv) places `n25e080` and `n25e085` in mosaic **45**, covering the Varanasi/Nepal tile domains. Mosaic42 is East Asia and is not the appropriate regional candidate. This is tile-envelope coverage, not a proof of valid observations or basin membership at every location.

| Public URL | Header-verified size | Type / convention | Published whole-file SHA256, not locally recomputed |
|---|---:|---|---|
| [flowdir45.tif](https://mghydro.com/watersheds/data/flowdir45.tif) | 276,428,799 bytes | UInt8, DEFLATE; flow-direction codes | `51834aef9beae54bbc2872a73678c8cf467688d32f2b83b8525d96a60fe17817` |
| [accum45.tif](https://mghydro.com/watersheds/data/accum45.tif) | 748,635,020 bytes | Int32, DEFLATE; upstream **pixel count**, NoData0 | `b6db95c629f7faad72df456d11d389b7d8f561ffef47ca6064b365bea001e74d` |

**Live metadata-only probe:** both returned exact HTTP206 `Content-Range` responses for requested bytes. Only TIFF header, IFD entries, and referenced geospatial metadata were read, with no strip/pixel decoding. Both are 42,000 by42,000 cells, one band, EPSG4326, pixel size1/1200 degree, upper-left corner `(64.99958333333333, 39.999583333333334)`, one compressed **row per strip**, and no tile tags. Thus they are **not tiled/COG**. A bounded crop can request only intersecting compressed row strips, but the implementation must cap bytes, ranges, rows/cells and reject ignored ranges. A small x-window still decompresses whole selected rows.

The distributor's [flowdir merge source](https://github.com/mheberger/delineator/blob/main/data_mgmt/0_raster/qgis_merge_flowdir_rasters.py) sets output background247; the inspected file header has no explicit NoData tag. Preserve declared undefined/inland/mouth codes instead of routing them as ordinary directions. The [accumulation merge source](https://github.com/mheberger/delineator/blob/main/data_mgmt/0_raster/qgis_merge_accum_rasters.py) reads `*_upg.tif`, not `*_upa.tif`. **Do not report the accumulation mosaic as km².** Physical cell area varies with latitude; do not silently substitute pixel count for contributing area.

**Eligible scope:** bounded comparator/mechanics experiment named “MERIT-derived distributor mosaic, original version unverified.” **Not established:** pixel equivalence with producer v1.0.1, independently observed direction, full-file checksum match, or scientific improvement.

### Other routes

[EURAC's Alpine collection](https://edp-portal.eurac.edu/discovery/MERIT_HYDRO) and its [STAC collection metadata](https://stac.eurac.edu/collections/MERIT_HYDRO) declare CC-BY-NC-4.0, Yamazaki Lab producer/EURAC host, and bands `basins`, `elevtn`, `flwdir`, `lndslp`, `rivmsk`, `strord`, `uparea`. The collection envelope is longitude5.0746–15.8579, latitude43.6171–50.0313: **Alps only, not Nepal/India**. Metadata was accessible using ordinary authorized network access; no STAC item or raster values were opened. Its exact source version, reprocessing, direction encoding, per-band asset layout and bounded COG behavior remain unchecked. A catalog date in2024 is not a new MERIT survey epoch.

[FullHydro's own download description](https://fullhydro.org/downloads/merit-hydro-v1.0.1-90m/) explicitly says its products are independent derivatives and source `dir` / `elv` layers are **not redistributed**. It does not solve source-direction access. Iceland examples bundled with [delineator](https://github.com/mheberger/delineator) are derivative examples rather than field direction truth; no example rasters were read.

## Directional references and lineage

### Accessible prospective control: EIDC South Saskatchewan ADCP

The authoritative [EIDC catalog](https://catalogue.ceh.ac.uk/documents/e4fe2ebe-b207-47d5-8c77-9873afc63da9), DOI[10.5285/e4fe2ebe-b207-47d5-8c77-9873afc63da9](https://doi.org/10.5285/e4fe2ebe-b207-47d5-8c77-9873afc63da9), identifies field measurements by Unsworth, Nicholas, Ashworth, Parsons and Sambrook Smith, published4September2019 under the [Open Government Licence](https://eidc.ac.uk/licences/ogl/plain), copyright NERC. The [machine-readable primary metadata](https://catalogue.ceh.ac.uk/id/e4fe2ebe-b207-47d5-8c77-9873afc63da9?format=json) describes SonTek M9, RTK dGPS positioning, boat speed/heading correction, seven-ping averaging reduced to1Hz, and two horizontal depth-averaged velocity components. Catalog resolution10m is metadata, not a guarantee of independent10m directional samples. The broad catalog envelope is49–53.2N,110–105W.

**Verified legitimate listed access links:**

- [Data-package landing page](https://data-package.ceh.ac.uk/data/e4fe2ebe-b207-47d5-8c77-9873afc63da9) returnsHTTP200 and directly links the [whole ZIP](https://data-package.ceh.ac.uk/data/e4fe2ebe-b207-47d5-8c77-9873afc63da9.zip).
- [Supporting-document ZIP](https://data-package.ceh.ac.uk/sd/e4fe2ebe-b207-47d5-8c77-9873afc63da9.zip) is17,498bytes. Its inspected contents are `readme.html`, `ro-crate-metadata.json`, and `supporting-documents/adcp_metadata.rtf` only. No observation CSV was downloaded or opened by this audit.
- Main ZIP HEAD omits content length; both ZIP endpoints ignore byte ranges and returnHTTP200. Range probes aborted without reading bodies. **Main compressed size is not verified.** Parent will cap whole-package acquisition at64MiB, seal it, and inspect only the ZIP directory first. Supporting RO-Crate lists50CSV files totaling949,009 uncompressed bytes, largest37,524bytes, with per-file SHA256. This makes a small download plausible without falsely asserting an exact compressed size.

The RTF defines five columns, in this order; it does not establish the actual CSV header-row convention:

| Column | Definition | Units |
|---|---|---|
|1|Measurement location UTM Easting|m|
|2|Measurement location UTM Northing|m|
|3|Water depth|m|
|4|Depth-averaged velocity component in Easting direction|m/s|
|5|Depth-averaged velocity component in Northing direction|m/s|

The stated M9 accuracy is±1cm/s; this is a source specification, not independent certification. The document does not establish grid-north versus true-north treatment, compass calibration uncertainty or all positioning residuals. Do not equate reported coordinate decimals with measured spatial accuracy.

File names encode year and cross-section ID, `adcp_YYYY_xsN.csv`. Supporting-document dates are:

|Files|Collection date|
|---|---|
|2015 xs1–8|28August2015|
|2015 xs9–18|29August2015|
|2015 xs19–24|31August2015|
|2016 xs1–6|12September2016|
|2016 xs7–12|10September2016|
|2016 xs13–20|14September2016|
|2017 xs1–6|8June2017|

No independent cross-section-line geometry file is listed. Coordinates accompany the measurement locations; after protocol freeze, a geometry-only reader can use the first two columns while withholding depth/velocity components. Do not orient cross-sections or pick downstream from held velocity values. Transect IDs and repeated years are not independent basins.

**CRS gate:** the ADCP catalog saysWGS84/EPSG4326, whereas its RTF explicitly describes UTM metre columns and omits zone/datum. Companion [orthomosaic metadata](https://catalogue.ceh.ac.uk/documents/7473d4f9-c9a7-40ad-9f58-e58e25997fc5) and [DSM metadata](https://catalogue.ceh.ac.uk/documents/13695138-227f-4d85-9049-0a9cba9e1867), from the same grant, years and river study, explicitly identify WGS84/UTM13N. **EPSG32613 is a companion-supported inference, not an explicit ADCP declaration.** Declare it before opening observations; check transformed coordinate-only bounds against source envelopes, and preserve a blocked outcome if the match fails. Do not choose a projection based on directional agreement. No companion raster pixels were accessed; simulated-flow sibling datasets are not observational truth.

Example published identities from supporting RO-Crate, without inspecting contents:

|File|Bytes|SHA256|
|---|---:|---|
|`data/adcp_2015_xs1.csv`|11,810|`04b605707bf57b36a01123d56ebf5c3a32adbcbde7fb6c6da944f9587501c79a`|
|`data/adcp_2016_xs1.csv`|15,572|`662a5066e9998aff32ac8711634d0085d891c6ca5c99fa82301211f477a169cc`|
|`data/adcp_2017_xs1.csv`|37,524|`d79ee6eb87ecec3259e3c959b2baeca2a7a1e10fba8de60631d06de8329387e5`|

These examples are source identities, **not a selection of evaluation transects**. Select year/IDs by a recorded rule before direction inspection. The source supports local observed velocity comparisons under declared support/registration/temporal conditions. A singleD8 direction cannot represent every braid/eddy or establish hydraulic safety.

### Strongest observed candidates: USGS ADCP

**Sacramento near Glenn, DOI [10.5066/P13MZXEQ](https://doi.org/10.5066/P13MZXEQ).** The [USGS release](https://www.usgs.gov/data/thermal-imagery-acquired-uncrewed-aerial-system-uas-and-hydroacoustic-measurements-flow) identifies SonTek M9/ RiverSurveyor Live observations, multiple passes combined by VMT, and one comma-delimited output with `xs`, `x_meters`, `y_meters`, `depth_meters`, `vmag_meters_per_second`, `u_meters_per_second`, `v_meters_per_second`; positions are UTM10/WGS84, velocity components east/north in m/s. Rights are CC0. The [official metadata](https://data.usgs.gov/datacatalog/metadata/USGS.65eb1953d34e14033297db7d.xml) records ADCP collection on6–7 November2023 and thermal imagery on9–10 November, with no formal attribute/positional accuracy tests. Its release envelope is approximately `[-122.0066,39.5200,-121.9910,39.5276]`. An instrument observation is independent of DEM routing, but remains date/location/support specific; cross-section points are not independent rivers.

**Exposure disclosure:** a schema inspection of this XML inadvertently printed its attribute min/max ranges, including aggregate directional-component information. No observation rows, vector features, map images, or raster pixels were opened. Nevertheless Sacramento is **source-metadata-exposed DEVELOPMENT ONLY**, not an unread/blinded control. The exposure was reported to the parent immediately. Do not tune thresholds or select favorable transects from this information. Future schema extraction must allowlist field names/definitions/units and omit ranges, summaries and examples.

**Allegheny, DOI [10.5066/P14PDEE4](https://doi.org/10.5066/P14PDEE4).** The [USGS release](https://www.usgs.gov/data/river-depth-water-velocity-and-direction-three-locations-collected-2021-and-2022-allegheny) describes SonTek M9 observations processed with QREV at three focal areas on three dates in2021–2022, station/date-organized ZIPs containing Excel location/depth/velocity/direction outputs, and CC0 rights. Direction rows and attribute ranges were not read. The [catalog metadata](https://data.usgs.gov/datacatalog/data/USGS%3A67a3680cd34e91a4ffc730d4) establishes public access but does not verify per-file schema/CRS/size. These must be checked from individual metadata before acquisition.

**Access result for both:** ordinary ScienceBase item/JSON URLs returned HTTP403 from web access and an authorized local network read. The corresponding official catalog XML was accessible but its distribution links point back to the DOI, not verified individual attachments. No mirror, credential workaround, guessed file URL or bulk download was used. File sizes and actual download URLs remain **BLOCKED**, so neither is an acquired validation reference. A user-provided official attachment/export or a legitimately accessible attachment listing can close the gate.

An additional [USGS Wabash ADCP release](https://www.usgs.gov/data/spatial-distribution-depth-averaged-velocity-measured-wabash-river-near-west-lafayette-june-26), DOI10.5066/F78W3BDQ, describes georeferenced, depth-averaged measured velocities and CC0. It remains a metadata-only reserve prospect, with file schema/access/size unverified; it was not promoted to a benchmark by its title alone.

### Official NHD vector annotation control

The [USGS NHD service](https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer) is publicly queryable, non-proprietary, and reports a service refresh in October2026. Its [large-scale flowline layer6](https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6) advertises bounded queries, max2,000 records, `permanent_identifier`, `fdate`, `resolution`, `flowdir`, feature type/code and geometry. Metadata defines `flowdir=1` as “WithDigitized” and0 as “Uninitialized.” No feature query was made.

The [USGS feature dictionary](https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-feature-classes) defines FlowDir relative to coordinate order; `FDate` is last modification, not observation date. The [metadata-table dictionary](https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-metadata-tables) provides the required lineage chain: feature identifier → `FeatureToMetadata` / `NHDFeatureToMetadata` → `NHDMetadata` process description/date → `NHDSourceCitation` originator, title, source contribution, currentness and scale. Some processes have no source citation. Layer6 does not expose this complete chain in its listed fields/relationships. A small bounded vector query alone therefore does **not** establish per-feature source independence.

**Gate:** acquire the corresponding official HU/source metadata tables or other authoritative source record and document origin/vintage/processing for selected features. Without it, call results an official map-annotation comparison with unverified lineage. Restrict a natural-channel control in advance to eligible StreamRiver records, excluding uninitialized, artificial paths, canals/pipelines, tidal/reversing/bifurcating cases unless explicitly modeled. Freeze location/feature-selection rules before reading directions.

The [NHDPlus HR guide](https://pubs.usgs.gov/publication/sir20255031/full) documents hydroenforced DEM, flow-direction and accumulation products and its inherited NHD metadata relationships. These DEM-derived rasters are **not independent physical truth** for evaluating another DEM route. Curated vector orientation is a different reference type, but cannot be promoted to field-observed direction merely because it is official.

### Regional and engineered sources

- **Nepal:** the [DHM station catalog](https://www.dhm.gov.np/hydology/hydrological-stations) supplies station/river/location/elevation/drainage metadata. Its [data page](https://dhm.gov.np/pages/data) lists request/procurement procedures. Station location or stage/discharge at a site does not, by itself, supply directed interior segments for the pilot ROI. No request, payment or station-direction inference was made.
- **Varanasi:** an [official municipal report filed with the National Green Tribunal](https://www.greentribunal.gov.in/sites/default/files/news_updates/REPORT%20BY%20VARANASI%20MUNICIPAL%20CORPORATION%20IN%20OA%20NO.%20367%20of%202022%20RAJENDRA%20PRASAD%20GUPTA%20VS%20STATE%20OF%20U.P..pdf) describes named-drain flows, tapping/diversion and operational status. This is useful context, but no licensed georeferenced survey with matched interior direction, datum, date and uncertainty was established. Do not convert textual discharge/tapping status into per-reach truth.
- **Delhi engineered case:** the [officially hosted IIT Delhi Drainage Master Plan](https://ifc.delhi.gov.in/sites/default/files/ifc/universal/main_report_dmp_version51.pdf), sections2.3 and3.2, describes GSDL/survey-contractor inputs and substantial data collection/correction problems, including disagreement between flow direction and invert slope. Its existence does not authenticate the exact consumed GSDL From→To feature attributes as observations. The needed source is original surveyed chainage/invert records plus datum/date and documented observed or operating flow conditions; pumping/backwater/covered channels need explicit treatment. No such fresh independently matched records were acquired in this audit.

## Independent outlet asymmetry

A streamgage point is not automatically a basin outlet or an independently known downstream endpoint. A valid anchor needs an authoritative documented upstream/downstream relation or observed receiving-water connection, coordinate method/datum/vintage, and a verified link to the declared analysis domain. Prefer a spatially separate station/receiving-water source, identified before labels, with interior measured velocities withheld for scoring. Do not derive the anchor from the same interior vectors, a MERIT mouth code, reversed NHD geometry, width trend or the baseline DEM route being evaluated.

For Sacramento, [USGS station11389500 metadata](https://waterdata.usgs.gov/nwis/dv?referred_module=sw&site_no=11389500) provides a separately maintained Colusa gage location, with horizontal position interpolated from a map. The [authors' primary study description](https://www.mdpi.com/2073-4441/16/13/1870), section2.1, states the study reach is46km upstream of that gage. That is regional downstream context, **not** a surveyed outlet inside the1km crop; the relation also comes from the velocity study, so a wholly independent outlet-source claim is not established. No point should be silently promoted to a local outlet from distance alone.

### Canadian outlet metadata checked before observed-flow evaluation

The [NRCan National Hydro Network catalog](https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977) provides a separate map source under the Open Government Licence–Canada. The [05HG001 package](https://www.download-telecharger.services.geo.ca/pub/nrcan_rncan/vector/geobase_nhn_rhn/shp_en/05/nhn_rhn_05hg001_shp_en.zip) was verified by metadata-only ranges. Its XML envelope is `[-107.3,51.2,-106.0,52.4]` and covers the observed-flow control. The advertised archive length is 6,811,189 bytes. No flowline geometry or direction records were consumed. The direction field's domain and local outlet linkage remain unverified. A curated map direction would supply a map-assisted input with its own date and lineage.

The [validation report](REPORT.md) records the executed Canadian terrain-versus-observation comparison with zero independently matched outlets, the limits of the inferred ADCP coordinate system and the confirmed source receipts.
