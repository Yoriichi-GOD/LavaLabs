/* SI-assisted code: OpenAI Codex. NASA values are retained unchanged. */
'use strict';
const $ = id => document.getElementById(id);
let bundle, manifest, land, originals;
const state = {variable: 'T2M', region: 'delhi', window: 0};
const signed = (value, digits = 2) => `${value > 0 ? '+' : ''}${value.toFixed(digits)}`;
const probability = value => value == null ? 'Unavailable' : value < 0.001 ? '<0.001' : value.toFixed(3);
const normalized = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function parseQuestion(text, regions) {
  const query = normalized(text);
  if (/\b(will|forecast|predict|future|cause|why|because)\b/.test(query)) return {error: 'This demo describes historical trends. It cannot forecast change or identify a cause.'};
  if (/\b(19|20)\d{2}\b/.test(query)) return {error: 'Choose one of the three verified periods using the Period control, then ask again.'};
  const matches = regions.filter(region => query.includes(normalized(region.name)));
  const temperature = /temperatur|warm|cool|hot|heat/.test(query);
  const rain = /rain|wet|dry|precip/.test(query);
  if (matches.length !== 1 || temperature === rain) return {error: 'Name one supported location and either temperature or rainfall. For example: “Is Delhi getting wetter?”'};
  return {region: matches[0].id, variable: temperature ? 'T2M' : 'PRECTOTCORR'};
}

function drawChart(row, metadata) {
  const width = 850, height = 370, left = 65, right = 20, top = 24, bottom = 47;
  const values = row.annual.map(point => point.value);
  const min = Math.min(...values), max = Math.max(...values), padding = (max - min) * 0.12 || 1;
  const low = min - padding, high = max + padding;
  const x = year => left + (year - row.annual[0].year) / (row.annual.at(-1).year - row.annual[0].year) * (width - left - right);
  const y = value => height - bottom - (value - low) / (high - low) * (height - top - bottom);
  let svg = `<title>${metadata.name} near ${row.region.name}</title><desc>Complete annual values and an ordinary least-squares linear fit. Values are ${metadata.aggregation}, in ${metadata.unit}.</desc>`;
  for (let i = 0; i <= 4; i++) {
    const value = low + (high - low) * i / 4, py = y(value);
    svg += `<line class="grid" x1="${left}" x2="${width-right}" y1="${py}" y2="${py}"/><text x="${left-12}" y="${py+4}" text-anchor="end">${value.toFixed(state.variable === 'T2M' ? 1 : 0)}</text>`;
  }
  const first = row.annual[0].year, last = row.annual.at(-1).year;
  const ticks = [first, ...Array.from({length: last - first}, (_, i) => first + i + 1).filter(year => year % 10 === 0 && year < last - 2 && year > first + 2), last];
  for (const year of ticks) svg += `<text x="${x(year)}" y="${height-18}" text-anchor="middle">${year}</text>`;
  const path = points => points.map((point, i) => `${i ? 'L' : 'M'}${x(point.year).toFixed(2)},${y(point.value).toFixed(2)}`).join(' ');
  svg += `<path class="data-line" d="${path(row.annual)}"/>`;
  for (const point of row.annual) svg += `<circle cx="${x(point.year)}" cy="${y(point.value)}" r="2.5"><title>${point.year}: ${point.value.toFixed(2)} ${metadata.unit}</title></circle>`;
  if (row.fit) svg += `<path class="fit-line" d="${path(row.fit)}"/>`;
  $('chart').innerHTML = svg;
}

function drawMap(rows) {
  const project = ([lon, lat]) => [(lon+180)*2, (90-lat)*2];
  let paths = '';
  if (land) for (const feature of land.features) {
    const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    for (const polygon of polygons) paths += `<path class="land" fill-rule="evenodd" d="${polygon.map(ring => ring.map((point, i) => `${i ? 'L' : 'M'}${project(point).map(value => value.toFixed(2)).join(',')}`).join(' ') + ' Z').join(' ')}"/>`;
  }
  let graticule = '';
  for (const lat of [-60,-30,0,30,60]) graticule += `<line class="graticule" x1="0" x2="720" y1="${(90-lat)*2}" y2="${(90-lat)*2}"/>`;
  for (const lon of [-120,-60,0,60,120]) graticule += `<line class="graticule" x1="${(lon+180)*2}" x2="${(lon+180)*2}" y1="0" y2="360"/>`;
  $('map').innerHTML = graticule + paths;
  $('map-buttons').replaceChildren();
  for (const row of rows) {
    const button = document.createElement('button'), color = row.slope_per_decade > 0 ? '#dfaa83' : '#7cc5c0';
    button.className = 'map-point';
    button.style.left = `${(row.region.lon + 180) / 360 * 100}%`;
    button.style.top = `${(90-row.region.lat) / 180 * 100}%`;
    button.style.setProperty('--color', color);
    button.style.setProperty('--fill', row.significant ? color : '#101010');
    button.setAttribute('aria-label', `Inspect ${row.region.name} grid cell`);
    button.setAttribute('aria-pressed', String(row.region.id === state.region));
    button.title = `${row.region.name}: ${signed(row.slope_per_decade)} ${bundle.windows[state.window].variables[state.variable].unit}/decade`;
    button.onclick = () => {state.region = row.region.id; $('region').value = state.region; render();};
    $('map-buttons').append(button);
  }
}

