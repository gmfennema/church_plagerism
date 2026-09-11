/* Tucson Sermon Review. Convex is preferred; the generated JSON remains an offline fallback. */
(function () {
  'use strict';

  // Plain-language labels. The rubric wording ("evidence threshold met") lives in the expanded details.
  const STATUS = {
    unchecked: { label: 'Not yet reviewed', short: 'Not reviewed', color: '#8b949e' },
    partial: { label: 'Inconclusive', short: 'Inconclusive', color: '#c47a12' },
    inconclusive: { label: 'Inconclusive', short: 'Inconclusive', color: '#c47a12' },
    in_progress: { label: 'Review underway', short: 'Underway', color: '#2f6fb3' },
    cleared: { label: 'No concerns found', short: 'No concerns', color: '#2a8a63' },
    flagged: { label: 'Concerns found', short: 'Concerns', color: '#c23b4d' },
  };
  const CHURCH_BLURB = {
    unchecked: 'This church is on the map, but nobody has reviewed its sermons yet.',
    partial: 'Some preaching was reviewed, but there is not enough evidence to say either way.',
    inconclusive: 'Some preaching was reviewed, but there is not enough evidence to say either way.',
    in_progress: 'A review of this church’s sermons is in progress. Nothing has been published yet.',
    cleared: 'Reviewers compared this church’s sermons with other preachers’ work and found nothing notable.',
    flagged: 'The published evidence met the project’s threshold for concern. Read the details before drawing conclusions.',
  };
  const CHECK = { plagiarism: 'Copying', ai_writing: 'AI writing' };
  const METRIC_LABEL = {
    sermons_with_matches: 'Sermons with matches', sermons_compared: 'Sermons compared', corpus_coverage_pct: 'Matched text across all sermons',
    max_sermon_coverage_pct: 'Most matched text in one sermon', longest_non_scripture_run_words: 'Longest matching passage (words)',
    min_run_length_words: 'Shortest run counted (words)', ai_phrase_rate_per_1000: 'AI-associated phrases per 1,000 words',
    disfluency_rate_per_1000: 'Spoken “ums” and restarts per 1,000 words', mattr: 'Vocabulary variety (0 to 1)', baseline_available: 'Older sermons available to compare',
  };
  const REPO = 'https://github.com/gmfennema/church_plagerism';
  const TUCSON = [32.2226, -110.9247];
  const STATUS_ORDER = ['flagged', 'cleared', 'partial', 'in_progress', 'unchecked'];

  const state = { data: null, churches: [], filtered: [], status: '', tradition: '', query: '', selected: null, markers: new Map() };
  const $ = (sel) => document.querySelector(sel);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtDate = (iso) => { if (!iso) return ''; const d = new Date(iso + 'T12:00:00'); return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); };
  const fmtMonth = (iso) => { if (!iso) return ''; const d = new Date(iso + 'T12:00:00'); return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: 'numeric', month: 'long' }); };
  const fmtSize = (n) => (n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n > 1024 ? Math.round(n / 1024) + ' KB' : n + ' B');
  const label = (status) => STATUS[status]?.label || STATUS.unchecked.label;
  const pill = (status) => `<span class="pill pill-${esc(status || 'unchecked')}">${esc(label(status))}</span>`;
  const dotted = (status) => `<span class="dot status-${esc(status || 'unchecked')}"></span>${esc(label(status))}`;
  const confidence = (v) => v ? `<span class="conf">${esc(v)} confidence</span>` : '';
  const ext = (href, text) => `<a href="${esc(href)}" rel="noopener" target="_blank">${text}</a>`;
  const plural = (n, word) => `${n} ${n === 1 ? word : word.endsWith('ch') ? word + 'es' : word + 's'}`;

  // ---------- map ----------
  const map = L.map('map', { zoomControl: true, attributionControl: true }).setView(TUCSON, 11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const layer = L.layerGroup().addTo(map);

  const legend = L.control({ position: 'bottomleft' });
  legend.onAdd = function () {
    const div = L.DomUtil.create('div', 'map-legend');
    div.innerHTML = STATUS_ORDER.map((s) => `<div><span class="dot status-${s}"></span>${STATUS[s].label}</div>`).join('');
    return div;
  };
  legend.addTo(map);

  function markerFor(church) {
    const approx = church.location.geocode === 'approximate';
    const flagged = church.status === 'flagged';
    const m = L.circleMarker([church.location.lat, church.location.lng], {
      radius: flagged ? 9 : 7,
      color: '#ffffff',
      weight: 2,
      dashArray: approx ? '3 3' : null,
      fillColor: STATUS[church.status].color,
      fillOpacity: 1,
    });
    m.bindTooltip(`<b>${esc(church.name)}</b><span class="tip-status">${dotted(church.status)}</span>`, { direction: 'top', offset: [0, -8] });
    m.on('click', () => select(church.slug, { pan: false, fromMarker: true }));
    return m;
  }

  function renderMarkers() {
    layer.clearLayers();
    state.markers.clear();
    // Draw flagged churches last so they sit on top of the cluster.
    const ordered = [...state.filtered.filter((c) => c.plotted)].sort((a, b) => (a.status === 'flagged') - (b.status === 'flagged'));
    ordered.forEach((c) => {
      const m = markerFor(c);
      state.markers.set(c.slug, m);
      m.addTo(layer);
    });
  }

  // ---------- mobile bottom sheet ----------
  const mobile = window.matchMedia('(max-width: 860px)');
  const isMobile = () => mobile.matches;
  const sheet = () => $('#sidebar');

  function sheetPeekHeight() {
    const raw = getComputedStyle(sheet()).getPropertyValue('--sheet-peek').trim();
    const n = parseFloat(raw);
    return raw.endsWith('dvh') || raw.endsWith('vh') ? (window.innerHeight * n) / 100 : n;
  }

  function setSheet(open) {
    const el = sheet();
    el.classList.toggle('sheet-open', open);
    $('#sheet-handle').setAttribute('aria-expanded', String(open));
  }

  function initSheet() {
    const handle = $('#sheet-handle');
    const el = sheet();
    let startY = 0;
    let startOpen = false;
    let dragged = false;

    handle.addEventListener('click', () => { if (!dragged) setSheet(!el.classList.contains('sheet-open')); });
    handle.addEventListener('pointerdown', (e) => {
      if (!isMobile()) return;
      startY = e.clientY;
      startOpen = el.classList.contains('sheet-open');
      dragged = false;
      handle.setPointerCapture(e.pointerId);
      el.classList.add('sheet-dragging');
    });
    handle.addEventListener('pointermove', (e) => {
      if (!el.classList.contains('sheet-dragging')) return;
      const dy = e.clientY - startY;
      if (Math.abs(dy) > 4) dragged = true;
      const closedOffset = el.offsetHeight - sheetPeekHeight();
      const base = startOpen ? 0 : closedOffset;
      const next = Math.min(closedOffset, Math.max(0, base + dy));
      el.style.transform = `translateY(${next}px)`;
    });
    const endDrag = (e) => {
      if (!el.classList.contains('sheet-dragging')) return;
      el.classList.remove('sheet-dragging');
      el.style.transform = '';
      if (!dragged) return;
      const dy = e.clientY - startY;
      setSheet(dy < -40 ? true : dy > 40 ? false : startOpen);
    };
    handle.addEventListener('pointerup', endDrag);
    handle.addEventListener('pointercancel', endDrag);
    mobile.addEventListener('change', () => { el.style.transform = ''; setSheet(false); setTimeout(() => map.invalidateSize(), 60); });
  }

  // ---------- filtering ----------
  function applyFilters() {
    const q = state.query.trim().toLowerCase();
    state.filtered = state.churches.filter((c) => {
      if (state.status && c.status !== state.status) return false;
      if (state.tradition && c.tradition !== state.tradition) return false;
      if (!q) return true;
      const hay = [c.name, ...(c.aka || []), c.denomination, c.tradition_label, c.location.address, c.location.city, ...c.pastors.map((p) => p.name)].join(' ').toLowerCase();
      return hay.includes(q);
    });
    renderList();
    renderMarkers();
  }

  function renderList() {
    const ul = $('#church-list');
    const plotted = state.filtered.filter((c) => c.plotted);
    const unplotted = state.filtered.filter((c) => !c.plotted);
    const filtered = state.filtered.length !== state.churches.length;
    $('#result-count').textContent = filtered ? `${plural(state.filtered.length, 'church')} of ${state.churches.length}` : plural(state.churches.length, 'church');
    if (!state.filtered.length) { ul.innerHTML = $('#tpl-empty').innerHTML; return; }
    const item = (c) => `
      <li class="item ${state.selected === c.slug ? 'active' : ''}" data-slug="${esc(c.slug)}" tabindex="0" role="button">
        <div class="item-main">
          <div class="item-name">${esc(c.name)}</div>
          <div class="item-sub">${esc(c.tradition_label)}${c.location.city ? ' · ' + esc(c.location.city) : ''}</div>
        </div>
        <span class="pill pill-${esc(c.status)}">${esc(STATUS[c.status].short)}</span>
      </li>`;
    ul.innerHTML = plotted.map(item).join('') + (unplotted.length ? `<li class="section-label">Not on the map yet</li>` + unplotted.map(item).join('') : '');
  }

  // ---------- detail ----------
  function keyFacts(kind, f) {
    const m = f.metrics || {};
    const facts = [];
    if (kind === 'plagiarism') {
      if (m.sermons_with_matches != null && m.sermons_compared != null) facts.push([`${m.sermons_with_matches} of ${m.sermons_compared}`, 'sermons had matching passages']);
      if (m.longest_non_scripture_run_words != null) facts.push([`${m.longest_non_scripture_run_words} words`, 'longest matching passage, excluding Scripture']);
      if (m.max_sermon_coverage_pct != null) facts.push([`${m.max_sermon_coverage_pct}%`, 'of the most affected sermon matched a source']);
    } else {
      if (f.sermons_reviewed) facts.push([String(f.sermons_reviewed), 'sermons analysed']);
      if (m.baseline_available != null) facts.push([m.baseline_available ? 'Yes' : 'No', 'older sermons from the same preacher to compare against']);
    }
    return facts.length ? `<div class="facts">${facts.map(([v, l]) => `<div class="fact"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join('')}</div>` : '';
  }

  function allNumbers(f) {
    if (!f.metrics) return '';
    const rows = Object.entries(f.metrics).map(([k, v]) => `<li><span>${esc(METRIC_LABEL[k] || k.replace(/_/g, ' '))}</span><b>${esc(typeof v === 'boolean' ? (v ? 'Yes' : 'No') : v)}${k.endsWith('_pct') ? '%' : ''}</b></li>`);
    return `<details class="more"><summary>All the numbers</summary><div class="more-body"><ul class="numbers">${rows.join('')}</ul>${f.methods?.length ? `<p class="footnote">Methods: ${f.methods.map((x) => esc(x.replace(/_/g, ' '))).join(', ')}.</p>` : ''}</div></details>`;
  }

  function sourcesCompared(f) {
    if (!f.sources_compared?.length) return '';
    const credit = (s) => s.attributed_in_sermon === true ? 'credited in the sermon' : s.attributed_in_sermon === false ? 'not credited in the sermon' : 'credit not yet checked';
    return `<h5>Compared against</h5><ul class="plain">${f.sources_compared.map((s) => `<li>${esc(s.author)}, <em>${s.url ? ext(s.url, esc(s.title)) : esc(s.title)}</em> <span class="muted">· ${credit(s)}</span></li>`).join('')}</ul>`;
  }

  function examples(f) {
    if (!f.evidence?.length) return '';
    const one = (e) => `
      <div class="example">
        <p class="example-desc">${esc(e.description)}</p>
        ${e.excerpt ? `<p class="example-meta">“${esc(e.excerpt)}”${e.timestamp ? ` at ${esc(e.timestamp)}` : ''}</p>` : ''}
        ${e.sermon_excerpt || e.source_excerpt ? `<div class="compare"><blockquote><span>This sermon</span>${esc(e.sermon_excerpt || 'Excerpt not supplied')}</blockquote><blockquote><span>The source</span>${esc(e.source_excerpt || 'Excerpt not supplied')}</blockquote></div>` : ''}
        <div class="example-meta">${e.sermon_title ? (e.sermon_url ? ext(e.sermon_url, esc(e.sermon_title)) : esc(e.sermon_title)) + (e.sermon_date ? `, ${fmtDate(e.sermon_date)}` : '') : ''}${e.source_title ? ` · compared with ${esc(e.source_author || '')} ${e.source_url ? ext(e.source_url, esc(e.source_title)) : esc(e.source_title)}` : ''}</div>
      </div>`;
    return `<h5>${plural(f.evidence.length, 'example')}</h5>${f.evidence.map(one).join('')}`;
  }

  function findingDetails(kind, f) {
    if (!f || f.status === 'unchecked') return '';
    const when = f.sermons_reviewed ? `<p class="muted small">${plural(f.sermons_reviewed, 'sermon')} reviewed${f.review_period?.from ? `, ${fmtMonth(f.review_period.from)} to ${fmtMonth(f.review_period.to)}` : ''}.</p>` : '';
    return `<h5>${esc(CHECK[kind])}: ${esc(label(f.status))}</h5>
      ${f.summary ? `<p>${esc(f.summary)}</p>` : ''}
      ${keyFacts(kind, f)}${when}${sourcesCompared(f)}${examples(f)}${allNumbers(f)}`;
  }

  function reportsHTML(reports) {
    if (!reports?.length) return '';
    return `<ul class="reports">${reports.map((r) => `<li><a href="${esc(r.url)}" download target="_blank" rel="noopener"><span class="fmt">${esc(r.format.toUpperCase())}</span><span class="r-title">${esc(r.title)}</span><span class="r-size">${r.size_bytes ? fmtSize(r.size_bytes) : ''}</span></a></li>`).join('')}</ul>`;
  }

  function pastorHTML(p) {
    const plag = p.plagiarism || { status: 'unchecked' };
    const ai = p.ai_writing || { status: 'unchecked' };
    const reviewed = plag.status !== 'unchecked' || ai.status !== 'unchecked';
    const head = `<div class="pastor-head"><h4>${esc(p.name)}${p.bio_url ? ext(p.bio_url, 'bio') : ''}</h4><span class="role">${esc(p.role)}${p.active === false ? ' · former' : ''}</span></div>`;
    if (!reviewed) return `<article class="pastor">${head}<div class="pastor-status">Not yet reviewed</div></article>`;
    const row = (kind, f) => `<div class="check-row"><span class="check-name">${esc(CHECK[kind])}</span><span class="check-right">${confidence(f.confidence)}${pill(f.status)}</span></div>`;
    const more = `${findingDetails('plagiarism', plag)}${findingDetails('ai_writing', ai)}
      ${p.reports?.length ? `<h5>Full reports</h5>${reportsHTML(p.reports)}` : ''}
      ${p.notes ? `<h5>Reviewer notes</h5><div class="notes">${esc(p.notes)}</div>` : ''}
      ${p.last_reviewed ? `<p class="footnote">Last reviewed ${fmtDate(p.last_reviewed)}${p.reviewed_by ? ` by ${esc(p.reviewed_by)}` : ''}.</p>` : ''}`;
    return `<article class="pastor">${head}
      <div class="check-rows">${row('plagiarism', plag)}${row('ai_writing', ai)}</div>
      <details class="more"><summary>See the evidence</summary><div class="more-body">${more}</div></details>
    </article>`;
  }

  function reviewedLine(c) {
    const dates = c.pastors.map((p) => p.last_reviewed).filter(Boolean).sort();
    const sermons = c.pastors.reduce((n, p) => n + Math.max(p.plagiarism?.sermons_reviewed || 0, p.ai_writing?.sermons_reviewed || 0), 0);
    const parts = [];
    if (dates.length) parts.push(`Reviewed ${fmtMonth(dates[dates.length - 1])}`);
    if (sermons) parts.push(plural(sermons, 'sermon'));
    return parts.join(' · ');
  }

  function renderDetail(c) {
    const loc = c.location;
    const addr = [loc.address, loc.city, loc.state].filter(Boolean).join(', ');
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(c.name + ' ' + [loc.address, loc.city, loc.state, loc.postal_code].filter(Boolean).join(', '))}`;
    const yt = c.youtube?.channel_url || (c.youtube?.sermon_playlist_urls || [])[0];
    const plagStatus = c.plagiarism_status || c.status;
    const reviewed = c.status !== 'unchecked';
    const line = reviewedLine(c);
    const icon = (d) => `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    const html = `
      <div class="detail-head"><button class="btn-back" id="back">${icon('M10 3L5 8l5 5')}Back</button></div>
      <div class="detail-body">
        <h2>${esc(c.name)}</h2>
        <p class="detail-meta">${esc(c.denomination || c.tradition_label)}${addr ? ' · ' + esc(addr) : ''}</p>
        <div class="link-row">
          ${c.website ? ext(c.website, `${icon('M2 8h12M8 2c2.5 2.5 2.5 9.5 0 12M8 2C5.5 4.5 5.5 11.5 8 14M8 2a6 6 0 100 12A6 6 0 008 2z')}Website`) : ''}
          ${yt ? ext(yt, `${icon('M6 5.5v5l4.5-2.5z M2 4.5h12v7H2z')}Sermons`) : ''}
          ${addr ? ext(mapsUrl, `${icon('M8 14s4.5-4 4.5-7.5a4.5 4.5 0 10-9 0C3.5 10 8 14 8 14z M8 8a1.5 1.5 0 100-3 1.5 1.5 0 000 3z')}Directions`) : ''}
          ${(c.other_media || []).map((m) => ext(m.url, esc(m.label))).join('')}
        </div>

        <section class="verdict verdict-${esc(c.status)}" aria-label="Review result">
          <h3 class="verdict-title"><span class="dot status-${esc(c.status)}"></span>${esc(label(c.status))}</h3>
          <p>${esc(CHURCH_BLURB[c.status] || '')}</p>
          ${reviewed ? `<div class="verdict-checks">
            <div class="check"><div class="check-label">Copying</div><div class="check-value">${dotted(plagStatus)}</div></div>
            <div class="check"><div class="check-label">AI writing</div><div class="check-value">${dotted(c.ai_status)}</div></div>
          </div>` : ''}
          <div class="verdict-foot">${line ? esc(line) + ' · ' : ''}<a href="#" class="open-about">What do these labels mean?</a></div>
        </section>

        ${reviewed && c.summary ? `<p class="summary">${esc(c.summary)}</p>` : ''}

        <h3 class="sec">${c.pastors.length ? 'Preaching pastors' : 'Pastors'}</h3>
        ${c.pastors.length ? c.pastors.map(pastorHTML).join('') : '<p class="muted">No preaching pastors identified yet.</p>'}
        ${c.reports?.length ? `<h3 class="sec">Church-level reports</h3>${reportsHTML(c.reports)}` : ''}

        <details class="more">
          <summary>About this record</summary>
          <div class="more-body">
            ${c.aka?.length ? `<p>Also known as ${esc(c.aka.join(', '))}.</p>` : ''}
            ${loc.geocode === 'approximate' ? '<p>The map pin is approximate.</p>' : loc.geocode === 'missing' ? '<p>This church has not been placed on the map yet.</p>' : ''}
            ${c.notes ? `<h5>Research notes</h5><div class="notes">${esc(c.notes)}</div>` : ''}
            ${(c.sources || []).length ? `<h5>Where the facts came from</h5><ul class="plain">${c.sources.map((s) => `<li>${ext(s.url, esc(s.label))}${s.accessed ? ` <span class="muted">(${fmtDate(s.accessed)})</span>` : ''}</li>`).join('')}</ul>` : ''}
            <p class="footnote">Updated ${fmtDate(c.updated_at)} by ${esc(c.updated_by)} · ${ext(`${REPO}/blob/main/data/churches/${esc(c.slug)}.json`, 'source data')} · ${ext(`${REPO}/issues/new?title=${encodeURIComponent('Correction: ' + c.name)}`, 'suggest a correction')}</p>
          </div>
        </details>
      </div>`;
    const panel = $('#detail-panel');
    panel.innerHTML = html;
    panel.hidden = false;
    $('#list-panel').hidden = true;
    panel.scrollTop = 0;
    $('#back').addEventListener('click', () => select(null));
    panel.querySelector('.open-about').addEventListener('click', (e) => { e.preventDefault(); setAbout(true); });
  }

  function select(slug, opts = {}) {
    state.selected = slug;
    const c = slug ? state.churches.find((x) => x.slug === slug) : null;
    if (!c) {
      $('#detail-panel').hidden = true;
      $('#list-panel').hidden = false;
      history.replaceState(null, '', location.pathname + location.search);
      renderList();
      return;
    }
    history.replaceState(null, '', `#/church/${slug}`);
    renderDetail(c);
    renderList();
    if (isMobile()) setSheet(opts.fromMarker !== true);
    const m = state.markers.get(slug);
    if (m && opts.pan !== false) {
      const zoom = Math.max(map.getZoom(), 13);
      let target = m.getLatLng();
      if (isMobile()) {
        const pt = map.project(target, zoom);
        pt.y += sheetPeekHeight() / 2;
        target = map.unproject(pt, zoom);
      }
      map.flyTo(target, zoom, { duration: 0.6 });
    }
    if (m) m.openTooltip();
  }

  // ---------- controls ----------
  function setAbout(open) {
    const a = $('#about');
    a.hidden = !open;
    $('#about-toggle').setAttribute('aria-expanded', String(open));
    $('#app').classList.toggle('about-open', open);
    if (open) window.scrollTo(0, 0);
    setTimeout(() => map.invalidateSize(), 50);
  }

  function buildControls() {
    const counts = state.data.counts || {};
    const filters = $('#status-filters');
    const chip = (value, text, count, dot) => `<button class="chip" role="radio" data-status="${value}" aria-checked="${state.status === value}">${dot ? `<span class="dot status-${dot}"></span>` : ''}${text}<span class="count">${count}</span></button>`;
    filters.innerHTML = chip('', 'All', state.churches.length) + STATUS_ORDER.filter((s) => counts[s]).map((s) => chip(s, STATUS[s].label, counts[s], s)).join('');
    filters.querySelectorAll('.chip').forEach((b) => b.addEventListener('click', () => {
      state.status = b.dataset.status;
      filters.querySelectorAll('.chip').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
      applyFilters();
    }));

    const traditions = new Map();
    state.churches.forEach((c) => traditions.set(c.tradition, c.tradition_label));
    const sel = $('#tradition-filter');
    [...traditions.entries()].sort((a, b) => a[1].localeCompare(b[1])).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = v; sel.appendChild(o); });
    sel.addEventListener('change', () => { state.tradition = sel.value; $('#filter-toggle').classList.toggle('has-value', !!sel.value); applyFilters(); });
    $('#filter-toggle').addEventListener('click', () => {
      const more = $('#filter-more');
      more.hidden = !more.hidden;
      $('#filter-toggle').setAttribute('aria-expanded', String(!more.hidden));
    });
    $('#search').addEventListener('input', (e) => { state.query = e.target.value; applyFilters(); });
    $('#church-list').addEventListener('click', (e) => { const li = e.target.closest('li.item'); if (li) select(li.dataset.slug); });
    $('#church-list').addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { const li = e.target.closest('li.item'); if (li) { e.preventDefault(); select(li.dataset.slug); } } });
    $('#about-toggle').addEventListener('click', () => setAbout($('#about').hidden));
    $('#about-close').addEventListener('click', () => setAbout(false));
    $('#home-link').addEventListener('click', (e) => { e.preventDefault(); setAbout(false); select(null); });
    initSheet();
  }

  // ---------- boot ----------
  const API = window.SERMON_REVIEW_API || '';
  const fallback = () => fetch('data/churches.json', { cache: 'no-cache' }).then((r) => {
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    return r.json();
  });
  const loadData = API
    ? fetch(`${API}/api/v1/public/churches`, { cache: 'no-cache' })
      .then((r) => { if (!r.ok) throw new Error(r.status + ' ' + r.statusText); return r.json(); })
      .catch(fallback)
    : fallback();
  loadData
    .then((data) => {
      state.data = data;
      state.churches = data.churches;
      buildControls();
      applyFilters();
      const plotted = state.churches.filter((c) => c.plotted);
      if (plotted.length > 1) map.fitBounds(L.latLngBounds(plotted.map((c) => [c.location.lat, c.location.lng])).pad(0.15));
      const m = location.hash.match(/^#\/church\/([a-z0-9-]+)/);
      if (m) select(m[1]);
    })
    .catch((err) => {
      $('#church-list').innerHTML = `<li class="empty">Could not load the church data (${esc(err.message)}). Run <code>python3 tools/build.py</code> and serve the site folder over HTTP.</li>`;
    });
  window.addEventListener('hashchange', () => { const m = location.hash.match(/^#\/church\/([a-z0-9-]+)/); select(m ? m[1] : null); });
})();
