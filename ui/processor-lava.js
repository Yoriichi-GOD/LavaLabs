(() => {
  const processor = document.getElementById('flood-processor');
  const response = document.getElementById('flood-response');
  const nav = document.getElementById('flood-views');
  const root = processor.shadowRoot;
  const $ = id => root.getElementById(id);
  const views = ['terrain', 'analysis', 'response', 'flood-evidence'];
  const params = new URLSearchParams(location.search);
  const hosted = document.documentElement.hasAttribute('data-hosted');
  const initial = params.get('view');
  let view = views.includes(initial) ? initial : 'terrain';
  let run = params.get('run');
  let active = !['#cases', '#evidence'].includes(location.hash);
  let preview;
  const responseLink = $('processor-response-link');

  function href(next, id = run) {
    const query = new URLSearchParams();
    if (next !== 'terrain') query.set('view', next);
    if (id) query.set('run', id);
    return location.pathname + (query.size ? '?' + query : '') + '#terrain';
  }

  function render() {
    const terrain = document.getElementById('earth');
    document.body.classList.toggle('flood-subview', active && view !== 'terrain');
    nav.hidden = !active;
    terrain.hidden = !active || view !== 'terrain';
    processor.hidden = !active || !['analysis', 'flood-evidence'].includes(view);
    response.hidden = !active || view !== 'response';
    $('lab').hidden = view !== 'analysis';
    $('evaluation').hidden = view !== 'flood-evidence';
    for (const button of nav.querySelectorAll('button')) {
      button.setAttribute('aria-pressed', String(button.dataset.floodView === view));
    }
    if (!response.hidden) response.loadResponse(run);
    if (!terrain.hidden) window.LavaTerrain?.open(run);
  }

  function open(next, id = run) {
    if (view !== next) {
      document.querySelector('main').scrollTop = 0;
      window.scrollTo(0, 0);
    }
    view = next;
    run = id;
    history.replaceState(null, '', href(view));
    if (!active) window.Lava.show('terrain');
    else render();
    if (id && $('run').value !== id && [...$('run').options].some(option => option.value === id)) {
      $('run').value = id;
      $('run').dispatchEvent(new Event('change'));
    }
  }

  window.LavaFlood = {open};
  nav.addEventListener('click', event => {
    const button = event.target.closest('[data-flood-view]');
    if (button) open(button.dataset.floodView);
  });
  document.getElementById('earth-tab').addEventListener('click', () => open('terrain'));
  document.addEventListener('lavalabs:workspace', ({detail}) => {
    active = detail === 'terrain';
    render();
  });
  document.addEventListener('lavalabs:terrain-selection', ({detail}) => {
    if (!detail || detail === run) return;
    run = detail;
    if ($('run').value !== detail && [...$('run').options].some(option => option.value === detail)) {
      $('run').value = detail;
      $('run').dispatchEvent(new Event('change'));
    }
  });
  document.addEventListener('lavalabs:processed', ({detail}) => {
    if (active && view === 'analysis') open('response', detail);
  });
  document.addEventListener('lavalabs:selection', ({detail}) => {
    run = detail || null;
    preview?.abort();
    $('processor-response').hidden = true;
    responseLink.hidden = true;
  });
  document.addEventListener('lavalabs:run', async ({detail: result}) => {
    preview?.abort();
    run = result.run_id;
    if (active && view !== 'terrain') history.replaceState(null, '', href(view));
    if (active && view === 'response') response.loadResponse(result.synthetic ? null : run);
    if (result.synthetic) return;
    preview = new AbortController();
    const {signal} = preview;
    const status = $('processor-response-status');
    $('processor-response').hidden = false;
    status.textContent = 'Checking the saved run for priority locations…';
    try {
      const api = await fetch('/LavaLabs/api/flood/runs/' + encodeURIComponent(result.run_id) +
        (hosted ? '/response/brief.json' : '/response?brief=true'), {signal});
      if (!api.ok) throw new Error('Response evidence is unavailable for this analysis.');
      const brief = await api.json();
      if (signal.aborted) return;
      status.textContent = brief.lead ? 'First checks include ' + brief.lead + '.' :
        'Review the checks for people, crossings and radar gaps.';
      responseLink.href = href('response', result.run_id);
      responseLink.onclick = event => {
        event.preventDefault();
        // Recompute the response from this run's frozen evidence on demand.
        response.loadResponse(null);
        open('response', result.run_id);
      };
      responseLink.hidden = false;
    } catch (error) {
      if (!signal.aborted) status.textContent = error.message;
    }
  });
  if (active) window.Lava.show('terrain');
  else render();
})();
