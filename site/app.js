/* Tucson Sermon Review. Convex is preferred; generated JSON is the offline fallback. */
(function () {
  'use strict';

  const RESULTS = {
    plagiarism: { label: 'Plagiarism evidence', color: '#d94a4a', priority: 5 },
    ai: { label: 'AI-writing signs', color: '#7842ad', priority: 4 },
    concern: { label: 'Attribution concern', color: '#e27b22', priority: 3 },
    clear: { label: 'Reviewed — clear', color: '#2f9469', priority: 2 },
    unreviewed: { label: 'Not reviewed', color: '#8290a3', priority: 1 },
  };
  const RESULT_ORDER = ['plagiarism', 'ai', 'concern', 'clear', 'unreviewed'];
  const REPO = 'https://github.com/gmfennema/church_plagerism';
  const TUCSON = [32.2226, -110.9247];
  const state = {
    data: null,
    churches: [],
    filtered: [],
    activeResults: new Set(RESULT_ORDER),
    query: '',
    selected: null,
    markers: new Map(),
  };

  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
  const fmtDate = (iso) => {
    if (!iso) return '';
    const date = new Date(iso + 'T12:00:00');
    return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  };
  const short = (text, max = 260) => {
    const clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (clean.length <= max) return clean;
    const clipped = clean.slice(0, max);
    return clipped.slice(0, clipped.lastIndexOf(' ')) + '…';
  };
  const activePastors = (church) => {
    const pastors = church.pastors || [];
    return pastors.filter((pastor) => pastor.active !== false).length
      ? pastors.filter((pastor) => pastor.active !== false)
      : pastors;
  };

  function churchResult(church) {
    const pastors = activePastors(church);
    if (!pastors.length) return 'unreviewed';
    const plagiarism = pastors.map((pastor) => pastor.plagiarism?.status || 'unchecked');
    const ai = pastors.map((pastor) => pastor.ai_writing?.status || 'unchecked');

    // One color per church. The first matching rule wins.
    if (plagiarism.includes('flagged')) return 'plagiarism';
    if (ai.includes('flagged')) return 'ai';
    if (plagiarism.includes('inconclusive')) return 'concern';
    if (plagiarism.every((status) => status === 'cleared') && ai.every((status) => status === 'cleared')) return 'clear';
    return 'unreviewed';
  }

  function strongestFinding(church, key) {
    const weight = { flagged: 5, inconclusive: 3, cleared: 2, in_progress: 1, unchecked: 0 };
    return activePastors(church)
      .map((pastor) => ({ pastor, finding: pastor[key] || { status: 'unchecked' } }))
      .sort((a, b) => (weight[b.finding.status] || 0) - (weight[a.finding.status] || 0))[0]
      || { pastor: null, finding: { status: 'unchecked' } };
  }

  // ---------- map ----------
  const map = L.map('map', { zoomControl: true, attributionControl: true }).setView(TUCSON, 11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  const markerLayer = L.layerGroup().addTo(map);

  function markerFor(church) {
    const result = RESULTS[church._result];
    const approximate = church.location.geocode === 'approximate';
    const emphasized = church._result === 'plagiarism' || church._result === 'ai';
    const marker = L.circleMarker([church.location.lat, church.location.lng], {
      radius: emphasized ? 9 : 7.5,
      color: emphasized ? '#ffffff' : '#f9faf7',
      weight: emphasized ? 3 : 2,
      dashArray: approximate ? '3 3' : null,
      fillColor: result.color,
      fillOpacity: .96,
      className: 'marker-pin',
    });
    marker.bindTooltip(
      `<strong>${esc(church.name)}</strong><span>${esc(result.label)}${approximate ? ' · approximate location' : ''}</span>`,
      { direction: 'top', offset: [0, -8] },
    );
    marker.on('click', () => select(church.slug));
    return marker;
  }

  function renderMarkers() {
    markerLayer.clearLayers();
    state.markers.clear();
    state.filtered.filter((church) => church.plotted).forEach((church) => {
      const marker = markerFor(church);
      state.markers.set(church.slug, marker);
      marker.addTo(markerLayer);
    });
  }

  function renderLegend() {
    $('#map-legend').innerHTML = RESULT_ORDER.map((key) => `
      <span class="legend-item"><span class="status-dot result-${key}"></span>${esc(RESULTS[key].label)}</span>
    `).join('');
  }

  // ---------- map filters and list ----------
  function renderFilters() {
    const counts = Object.fromEntries(RESULT_ORDER.map((key) => [key, 0]));
    state.churches.forEach((church) => { counts[church._result] += 1; });
    $('#status-filters').innerHTML = RESULT_ORDER.map((key) => {
      const active = state.activeResults.has(key);
      return `
        <button type="button" class="filter-option result-${key}" data-result="${key}" aria-pressed="${active}">
          <span class="status-dot"></span>
          <span class="label">${esc(RESULTS[key].label)}</span>
          <span class="count">${counts[key]}${active ? ' ✓' : ''}</span>
        </button>`;
    }).join('');
  }

  function applyFilters() {
    const query = state.query.trim().toLowerCase();
    state.filtered = state.churches.filter((church) => {
      if (!state.activeResults.has(church._result)) return false;
      if (!query) return true;
      const haystack = [
        church.name,
        ...(church.aka || []),
        church.denomination,
        church.tradition_label,
        church.location?.address,
        church.location?.city,
        ...activePastors(church).map((pastor) => pastor.name),
      ].join(' ').toLowerCase();
      return haystack.includes(query);
    });
    renderFilters();
    renderList();
    renderMarkers();
  }

  function renderList() {
    const list = $('#church-list');
    const plotted = state.filtered.filter((church) => church.plotted);
    const unplotted = state.filtered.filter((church) => !church.plotted);
    const count = state.filtered.length;
    $('#result-count').textContent = `${count} ${count === 1 ? 'church' : 'churches'}`;
    if (!count) {
      list.innerHTML = $('#tpl-empty').innerHTML;
      return;
    }

    const item = (church) => {
      const result = RESULTS[church._result];
      const place = [church.denomination || church.tradition_label, church.location?.city].filter(Boolean).join(' · ');
      return `
        <li class="item" data-slug="${esc(church.slug)}" tabindex="0" role="button" aria-label="Open ${esc(church.name)}">
          <span class="status-dot result-${church._result}" aria-hidden="true"></span>
          <span>
            <span class="item-name">${esc(church.name)}</span>
            <span class="item-sub">${esc(place)}</span>
            <span class="result-pill result-${church._result}">${esc(result.label)}</span>
          </span>
          <span class="item-arrow" aria-hidden="true">›</span>
        </li>`;
    };
    list.innerHTML = plotted.map(item).join('')
      + (unplotted.length
        ? '<li class="section-label">Location pending</li>' + unplotted.map(item).join('')
        : '');
  }

  // ---------- simple church view ----------
  function plagiarismScale(info) {
    const finding = info.finding;
    const metrics = finding.metrics || {};
    const attributionAbsent = (finding.sources_compared || []).some((source) => source.attributed_in_sermon === false)
      || Number(metrics.sermons_without_source_attribution || 0) > 0;
    const repeatedCount = Number(metrics.sermons_with_matches || finding.sermons_reviewed || 0);
    const maximum = Number(metrics.max_sermon_body_overlap_pct || metrics.max_sermon_coverage_pct || 0);
    let current = null;
    if (finding.status === 'cleared') current = 0;
    if (finding.status === 'inconclusive') current = 1;
    if (finding.status === 'flagged') current = attributionAbsent && (repeatedCount >= 5 || maximum >= 20) ? 3 : 2;
    return {
      current,
      result: current == null ? (finding.status === 'in_progress' ? 'Review underway' : 'Not reviewed') : [
        'No evidence', 'Attribution unclear', 'Repeated overlap', 'Extensive unattributed pattern',
      ][current],
      steps: ['No evidence', 'Attribution unclear', 'Repeated overlap', 'Extensive unattributed pattern'],
      support: plagiarismSupport(info),
    };
  }

  function plagiarismSupport(info) {
    const finding = info.finding;
    const metrics = finding.metrics || {};
    const min = metrics.min_sermon_body_overlap_pct;
    const max = metrics.max_sermon_body_overlap_pct;
    const aggregate = metrics.sermon_body_overlap_pct;
    const sermonCount = Number(finding.sermons_reviewed || metrics.sermons_with_matches || 0);
    const sourceAbsent = Number(metrics.sermons_without_source_attribution || 0);
    if (min != null && max != null && aggregate != null) {
      const whose = info.pastor?.name ? ` by ${info.pastor.name}` : '';
      const attribution = sourceAbsent
        ? ` The source was not named in those ${sourceAbsent} sermons.`
        : '';
      return `${sermonCount} sermons${whose}: ${min}–${max}% of sermon-body words fall inside reused regions (${aggregate}% overall).${attribution}`;
    }
    if (finding.status === 'cleared') return short(finding.summary || 'The completed review found no meaningful text reuse.');
    if (finding.status === 'inconclusive') return short(finding.summary || 'The available evidence does not support a conclusion.');
    if (finding.status === 'flagged') return short(finding.summary || 'Repeated text overlap met the project evidence threshold.');
    if (finding.status === 'in_progress') return 'A review is underway; no finding has been published yet.';
    return 'No text-reuse review has been published.';
  }

  function aiScale(info) {
    const finding = info.finding;
    let current = null;
    if (finding.status === 'cleared') current = 0;
    if (finding.status === 'inconclusive') current = 1;
    if (finding.status === 'flagged') current = finding.confidence === 'high' ? 3 : 2;
    return {
      current,
      result: current == null ? (finding.status === 'in_progress' ? 'Review underway' : 'Not reviewed') : [
        'No evidence', 'Inconclusive', 'Signs detected', 'Strong unedited AI pattern',
      ][current],
      steps: ['No evidence', 'Inconclusive', 'Signs detected', 'Strong unedited AI pattern'],
      support: finding.status === 'inconclusive'
        ? 'No same-preacher baseline is available, so no conclusion is drawn.'
        : finding.status === 'cleared'
          ? short(finding.summary || 'The review found no converging AI-writing signal.')
          : finding.status === 'flagged'
            ? short(finding.summary || 'Multiple signals and corroborating evidence were found.')
            : finding.status === 'in_progress'
              ? 'A review is underway; no finding has been published yet.'
              : 'No AI-writing review has been published.',
    };
  }

  function scaleHTML(kind, view) {
    const unreviewed = view.current == null;
    const classes = [
      'scale',
      kind === 'text' ? 'scale-text' : 'scale-ai',
      unreviewed ? 'scale-unreviewed' : '',
      kind === 'ai' && view.current >= 2 ? 'ai-strong' : '',
    ].filter(Boolean).join(' ');
    return `
      <section class="${classes}">
        <div class="scale-head">
          <span class="scale-title">${kind === 'text' ? 'Text reuse' : 'AI-writing indicators'}</span>
          <span class="scale-result">${esc(view.result)}</span>
        </div>
        <p class="scale-support">${esc(view.support)}</p>
        <div class="severity" aria-label="${kind === 'text' ? 'Text reuse' : 'AI-writing'} scale: ${esc(view.result)}">
          ${view.steps.map((step, index) => `
            <span class="severity-step ${view.current != null && index <= view.current ? 'reached' : ''} ${index === view.current ? 'is-current' : ''}">
              <span class="severity-dot" aria-hidden="true"></span><span>${esc(step)}</span>
            </span>`).join('')}
        </div>
      </section>`;
  }

  function reportFor(church) {
    const reports = [
      ...(church.reports || []),
      ...activePastors(church).flatMap((pastor) => pastor.reports || []),
    ];
    return reports.find((report) => report.format === 'pdf' && /dependence|similarity|text/i.test(report.title))
      || reports.find((report) => report.format === 'pdf')
      || null;
  }

  function renderDetail(church) {
    const plagiarism = strongestFinding(church, 'plagiarism');
    const ai = strongestFinding(church, 'ai_writing');
    const plagiarismView = plagiarismScale(plagiarism);
    const aiView = aiScale(ai);
    const latestReview = activePastors(church).map((pastor) => pastor.last_reviewed).filter(Boolean).sort().at(-1);
    const location = [church.location?.city, church.location?.state].filter(Boolean).join(', ');
    const subtitle = [church.denomination || church.tradition_label, location].filter(Boolean).join(' · ');
    const report = reportFor(church);
    const brief = church.summary
      || plagiarism.finding.summary
      || 'No published review summary is available for this church.';
    const reportHTML = report ? `
      <a class="report-button" href="${esc(report.url || report.path || '#')}" target="_blank" rel="noopener" download>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2h8l4 4v16H6z"></path><path d="M14 2v5h5M9 16h6M9 12h6"></path></svg>
        Download full report
      </a>
      <small>Sources, methods, excerpts, and sermon-by-sermon results are included in the report.</small>`
      : '<span class="report-unavailable">A downloadable report is not available yet.</span>';

    $('#detail-panel').innerHTML = `
      <article class="detail-shell">
        <button class="back-link" id="back-to-map" type="button">← Back to map</button>
        <header class="detail-heading">
          <h1>${esc(church.name)}</h1>
          <p class="detail-sub">${esc(subtitle)}</p>
          ${latestReview ? `<p class="detail-reviewed">Reviewed ${esc(fmtDate(latestReview))}</p>` : ''}
          <p class="detail-notice">Evidence review, not a verdict.</p>
        </header>
        <section class="review-card">
          <h2>Review summary</h2>
          ${scaleHTML('text', plagiarismView)}
          ${scaleHTML('ai', aiView)}
        </section>
        <section class="brief">
          <h2>In brief</h2>
          <p>${esc(short(brief, 520))}</p>
        </section>
        <div class="report-action">${reportHTML}</div>
      </article>`;
    $('#back-to-map').addEventListener('click', () => select(null));
  }

  function select(slug) {
    const church = slug ? state.churches.find((item) => item.slug === slug) : null;
    state.selected = church?.slug || null;
    closeAbout();
    if (!church) {
      $('#detail-view').hidden = true;
      $('#explore-view').hidden = false;
      $('#explore-link').setAttribute('aria-current', 'page');
      $('#correction-link').href = `${REPO}/issues/new`;
      document.title = 'Tucson Sermon Review';
      history.replaceState(null, '', location.pathname + location.search);
      setTimeout(() => map.invalidateSize(), 40);
      return;
    }

    renderDetail(church);
    $('#explore-view').hidden = true;
    $('#detail-view').hidden = false;
    $('#explore-link').removeAttribute('aria-current');
    $('#correction-link').href = `${REPO}/issues/new?title=${encodeURIComponent('Correction: ' + church.name)}`;
    document.title = `${church.name} · Tucson Sermon Review`;
    history.replaceState(null, '', `#/church/${church.slug}`);
    $('#detail-view').scrollTop = 0;
  }

  // ---------- mobile result sheet ----------
  const mobile = window.matchMedia('(max-width: 760px)');
  function setSheet(open) {
    const panel = $('#sidebar');
    panel.classList.toggle('sheet-open', open);
    $('#sheet-handle').setAttribute('aria-expanded', String(open));
  }

  function initSheet() {
    const handle = $('#sheet-handle');
    const panel = $('#sidebar');
    let startY = 0;
    let startedOpen = false;
    let dragged = false;

    handle.addEventListener('click', () => {
      if (!dragged) setSheet(!panel.classList.contains('sheet-open'));
    });
    handle.addEventListener('pointerdown', (event) => {
      if (!mobile.matches) return;
      startY = event.clientY;
      startedOpen = panel.classList.contains('sheet-open');
      dragged = false;
      handle.setPointerCapture(event.pointerId);
      panel.classList.add('sheet-dragging');
    });
    handle.addEventListener('pointermove', (event) => {
      if (!panel.classList.contains('sheet-dragging')) return;
      const delta = event.clientY - startY;
      if (Math.abs(delta) > 4) dragged = true;
      const closedOffset = panel.offsetHeight * .54;
      panel.style.transform = `translateY(${Math.min(closedOffset, Math.max(0, (startedOpen ? 0 : closedOffset) + delta))}px)`;
    });
    const finish = (event) => {
      if (!panel.classList.contains('sheet-dragging')) return;
      panel.classList.remove('sheet-dragging');
      panel.style.transform = '';
      if (dragged) {
        const delta = event.clientY - startY;
        setSheet(delta < -40 ? true : delta > 40 ? false : startedOpen);
      }
    };
    handle.addEventListener('pointerup', finish);
    handle.addEventListener('pointercancel', finish);
    mobile.addEventListener('change', () => { panel.style.transform = ''; setSheet(false); });
  }

  // ---------- controls and loading ----------
  function closeAbout() {
    $('#about').hidden = true;
    $('#about-toggle').setAttribute('aria-expanded', 'false');
  }

  function bindControls() {
    $('#status-filters').addEventListener('click', (event) => {
      const button = event.target.closest('[data-result]');
      if (!button) return;
      const key = button.dataset.result;
      if (state.activeResults.has(key)) state.activeResults.delete(key);
      else state.activeResults.add(key);
      applyFilters();
    });
    $('#reset-filters').addEventListener('click', () => {
      state.activeResults = new Set(RESULT_ORDER);
      applyFilters();
    });
    $('#search').addEventListener('input', (event) => {
      state.query = event.target.value;
      applyFilters();
    });
    $('#church-list').addEventListener('click', (event) => {
      const item = event.target.closest('[data-slug]');
      if (item) select(item.dataset.slug);
    });
    $('#church-list').addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const item = event.target.closest('[data-slug]');
      if (!item) return;
      event.preventDefault();
      select(item.dataset.slug);
    });
    $('#about-toggle').addEventListener('click', () => {
      const panel = $('#about');
      panel.hidden = !panel.hidden;
      $('#about-toggle').setAttribute('aria-expanded', String(!panel.hidden));
    });
    $('#about-close').addEventListener('click', closeAbout);
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeAbout(); });
    initSheet();
  }

  renderLegend();
  bindControls();

  const API = new URLSearchParams(location.search).has('offline') ? '' : (window.SERMON_REVIEW_API || '');
  const fallback = () => fetch('data/churches.json', { cache: 'no-cache' }).then((response) => {
    if (!response.ok) throw new Error(response.status + ' ' + response.statusText);
    return response.json();
  });
  const loadData = API
    ? fetch(`${API}/api/v1/public/churches`, { cache: 'no-cache' })
      .then((response) => {
        if (!response.ok) throw new Error(response.status + ' ' + response.statusText);
        return response.json();
      })
      .catch(fallback)
    : fallback();

  loadData
    .then((data) => {
      state.data = data;
      state.churches = data.churches.map((church) => ({ ...church, _result: churchResult(church) }));
      applyFilters();
      const plotted = state.churches.filter((church) => church.plotted);
      if (plotted.length > 1) {
        map.fitBounds(L.latLngBounds(plotted.map((church) => [church.location.lat, church.location.lng])).pad(.12));
      }
      const match = location.hash.match(/^#\/church\/([a-z0-9-]+)/);
      if (match) select(match[1]);
    })
    .catch((error) => {
      $('#church-list').innerHTML = `<li class="empty">The church directory could not be loaded. ${esc(error.message)}</li>`;
    });

  window.addEventListener('hashchange', () => {
    const match = location.hash.match(/^#\/church\/([a-z0-9-]+)/);
    select(match ? match[1] : null);
  });
})();