function render() {
  const data = bundle.windows[state.window];
  const metadata = data.variables[state.variable];
  const rows = data.results.filter(row => row.variable === state.variable);
  const row = rows.find(item => item.region.id === state.region);
  const units = `${metadata.unit}/decade`;
  $('chart-title').textContent = `${metadata.name} near ${row.region.name}`;
  $('chart-subtitle').textContent = `${data.start}–${data.end} · ${row.n} complete years · ${metadata.aggregation}`;
  $('chart-note').textContent = `${row.region.lat.toFixed(3)}° latitude, ${row.region.lon.toFixed(3)}° longitude · ${metadata.unit} · Monthly NASA inputs; complete annual aggregation.`;
  drawChart(row, metadata);
  $('finding-copy').textContent = `The fitted ${metadata.name.toLowerCase()} trend near ${row.region.name} is ${signed(row.slope_per_decade)} ${units} over ${data.start}–${data.end}.`;
  const lo = row.ci95_per_decade[0], hi = row.ci95_per_decade[1];
  $('metrics').innerHTML = [
    ['Rate of change', `${signed(row.slope_per_decade)} ${units}`],
    ['95% slope interval¹', `${signed(lo)} to ${signed(hi)}`],
    ['Fitted change', `${signed(row.fitted_change)} ${metadata.unit}`],
    ['Adjusted p · 36 tests', probability(row.p_adjusted)],
    ['Complete annual values', `${row.n} / ${data.end-data.start+1}`]
  ].map(([label,value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('');
  $('verdict').textContent = row.significant ? `Evidence of ${row.slope_per_decade > 0 ? 'an increasing' : 'a decreasing'} trend under the stated model and correction.` : 'Insufficient evidence after correction. This does not establish no change.';
  $('verdict').style.color = row.significant ? 'var(--gold)' : 'var(--muted)';
  $('chart-note').textContent += ' ¹ Interval is before multiple-test correction.';
  $('slope-heading').textContent = `${metadata.unit} / decade`;
  $('comparison-body').innerHTML = rows.map(item => `<tr class="${item.region.id === state.region ? 'selected' : ''}"><td><button data-region="${item.region.id}"><span class="direction" style="--color:${item.slope_per_decade > 0 ? 'var(--up)' : 'var(--down)'}"></span>${item.region.name}</button></td><td class="${item.slope_per_decade > 0 ? 'up' : 'down'}">${signed(item.slope_per_decade)}</td><td>${probability(item.p_adjusted)}</td></tr>`).join('');
  for (const button of $('comparison-body').querySelectorAll('button')) button.onclick = () => {state.region=button.dataset.region; $('region').value=state.region; render();};
  drawMap(rows);
  const source = manifest.entries.find(entry => entry.region.id === state.region);
  $('source-detail').textContent = `Retrieved ${source.retrieved_utc.slice(0,10)} (UTC) · POWER API ${source.header.api.version} · 504 monthly records per variable for the full snapshot. Source SHA-256: ${source.sha256.slice(0,16)}…`;
  $('live-source').href = row.source_url;
  $('raw-source').href = `/trends-data/data/sources/${source.file}`;
  const exportBase = `/api/lava/trends/${state.region}/${state.variable}/${state.window}`;
  const hosted = document.documentElement.hasAttribute('data-hosted');
  $('csv').href = `${exportBase}/${hosted ? 'annual.csv' : 'csv'}`;
  $('receipt').href = `${exportBase}/${hosted ? 'annual.json' : 'json'}`;
  $('status').textContent = '';
}

function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const anchor = document.createElement('a'); anchor.href=url; anchor.download=filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function load() {
  try {
    const embedded = document.getElementById('frozen-data');
    if (embedded) {
      ({bundle,manifest,land,originals} = JSON.parse(embedded.textContent));
    } else {
      const responses = await Promise.all(['data/analysis.json','data/manifest.json','land.geojson'].map(path => fetch('/trends-data/'+path)));
      for (const response of responses) if (!response.ok) throw new Error(`A retained data file could not load (${response.status}).`);
      [bundle,manifest,land] = await Promise.all(responses.map(response => response.json()));
    }
    for (const [id,key] of [['variable','variable'],['region','region'],['window','window']]) $(id).addEventListener('change', event => {state[key] = key === 'window' ? Number(event.target.value) : event.target.value; render();});
    $('question-form').addEventListener('submit', event => {
      event.preventDefault();
      const parsed = parseQuestion($('question').value, bundle.windows[0].results.filter(row => row.variable === 'T2M').map(row => row.region));
      $('question-help').textContent = parsed.error || 'Matched a supported historical trend. The controls show exactly what was analyzed.';
      if (parsed.error) return;
      state.region=parsed.region; state.variable=parsed.variable; $('region').value=state.region; $('variable').value=state.variable; render();
    });
    if (originals) {
      $('raw-source').onclick = event => {event.preventDefault(); download(`${state.region}.json`,originals[state.region],'application/json');};
      document.querySelector('a[href="data/manifest.json"]').onclick = event => {event.preventDefault(); download('manifest.json',JSON.stringify(manifest,null,2),'application/json');};
    }
    $('workspace').hidden=false;
    render();
  } catch (error) {
    $('status').textContent = `The retained data could not load. Serve this folder over HTTP and reload. ${error.message}`;
    for (const element of document.querySelectorAll('.controls select,.question-form button')) element.disabled=true;
  }
}

if (typeof document !== 'undefined') load();
if (typeof module !== 'undefined') module.exports = {parseQuestion, probability};
