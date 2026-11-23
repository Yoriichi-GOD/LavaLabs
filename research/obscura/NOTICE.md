# Attribution and SI disclosure

LavaLabs Atmospheric Lab is developed by Saishreek Singh for OBSCURA, November 2026.

The regularized HistGradientBoosting parameter recipe and official 54 chip summaries are adapted from Zelzy's **OBSCURA Starter Baseline**, displayed under Apache License 2.0 on Kaggle. Original source: https://www.kaggle.com/code/zelza0/obscura-starter-baseline (audited version 359068856). Changes include independent modular implementation, explicit no-random-row early stopping, nested group-based mixture selection, a second site partition, alternative missing/quality and spatial summaries, strict exports, receipts and regression checks. Do not represent those adapted components as wholly original.

License text: https://www.apache.org/licenses/LICENSE-2.0 . Preserve required attribution and license text when redistributing adapted source. The competition dataset has its own restricted license and is not covered by a code license. No restricted observations are included in this source package.

Scientific references: Varon et al. (2021), https://amt.copernicus.org/articles/14/2771/2021/ ; Cawley and Talbot (2010), https://www.jmlr.org/papers/v11/cawley10a.html ; Copernicus Sentinel-2 L2A data documentation, https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html . These motivate hypotheses and correct interpretation; they do not validate our predictions or establish a new physical retrieval.

OpenAI Codex assisted source implementation, synthetic tests, research synthesis, analysis automation, interface work and documentation. Competition observations retain organizer provenance; no generated training labels or fabricated performance figures were added. Any public visual demonstration must distinguish measured aggregate results from synthetic examples. Earlier LavaLabs volcano branding and prior flood/terrain research retain their own provenance.

Dependencies: NumPy (BSD), pandas (BSD), scikit-learn (BSD), SciPy (BSD), Rasterio (BSD), threadpoolctl (BSD); GDAL follows its own distribution license. Exact runtime versions are recorded by each measured receipt. No pretrained model or external environmental dataset is used by the current recipe.
