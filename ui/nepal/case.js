/* SI-assisted implementation. Calculations and source identities are frozen by build_nepal_case.py. */
(() => {
  const $ = id => document.getElementById(id);
  const set = (id, value) => { $(id).textContent = value; };
  const fmt = (n, digits = 2) => n.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const signed = (n, digits) => `${n < 0 ? '−' : '+'}${fmt(Math.abs(n), digits)}`;
  const probability = n => n < .0001 ? n.toExponential(2) : n.toFixed(4);
  const coords = ({ lat, lon }) => `${lat.toFixed(2)}° N, ${lon.toFixed(3)}° E`;
  const params = new URLSearchParams(location.search);
  let data, cell, variable = params.get('variable') === 'PRECTOTCORR' ? 'PRECTOTCORR' : 'T2M';
  const element = (tag, value) => Object.assign(document.createElement(tag), { textContent: value });
  const svg = (tag, attributes, value) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, item] of Object.entries(attributes)) node.setAttribute(key, item);
    if (value !== undefined) node.textContent = value;
    return node;
  };
  const digits = () => variable === 'T2M' ? 3 : 1;
  const unit = () => variable === 'T2M' ? '°C' : 'mm';
  const annualUnit = () => variable === 'T2M' ? '°C' : 'mm/year';
  const slope = n => `${signed(n, digits())} ${unit()}/decade`;

  function facts(id, pairs) {
    $(id).replaceChildren(...pairs.map(([key, value]) => {
      const row = element('div', '');
      row.append(element('dt', key), element('dd', value));
      return row;
    }));
  }

  function table(id, columns, rows, caption) {
    const table = element('table', '');
    if (caption) table.append(element('caption', caption));
    const head = table.createTHead().insertRow();
    for (const label of columns) {
      const column = element('th', label);
      column.scope = 'col';
      head.append(column);
    }
    const body = table.createTBody();
    for (const row of rows) {
      const tr = body.insertRow();
      for (const value of row) tr.insertCell().textContent = value;
    }
    $(id).replaceChildren(table);
  }

  function drawGrid() {
    const climate = data.climate;
    const grid = $('nepal-grid');
    const oldFocus = grid.contains(document.activeElement) ? document.activeElement.dataset.cell : null;
    const rows = [...new Set(climate.cells.map(record => record.lat))];
    const columns = [...new Set(climate.cells.map(record => record.lon))];
    const label = text => { const axis = element('span', text); axis.className = 'grid-axis'; return axis; };
    grid.replaceChildren(label('N / E'), ...columns.map(lon => label(`${lon}° E`)));
    for (const lat of rows) {
      grid.append(label(`${lat}° N`));
      for (const record of climate.cells.filter(point => point.lat === lat)) {
        const row = record.trends[variable];
        const site = record.id === climate.site.matching_cell;
        const ok = row.status === 'ok';
        const sign = ok && row.slope_per_decade < 0 ? 'colder' : ok && row.slope_per_decade > 0 ? 'warmer' : '';
        const button = element('button', '');
        button.type = 'button';
        button.className = `cell ${sign}`;
        button.dataset.cell = record.id;
        button.setAttribute('aria-pressed', String(record.id === cell.id));
        button.setAttribute('aria-label', `${coords(record)}${site ? ', Syapru match' : ''}. ${ok ? `${slope(row.slope_per_decade)}, ${row.significant ? 'significant' : 'inconclusive'}` : 'Trend unavailable'}`);
        const reading = element('span', ok ? `${sign === 'colder' ? '↓' : sign === 'warmer' ? '↑' : ''} ${signed(row.slope_per_decade, digits())}` : '—');
        reading.className = 'value';
        const flags = element('span', [ok && row.significant ? '●' : '', site ? '◎' : ''].join(' ').trim());
        flags.className = 'flags';
        flags.setAttribute('aria-hidden', 'true');
        button.append(reading, flags);
        button.addEventListener('click', () => { cell = record; render(); });
        grid.append(button);
      }
    }
    const fitted = climate.cells.map(item => item.trends[variable]).filter(row => row.status === 'ok');
    const significant = fitted.filter(row => row.significant).length;
    const falling = fitted.filter(row => row.slope_per_decade < 0).length;
    const rising = fitted.filter(row => row.slope_per_decade > 0).length;
    set('regional-summary', `${rising} rising, ${falling} falling${fitted.length !== climate.cells.length ? `, ${climate.cells.length - fitted.length} unavailable` : ''}. ${significant} of ${climate.cells.length} clear the adjusted threshold. Values are ${unit()} per decade.`);
    if (oldFocus) grid.querySelector(`[data-cell="${oldFocus}"]`)?.focus({ preventScroll: true });
  }

  function drawChart(row) {
    const chart = $('annual-chart');
    chart.replaceChildren();
    if (!row.annual.length) {
      chart.append(svg('text', { x: 58, y: 94 }, 'No complete annual values'));
      return;
    }
    const points = row.annual;
    const values = [...points, ...(row.fit || [])].map(point => point.value);
    const min = Math.min(...values), max = Math.max(...values);
    const pad = (max - min) * .08 || 1;
    const lo = min - pad, hi = max + pad;
    const [start, end] = data.climate.period;
    const x = year => 59 + (year - start) / (end - start) * 486;
    const y = value => 173 - (value - lo) / (hi - lo) * 152;
    const path = sequence => sequence.map((point, index) => {
      const contiguous = index && point.year === sequence[index - 1].year + 1;
      return `${contiguous ? 'L' : 'M'}${x(point.year).toFixed(2)} ${y(point.value).toFixed(2)}`;
    }).join(' ');
    chart.setAttribute('aria-label', `Annual ${variable === 'T2M' ? 'temperature' : 'precipitation'} at ${coords(cell)}, ${start} to ${end}, units ${annualUnit()}`);
    chart.append(svg('text', { x: 59, y: 13 }, annualUnit()));
    for (let tick = 0; tick <= 4; ++tick) {
      const value = lo + (hi - lo) * tick / 4;
      const h = y(value);
      chart.append(svg('line', { x1: 59, y1: h, x2: 545, y2: h, class: 'chart-grid' }),
        svg('text', { x: 53, y: h + 4, 'text-anchor': 'end' }, fmt(value, variable === 'T2M' ? 1 : 0)));
    }
    for (const year of [start, 1994, 2004, 2014, end]) chart.append(svg('text', { x: x(year), y: 195, 'text-anchor': 'middle' }, year));
    chart.append(svg('path', { d: path(points), class: 'observed', fill: 'none' }));
    if (row.fit) chart.append(svg('path', { d: path(row.fit), class: 'fitted', fill: 'none' }));
  }

  function updateDownloads() {
    const url = `/LavaLabs/api/lava/nepal/${cell.id}/${variable}`;
    const hosted = document.documentElement.hasAttribute('data-hosted');
    $('annual-download').href = `${url}/${hosted ? 'annual.csv' : 'csv'}`;
    $('receipt-download').href = `${url}/${hosted ? 'annual.json' : 'json'}`;
    $('raw-download').href = `/LavaLabs/ui/nepal/data/${data.climate.sources[variable].file}`;
    $('diagnostic-download').href = `${url}/${hosted ? 'diagnostics.csv' : 'diagnostics'}`;
  }

  function drawDiagnostic() {
    const check = cell.trends[variable].seasonal_check;
    const chart = $('diagnostic-chart');
    chart.replaceChildren();
    $('diagnostic-stats').replaceChildren();
    $('diagnostic-download').hidden = check?.status !== 'ok';
    if (check?.status !== 'ok') {
      set('diagnostic-reading', check?.reason || 'This saved case predates the seasonal diagnostic.');
      return;
    }
    const seasonal = $('diagnostic-view').value === 'seasonal';
    const series = seasonal ? check.climatology : check.annual.flatMap(point => [point.value, point.ols_fit, point.robust_fit]);
    const min = Math.min(...series), max = Math.max(...series), padding = (max - min) * .1 || 1;
    const low = min - padding, high = max + padding;
    const rows = seasonal ? check.climatology.map((value, i) => ({x: i, value})) : check.annual.map(point => ({...point, x: point.year}));
    const first = rows[0].x, last = rows[rows.length - 1].x;
    const x = value => 59 + (value - first) / (last - first) * 486;
    const y = value => 173 - (value - low) / (high - low) * 152;
    const path = key => rows.map((point, i) => `${i ? 'L' : 'M'}${x(point.x).toFixed(2)} ${y(point[key]).toFixed(2)}`).join(' ');
    chart.append(svg('text', {x: 59, y: 13}, seasonal ? check.monthly_unit : check.annual_unit + ' departure'));
    for (let index = 0; index <= 4; index++) {
      const value = low + (high - low) * index / 4, h = y(value);
      chart.append(svg('line', {x1: 59, y1: h, x2: 545, y2: h, class: 'chart-grid'}),
        svg('text', {x: 53, y: h + 4, 'text-anchor': 'end'}, fmt(value, variable === 'T2M' ? 1 : 0)));
    }
    const tickValues = seasonal ? [0, 2, 4, 6, 8, 10] : [1984, 1994, 2004, 2014, 2025];
    for (const value of tickValues) chart.append(svg('text', {x: x(value), y: 195, 'text-anchor': 'middle'},
      seasonal ? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][value] : value));
    chart.append(svg('path', {d: path('value'), class: 'observed', fill: 'none'}));
    if (!seasonal) for (const [key, className] of [['ols_fit', 'fitted'], ['robust_fit', 'robust-fit']]) {
      chart.append(svg('path', {d: path(key), class: className, fill: 'none'}));
    }
    $('diagnostic-key').hidden = seasonal;
    chart.setAttribute('aria-label', seasonal ? `Calendar-month climatology at ${coords(cell)}, ${check.monthly_unit}`
      : `Annual departures with ordinary and robust fitted trends at ${coords(cell)}`);
    const difference = Math.abs(check.slope_difference_per_decade);
    const units = variable === 'T2M' ? '°C' : 'mm';
    set('diagnostic-reading', seasonal
      ? 'Each point averages the same calendar month over 1984–2025. Rainfall values are monthly totals.'
      : `The robust and ordinary fits ${check.same_direction ? 'agree on the trend direction' : 'give different trend directions'}. Their slopes differ by ${fmt(difference, digits())} ${units}/decade. The primary significance result is shown above.`);
    facts('diagnostic-stats', [
      ['OLS on yearly departures', slope(check.ols_slope_per_decade)],
      ['Robust fit on yearly departures', slope(check.robust_slope_per_decade)],
      ['Years with fit weight below 0.5', check.downweighted_years.join(', ') || 'None'],
    ]);
  }

  function render() {
    const row = cell.trends[variable];
    const atSite = cell.id === data.climate.site.matching_cell;
    const ok = row.status === 'ok';
    set('cell-title', `${coords(cell)} · ${atSite ? 'Matched to Syapru Besi' : 'Model grid centre'}`);
    set('cell-slope', ok ? slope(row.slope_per_decade) : 'Trend unavailable');
    set('verdict', ok ? (row.significant ? 'Significant in this test' : 'Inconclusive after correction') : 'Insufficient evidence');
    $('verdict').classList.toggle('supported', ok && row.significant);
    set('cell-reading', ok ? (row.significant ? 'This cell clears the adjusted threshold for the specified period and method.' : 'The fitted slope shows a direction. This test leaves the evidence for a trend inconclusive.') : row.reason);
    facts('trend-stats', [
      ['95% slope interval (marginal)', ok ? `${row.ci95_per_decade.map(n => signed(n, digits())).join(' to ')} ${unit()}/decade` : 'Unavailable'],
      ['Holm-adjusted p-value', ok ? probability(row.p_adjusted) : 'Unavailable'],
      ['Complete years', `${row.annual.length} of 42`]
    ]);
    if (ok) {
      table('sensitivity', ['HAC lag', 'Marginal 95% slope interval', 'Adjusted p'], Object.entries(row.hac_sensitivity).map(([lag, item]) => [
        lag === '3' ? '3 (primary)' : lag, item.ci95_per_decade.map(n => signed(n, digits())).join(' to ') + ` ${unit()}/decade`, probability(item.p_adjusted)
      ]));
      $('sensitivity').append(element('p', 'Each lag is corrected over the same 30 comparisons. The lag 3 result defines the primary verdict.'));
    } else set('sensitivity', row.reason);
    table('subperiods', ['Period', 'Descriptive slope'], row.descriptive_subperiods.map(item => [
      item.period.join('–'), item.slope_per_decade === null ? 'Unavailable' : slope(item.slope_per_decade)
    ]));
    $('subperiods').append(element('p', 'These fits describe the two fixed halves. The primary test covers the full record. A change in slope between the halves would require its own test.'));
    drawGrid();
    drawChart(row);
    drawDiagnostic();
    updateDownloads();
    const url = new URL(location.href);
    url.searchParams.set('cell', cell.id);
    url.searchParams.set('variable', variable);
    history.replaceState(null, '', url);
  }

  function eventEvidence() {
    const event = data.event;
    const metrics = event.metrics;
    const show = index => {
      const scene = event.sar[index];
      $('radar-image').src = `/LavaLabs/ui/nepal/data/${scene.file}`;
      $('radar-image').alt = `${index === 0 ? 'Before' : 'After'} event Sentinel-1 radar preview`;
      set('radar-caption', `Sentinel-1D · ${scene.date} · saved radar preview`);
      $('before-button').setAttribute('aria-pressed', String(index === 0));
      $('after-button').setAttribute('aria-pressed', String(index === 1));
    };
    $('before-button').addEventListener('click', () => show(0));
    $('after-button').addEventListener('click', () => show(1));
    show(1);
    facts('event-stats', [
      ['New-water candidates', `${fmt(metrics.new_water_m2 / 10000)} ha (${fmt(metrics.new_water_pixels, 0)} pixels)`],
      ['Valid radar grid', `${fmt(metrics.valid_pixels / metrics.total_pixels * 100, 1)}% (${fmt(metrics.valid_pixels, 0)} of ${fmt(metrics.total_pixels, 0)})`],
      ['Candidate intersections', `${metrics.exposed_buildings} mapped buildings · ${fmt(metrics.exposed_road_m, 1)} m of roads`],
      ['Road access', event.connectivity_status]
    ]);
    set('event-boundary', event.interpretation);
    const labels = { eroded_1px: 'Erode by 1 pixel', original: 'Original mask', dilated_1px: 'Dilate by 1 pixel' };
    table('event-sensitivity', ['Candidate mask', 'Mapped buildings', 'Road overlap (m)'], Object.entries(event.mask_sensitivity).map(([key, row]) => [labels[key], row.exposed_buildings, fmt(row.exposed_road_m, 1)]));
    $('event-sensitivity').append(element('p', 'This is a mask sensitivity check. The change in overlap shows how strongly the result depends on the candidate boundary.'));
    for (const optical of event.optical_coverage) $('event-sensitivity').append(element('p', `Sentinel-2 ${optical.date}: ${fmt(optical.clear_pixels / optical.total_grid_pixels * 100, 1)}% clear on the retained grid.`));
  }

  async function start() {
    try {
      const response = await fetch('/LavaLabs/ui/nepal/data/case.json');
      if (!response.ok) throw new Error('Case evidence could not be loaded.');
      data = await response.json();
      if (data.schema !== 1 || data.climate.cells.length !== 15 || data.climate.method.tests_per_family !== 30) throw new Error('The retained case is incomplete.');
      const match = data.climate.cells.find(row => row.id === data.climate.site.matching_cell);
      cell = data.climate.cells.find(row => row.id === params.get('cell')) || match;
      $('case-variable').value = variable;
      $('case-variable').addEventListener('change', event => { variable = event.target.value; render(); });
      $('select-site').addEventListener('click', () => { cell = match; render(); });
      $('diagnostic-view').addEventListener('change', drawDiagnostic);
      const [lon, lat] = data.climate.site.requested_lon_lat;
      set('site-match', `Requested location ${lat}° N, ${lon}° E. Both 504-month point series exactly match the regional series at ${coords(match)}. The model grid is 0.5° × 0.625°. This checks cell identity within the same product.`);
      set('trend-method', [data.climate.method.fit, data.climate.method.multiple_testing, data.climate.method.coverage, data.climate.method.scope].join(' '));
      render();
      eventEvidence();
      $('case-status').hidden = true;
      $('case-content').hidden = false;
      if (['#regional', '#event', '#audit'].includes(location.hash)) document.getElementById(location.hash.slice(1)).scrollIntoView();
    } catch (error) {
      set('case-status', `Evidence unavailable. ${error.message}`);
    }
  }
  start();
})();
