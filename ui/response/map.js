(() => {
  const host = document.getElementById('flood-response')
  const root = host?.shadowRoot || document
  const $ = id => root.getElementById(id)
  const svgNS = 'http://www.w3.org/2000/svg'
  const responseUrl = id => '/LavaLabs/?view=response&run=' + encodeURIComponent(id) + '#terrain'
  const states = {candidate: 'Candidate at point', nearby: 'Near a candidate', no_contact: 'No candidate nearby', unobserved: 'Radar gap', outside: 'Outside scene'}
  const titles = ['Check people first', 'Verify crossings and roads', 'Recheck when warnings change']
  const artifactLabels = {'result.json': 'Run calculations', 'manifest.json': 'Run source manifest', 'prediction.tif': 'Radar candidate raster', 'layers.geojson': 'Historical map layers', 'exposure.csv': 'Water intersections', 'connectivity.json': 'Historical access scenarios', 'topology-audit.json': 'Road and settlement audit'}
  const controls = new Map()
  let data, selected, run, pending, optical, zoom = 1

  function html(tag, content, parent, attrs = {}) {
    const el = document.createElement(tag)
    el.textContent = content
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value)
    parent.append(el)
    return el
  }

  function svg(tag, attributes, parent) {
    const el = document.createElementNS(svgNS, tag)
    for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, value)
    parent.append(el)
    return el
  }

  function shortEvidence(site) {
    const e = site.evidence
    if (site.kind === 'gap') return 'Unobserved patch'
    if (e.overlap !== undefined) return e.overlap.toFixed(1) + (e.unit === 'm2' ? ' m² overlap' : ' m overlap')
    if (e.state === 'nearby') return e.distance_m.toFixed(0) + ' m to candidate'
    return states[e.state]
  }

  function osmLink(id) {
    if (/^(node|way|relation)\/\d+$/.test(id)) return 'https://www.openstreetmap.org/' + id
    return null
  }

  function paintSelection() {
    const detail = $('pin-detail')
    detail.replaceChildren()
    if (!selected) {
      html('p', 'This run has no map locations for the ranked checks.', detail)
      return
    }
    root.querySelectorAll('[data-site]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.site === selected.id)))
    html('strong', 'P' + selected.priority + ' · ' + selected.name, detail, {class: 'p' + selected.priority})
    html('p', selected.detail, detail)
    const [lon, lat] = selected.lonlat
    html('p', lat.toFixed(5) + '°, ' + lon.toFixed(5) + '° · ' + selected.evidence.source, detail)
    const url = osmLink(selected.id)
    if (url) html('a', 'OSM ' + selected.id, detail, {href: url})
  }

  function saveZoom(next) {
    zoom = Math.max(1, Math.min(5, next))
    const centre = selected && zoom > 1 ? controls.get(selected.id) : [325, 260]
    const width = 650 / zoom, height = 520 / zoom
    $('response-svg').setAttribute('viewBox', [centre[0] - width / 2, centre[1] - height / 2, width, height].join(' '))
    for (const pin of $('pin-layer').children) {
      const [x, y] = controls.get(pin.dataset.site)
      pin.setAttribute('transform', 'translate(' + x + ',' + y + ') scale(' + 1 / zoom + ')')
    }
    $('map-plus').disabled = zoom === 5
    $('map-minus').disabled = zoom === 1
    $('map-fit').disabled = zoom === 1
  }

  function select(site) {
    selected = site
    saveZoom(zoom)
    paintSelection()
  }

  function renderMap() {
    const [west, south, east, north] = data.map.bounds
    const unit = Math.min(590 / (east - west), 475 / (north - south))
    const width = (east - west) * unit, height = (north - south) * unit
    const left = (650 - width) / 2, top = (520 - height) / 2
    const at = ([x, y]) => [left + (x - west) * unit, top + (north - y) * unit]
    const size = {x: left, y: top, width, height, preserveAspectRatio: 'none'}
    svg('image', {...size, id: 'radar-basemap', href: 'data:image/png;base64,' + data.map.png}, $('raster-layer'))
    if (optical) {
      const image = svg('image', {...size, id: 'optical-basemap', hidden: ''}, $('raster-layer'))
      svg('image', {...size, id: 'optical-overlay', hidden: '', href: 'data:image/png;base64,' + data.map.overlay}, $('raster-layer'))
      image.addEventListener('load', () => {
        if (!image.isConnected) return
        $('map-optical').disabled = false
        $('optical-state').textContent = 'Sentinel-2 RGB · ' + optical.date
      })
      image.addEventListener('error', () => {
        if (!image.isConnected) return
        $('map-optical').disabled = true
        $('optical-state').textContent = 'RGB could not load for this run'
      })
      image.setAttribute('href', optical.url)
    }
    svg('rect', {x: left, y: top, width, height, fill: 'none', stroke: '#62646d'}, $('raster-layer'))
    data.map.roads.forEach(road => svg('polyline', {
      points: road.xy.map(xy => at(xy).map(v => v.toFixed(2)).join(',')).join(' '),
      class: road.check ? 'road road-check' : 'road',
    }, $('road-layer')))
    const points = data.priorities.flatMap(priority => priority.sites)
    for (const site of [...points].reverse()) {
      const [x, y] = at(site.xy)
      controls.set(site.id, [x, y])
      const group = svg('g', {class: 'map-pin p' + site.priority, transform: 'translate(' + x + ',' + y + ')',
        'data-site': site.id, 'aria-label': 'Priority ' + site.priority + ', ' + site.name + ', ' + shortEvidence(site),
        'aria-pressed': 'false', tabindex: '0', role: 'button'}, $('pin-layer'))
      svg('circle', {cx: 0, cy: 0, r: 12}, group)
      svg('circle', {cx: 0, cy: 0, r: 15}, group)
      svg('text', {'text-anchor': 'middle', y: 5}, group).textContent = site.priority
      group.addEventListener('click', () => select(site))
      group.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return
        event.preventDefault()
        select(site)
      })
    }
    $('map-plus').onclick = () => saveZoom(zoom + 1)
    $('map-minus').onclick = () => saveZoom(zoom - 1)
    $('map-fit').onclick = () => saveZoom(1)
    selected = points[0]
    saveZoom(1)
  }

  function renderPriorities() {
    const makeSite = (site, container) => {
      const button = html('button', '', container, {class: 'site', type: 'button', 'data-site': site.id, 'aria-pressed': 'false'})
      html('b', site.name, button)
      html('small', shortEvidence(site), button)
      button.addEventListener('click', () => select(site))
    }
    for (const priority of data.priorities) {
      const section = html('section', '', $('priority-list'), {class: 'priority'})
      const heading = html('h3', '', section)
      html('span', 'P' + priority.level, heading, {class: 'badge p' + priority.level})
      html('span', titles[priority.level - 1], heading)
      html('p', priority.action, section)
      const primary = html('div', '', section, {class: 'sites'})
      const visible = priority.level === 1 ? 5 : 4
      priority.sites.slice(0, visible).forEach(site => makeSite(site, primary))
      if (priority.sites.length > visible) {
        const more = html('details', '', section, {class: 'more-sites'})
        html('summary', 'Show ' + (priority.sites.length - visible) + ' more map checks', more)
        const additional = html('div', '', more, {class: 'sites'})
        priority.sites.slice(visible).forEach(site => makeSite(site, additional))
      }
      if (priority.more) html('p', priority.more + ' additional features in the saved evidence table.', section)
    }
  }

  function renderAccess() {
    const parent = $('access-result')
    if (data.access.length && data.access.every(row => row.status === 'unknown_no_hubs')) {
      html('p', 'Access unknown. The historical network contains no destination hubs in this run. Escalate access checks before allocating transport.', parent)
    } else if (!data.access.length) {
      html('p', 'This run has no linked settlement access records. Request a road and destination check.', parent)
    } else {
      const list = html('ul', '', parent)
      for (const row of data.access) {
        const item = html('li', '', list)
        html('strong', row.name + ' · ', item)
        let message
        if (row.before === true && row.optimistic === false && row.conservative === false) {
          message = 'No route remained inside the modeled network under either disruption scenario.'
          if (row.hub_name) message += ' The modeled pre-event destination was ' + row.hub_name + '.'
        } else if (row.optimistic === true && row.conservative === true) {
          message = 'The historical model retained connectivity under both scenarios. Verify current conditions.'
        } else if (row.optimistic !== row.conservative && row.optimistic !== null && row.conservative !== null) {
          message = 'Access depended on the disruption assumptions in this model.'
        } else {
          message = row.status === 'unknown_off_network' ? 'The settlement could not be linked to a road node.' : 'Available observations leave access unresolved.'
        }
        if (row.boundary_truncated) message += ' The network stops at the study boundary. Real access remains unknown.'
        html('span', message, item)
      }
    }
    if (data.care.length) {
      html('h3', 'Facilities to verify', $('care-list'))
      const list = html('ul', '', $('care-list'))
      for (const site of data.care) {
        const item = html('li', '', list)
        const url = osmLink(site.id)
        if (url) html('a', site.name, item, {href: url})
        else html('span', site.name, item)
        html('span', ' · ' + states[site.state], item)
      }
      html('p', 'Historical directory entries. Verify operating status, receiving capacity and access.', $('care-list'))
    }
    if (data.nearby_run) {
      const link = $('related-run')
      link.href = responseUrl(data.nearby_run)
      link.textContent = data.nearby_run === 'nepal-syapru-004' ? 'Review wider Nepal access and mapped care sites →' : 'Review the narrower Syapru Besi footprint →'
      link.hidden = false
      link.onclick = event => {
        if (window.LavaFlood) {
          event.preventDefault()
          window.LavaFlood.open('response', data.nearby_run)
        }
      }
    }
  }

  function renderCoverage() {
    const observed = (100 * data.coverage.valid_pixels / data.coverage.total_pixels).toFixed(1)
    $('coverage-text').textContent = observed + '% of the raster had paired observations. Check grey gaps with ground reports.'
    const parent = $('settlements')
    if (!data.settlements.length) {
      html('p', 'No linked settlement points were retained within this raster. Request community locations from local responders.', parent)
    } else {
      const list = html('ul', '', parent)
      const sorted = [...data.settlements].sort((a, b) => (a.distance_m ?? Infinity) - (b.distance_m ?? Infinity))
      for (const site of sorted.slice(0, 12)) html('li', site.name + ' · ' + states[site.state], list)
      if (sorted.length > 12) html('p', 'All ' + sorted.length + ' linked settlements are listed in the brief.', parent)
      if (!sorted.some(site => site.state === 'no_contact')) html('p', 'Every listed point was near a candidate or fell in an unobserved pixel.', parent)
      else html('p', 'No candidate nearby describes the mapped point and available radar coverage. Confirm conditions for the surrounding community.', parent)
    }
    $('official-links').hidden = !data.nepal
  }

  function renderSources() {
    $('method-description').textContent = 'Direct intersections rank first for people and bridges rank first for access. Settlement points within ' + data.contact_radius_m + ' m of a water candidate enter the welfare-check list. This distance is a screening choice. Follow-up gaps have at least nine adjoining unobserved pixels within the same radius by pixel centres.'
    let source = 'OpenStreetMap snapshot ' + (data.osm.snapshot?.slice(0, 10) || 'date unavailable') + '. ' + data.osm.source + '.'
    if (data.osm.source_sha256) source += ' Source SHA-256 ' + data.osm.source_sha256 + '.'
    $('osm-source').textContent = source
    for (const [file, digest] of Object.entries(data.sources)) {
      const row = html('li', '', $('source-links'))
      html('a', artifactLabels[file] || file, row, {href: '/LavaLabs/api/flood/runs/' + encodeURIComponent(run) + '/artifact/' + file})
      html('span', ' · SHA-256 ' + digest, row)
    }
    if (optical) {
      const row = html('li', '', $('source-links'))
      html('a', 'Sentinel-2 RGB · ' + optical.date, row, {href: optical.url})
      html('span', ' · SHA-256 ' + optical.source_sha256 + ' · ' + optical.display, row)
    }
  }

  function changeBasemap(useOptical) {
    $('map-radar').setAttribute('aria-pressed', String(!useOptical))
    $('map-optical').setAttribute('aria-pressed', String(useOptical))
    $('radar-basemap')?.toggleAttribute('hidden', useOptical)
    $('optical-basemap')?.toggleAttribute('hidden', !useOptical)
    $('optical-overlay')?.toggleAttribute('hidden', !useOptical)
    $('paired-water-key').hidden = useOptical
    root.querySelector('.response-map').classList.toggle('optical-map', useOptical)
  }

  async function initialize(id) {
    if (id === run && id) return
    pending?.abort()
    run = id
    $('response-content').hidden = true
    $('map-optical').disabled = true
    $('download-brief').hidden = true
    $('load-status').hidden = false
    $('load-status').textContent = id ? 'Checking saved evidence…' : 'Select a completed flood analysis to see response priorities.'
    if (!id) return
    pending = new AbortController()
    const {signal} = pending
    const base = '/LavaLabs/api/flood/runs/' + encodeURIComponent(id)
    const api = base + '/response'
    try {
      const [response, context] = await Promise.all([
        fetch(api, {signal}),
        fetch(base + '/visual-context', {signal}).then(res => res.ok ? res.json() : null).catch(() => null),
      ])
      const packet = await response.json()
      if (signal.aborted) return
      if (!response.ok) throw new Error(typeof packet.detail === 'string' ? packet.detail : 'Saved response evidence is unavailable.')
      data = packet
      const grid = context?.after?.grid
      optical = context?.optical_available && grid?.crs === data.map.crs &&
        grid.width === data.map.width && grid.height === data.map.height &&
        JSON.stringify(grid.transform) === JSON.stringify(data.map.transform)
        ? context.after : null
      for (const node of ['raster-layer', 'road-layer', 'pin-layer', 'priority-list', 'access-result',
                          'care-list', 'settlements', 'source-links']) $(node).replaceChildren()
      controls.clear()
      $('related-run').hidden = true
      $('map-optical').disabled = true
      $('optical-state').textContent = optical ? 'Loading retained RGB…' : 'No matching optical RGB for this analysis'
      changeBasemap(false)
      const name = id === 'event-fe47db331390' ? 'Syapru Besi, Nepal' : data.event_name.replace(/\s+—.*$/, '')
      $('event-label').textContent = name + ' · ' + data.event_date.slice(0, 10)
      $('observation-dates').textContent = 'Radar pair ' + data.observations.map(value => value.slice(0, 10)).join(' / ')
      $('download-brief').href = api + (document.documentElement.hasAttribute('data-hosted') ? '/brief.json' : '?brief=true')
      $('download-brief').download = 'lavalabs-response-' + id + '.json'
      renderMap()
      renderPriorities()
      paintSelection()
      renderAccess()
      renderCoverage()
      renderSources()
      $('download-brief').hidden = false
      $('response-content').hidden = false
      $('load-status').hidden = true
    } catch (error) {
      if (!signal.aborted) {
        run = undefined
        $('load-status').textContent = error.message
      }
    }
  }

  $('map-radar').onclick = () => changeBasemap(false)
  $('map-optical').onclick = () => changeBasemap(true)
  if (host) host.loadResponse = initialize
  else initialize(new URL(location.href).searchParams.get('run'))
})()
