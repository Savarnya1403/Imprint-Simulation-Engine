/* Imprint Studio — simulation console */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const ICONS = {
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/></svg>',
  help: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.6 2.6 0 1 1 3.6 2.4c-.8.4-1.1 1-1.1 2"/><circle cx="12" cy="17" r=".7" fill="currentColor" stroke="none"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5l12 7.5-12 7.5z"/></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4" height="15"/><rect x="14" y="4.5" width="4" height="15"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M5 5l14 14M19 5L5 19"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M4 12h15"/><path d="M13 6l6 6-6 6"/></svg>',
  bolt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M13 2.5L5 13.5h6L10 21.5l8-11h-6z"/></svg>'
};
const injectIcons = (root = document) => $$('[data-icon]', root).forEach(el => {
  if (ICONS[el.dataset.icon]) el.innerHTML = ICONS[el.dataset.icon];
});

const S = {
  meta: null, run: null, day: 1, tab: 'world', scenario: 'base',
  playing: false, playTimer: null,
  social: { platform: 'all', tier: '', sort: 'impact', limit: 40 },
  agentLimit: 36,
  forecast: null, scenarios: null,
  evidenceDomain: '', evidenceQuery: '',
  focusRounds: [], drawerAgent: null, chats: {},
  map: null,
  atlas: null, precedents: null, causal: null, calibration: null,
  validation: null, modelcard: null, robust: null, sens: null, validationLoading: false,
  atlasQuery: '', atlasDimension: '', atlasTimer: null,
  causalLoaded: false, calibrationLoaded: false,
  reasoning: null, reasoningLoaded: false, reasoningBusy: false, reasoningKey: '', agentField: { raf: null, agents: [] },
  opsLog: [], opsPaused: false, compareRuns: [], compareOpen: false,
};

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 1) => `${(Number(v || 0) * 100).toFixed(d)}%`;
const signed = (v, d = 2) => `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(d)}`;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const money = v => {
  const n = Number(v || 0);
  if (!n) return '₹0';
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(2)} L`;
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
};
const initials = n => String(n || '').split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
const tierClass = t => `tag tag--t${t}`;
const sentimentWord = v => v > .18 ? 'positive' : v < -.12 ? 'negative' : 'split';
const toast = (msg) => {
  const el = $('#toast'); el.textContent = msg; el.classList.add('show');
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove('show'), 2200);
};

/* ---------- avatars ---------- */
function avatar(a, size = 34) {
  const look = a?.look || {};
  const variant = Number(look.variant || 0) % 20;
  const hair = look.hair || (a?.gender === 'female' ? 'long' : 'short');
  const attire = look.attire || 'kurta';
  const acc = look.accessory || 'none';
  const skin = ['#a9a9a9', '#b7b7b7', '#949494', '#c0c0c0'][variant % 4];
  const bg = ['#141416', '#17171a', '#121214', '#1a1a1d'][variant % 4];
  const shoulder = attire === 'saree' || attire === 'saree_young' ? '#2a2a2d' : attire === 'hoodie' ? '#222225' : attire === 'uniform' ? '#26262a' : '#242427';
  const hairFill = hair === 'turban' ? '#cfcfcf' : ['#1c1c1e', '#252528', '#303034'][variant % 3];
  let hairPath = '';
  if (hair === 'short') hairPath = `<path d="M19 26c-.6-9 4.6-15 13-15s13.6 6 13 15c-2.5-6-6.8-8.4-13-8.4S21.5 20 19 26z" fill="${hairFill}"/>`;
  if (hair === 'long') hairPath = `<path d="M18 27c-1-10 5-16 14-16s15 6 14 16l-2 14c-2-8-3-13-5-16-3 4-10 5-14 3-2 3-3 7-5 13z" fill="${hairFill}"/>`;
  if (hair === 'bun') hairPath = `<circle cx="45" cy="14" r="6" fill="${hairFill}"/><path d="M19 26c-.6-9 4.6-15 13-15s13.6 6 13 15c-2.5-6-6.8-8.4-13-8.4S21.5 20 19 26z" fill="${hairFill}"/>`;
  if (hair === 'curly') hairPath = `<path d="M19 27c-2-11 5-17 13-17 9 0 15 6 13 17-2-2-2-5-4-5-1-4-4-4-5-7-3 3-4 6-6 5-1 4-4 3-5 7-2 0-4 2-6 0z" fill="${hairFill}"/>`;
  if (hair === 'turban') hairPath = `<path d="M16 25c0-10 7-17 16-17s16 7 16 17c-4 3-9 4-16 4s-12-1-16-4z" fill="${hairFill}" opacity=".9"/><path d="M19 22c4-3 8-4 13-4s9 1 13 4" fill="none" stroke="rgba(0,0,0,.25)" stroke-width="1"/>`;
  const glasses = acc === 'spectacles' ? `<circle cx="26" cy="29" r="4.6" fill="none" stroke="rgba(10,10,10,.8)" stroke-width="1"/><circle cx="38" cy="29" r="4.6" fill="none" stroke="rgba(10,10,10,.8)" stroke-width="1"/><path d="M30.6 29h2.8" stroke="rgba(10,10,10,.8)" stroke-width="1"/>` : '';
  const helmet = acc === 'helmet' ? `<path d="M16 25c1-11 8-17 16-17s15 6 16 17h-4c-1-8-5-12-12-12s-11 4-12 12z" fill="#d0d0d0" opacity=".75"/>` : '';
  const dupatta = acc === 'dupatta' ? `<path d="M22 44c4 2 7 6 8 18h-7c0-8-2-13-5-15z" fill="#a5a5a5" opacity=".45"/>` : '';
  const bag = acc === 'bag' ? `<path d="M43 44l5 1-2 14h-5z" fill="#3a3a3e"/>` : '';
  return `<svg viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true">
    <rect width="64" height="64" fill="${bg}"/>
    <circle cx="32" cy="30" r="19" fill="rgba(255,255,255,.025)"/>
    <path d="M8 64c1-13 11-20 24-20s23 7 24 20z" fill="${shoulder}" stroke="rgba(255,255,255,.15)" stroke-width=".8"/>
    <rect x="29" y="36" width="6" height="8" fill="${skin}" opacity=".8"/>
    <ellipse cx="32" cy="29" rx="13" ry="14.5" fill="${skin}" stroke="rgba(255,255,255,.18)" stroke-width=".8"/>
    ${hairPath}${helmet}
    <circle cx="27" cy="29" r="1" fill="#151515"/><circle cx="37" cy="29" r="1" fill="#151515"/>
    <path d="M28.5 36c2 1.4 5 1.4 7 0" fill="none" stroke="rgba(20,20,20,.55)" stroke-width="1" stroke-linecap="round"/>
    ${glasses}${dupatta}${bag}
  </svg>`;
}
const avatarOf = (id, cls = 'avatar') => {
  const a = S.run?.agents?.find(x => x.id === id);
  return `<span class="${cls}">${avatar(a)}</span>`;
};

/* ---------- charts ---------- */
function lineChart(el, series, opts = {}) {
  if (!el) return;
  const W = 620, H = opts.height || 160, L = 30, R = 8, T = 9, B = 18;
  const n = Math.max(...series.map(s => s.values.length));
  if (!n) { el.innerHTML = ''; return; }
  const min = opts.min ?? 0, max = opts.max ?? 1;
  const px = i => L + (i / Math.max(1, n - 1)) * (W - L - R);
  const py = v => T + (1 - clamp((v - min) / (max - min || 1), 0, 1)) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  svg += '<g class="chart-grid">';
  for (let i = 0; i <= 4; i++) {
    const y = T + (i / 4) * (H - T - B);
    svg += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}"/>`;
  }
  svg += '</g>';
  const fmt = opts.fmt || (v => `${Math.round(v * 100)}%`);
  for (let i = 0; i <= 4; i++) {
    const y = T + (i / 4) * (H - T - B) + 3;
    svg += `<text class="chart-label" x="2" y="${y}">${fmt(max - (i / 4) * (max - min))}</text>`;
  }
  series.forEach(s => {
    if (s.area && s.values.length) {
      const pts = s.values.map((v, i) => `${px(i)},${py(v)}`).join(' ');
      svg += `<polygon points="${L},${H - B} ${pts} ${W - R},${H - B}" fill="${s.area}" opacity=".8"/>`;
    }
    const d = s.values.map((v, i) => `${i ? 'L' : 'M'}${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    svg += `<path d="${d}" fill="none" stroke="${s.color || 'rgba(255,255,255,.7)'}" stroke-width="${s.width || 1.6}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''} stroke-linecap="round" stroke-linejoin="round" opacity="${s.opacity ?? 1}"/>`;
    if (s.dots) s.values.forEach((v, i) => { if (i % Math.max(1, Math.floor(n / 10)) === 0) svg += `<circle cx="${px(i)}" cy="${py(v)}" r="1.3" fill="${s.color}" opacity=".75"/>`; });
  });
  if (opts.marker != null) {
    const x = px(opts.marker);
    svg += `<line x1="${x}" y1="${T}" x2="${x}" y2="${H - B}" stroke="rgba(255,255,255,.34)" stroke-width="1" stroke-dasharray="2 3"/>`;
    series.forEach(s => {
      const v = s.values[opts.marker];
      if (v != null) svg += `<circle cx="${x}" cy="${py(v)}" r="2.6" fill="${s.color}" stroke="#0a0a0c" stroke-width="1.4"/>`;
    });
  }
  if (opts.labels) {
    const picks = [0, Math.floor((n - 1) / 2), n - 1];
    picks.forEach((i, k) => {
      const x = px(i);
      const anchor = k === 0 ? 'start' : k === 2 ? 'end' : 'middle';
      svg += `<text class="chart-label" x="${x}" y="${H - 5}" text-anchor="${anchor}">${esc(opts.labels[i] || '')}</text>`;
    });
  }
  svg += '</svg>';
  el.innerHTML = svg;
}

function forecastChart(el, data) {
  if (!el) return;
  const hist = data.history.values, rawFc = data.forecast.point;
  const rBlock = data.reasoned_forecast;
  const useReasoned = Array.isArray(rBlock?.point) && rBlock.point.length === rawFc.length
    && Array.isArray(rBlock.p10) && Array.isArray(rBlock.p90);
  const fc = useReasoned ? rBlock.point.map(Number) : rawFc;
  const lo = useReasoned ? rBlock.p10.map(Number) : data.forecast.p10;
  const hi = useReasoned ? rBlock.p90.map(Number) : data.forecast.p90;
  const labels = [...data.history.labels, ...data.forecast.labels];
  const W = 760, H = 300, L = 40, R = 12, T = 14, B = 24;
  const all = [...hist, ...hi, ...lo, ...rawFc];
  let min = Math.min(...all), max = Math.max(...all);
  const pad = (max - min) * .12 || 1;
  min -= pad; max += pad;
  const n = hist.length + fc.length;
  const px = i => L + (i / Math.max(1, n - 1)) * (W - L - R);
  const py = v => T + (1 - (v - min) / (max - min || 1)) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  for (let i = 0; i <= 4; i++) {
    const y = T + (i / 4) * (H - T - B);
    svg += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" stroke="rgba(255,255,255,.045)"/>`;
    svg += `<text class="chart-label" x="3" y="${y + 3}">${(max - (i / 4) * (max - min)).toFixed(1)}</text>`;
  }
  const histPts = hist.map((v, i) => `${px(i)},${py(v)}`).join(' ');
  const fStart = hist.length - 1;
  const bandPts = [
    ...hist.slice(-1).map((_, i) => `${px(fStart)},${py(hist.at(-1))}`),
    ...hi.map((v, i) => `${px(hist.length + i)},${py(v)}`),
    ...lo.map((v, i) => `${px(hist.length + lo.length - 1 - i)},${py(v)}`),
  ].join(' ');
  svg += `<polygon points="${bandPts}" fill="rgba(74,222,128,.10)" stroke="rgba(74,222,128,.16)" stroke-width=".7"/>`;
  svg += `<path d="M${histPts.replace(/ /g, ' L')}" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="1.5" stroke-linejoin="round"/>`;
  const fcPts = [`${px(fStart)},${py(hist.at(-1))}`, ...fc.map((v, i) => `${px(hist.length + i)},${py(v)}`)].join(' ');
  svg += `<path d="M${fcPts.replace(/ /g, ' L')}" fill="none" stroke="#4ADE80" stroke-width="1.8" stroke-linejoin="round"/>`;
  if (useReasoned && rawFc.some((v, i) => Math.abs(Number(v) - fc[i]) > 1e-9)) {
    const rawPts = [`${px(fStart)},${py(hist.at(-1))}`, ...rawFc.map((v, i) => `${px(hist.length + i)},${py(v)}`)].join(' ');
    svg += `<path d="M${rawPts.replace(/ /g, ' L')}" fill="none" stroke="rgba(255,255,255,.38)" stroke-width="1.2" stroke-dasharray="3 4" stroke-linejoin="round"/>`;
  }
  svg += `<path d="M${px(fStart)},${T} L${px(fStart)},${H - B}" stroke="rgba(255,255,255,.3)" stroke-width="1" stroke-dasharray="2 3"/>`;
  svg += `<circle cx="${px(fStart)}" cy="${py(hist.at(-1))}" r="2.8" fill="#fff" stroke="#0a0a0c" stroke-width="1.4"/>`;
  svg += `<circle cx="${px(n - 1)}" cy="${py(fc.at(-1))}" r="3" fill="#4ADE80" stroke="#0a0a0c" stroke-width="1.4"/>`;
  [0, Math.floor(n / 2), n - 1].forEach((i, k) => {
    const anchor = k === 0 ? 'start' : k === 2 ? 'end' : 'middle';
    svg += `<text class="chart-label" x="${px(i)}" y="${H - 6}" text-anchor="${anchor}">${esc(labels[i] || '')}</text>`;
  });
  svg += '</svg>';
  el.innerHTML = svg;
}

function scenarioChart(el, curves) {
  if (!el) return;
  const W = 420, H = 170, L = 26, R = 6, T = 8, B = 16;
  const n = Math.max(...curves.map(c => c.series.length));
  const max = Math.max(.001, ...curves.map(c => Math.max(...c.series)));
  const px = i => L + (i / Math.max(1, n - 1)) * (W - L - R);
  const py = v => T + (1 - v / max) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  for (let i = 0; i <= 3; i++) { const y = T + (i / 3) * (H - T - B); svg += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" stroke="rgba(255,255,255,.045)"/>`; }
  curves.forEach((c, k) => {
    const isBase = c.id === 'base';
    const color = isBase ? 'rgba(255,255,255,.75)' : ['#4ADE80', '#fbbf24', '#f87171', '#93c5fd', '#c4b5fd', '#f9a8d4'][k % 6];
    const d = c.series.map((v, i) => `${i ? 'L' : 'M'}${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
    svg += `<path d="${d}" fill="none" stroke="${color}" stroke-width="${isBase ? 1.7 : 1.1}" opacity="${isBase ? 1 : .75}" stroke-linejoin="round"/>`;
  });
  svg += '</svg>';
  el.innerHTML = svg;
}

/* ---------- map ---------- */
function renderMap() {
  const el = $('#indiaMap');
  if (!el || !S.map) return;
  const byMap = {};
  (S.meta?.states || []).forEach(s => { byMap[s.map_name || s.name] = s; });
  el.innerHTML = S.map.states.map(s => {
    const m = byMap[s.name];
    const base = m ? (.035 + (m.internet_pct / 100) * .13) : .06;
    return `<path class="map-state" data-state="${esc(s.name)}" style="--base:${base.toFixed(3)}" d="${s.path}"><title>${esc(s.name)}${m ? ` · internet ${m.internet_pct}%` : ''}</title></path>`;
  }).join('');
}

function updateMap(dayIdx) {
  if (!S.run || !S.map) return;
  const row = S.run.timeline[dayIdx] || S.run.timeline.at(-1);
  const tops = (row.top_states || []).map(x => x.name);
  $$('#indiaMap .map-state').forEach(p => {
    p.classList.toggle('hot', tops[0] === p.dataset.state);
    p.classList.toggle('warm', tops.slice(1).includes(p.dataset.state));
  });
  const box = $('#topStates');
  if (box) {
    box.innerHTML = (row.top_states || []).map(s => {
      const max = Math.max(.001, ...(row.top_states || []).map(x => x.adoption));
      return `<div class="top-state"><span>${esc(s.name)}</span><div class="bar"><i style="width:${Math.max(4, (s.adoption / max) * 100)}%"></i></div><b>${pct(s.adoption)}</b></div>`;
    }).join('');
  }
}

/* ---------- render helpers ---------- */
function agentById(id) { return S.run?.agents?.find(a => a.id === id); }

function metric(label, value, sub, cls = '', bar = null) {
  return `<div class="metric ${cls}">
    <div class="metric__label">${esc(label)}</div>
    <div class="metric__value">${value}</div>
    <div class="metric__sub">${esc(sub || '')}</div>
    ${bar != null ? `<span class="metric__bar" style="width:${clamp(bar, 0, 1) * 100}%"></span>` : ''}
  </div>`;
}

function renderWorld() {
  const r = S.run;
  if (!r) return;
  const row = r.timeline[S.day - 1];
  const s = r.summary;
  const placeAgent = r.agents.find(a => a.panel) || r.agents[0];
  $('#sceneDay').textContent = S.day;
  $('#scenePlace').textContent = `${placeAgent.city}, ${placeAgent.state}`;
  $('#timelineDay').textContent = `Day ${S.day}`;
  $('#timelineEnd').textContent = r.rounds;
  $('#dayRange').max = r.rounds;
  $('#dayRange').value = S.day;
  $('#hudAware').textContent = `awareness ${pct(row.awareness)}`;
  $('#hudAdopt').textContent = `adoption ${pct(row.adoption)}`;
  $('#hudSent').textContent = `sentiment ${signed(row.sentiment)}`;
  $('#mapMeta').textContent = `Day ${S.day} · ${row.addressable} addressable`;

  $('#worldMetrics').innerHTML = [
    metric('Population', r.population, `${r.rounds} rounds · seed ${r.seed}`),
    metric('Aware', pct(row.awareness), 'of the synthetic population', '', row.awareness),
    metric('Adopted', pct(row.adoption), `${Math.round(row.conversion * 100)}% of addressable pool`, 'metric--green', row.conversion),
    metric('Sentiment', signed(row.sentiment), sentimentWord(row.sentiment), row.sentiment < 0 ? 'metric--red' : ''),
    metric('Rejected', pct(row.rejected / Math.max(1, row.addressable)), `${row.rejected} people said no`, 'metric--red'),
    metric('Verdict', s.verdict, `${pct(s.confidence, 0)} confidence · ${s.best_tier ? `T${s.best_tier} leads` : ''}`),
  ].join('');

  $('#worldChart').innerHTML = '';
  lineChart($('#worldChart'), [
    { values: r.timeline.map(x => x.awareness), color: 'rgba(255,255,255,.62)', width: 1.5 },
    { values: r.timeline.map(x => x.adoption), color: '#4ADE80', width: 1.9, area: 'rgba(74,222,128,.07)' },
    { values: r.timeline.map(x => (x.sentiment + 1) / 2), color: 'rgba(255,255,255,.24)', width: 1.1, dash: '3 4' },
  ], { marker: S.day - 1, labels: r.timeline.map(x => `D${x.day}`) });

  $('#worldVerdict').innerHTML = `
    <div>
      <span class="panel__eyebrow">Read</span>
      <span class="verdict-badge ${s.verdict}">${s.verdict}</span>
      <p class="verdict-headline">${esc(s.headline)}</p>
      <p class="verdict-copy">${esc(r.report.summary || '')}</p>
    </div>
    <div class="verdict-tiers">
      ${[1, 2, 3, 4].map(t => `<div class="verdict-tier"><span>Tier ${t}</span><b>${pct(s.tier_adoption[String(t)] || 0)}</b><div class="bar"><i style="width:${clamp((s.tier_adoption[String(t)] || 0) * 6, 2, 100)}%"></i></div></div>`).join('')}
    </div>`;

  renderFeed(row);
  updateMap(S.day - 1);
  setupAgentField();
  renderVenn();
  initTownAgents();
  if (townState.raf) cancelAnimationFrame(townState.raf);
  townState.raf = requestAnimationFrame(drawTown);
}

function truncate(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

function renderFeed(row) {
  const r = S.run;
  const items = [];
  (r.events || []).filter(e => e.day <= S.day).forEach(e => items.push({ day: e.day, cls: 'event', title: e.text, meta: e.label || 'scenario event' }));
  r.posts.filter(p => p.day === S.day).slice(0, 5).forEach(p => items.push({
    day: p.day, cls: p.tone === 'negative' || p.flagged ? 'reject' : 'adopt',
    title: `${p.name}: ${truncate(p.text.replace(/[#*]/g, ''), 110)}`,
    meta: `${p.platform} · T${p.tier} · ${p.city} · ${p.likes} likes`,
  }));
  r.agents.filter(a => a.adopt_day === S.day).slice(0, 4).forEach(a => items.push({
    day: S.day, cls: 'adopt', title: `${a.name} adopted. ${a.occupation} in ${a.city}.`,
    meta: `“${a.quote}”`,
  }));
  r.agents.filter(a => a.rejected && a.adopt_day == null).slice(0, 2).forEach(a => items.push({
    day: Math.max(1, S.day - 1), cls: 'reject', title: `${a.name} rejected: ${a.rejection_reason || 'the failure mode'}.`,
    meta: `${a.occupation} · ${a.city} · T${a.tier}`,
  }));
  items.sort((a, b) => b.day - a.day);
  $('#worldFeed').innerHTML = items.length ? items.slice(0, 12).map(i => `
    <div class="feed-item feed-item--${i.cls}"><span class="feed-item__dot"></span><span class="feed-item__day">D${i.day}</span>
    <div class="feed-item__body"><div class="feed-item__title">${esc(i.title)}</div><div class="feed-item__meta">${esc(i.meta)}</div></div></div>`).join('')
    : `<p class="small-copy" style="padding:10px 0">No activity yet. Move the timeline forward.</p>`;
}

/* ---------- social ---------- */
function renderSocial() {
  const r = S.run;
  if (!r) return;
  $('#socialStats').innerHTML = `
    <div class="vstat"><span>posts</span><b>${r.posts.length}</b></div>
    <div class="vstat"><span>reach</span><b>${compact(r.posts.reduce((a, p) => a + p.reach, 0))}</b></div>
    <div class="vstat"><span>sentiment</span><b>${signed(r.summary.sentiment)}</b></div>`;
  const platforms = ['all', ...Object.keys(r.platforms)];
  $('#platformFilters').innerHTML = platforms.map(p => `<button class="chip ${S.social.platform === p ? 'active' : ''}" data-platform="${esc(p)}">${p === 'all' ? 'All' : esc(p)}</button>`).join('');
  renderPostList();
  renderSocialSide();
}

function renderPostList() {
  const r = S.run;
  if (!r) return;
  let posts = r.posts.slice();
  if (S.social.platform !== 'all') posts = posts.filter(p => p.platform === S.social.platform);
  if (S.social.tier) posts = posts.filter(p => String(p.tier) === S.social.tier);
  if (S.social.sort === 'recent') posts.sort((a, b) => b.day - a.day || b.likes - a.likes);
  else if (S.social.sort === 'contested') posts.sort((a, b) => Math.abs(b.stance - .5) - Math.abs(a.stance - .5));
  else posts.sort((a, b) => (b.likes + b.shares * 3 + b.reach * .01) - (a.likes + a.shares * 3 + a.reach * .01));
  const shown = posts.slice(0, S.social.limit);
  $('#socialFeed').innerHTML = shown.map(p => postCard(p)).join('') || `<p class="small-copy" style="padding:18px">No posts match this filter.</p>`;
  $('#loadMorePosts').style.display = posts.length > shown.length ? 'block' : 'none';
  $('#loadMorePosts').textContent = `Load more · ${posts.length - shown.length} remaining`;
}

function postCard(p) {
  const a = agentById(p.agent_id) || p;
  const t = p.tone === 'negative' ? 'neg' : p.tone === 'positive' ? 'pos' : '';
  return `<article class="post" data-agent="${esc(p.agent_id)}">
    <div class="post__head">
      <span class="avatar" data-agent-open="${esc(p.agent_id)}" title="Open citizen file">${avatar(a)}</span>
      <div class="post__who">
        <div class="post__name">${esc(p.name)} <i>@${esc(p.handle)}</i></div>
        <div class="post__sub">${esc(p.occupation)} · ${esc(p.city)}, ${esc(p.state)} · ${esc(p.language)}</div>
      </div>
      <div class="post__badges">
        <span class="tag tag--platform">${esc(p.platform)}</span>
        <span class="${tierClass(p.tier)}">T${p.tier}</span>
        <span class="tag">D${p.day}</span>
      </div>
    </div>
    <div class="post__body">${esc(p.text)}${p.translation ? `<span class="post__translation">${esc(p.translation)}</span>` : ''}</div>
    ${p.hashtags?.length ? `<div class="post__tags">${p.hashtags.map(h => `<span>${esc(h)}</span>`).join('')}</div>` : ''}
    ${p.flagged && p.fact_check ? `<div class="factcheck">⚠ ${esc(p.fact_check)}</div>` : ''}
    <div class="post__stats">
      <span>♡ <b>${compact(p.likes)}</b></span><span>↗ <b>${compact(p.shares)}</b></span><span>◌ <b>${compact(p.reach)}</b></span>
      <span>${p.thread?.length ? `<button data-thread="${esc(p.id)}">thread (${p.thread.length})</button>` : ''}</span>
      <span class="post__actions"><button data-agent-open="${esc(p.agent_id)}">Ask ${esc(p.name.split(' ')[0])} →</button></span>
    </div>
    <div class="thread" id="thread-${esc(p.id)}">${(p.thread || []).map(c => `<div class="thread__item"><b>${esc(c.name)}</b> · T${c.tier} · ${esc(c.city)}<br>${esc(c.text)}</div>`).join('')}</div>
  </article>`;
}

function renderSocialSide() {
  const r = S.run;
  const words = {};
  r.posts.forEach(p => (p.hashtags || []).forEach(h => { words[h] = (words[h] || 0) + 1; }));
  const top = Object.entries(words).sort((a, b) => b[1] - a[1]).slice(0, 7);
  const maxW = Math.max(1, ...top.map(x => x[1]));
  $('#trendingWords').innerHTML = top.map(([w, c], i) => `<div class="trend"><span class="trend__rank">${String(i + 1).padStart(2, '0')}</span><span class="trend__word">${esc(w)}</span><div class="trend__bar"><i style="width:${(c / maxW) * 100}%"></i></div><span class="trend__val">${c}</span></div>`).join('') || '<p class="small-copy">No hashtags yet.</p>';

  const tiers = r.report.segments.tier || [];
  $('#moodByTier').innerHTML = [1, 2, 3, 4].map(t => {
    const row = tiers.find(x => String(x.name) === String(t));
    const v = row ? row.sentiment : 0;
    const p = (v + 1) / 2;
    return `<div class="mood"><span>T${t}</span><div class="bar"><i style="width:${p * 100}%;background:${v >= 0 ? 'rgba(74,222,128,.55)' : 'rgba(248,113,113,.55)'}"></i></div><b>${signed(v)}</b></div>`;
  }).join('');

  const total = Math.max(1, Object.values(r.platforms).reduce((a, b) => a + b, 0));
  $('#platformMix').innerHTML = Object.entries(r.platforms).slice(0, 8).map(([p, c]) => `<div class="mix"><i></i><span style="flex:0 0 70px">${esc(p)}</span><div class="bar"><b style="width:${(c / total) * 100}%"></b></div><span>${Math.round((c / total) * 100)}%</span></div>`).join('');
}

function compact(n) {
  n = Number(n || 0);
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}m`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(Math.round(n));
}

/* ---------- debate ---------- */
function renderDebate() {
  const r = S.run;
  if (!r) return;
  $('#debateMotion').textContent = `“${r.topic.motion || 'This will work in India.'}”`;
  const speakers = [];
  const seen = new Set();
  (r.debate || []).forEach(m => { if (m.speaker_id !== 'moderator' && !seen.has(m.speaker_id)) { seen.add(m.speaker_id); speakers.push(m); } });
  $('#debateSpeakers').innerHTML = speakers.map(m => {
    const side = m.side === 'con' ? 'con' : 'pro';
    return `<div class="speaker" data-agent-open="${esc(m.speaker_id)}"><span class="avatar">${avatar(agentById(m.speaker_id))}</span><div class="speaker__body"><div class="speaker__name">${esc(m.speaker_name)}</div><div class="speaker__role">${esc(m.speaker_role)}</div></div><span class="speaker__side ${side}">${side}</span></div>`;
  }).join('');
  $('#debateSpeakers').innerHTML = speakers.map(m => {
    const side = m.side === 'con' ? 'con' : 'pro';
    return `<div class="speaker" data-agent-open="${esc(m.speaker_id)}"><span class="avatar">${avatar(agentById(m.speaker_id))}</span><div class="speaker__body"><div class="speaker__name">${esc(m.speaker_name)}</div><div class="speaker__role">${esc(m.speaker_role)}</div></div><span class="speaker__side ${side}">${side}</span></div>`;
  }).join('');
  $('#debateTranscript').innerHTML = (r.debate || []).map((m, i) => debateMsg(m, i)).join('');
  updateDebateBalance();
}

function debateMsg(m, i) {
  if (m.speaker_id === 'moderator') {
    return `<div class="msg msg--moderator" data-i="${i}"><div class="msg__body"><div class="msg__text">${esc(m.text)}</div></div></div>`;
  }
  const side = m.type === 'con' ? 'con' : 'pro';
  const right = side === 'con';
  const ev = m.evidence ? `<div class="msg__ev">↳ ${esc(m.evidence.claim)}: <b>${esc(m.evidence.value)} ${esc(m.evidence.unit)}</b> · ${esc(m.evidence.org)}, ${esc(m.evidence.year)}</div>` : '';
  return `<div class="msg msg--${side} ${right ? 'msg--right' : ''}" data-i="${i}">
    <span class="avatar msg__avatar" data-agent-open="${esc(m.speaker_id)}">${avatar(agentById(m.speaker_id))}</span>
    <div class="msg__body">
      <div class="msg__who"><b>${esc(m.speaker_name)}</b><span>${esc(m.speaker_role)}</span></div>
      <div class="msg__text">${esc(m.text)}${ev}</div>
      <div class="msg__conf"><i><b style="width:${Math.round((m.confidence || .7) * 100)}%"></b></i> ${Math.round((m.confidence || .7) * 100)}% confidence · ${esc(m.type)}</div>
    </div></div>`;
}

let debatePlay = null;
function playDebate() {
  const msgs = $$('#debateTranscript .msg');
  if (!msgs.length) return;
  if (debatePlay) { clearInterval(debatePlay); debatePlay = null; msgs.forEach(m => m.style.display = ''); $('#playDebate').innerHTML = `${ICONS.play}Play debate`; return; }
  msgs.forEach(m => m.style.display = 'none');
  let i = 0;
  $('#playDebate').innerHTML = `${ICONS.pause}Stop`;
  const tick = () => {
    if (i >= msgs.length) { clearInterval(debatePlay); debatePlay = null; $('#playDebate').innerHTML = `${ICONS.play}Replay`; return; }
    msgs[i].style.display = ''; msgs[i].scrollIntoView({ block: 'nearest', behavior: 'smooth' }); i++;
  };
  tick();
  debatePlay = setInterval(tick, 1100);
}

function updateDebateBalance() {
  const r = S.run; if (!r) return;
  const msgs = r.debate || [];
  const pro = msgs.filter(m => m.speaker_id !== 'moderator' && m.side !== 'con').length;
  const con = msgs.filter(m => m.side === 'con').length;
  const total = pro + con || 1;
  const pctPro = (pro / total) * 100;
  const bar = $('#debateBalanceBar'); if (bar) bar.style.width = `${pctPro}%`;
  const val = $('#debateBalanceVal'); if (val) val.textContent = `${pro} pro · ${con} con`;
}

async function challengeDebate() {
  const r = S.run;
  if (!r) { toast('Run a simulation first.'); return; }
  const transcript = $('#debateTranscript');
  const msgs = $$('#debateTranscript .msg');
  const last = msgs.length ? msgs[msgs.length - 1] : null;
  const lastText = last ? (last.querySelector('.msg__text')?.textContent || '') : (r.topic.motion || '');
  const speakers = (r.debate || []).filter(m => m.speaker_id !== 'moderator');
  const lastSide = last && last.classList.contains('msg--con') ? 'con' : 'pro';
  const opposite = speakers.filter(m => (m.side === 'con') !== (lastSide === 'con'));
  const pick = opposite.length ? opposite[Math.floor(Math.random() * opposite.length)] : speakers[0];
  if (!pick) { toast('No speaker available.'); return; }
  const agent = agentById(pick.speaker_id);
  if (!agent) { toast('Speaker not found.'); return; }
  const btn = $('#challengeDebate');
  const label = btn.innerHTML;
  btn.disabled = true; btn.textContent = 'Challenging…';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brief: r.brief, agent_id: pick.speaker_id, agent,
        message: `Challenge this claim in the debate: "${String(lastText).slice(0, 200)}". Give one counter-argument with evidence.`,
        seed: r.seed, state: r.focus_state || null,
      }),
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Chat failed');
    const side = pick.side === 'con' ? 'con' : 'pro';
    const right = side === 'con';
    const html = `<div class="msg msg--${side} ${right ? 'msg--right' : ''} msg--challenge">
      <span class="avatar msg__avatar" data-agent-open="${esc(pick.speaker_id)}">${avatar(agent)}</span>
      <div class="msg__body">
        <div class="msg__who"><b>${esc(agent.name)}</b><span>${esc(agent.occupation)} · challenge</span></div>
        <div class="msg__text">${esc(d.reply || 'I disagree. Let us test it.')}</div>
      </div></div>`;
    transcript.insertAdjacentHTML('beforeend', html);
    const added = transcript.lastElementChild;
    if (added) { added.style.display = 'none'; requestAnimationFrame(() => { added.style.display = ''; added.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }); }
    toast('Challenge added to the transcript.');
    ops('llm', `challenge: ${agent.name} countered ${pick.speaker_name || pick.speaker_id}`);
  } catch (e) {
    toast(e.message);
  } finally {
    btn.disabled = false; btn.innerHTML = label; injectIcons(btn);
  }
}

/* ---------- focus ---------- */
function renderFocus() {
  const r = S.run;
  if (!r) return;
  const first = S.focusRounds[0];
  const members = [];
  const seen = new Set();
  (r.focus_group || []).forEach(g => { if (!seen.has(g.agent_id)) { seen.add(g.agent_id); members.push(g); } });
  $('#focusMembers').innerHTML = members.map(g => `<div class="member" data-agent-open="${esc(g.agent_id)}"><span class="avatar">${avatar(agentById(g.agent_id))}</span><div class="member__body"><div class="member__name">${esc(g.name)}</div><div class="member__role">${esc(g.role)}</div></div><div class="member__stance"><div class="bar"><i style="width:${g.stance * 100}%"></i></div><span>${Math.round(g.stance * 100)}</span></div></div>`).join('');
  $('#focusMeta').textContent = `${members.length} participants · ${S.focusRounds.length} round${S.focusRounds.length > 1 ? 's' : ''}`;
  renderFocusChat();
}

function renderFocusChat() {
  const box = $('#focusChat');
  box.innerHTML = S.focusRounds.map((round, ri) => `
    <div class="focus-question" style="margin:0 0 4px;padding:0 0 8px;border-bottom:1px solid rgba(255,255,255,.06)">
      <span style="color:rgba(255,255,255,.28);font-size:8px;letter-spacing:.14em;text-transform:uppercase;flex:0 0 auto">Round ${ri + 1}</span>
      <b>${esc(round.question)}</b>
    </div>
    ${(round.group || []).map(g => `<div class="fmsg"><span class="avatar">${avatar(agentById(g.agent_id))}</span><div class="fmsg__body">
      <div class="fmsg__who"><b>${esc(g.name)}</b><span>${esc(g.role)}</span><span class="tag">${esc(g.stance_label)}</span></div>
      <div class="fmsg__text">${esc(g.reply)}</div>
      <div class="fmsg__inner"><button class="fmsg__toggle" data-mono="${ri}-${esc(g.agent_id)}">Inner monologue · ${Math.round((g.confidence || .7) * 100)}% confidence</button><div class="fmsg__mono" id="mono-${ri}-${esc(g.agent_id)}">${(g.inner_monologue || []).map(x => `<div>${esc(x)}</div>`).join('')}</div></div>
      ${g.evidence ? `<div class="fmsg__ev">↳ ${esc(g.evidence.claim)}: ${esc(g.evidence.value)} ${esc(g.evidence.unit)} (${esc(g.evidence.org)}, ${esc(g.evidence.year)})</div>` : ''}
    </div></div>`).join('')}
  `).join('');
  box.scrollTop = box.scrollHeight;
}

/* ---------- cognition ---------- */
function renderPerception() {
  const r = S.run; if (!r) return;
  const co = r.cognitive || {};
  const s = r.summary || {};

  $('#perceptionMetrics').innerHTML = [
    metric('Bass p (innovator)', co.bass_p ?? '—', `q (imitation) ${co.bass_q ?? '—'} · R² ${co.bass_r2 ?? '—'}`),
    metric('Consolidation rate', pct(co.consolidation_rate || 0, 0), 'agents with ≥5 exposures'),
    metric('Susceptibility', Number(co.susceptibility_mean || 0).toFixed(1), 'Bearden interpersonal index'),
    metric('Need for cognition', Number(co.need_for_cognition_mean || 0).toFixed(1), 'Cacioppo & Petty deliberate index'),
    metric('Rogers: early adopters', String((co.rogers || {}).early_adopter ?? 0), 'before mass adoption'),
    metric('Bootstrap CI', co.bootstrap_adoption_ci?.lower != null ? `±${pct(co.bootstrap_adoption_ci.half_width, 1)}` : '—', `lower ${pct(co.bootstrap_adoption_ci?.lower || 0, 1)} · upper ${pct(co.bootstrap_adoption_ci?.upper || 0, 1)}`),
  ].join('');

  $('#bassView').innerHTML = `
    <div class="causal-row"><span>Innovator coefficient p</span><b>${co.bass_p ?? '—'}</b></div>
    <div class="causal-row"><span>Imitation coefficient q</span><b>${co.bass_q ?? '—'}</b></div>
    <div class="causal-row"><span>Fit quality (R²)</span><b class="${(co.bass_r2 || 0) >= 0.3 ? 'good' : 'warn'}">${co.bass_r2 ?? '—'}</b></div>
    <div class="causal-row"><span>Peak adoption day</span><b>${co.bass_peak_day ?? '—'}</b></div>
    <div class="causal-row"><span>Bass interpretation</span><b>${esc(co.bass_interpretation || '—')}</b></div>
    <p class="causal-note">Bass 1969: N(t) = M · (1 − exp(−(p + q·N(t)/M)·t)). Fitted on simulated cumulative adoption; M = addressable pool. Weak R² means the curve is not Bass-shaped at this horizon — information, not failure.</p>`;

  // Rogers chart — bar chart via lineChart with area? Use a custom SVG bar chart
  const buckets = co.rogers || {};
  const rogEl = $('#rogersChart');
  if (rogEl) {
    const total = Object.values(buckets).reduce((a, b) => a + b, 0) || 1;
    const items = [
      ['Innovators', buckets.innovator || 0, '#4ADE80'],
      ['Early adopters', buckets.early_adopter || 0, '#8ae2a8'],
      ['Early majority', buckets.early_majority || 0, 'rgba(255,255,255,.55)'],
      ['Late majority', buckets.late_majority || 0, 'rgba(255,255,255,.3)'],
      ['Laggards', buckets.laggard || 0, 'rgba(255,255,255,.15)'],
    ];
    const maxB = Math.max(...items.map(i => i[1]), 1);
    rogEl.innerHTML = `<svg viewBox="0 0 620 220" preserveAspectRatio="none">
      ${items.map(([label, count, color], i) => {
        const y = 18 + i * 40, w = (count / maxB) * 480 + 4;
        return `<text x="2" y="${y + 14}" fill="rgba(255,255,255,.6)" font-size="10">${esc(label)}</text>
          <rect x="110" y="${y}" width="${w}" height="22" rx="3" fill="${color}" opacity=".75"/>
          <text x="${116 + w}" y="${y + 15}" fill="rgba(255,255,255,.7)" font-size="11">${count}</text>`;
      }).join('')}
      <text x="2" y="216" fill="rgba(255,255,255,.3)" font-size="8">Order of adoption waves · ${total} adopters</text>
    </svg>`;
  }

  // Prospect S-curve
  const prosEl = $('#prospectChart');
  if (prosEl) {
    const xs = [-100, -75, -50, -25, -10, 0, 10, 25, 50, 75, 100];
    const lambda = 2.25, alpha = 0.88;
    const ys = xs.map(x => x >= 0 ? Math.pow(x, alpha) : -lambda * Math.pow(-x, alpha));
    lineChart(prosEl, [{ values: ys, color: '#a8d8ff', width: 1.8, area: 'rgba(168,216,255,.08)' }], {
      min: -250, max: 100, fmt: v => v.toFixed(0), labels: xs.map(String), height: 240,
    });
    prosEl.insertAdjacentHTML('beforeend', `<text x="310" y="14" fill="rgba(255,255,255,.4)" font-size="9">λ = 2.25 · α = 0.88</text>`);
  }

  // Mere exposure curve
  const mereEl = $('#mereExposureChart');
  if (mereEl) {
    const values = Array.from({ length: 21 }, (_, i) => 0.35 * (1 - Math.pow(0.5, i / 8)));
    lineChart(mereEl, [{ values, color: '#fbbf24', width: 1.8, area: 'rgba(251,191,36,.09)' }], {
      min: 0, max: 0.35, fmt: v => v.toFixed(2), labels: Array.from({ length: 21 }, (_, i) => String(i)), height: 240,
    });
    mereEl.insertAdjacentHTML('beforeend', `<text x="290" y="20" fill="rgba(255,255,255,.45)" font-size="9">Zajonc habituation: effect saturates ~15 exposures</text>`);
  }
}

function renderCognition() {
  const r = S.run;
  if (!r) return;
  const tiers = S.meta?.tiers || [];
  $('#tierCards').innerHTML = tiers.map(t => {
    const ad = r.summary.tier_adoption[String(t.id)] || 0;
    return `<div class="tier-card"><span class="tier-card__n">0${t.id}</span><h3>${esc(t.label)} · ${esc(t.name)}</h3><div class="tier-card__sub">${Math.round(t.share * 100)}% of the sample</div>
      <p>${esc(t.worldview)}</p>
      <div class="tier-card__row"><span>Decision</span><b>${esc(truncate(t.decision, 70))}</b></div>
      <div class="tier-card__row"><span>Money</span><b>${esc(truncate(t.money, 60))}</b></div>
      <div class="tier-card__adopt"><div class="bar"><i style="width:${clamp(ad * 6, 2, 100)}%"></i></div><b>${pct(ad)} adopted</b></div>
    </div>`;
  }).join('');

  const traits = (r.report.trait_correlations || []).slice(0, 8);
  $('#traitDrivers').innerHTML = traits.map(t => barRow(t.trait.replace(/_/g, ' '), t.corr)).join('') || '<p class="small-copy">Not enough variance in this run.</p>';
  const biases = (r.report.bias_correlations || []).slice(0, 8);
  $('#biasDrivers').innerHTML = biases.map(b => barRow(b.label, b.corr)).join('') || '<p class="small-copy">Not enough variance in this run.</p>';
  renderAgents();
}

function barRow(label, corr) {
  const w = Math.min(50, Math.abs(corr) * 100);
  return `<div class="barrow"><span>${esc(label)}</span><div class="bar"><i class="${corr < 0 ? 'neg' : ''}" style="${corr < 0 ? 'right:50%' : 'left:50%'};width:${w}%"></i></div><b>${signed(corr)}</b></div>`;
}

function renderAgents() {
  const r = S.run;
  if (!r) return;
  const q = ($('#agentSearch').value || '').toLowerCase();
  const tier = $('#agentTier').value;
  let agents = r.agents.filter(a => {
    if (tier && String(a.tier) !== tier) return false;
    if (!q) return true;
    return `${a.name} ${a.city} ${a.state} ${a.occupation} ${a.language}`.toLowerCase().includes(q);
  });
  const total = agents.length;
  agents = agents.slice(0, S.agentLimit);
  $('#agentGrid').innerHTML = agents.map(a => {
    const decision = a.decision === 'Adopted' ? 'adopted' : a.decision === 'Rejected' ? 'rejected' : '';
    return `<div class="agent-card" data-agent-open="${esc(a.id)}"><span class="avatar">${avatar(a)}</span><div class="agent-card__body"><div class="agent-card__name">${esc(a.name)}</div><div class="agent-card__role">${esc(a.occupation)} · ${esc(a.city)} · ${esc(a.language)}</div></div><span class="${tierClass(a.tier)}">T${a.tier}</span><span class="agent-card__tag ${decision}">${esc(a.decision)}</span></div>`;
  }).join('') || '<p class="small-copy" style="padding:16px">No citizens match.</p>';
  $('#loadMoreAgents').style.display = total > agents.length ? 'block' : 'none';
  $('#loadMoreAgents').textContent = `Show more · ${total - agents.length} remaining`;
}

/* ---------- forecast ---------- */
function populateForecastTopics() {
  const sel = $('#forecastTopic');
  if (!S.meta || sel.options.length) return;
  sel.innerHTML = S.meta.topics.map(t => `<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('');
  if (S.run) sel.value = S.run.topic.id;
}

async function loadForecast() {
  populateForecastTopics();
  const topic = $('#forecastTopic').value || S.run?.topic?.id || 'ev-car';
  const horizon = Number($('#forecastHorizon').value || 12);
  const box = $('#forecastChart');
  box.innerHTML = '<div class="skeleton" style="height:100%;width:100%"></div>';
  try {
    const res = await fetch(`/api/forecast?topic_id=${encodeURIComponent(topic)}&horizon=${horizon}`);
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Forecast failed');
    S.forecast = d;
    $('#forecastTitle').textContent = d.topic.label;
    $('#forecastUnit').textContent = d.topic.unit || d.topic.category || '';
    const aug = d.test_time_augmentation || {};
    const isTfm = d.engine.name.startsWith('timesfm');
    $('#forecastEngine').textContent = isTfm
      ? `TimesFM 3.0 · ${aug.augmented ? 'aug3' : 'zero-shot'}`
      : 'Fallback baseline';
    forecastChart(box, d);
    const s = d.summary;
    const r = d.reasoned || {};
    const hasR = !!r.available;
    const rEnd = hasR && r.point?.length ? Number(r.point.at(-1)) : null;
    const corr = hasR && Number.isFinite(Number(r.correction_pct)) ? Number(r.correction_pct) : 0;
    const conf = hasR && Number.isFinite(Number(r.confidence)) ? Math.round(Number(r.confidence) * 100) : null;
    $('#forecastStats').innerHTML = `
      <div class="fstat"><span>Last actual</span><b>${s.last_actual}</b><i>${esc(d.history.labels.at(-1))}</i></div>
      <div class="fstat"><span>TimesFM end</span><b>${s.end_point}</b><i>raw foundation</i></div>
      <div class="fstat"><span>Audited end</span><b>${rEnd == null ? '—' : rEnd.toFixed(2)}</b><i>${hasR ? `${signed(corr, 2)}% vs raw` : 'audit unavailable'}</i></div>
      <div class="fstat"><span>Confidence</span><b>${conf == null ? '—' : `${conf}%`}</b><i>${hasR ? esc(r.direction || '') : 'no audit'}</i></div>
      <div class="fstat"><span>80% band</span><b>${s.band_width_end}</b><i>p10–p90 at horizon</i></div>`;
    const augText = aug.augmented
      ? `Test-time augmentation is active: the path averages TimesFM on the level, log and first-differenced series (${(aug.views || []).join(' + ')}).`
      : 'Test-time augmentation is inactive for this series; the path is the raw foundation output.';
    $('#forecastNote').textContent = `${s.trend_note} The shaded region is the 10th–90th percentile band from ${isTfm ? 'TimesFM 3.0, zero-shot' : 'a damped-trend fallback'} — not a probability of any single outcome. ${augText}`;
    $('#forecastKV').innerHTML = `<div><span>Backend</span><b>${esc(d.engine.backend)}</b></div><div><span>Checkpoint</span><b>${esc(d.engine.checkpoint)}</b></div><div><span>Horizon</span><b>${d.engine.horizon_months} months</b></div><div><span>Views</span><b>${esc((aug.views || ['level']).join(' · '))}</b></div>`;
    $('#forecastLicense').textContent = d.engine.license_note + ' ' + d.engine.caveat;

    // Reasoning audit: named rules, hypothesis weights and the falsifier. The
    // point path is the foundation path unless a named rule fired.
    const modeLabel = { foundation_first_with_critique: 'foundation first', foundation_ensemble_blend: 'ensemble blend', ensemble_only: 'ensemble only' }[r.mode] || (hasR ? r.mode : 'unavailable');
    $('#forecastMode').textContent = modeLabel;
    if (!hasR) {
      $('#forecastReason').innerHTML = `<div class="reason-check warn"><i>!</i><div><b>No audit</b><span>${esc(r.reason || 'The reasoning layer did not return a path.')}</span></div></div>`;
    } else {
      const weights = Object.entries(r.weights || {}).map(([k, v]) => `${k} ${Math.round(Number(v) * 100)}%`).join(' · ');
      const rows = (r.critique || []).map((c, i) => `<div class="reason-check ${i === 0 && /No rule fired/i.test(c) ? 'ok' : 'warn'}"><i>${i === 0 && /No rule fired/i.test(c) ? '✓' : '!'}</i><div><b>${i === 0 && /No rule fired/i.test(c) ? 'No rule fired' : `Rule ${i + 1}`}</b><span>${esc(c)}</span></div></div>`).join('');
      $('#forecastReason').innerHTML = `
        <div class="reason-check"><i>≡</i><div><b>Hypothesis weights</b><span>${esc(weights)} · foundation ${Math.round(Number(r.foundation_weight || 0) * 100)}%</span></div></div>
        <div class="reason-check"><i>σ</i><div><b>Rolling error vs drift</b><span>${esc(Object.entries(r.rolling_mae || {}).map(([k, v]) => `${k} ${v}`).join(' · '))} · skill ${signed(Number(r.skill_vs_drift || 0), 2)}</span></div></div>
        ${rows}
        <div class="reason-check"><i>✕</i><div><b>Falsifier</b><span>${esc(r.falsifier || '')}</span></div></div>`;
    }
  } catch (err) {
    box.innerHTML = `<p class="small-copy" style="padding:20px">Forecast unavailable: ${esc(err.message)}</p>`;
    $('#forecastEngine').textContent = 'Unavailable';
  }
}

async function loadScenarios() {
  if (!S.run) return;
  const el = $('#scenarioChart');
  el.innerHTML = '<div class="skeleton" style="height:100%;width:100%"></div>';
  try {
    const res = await fetch('/api/scenarios', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief: S.run.brief, n_agents: 160, rounds: S.run.rounds, seed: S.run.seed })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Scenario run failed');
    S.scenarios = d.curves;
    scenarioChart(el, d.curves);
    $('#scenarioList').innerHTML = d.curves.map(c => `<div class="scenario-row"><span class="scenario-dot" style="background:${c.id === 'base' ? 'rgba(255,255,255,.6)' : 'rgba(74,222,128,.6)'}"></span><span>${esc(c.label)}</span><b>${pct(c.adoption)}</b><i class="${c.delta_adoption < 0 ? 'neg' : ''}">${c.delta_adoption > 0 ? '+' : ''}${c.delta_adoption}pp</i></div>`).join('');
  } catch (err) {
    el.innerHTML = `<p class="small-copy" style="padding:12px">${esc(err.message)}</p>`;
  }
}

/* ---------- evidence ---------- */
function renderEvidence() {
  const ev = S.meta?.evidence || [];
  const domains = [...new Set(ev.map(e => e.domain))].sort();
  $('#domainChips').innerHTML = ['', ...domains].map(d => `<button class="chip ${S.evidenceDomain === d ? 'active' : ''}" data-domain="${esc(d)}">${d ? esc(d) : 'All domains'}</button>`).join('');
  let rows = ev.slice();
  if (S.evidenceDomain) rows = rows.filter(e => e.domain === S.evidenceDomain);
  if (S.evidenceQuery) {
    const q = S.evidenceQuery.toLowerCase();
    rows = rows.filter(e => JSON.stringify(e).toLowerCase().includes(q));
  }
  const cited = new Set((S.run?.evidence || []).map(e => e.id));
  rows.sort((a, b) => (cited.has(b.id) ? 1 : 0) - (cited.has(a.id) ? 1 : 0));
  $('#evidenceCount').textContent = `${rows.length} cards`;
  $('#evidenceGrid').innerHTML = rows.map(e => `<article class="ev-card">
    <div class="ev-card__domain">${esc(e.domain)}${cited.has(e.id) ? ' · cited in run' : ''}</div>
    <div class="ev-card__claim">${esc(e.claim)}</div>
    <div class="ev-card__value">${esc(e.value)} <small>${esc(e.unit)}</small></div>
    <div class="ev-card__source"><b>${esc(e.org)}</b> · ${e.year}<br>${esc(e.source)}</div>
    ${e.note ? `<div class="ev-card__note">${esc(e.note)}</div>` : ''}
    ${e.url ? `<a class="ev-card__link" href="${esc(e.url)}" target="_blank" rel="noopener" title="Open source">↗</a>` : ''}
  </article>`).join('') || '<p class="small-copy">No evidence matches.</p>';
}

/* ---------- report ---------- */
function renderReport() {
  const r = S.run;
  if (!r) return;
  const s = r.summary, rep = r.report;
  $('#reportHead').innerHTML = `
    <span class="verdict-badge ${s.verdict}">${s.verdict}</span>
    <h2 class="report-headline">${esc(rep.headline)}</h2>
    <p class="report-sub">${esc(rep.summary)}</p>`;
  $('#reportMain').innerHTML = `
    <h3>What to do</h3>
    <ol class="rec-list">${(rep.recommendations || []).map((x, i) => `<li><b>0${i + 1}</b><span>${esc(x)}</span></li>`).join('')}</ol>
    <div class="driver-list">${(rep.drivers || []).map(d => `<div>${esc(d)}</div>`).join('')}</div>
    <h3 style="margin-top:20px">Objections that matter</h3>
    <table class="report-table"><thead><tr><th>Reason</th><th>People</th><th>Tier</th></tr></thead><tbody>
      ${(rep.objections || []).map(o => `<tr><td>${esc(o.reason)}</td><td>${o.count}</td><td>${esc(o.tier)}</td></tr>`).join('') || '<tr><td colspan="3">No active rejection in this run.</td></tr>'}
    </tbody></table>
    <h3 style="margin-top:20px">Next experiments</h3>
    <div class="exp-list">${(rep.next_experiments || []).map(x => `<div>↳ ${esc(x)}</div>`).join('')}</div>
    ${(r.context?.facts || []).length ? `<div class="report-ctx"><h3>Context retrieved for this run</h3><div class="context-list">${r.context.facts.map(c => `<div class="ctx-item"><b>${esc(c.claim)}</b><span>${esc(truncate(c.detail || c.value || '', 190))}</span><em>${esc((c.sources || []).map(x => `${x.org || x.title} ${x.year || ''}`).join(' · '))}</em></div>`).join('')}</div></div>` : ''}`;

  $('#reportVerdict').innerHTML = `
    <div class="panel__head"><div><span class="panel__eyebrow">Verdict</span><h2 class="panel__title">${esc(s.verdict)}</h2></div><span class="tag">${pct(s.confidence, 0)} confidence</span></div>
    <div class="kv">
      <div><span>Penetration</span><b>${pct(s.adoption)}</b></div>
      <div><span>Addressable converted</span><b>${pct(s.conversion)}</b></div>
      <div><span>Sentiment</span><b>${signed(s.sentiment)}</b></div>
      <div><span>Rejection</span><b>${pct(s.rejection_rate)}</b></div>
      <div><span>Tipping point</span><b>${s.tipping_point ? `Day ${s.tipping_point}` : 'Not reached'}</b></div>
      <div><span>Peak growth</span><b>Day ${s.peak_growth_day}</b></div>
    </div>`;

  const seg = rep.segments || {};
  $('#reportSegments').innerHTML = `<div class="panel__head"><div><span class="panel__eyebrow">Segments</span><h2 class="panel__title">Who moves first</h2></div></div>
    <table class="report-table"><thead><tr><th>Occupation</th><th>Adopt</th><th>Sent.</th></tr></thead><tbody>
    ${(seg.occupation || []).slice(0, 7).map(x => `<tr><td>${esc(x.name)}</td><td>${pct(x.adoption)}</td><td>${signed(x.sentiment)}</td></tr>`).join('')}
    </tbody></table>
    <table class="report-table" style="margin-top:12px"><thead><tr><th>State</th><th>Adopt</th><th>Sent.</th></tr></thead><tbody>
    ${(seg.state || []).slice(0, 6).map(x => `<tr><td>${esc(x.name)}</td><td>${pct(x.adoption)}</td><td>${signed(x.sentiment)}</td></tr>`).join('')}
    </tbody></table>`;

  $('#reportCaveats').innerHTML = `<div class="panel__head"><div><span class="panel__eyebrow">Caveats</span><h2 class="panel__title">Read before you spend</h2></div></div>
    <ul class="report-caveats">${(rep.caveats || []).map(c => `<li>${esc(c)}</li>`).join('')}</ul>`;

  const pr = r.precedents || {};
  const adj = pr.adjustments || {};
  $('#reportMethod').innerHTML = `<div class="panel__head"><div><span class="panel__eyebrow">Method</span><h2 class="panel__title">What produced this output</h2></div><span class="panel__meta">${r.population} agents · ${r.rounds} rounds · seed ${r.seed}</span></div>
    <div class="method-grid">${(rep.methods || []).map(m => `<div>${esc(m)}</div>`).join('')}</div>
    <div class="report-ctx"><h3>Precedent prior</h3><p class="small-copy">${esc(pr.note || '')}</p><div class="causal-row"><span>Analogous cases</span><b>${(pr.precedents || []).map(c => `${esc(c.brand)} (${esc(c.year)})`).join(' · ') || '—'}</b></div><div class="causal-row"><span>Trust-shock scaling</span><b>${esc(adj.trust_shock_scale ?? '—')} · recovery ${esc(adj.recovery_days ?? '—')}d</b></div><div class="causal-row"><span>Outcome direction</span><b>${esc(adj.outcome_direction || '—')} · negative base rate ${pct(adj.negative_outcome_share || 0, 0)}</b></div></div>
    <div class="report-ctx"><h3>Run audit</h3><div class="causal-row"><span>Checks passed</span><b class="${r.audit?.ok ? 'good' : 'bad'}">${r.audit?.score ?? '—'}% · ${r.audit?.failed ?? 0} failed · ${r.audit?.warnings ?? 0} warnings</b></div><div class="causal-row"><span>Context coverage</span><b>${pct(s.context_coverage || 0, 0)} of agents carry citations</b></div></div>`;
}

/* ---------- drawer ---------- */
function openAgent(id) {
  const a = agentById(id);
  if (!a) return;
  S.drawerAgent = a;
  const chat = S.chats[a.id] || [];
  const topBiases = Object.entries(a.biases || {}).sort((x, y) => y[1] - x[1]).slice(0, 5);
  const traits = ['risk', 'optimism', 'price', 'trust_gov', 'conformity', 'fatalism'];
  const mem = a.memory || {};
  const memHtml = (mem.memories || []).slice(-6).map(m => `<div class="mem-row mem-row--${m.kind}"><span class="mem-kind">${m.kind}</span><span>${esc(m.text)}</span></div>`).join('');
  const reflHtml = (mem.reflections || []).slice(0, 3).map(r => `<div class="mem-row mem-row--reflection"><span class="mem-kind">reflection</span><span>${esc(r)}</span></div>`).join('');
  $('#drawerBody').innerHTML = `
    <div class="drawer-profile"><span class="avatar">${avatar(a, 64)}</span><div><div class="drawer-name">${esc(a.name)}</div><div class="drawer-role">${esc(a.occupation)} · ${esc(a.city)}, ${esc(a.state)}<br>${esc(a.language)} · T${a.tier} · ${esc(a.gender)}, ${a.age}</div></div></div>
    <div class="drawer-chiprow"><span class="${tierClass(a.tier)}">Tier ${a.tier}</span><span class="chip">${esc(a.decision)}</span><span class="chip">${esc(a.caste_group)}</span><span class="chip">${esc(a.religion)}</span></div>
    <p class="drawer-quote">“${esc(a.quote)}”</p>
    <div class="drawer-kv">
      <div><span>Household income</span><b>${money(a.household_income)}/mo</b></div>
      <div><span>Own income</span><b>${money(a.income_monthly)}/mo</b></div>
      <div><span>Awareness</span><b>${pct(a.awareness)}</b></div>
      <div><span>Stance</span><b>${signed(a.stance * 2 - 1)}</b></div>
      <div><span>Adoption day</span><b>${a.adopt_day ? `Day ${a.adopt_day}` : '—'}</b></div>
      <div><span>Digital access</span><b>${pct(a.digital)}</b></div>
    </div>
    <div class="drawer-section"><h4>Traits</h4>${traits.map(t => `<div class="trait-row"><span>${t.replace(/_/g, ' ')}</span><div class="bar"><i style="width:${(a.traits[t] || 0) * 100}%"></i></div><b>${Math.round((a.traits[t] || 0) * 100)}</b></div>`).join('')}</div>
    <div class="drawer-section"><h4>Biases</h4>${topBiases.map(([k, v]) => `<div class="trait-row"><span>${esc(k.replace(/_/g, ' '))}</span><div class="bar"><i style="width:${v * 100}%"></i></div><b>${Math.round(v * 100)}</b></div>`).join('')}</div>
    <div class="drawer-section"><h4>Life</h4><p class="small-copy">${esc(a.bio)}</p><p class="small-copy" style="margin-top:6px"><b style="color:rgba(255,255,255,.7)">Aspires:</b> ${esc(a.aspiration)}</p><p class="small-copy" style="margin-top:4px"><b style="color:rgba(255,255,255,.7)">Fears:</b> ${esc((a.fears || []).join(', '))}</p></div>
    ${mem.count ? `<div class="drawer-section"><h4>Memory stream <span style="opacity:.4">(${mem.count})</span></h4>${memHtml}${reflHtml}</div>` : ''}
    ${(a.context || []).length ? `<div class="drawer-section"><h4>Context this citizen carries</h4><div class="context-list">${a.context.map(c => `<div class="ctx-item"><b>${esc(c.claim)}</b><span>${esc(truncate(c.detail || c.value || '', 170))}</span><em>${esc(c.why || 'retrieved context')} · ${esc((c.sources || []).map(x => x.org || x.title).join(', '))}</em></div>`).join('')}</div></div>` : ''}
    <div class="drawer-section"><h4>Ask ${esc(a.name.split(' ')[0])} anything</h4>
      <div class="dsuggest">${(chat.suggested || ['Would you buy this?', 'What would change your mind?', 'Who do you trust?']).map(q => `<button data-ask="${esc(q)}">${esc(q)}</button>`).join('')}</div>
      <div class="dchat" id="drawerChat">${chat.messages?.map(m => `<div class="dmsg ${m.role}">${esc(m.text)}</div>`).join('') || ''}</div>
      <form class="dchat-form" id="drawerForm"><input id="drawerInput" placeholder="Type a question…" maxlength="400" autocomplete="off"/><button class="ask-send" type="submit">${ICONS.arrow}</button></form>
    </div>`;
  $('#agentDrawer').classList.add('open');
  $('#agentDrawer').setAttribute('aria-hidden', 'false');
  $('#drawerBackdrop').classList.add('open');
  $('#drawerBody').scrollTop = 0;
  $('#drawerForm')?.addEventListener('submit', e => { e.preventDefault(); askAgent($('#drawerInput').value); });
  $$('#drawerBody [data-ask]').forEach(b => b.addEventListener('click', () => askAgent(b.dataset.ask)));
}

function closeDrawer() {
  $('#agentDrawer').classList.remove('open');
  $('#agentDrawer').setAttribute('aria-hidden', 'true');
  $('#drawerBackdrop').classList.remove('open');
  S.drawerAgent = null;
}

async function askAgent(message) {
  const a = S.drawerAgent;
  if (!a || !message || !message.trim()) return;
  const chat = S.chats[a.id] || (S.chats[a.id] = { messages: [] });
  chat.messages.push({ role: 'user', text: message.trim() });
  chat.messages.push({ role: 'agent', text: '…' });
  renderDrawerChat(chat);
  try {
    const res = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief: S.run.brief, agent_id: a.id, message: message.trim(), seed: S.run.seed })
    });
    const d = await res.json();
    chat.messages.pop();
    chat.messages.push({ role: 'agent', text: d.reply || 'No reply.' });
    chat.suggested = d.suggested;
    ops(d.llm_used ? 'llm' : 'chat', `citizen ${a.name}: ${String(d.reply || '').slice(0,40)}`);
  } catch (err) {
    chat.messages.pop();
    chat.messages.push({ role: 'agent', text: 'The line dropped. Try again.' });
  }
  renderDrawerChat(chat);
}

function renderDrawerChat(chat) {
  const el = $('#drawerChat');
  if (!el) return;
  el.innerHTML = (chat.messages || []).map(m => `<div class="dmsg ${m.role}">${esc(m.text)}</div>`).join('');
  el.scrollTop = el.scrollHeight;
  const inp = $('#drawerInput'); if (inp) inp.value = '';
}


/* ---------- atlas ---------- */
function ctxSourceLine(sources) {
  return (sources || []).map(s => s.url
    ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.org || s.title)} · ${esc(s.year || '')}</a>`
    : `<span>${esc(s.org || s.title || '')} · ${esc(s.year || '')}</span>`).join('');
}

function atlasNode(n) {
  return `<article class="atlas-node">
    <div class="atlas-node__top">
      <div><div class="atlas-node__type">${esc(n.type || 'context')} · ${esc(n.dimension || 'context')}</div>
      <div class="atlas-node__claim">${esc(n.title || n.claim || '')}</div></div>
      ${n.value ? `<div class="atlas-node__value">${esc(n.value)}${n.unit ? `<small style="font-family:var(--sans);font-size:8px;color:var(--muted)"> ${esc(n.unit)}</small>` : ''}</div>` : ''}
    </div>
    ${n.body || n.detail ? `<div class="atlas-node__detail">${esc(truncate(n.body || n.detail, 260))}</div>` : ''}
    <div class="atlas-node__meta">
      <span>${esc(n.geo || 'India')}</span>${n.year ? `<span>${esc(n.year)}</span>` : ''}
      <span>${esc(n.confidence || 'modelled')}</span>
      ${n.why ? `<span>↳ ${esc(n.why)}</span>` : ''}
      ${n.score != null ? `<span>score ${esc(n.score)}</span>` : ''}
      ${ctxSourceLine(n.sources)}
    </div>
  </article>`;
}

function renderAtlasAudit(d) {
  const cov = d.coverage || {};
  const checks = (d.audit && d.audit.checks) || [];
  $('#atlasAudit').innerHTML = checks.map(c => `<div class="audit-row ${c.ok ? 'ok' : 'bad'}"><i>${c.ok ? '✓' : '!'}</i><div><b>${esc(c.id.replace(/_/g, ' '))}</b><br>${esc(c.detail)}</div></div>`).join('') +
    `<div class="audit-row ok"><i>◌</i><div><b>corpus scope</b><br>${cov.sources || 0} sources · ${cov.facts || 0} curated facts · ${cov.derived_nodes || 0} derived nodes · ${cov.document_chunks || 0} ingested chunks</div></div>`;
  $('#atlasNote').textContent = cov.scope_note || 'Derived nodes are generated from public packs and labelled as modelled, not observed.';
}

function renderAtlas() {
  const d = S.atlas; if (!d) return;
  const c = d.coverage || {};
  $('#atlasCount').textContent = `${c.nodes || 0} nodes · ${c.sources || 0} sources`;
  $('#atlasMetrics').innerHTML = [
    metric('Curated facts', String(c.facts || 0), `${c.sources || 0} cited sources`),
    metric('Derived nodes', String(c.derived_nodes || 0), 'state · tier · occupation · category', '', null),
    metric('Document chunks', String(c.document_chunks || 0), 'ingested corpus', '', null),
    metric('Dimensions', String((c.dimensions || []).length), 'retrieval axes'),
    metric('Regions', String(c.regions || 0), 'cultural context packs'),
    metric('Norms', String(c.norms || 0), 'behavioural priors'),
  ].join('');
  $('#atlasDims').innerHTML = `<button class="chip ${S.atlasDimension === '' ? 'active' : ''}" data-atlas-dim="">All dimensions</button>` +
    (c.dimensions || []).slice(0, 14).map(x => `<button class="chip ${S.atlasDimension === x.id ? 'active' : ''}" data-atlas-dim="${esc(x.id)}">${esc(x.id)} <b style="font-weight:400;opacity:.5">${x.count}</b></button>`).join('');
  $('#atlasSourceCount').textContent = `${(d.sources || []).length} sources`;
  $('#atlasSources').innerHTML = (d.sources || []).map(src => `<div class="source-card">
    <span>${esc(src.type || 'source')}</span><b>${esc(src.org || '')}</b>
    <em>${esc(truncate(src.title || '', 72))}${src.year ? ` · ${esc(src.year)}` : ''}</em>
    ${src.url ? `<a class="ev-card__link" href="${esc(src.url)}" target="_blank" rel="noopener">↗</a>` : ''}
  </div>`).join('');
  renderAtlasAudit(d);
  searchAtlas();
}

async function searchAtlas() {
  const q = S.atlasQuery;
  const dim = S.atlasDimension;
  const url = `/api/atlas/search?q=${encodeURIComponent(q)}&limit=24${dim ? `&dimension=${encodeURIComponent(dim)}` : ''}`;
  try {
    const res = await fetch(url);
    const d = await res.json();
    $('#atlasResultTitle').textContent = q ? `Matches for “${q}”` : 'Most relevant nodes';
    $('#atlasResultCount').textContent = `${d.count} nodes`;
    $('#atlasResults').innerHTML = (d.results || []).map(atlasNode).join('') || '<p class="small-copy">No node matches that query. Try a state, category or norm.</p>';
  } catch (err) {
    $('#atlasResults').innerHTML = '<p class="small-copy">Could not load the context graph.</p>';
  }
}

async function loadAtlas() {
  if (S.atlas) { renderAtlas(); return; }
  $('#atlasResults').innerHTML = '<p class="small-copy">Loading the context graph…</p>';
  try {
    const d = await fetch('/api/atlas').then(r => r.json());
    S.atlas = d; renderAtlas();
  } catch (err) {
    $('#atlasResults').innerHTML = '<p class="small-copy">Could not load the context graph.</p>';
  }
}

/* ---------- precedents ---------- */
function renderPrecedents() {
  const d = S.precedents; if (!d) return;
  const b = d.base_rates || {};
  $('#precedentMetrics').innerHTML = [
    metric('Cases', String(d.count || 0), 'reconstructed arcs'),
    metric('Negative outcomes', String(b.negative_outcomes || 0), `${pct(b.share_negative || 0, 0)} of library`),
    metric('Median peak oppose', b.median_peak_oppose_share != null ? pct(b.median_peak_oppose_share) : '—', 'share of conversation'),
    metric('Median peak day', b.median_peak_oppose_day != null ? `Day ${b.median_peak_oppose_day}` : '—', 'after announcement'),
    metric('Median half-life', b.median_half_life_days != null ? `${b.median_half_life_days}d` : '—', 'attention decay'),
    metric('Daily points', String((d.days || []).length), 'day −14 to +60'),
  ].join('');
  $('#precedentNote').textContent = d.provenance_note || '';
  $('#precedentGrid').innerHTML = (d.cases || []).map(c => {
    const o = c.outcome || {};
    const dir = o.direction === 'down' ? 'var(--red)' : o.direction === 'up' ? 'var(--green)' : 'var(--muted)';
    return `<article class="prec-card">
      <div class="prec-card__head"><div><div class="prec-card__brand">${esc(c.brand)}</div><div class="prec-card__year">${esc(c.year)} · ${esc(c.geography)}</div></div><span class="chip">${esc(c.treatment_type || 'decision')}</span></div>
      <div class="prec-card__decision">${esc(c.decision)}</div>
      <p class="prec-card__summary">${esc(c.summary)}</p>
      <div class="prec-card__outcome">
        <div><span>KPI</span><b>${esc(o.kpi || '—')}</b></div>
        <div><span>Direction</span><b style="color:${dir}">${esc(o.direction || '—')}</b></div>
        <div><span>Magnitude</span><b>${o.magnitude_pct != null ? `${o.magnitude_pct > 0 ? '+' : ''}${o.magnitude_pct}%` : '—'}</b></div>
        <div><span>Peak oppose</span><b>Day ${esc(c.peak_oppose_day ?? '—')}</b></div>
        <div><span>Half-life</span><b>${esc(c.half_life_days ?? '—')}d</b></div>
      </div>
      <div class="prec-card__tags">${(c.tags || []).slice(0, 7).map(t => `<span>${esc(t)}</span>`).join('')}${(c.mechanisms || []).slice(0, 4).map(t => `<span>◆ ${esc(t)}</span>`).join('')}</div>
      ${c.caveats ? `<div class="prec-card__caveat">${esc(c.caveats)}</div>` : ''}
      <div class="prec-card__sources">${(c.sources || []).map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.org)} · ${esc(x.year)} ↗</a>`).join('')}</div>
    </article>`;
  }).join('');
}

async function loadPrecedents() {
  if (S.precedents) { renderPrecedents(); return; }
  $('#precedentGrid').innerHTML = '<p class="small-copy">Loading the precedent library…</p>';
  try {
    S.precedents = await fetch('/api/precedents').then(r => r.json());
    renderPrecedents();
  } catch (err) {
    $('#precedentGrid').innerHTML = '<p class="small-copy">Could not load precedents.</p>';
  }
}

/* ---------- causal ---------- */
function causalChart(el, d) {
  if (!el || !d) return;
  const vals = d.series.values || [];
  const labels = d.series.labels || [];
  const cf = d.counterfactual.point || [];
  const lo = d.counterfactual.p10 || [];
  const hi = d.counterfactual.p90 || [];
  const pre = d.series.pre_end;
  if (!vals.length) { el.innerHTML = ''; return; }
  const W = 700, H = 230, L = 42, R = 10, T = 12, B = 22;
  const all = vals.concat(lo, hi);
  const min = Math.min(...all), max = Math.max(...all);
  const pad = (max - min) * .08 || 1;
  const y0 = min - pad, y1 = max + pad;
  const n = vals.length;
  const px = i => L + (i / Math.max(1, n - 1)) * (W - L - R);
  const py = v => T + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  for (let i = 0; i <= 4; i++) {
    const y = T + (i / 4) * (H - T - B);
    svg += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" stroke="rgba(255,255,255,.055)"/>`;
    svg += `<text x="2" y="${y + 3}" fill="rgba(255,255,255,.28)" font-size="7">${(y1 - (i / 4) * (y1 - y0)).toFixed(2)}</text>`;
  }
  const bandPts = [];
  for (let i = 0; i < cf.length; i++) bandPts.push(`${px(pre + i)},${py(hi[i])}`);
  for (let i = cf.length - 1; i >= 0; i--) bandPts.push(`${px(pre + i)},${py(lo[i])}`);
  if (bandPts.length) svg += `<polygon points="${bandPts.join(' ')}" fill="rgba(74,222,128,.10)" stroke="none"/>`;
  const dObs = vals.map((v, i) => `${i ? 'L' : 'M'}${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
  svg += `<path d="${dObs}" fill="none" stroke="rgba(255,255,255,.78)" stroke-width="1.7" stroke-linejoin="round"/>`;
  const dCf = cf.map((v, i) => `${i ? 'L' : 'M'}${px(pre + i).toFixed(1)} ${py(v).toFixed(1)}`).join(' ');
  svg += `<path d="${dCf}" fill="none" stroke="#4ADE80" stroke-width="1.5" stroke-dasharray="4 4" stroke-linejoin="round"/>`;
  svg += `<line x1="${px(pre)}" y1="${T}" x2="${px(pre)}" y2="${H - B}" stroke="rgba(251,191,36,.45)" stroke-width="1" stroke-dasharray="2 3"/>`;
  svg += `<text x="${px(pre) + 4}" y="${T + 9}" fill="rgba(251,191,36,.7)" font-size="7">decision</text>`;
  const step = Math.max(1, Math.floor(n / 8));
  for (let i = 0; i < n; i += step) svg += `<text x="${px(i)}" y="${H - 6}" fill="rgba(255,255,255,.24)" font-size="6.5" text-anchor="middle">${esc(labels[i] || '')}</text>`;
  svg += '</svg>';
  el.innerHTML = svg;
}

function renderCausal() {
  const d = S.causal; if (!d) return;
  const a = d.att || {}, b = d.bayesian || {}, mc = d.monte_carlo || {}, npv = d.npv || {};
  const sc = d.synthetic_control || {}, pl = d.placebo_time || {};
  $('#causalUnit').textContent = `Observed vs counterfactual · ${d.topic.unit || ''}`;
  $('#causalTitle').textContent = d.topic.label;
  $('#causalEngine').textContent = d.counterfactual.engine;
  causalChart($('#causalChart'), d);
  $('#causalMetrics').innerHTML = [
    metric('ATT (relative)', `${signed(a.relative_pct, 1)}%`, `cumulative ${signed(a.cumulative, 2)}`, '', null),
    metric('Conformal 90%', `${signed(a.conformal_relative_low ?? a.conformal_low, 1)}% → ${signed(a.conformal_relative_high ?? a.conformal_high, 1)}%`, 'rolling-origin · approximate'),
    metric('Placebo p', pl.p_value != null ? pl.p_value.toFixed(3) : '—', `${pl.n || 0} placebo dates`, pl.p_value != null && pl.p_value < .1 ? 'good' : 'warn'),
    metric('Synthetic control', sc.available ? `${signed(sc.att_relative_pct, 1)}%` : 'Unavailable', sc.available ? `p=${sc.p_value != null ? sc.p_value.toFixed(3) : '—'}` : 'donor pool too small'),
    metric('Posterior', `${signed(b.posterior_mean, 1)}%`, `sd ${b.posterior_sd}${b.disagreement ? ' · disagrees with prior' : ''}`),
    metric('P(effect > 0)', pct(mc.prob_positive || 0, 0), 'block bootstrap'),
  ].join('');
  $('#causalStats').innerHTML = [
    ['Pre-period fit MAPE', `${d.counterfactual.pre_fit_mape_pct}%`],
    ['Mean effect / period', signed(a.mean_per_period, 3)],
    ['Cumulative effect', signed(a.cumulative, 3)],
    ['Relative effect', `${signed(a.relative_pct, 1)}%`],
    ['Monte Carlo p10 / p90', `${signed(mc.relative_p10, 1)}% → ${signed(mc.relative_p90, 1)}%`],
    ['Bad-tail (CVaR 5%)', `${signed(mc.cvar5, 1)}%`],
  ].map(([k, v]) => `<div><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');
  $('#causalRefute').innerHTML = `
    <div class="causal-row"><span>Placebo in time</span><b class="${pl.p_value != null && pl.p_value < .1 ? 'good' : 'warn'}">p = ${pl.p_value != null ? pl.p_value.toFixed(3) : '—'}</b></div>
    <div class="causal-row"><span>Placebo draws</span><b>${pl.n || 0}</b></div>
    <div class="causal-row"><span>Synthetic control</span><b class="${sc.available ? '' : 'warn'}">${sc.available ? `${signed(sc.att_relative_pct, 1)}% · p=${sc.p_value != null ? sc.p_value.toFixed(3) : '—'}` : 'unavailable'}</b></div>
    <div class="causal-row"><span>Donor pre-fit MAPE</span><b>${sc.available ? `${sc.pre_fit_mape}%` : '—'}</b></div>
    <div class="causal-row"><span>Top donors</span><b>${(sc.donors || []).slice(0, 3).map(x => `${esc(x.topic)} ${pct(x.weight, 0)}`).join(' · ') || '—'}</b></div>
    <div class="causal-row"><span>Sim vs data</span><b class="${b.disagreement ? 'bad' : 'good'}">${b.disagreement ? 'disagree — reconcile' : 'broadly consistent'}</b></div>
    <p class="causal-note">${esc((d.placebo_time || {}).note || '')} ${esc((sc.note || ''))}</p>`;
  $('#causalMC').innerHTML = `
    <div class="causal-row"><span>Cumulative p10 / p50 / p90</span><b>${signed(mc.cumulative_p10, 2)} / ${signed(mc.cumulative_p50, 2)} / ${signed(mc.cumulative_p90, 2)}</b></div>
    <div class="causal-row"><span>Relative p10 / p50 / p90</span><b>${signed(mc.relative_p10, 1)}% / ${signed(mc.relative_p50, 1)}% / ${signed(mc.relative_p90, 1)}%</b></div>
    <div class="causal-row"><span>P(positive effect)</span><b class="good">${pct(mc.prob_positive || 0, 1)}</b></div>
    <div class="causal-row"><span>NPV mean</span><b>${money(npv.mean)}</b></div>
    <div class="causal-row"><span>NPV p05 / p95</span><b>${money(npv.p05)} / ${money(npv.p95)}</b></div>
    <div class="causal-row"><span>P(NPV > 0)</span><b class="${(npv.prob_positive || 0) > .6 ? 'good' : 'warn'}">${pct(npv.prob_positive || 0, 1)}</b></div>
    <div class="causal-row"><span>CVaR 5%</span><b class="bad">${money(npv.cvar5)}</b></div>
    <p class="causal-note">${esc(mc.note || '')}</p>`;
  const pr = d.precedents || {};
  const adj = pr.adjustments || {};
  $('#causalPrecedents').innerHTML = `
    <div class="causal-row"><span>Prior direction</span><b>${esc(adj.outcome_direction || '—')}</b></div>
    <div class="causal-row"><span>Negative-outcome base rate</span><b>${pct(adj.negative_outcome_share || 0, 0)}</b></div>
    <div class="causal-row"><span>Trust-shock scale</span><b>${esc(adj.trust_shock_scale ?? '—')}</b></div>
    <div class="causal-row"><span>Recovery window</span><b>${esc(adj.recovery_days ?? '—')} days</b></div>
    <div class="context-list">${(pr.precedents || []).slice(0, 4).map(c => `<div class="ctx-item"><b>${esc(c.brand)} · ${esc(c.year)}</b><span>${esc(c.decision)} — ${esc(c.outcome?.direction || '')} ${c.outcome?.magnitude_pct != null ? `${c.outcome.magnitude_pct}%` : ''}</span><em>peak oppose ${pct(Math.max(...(c.curve || [{ oppose: 0 }]).map(x => x.oppose)))} · similarity ${pct(c.similarity || 0, 0)}</em></div>`).join('')}</div>
    <p class="causal-note">${esc(pr.note || '')}</p>`;
  $('#causalCaveats').innerHTML = (d.caveats || []).map(c => `<li>${esc(c)}</li>`).join('');
}

async function loadCausal() {
  try {
    if (!S.causalTopics) S.causalTopics = await fetch('/api/causal/topics').then(r => r.json());
    const sel = $('#causalTopic');
    if (!sel.options.length) {
      sel.innerHTML = S.causalTopics.topics.map(t => `<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('');
      sel.value = (S.run && S.run.topic && S.run.topic.id) || 'ev-car';
    }
    await runCausal();
  } catch (err) {
    $('#causalTitle').textContent = 'Could not load the causal layer.';
  }
}

async function runCausal() {
  const btn = $('#causalRun'); const label = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Analysing…'; }
  const q = new URLSearchParams({
    topic_id: $('#causalTopic').value || 'ev-car',
    pre_end: $('#causalPre').value || '72',
    horizon: $('#causalHorizon').value || '12',
    sim_effect_pct: $('#causalPrior').value || '0',
    baseline_value: $('#causalValue').value || '1000000',
  });
  try {
    const res = await fetch(`/api/causal?${q}`);
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Causal analysis failed');
    S.causal = d; renderCausal();
  } catch (err) {
    toast(err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = label; injectIcons(btn); }
  }
}

/* ---------- calibration ---------- */
function renderCalibration() {
  const d = S.calibration; if (!d) return;
  const o = d.objective || {};
  const last = d.last_run || {};
  $('#calibrationUpdated').textContent = d.updated ? `Updated ${d.updated.slice(0, 10)}` : 'Defaults';
  $('#calibrationMetrics').innerHTML = [
    metric('Adopted loss', o.after_loss != null ? o.after_loss.toFixed(2) : '—', o.before_loss != null ? `before ${o.before_loss.toFixed(2)}` : 'not yet run'),
    metric('Anchor MAE', o.after_mae != null ? pct(o.after_mae, 1) : '—', o.before_mae != null ? `before ${pct(o.before_mae, 1)}` : ''),
    metric('Within range', o.n_topics ? `${o.within_range_after}/${o.n_topics}` : '—', 'public anchor ranges'),
    metric('Evaluations', String(last.evaluations || 0), last.stop_reason || '—'),
    metric('History', String((d.history || []).length), 'persisted runs'),
    metric('Bounds', String(Object.keys(d.specs || {}).length), 'declared parameters'),
  ].join('');
  const specs = d.specs || {};
  $('#calibrationParams').innerHTML = Object.entries(d.params || {}).map(([k, v]) => {
    const sp = specs[k] || { low: 0, high: 2 };
    const pos = clamp(((v - sp.low) / (sp.high - sp.low || 1)) * 100, 0, 100);
    return `<div class="param-row"><span>${esc(k.replace(/_/g, ' '))}</span><div class="bar"><i style="width:${pos}%"></i></div><b>${Number(v).toFixed(2)}</b></div>`;
  }).join('');
  $('#calibrationNote').textContent = d.note || '';
  const topics = {};
  (last.topics || []).forEach(t => { topics[t.topic_id] = t; });
  $('#calibrationAnchors').innerHTML = `<table class="anchor-table"><thead><tr><th>Category</th><th>Anchor</th><th>Simulated</th><th>Error</th></tr></thead><tbody>` +
    (d.anchors || []).map(a => {
      const t = topics[a.topic_id];
      const ok = t && t.simulated != null && t.simulated >= a.low && t.simulated <= a.high;
      return `<tr><td><b>${esc(a.label)}</b></td><td>${pct(a.target, 0)} <span style="opacity:.4">(${pct(a.low, 0)}–${pct(a.high, 0)})</span></td><td class="${ok ? 'good' : ''}" style="color:${t ? (ok ? 'var(--green)' : 'var(--amber)') : 'var(--muted)'}">${t && t.simulated != null ? pct(t.simulated, 1) : '—'}</td><td>${t && t.error_pct_points != null ? `${signed(t.error_pct_points, 1)} pp` : '—'}</td></tr>`;
    }).join('') + '</tbody></table>' +
    `<p class="causal-note">${esc(d.provenance_note || '')}</p>`;
  $('#calibrationHistory').innerHTML = (d.history || []).length
    ? (d.history || []).map(h => `<div class="history-row"><div><b>${esc(h.at ? h.at.slice(0, 19).replace('T', ' ') : h.id)}</b><br><span>${h.before_loss != null ? h.before_loss.toFixed(2) : '—'} → ${h.after_loss != null ? h.after_loss.toFixed(2) : '—'} loss · ${h.evaluations || 0} evaluations</span></div><div style="text-align:right"><b style="color:${h.improved ? 'var(--green)' : 'var(--amber)'}">${h.improved ? 'adopted' : 'kept previous'}</b><br><span>${Object.entries(h.params || {}).slice(0, 3).map(([k, v]) => `${k.replace(/_/g, ' ')} ${Number(v).toFixed(2)}`).join(' · ')}</span></div></div>`).join('')
    : '<p class="small-copy">No calibration run yet. The simulator is using its documented defaults.</p>';
}

async function loadCalibration() {
  try {
    S.calibration = await fetch('/api/calibration').then(r => r.json());
    renderCalibration();
  } catch (err) {
    $('#calibrationParams').innerHTML = '<p class="small-copy">Could not load calibration.</p>';
  }
}

async function runCalibration() {
  const btn = $('#calibrationRun'); const label = btn.innerHTML;
  btn.disabled = true; btn.textContent = 'Calibrating…';
  $('#calibrationUpdated').textContent = 'Running coordinate search';
  try {
    const res = await fetch('/api/calibration/run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget: 24, n_agents: 420, rounds: 28, seed: 11 })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Calibration failed');
    S.calibration = d; renderCalibration();
    const o = d.objective || {};
    toast(`Calibrated · loss ${o.before_loss?.toFixed(2)} → ${o.after_loss?.toFixed(2)}`);
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false; btn.innerHTML = label; injectIcons(btn);
  }
}

/* ---------- reasoning ---------- */
function reasonCheck(label, ok, detail, level = 'error') {
  const cls = ok ? 'ok' : (level === 'warn' ? 'warn' : 'bad');
  const glyph = ok ? '✓' : (level === 'warn' ? '!' : '×');
  return `<div class="reason-check ${cls}"><i>${glyph}</i><div><b>${esc(label.replace(/_/g, ' '))}</b><span>${esc(detail)}</span></div></div>`;
}

function renderReasoning() {
  const d = S.reasoning;
  if (!d) return;
  const rv = d.revise || {};
  const crit = d.critique || {};
  const st = d.stability || {};
  const stress = d.stress || {};
  const memo = d.memo || {};
  const ca = d.causal_check || {};

  $('#reasonElapsed').textContent = `${(d.elapsed_ms / 1000).toFixed(1)}s · ${st.runs || 0} seeds`;
  $('#reasonPosture').innerHTML = `
    <div class="reason-posture__main">
      <span class="panel__eyebrow">Posture after revision</span>
      <div class="reason-posture__row">
        <div class="reason-posture__verdict">${esc(d.posture || rv.posture || '—')}</div>
        <span class="reason-verdict-tag ${rv.downgraded ? 'warn' : 'ok'}">${esc(rv.original_verdict || '—')} → ${esc(rv.revised_verdict || '—')}</span>
      </div>
      <p>${esc(memo.headline || '')}</p>
      <div class="reason-chips">
        <span class="chip chip--warn">Binding: ${esc(d.binding_constraint?.label || '—')}</span>
        <span class="chip">${crit.passed || 0}/${crit.total || 0} checks passed</span>
        <span class="chip ${st.stable ? 'chip--green' : 'chip--warn'}">${st.stable ? 'Seed-stable' : 'Seed-sensitive'}</span>
        <span class="chip ${stress.robust ? 'chip--green' : 'chip--warn'}">${stress.robust ? 'Assumption-robust' : `${stress.verdict_flips} verdict flip(s)`}</span>
      </div>
    </div>
    <div class="reason-posture__conf">
      <span>${esc((rv.original_confidence * 100).toFixed(0))}%</span>
      <em>→</em>
      <b>${esc((rv.revised_confidence * 100).toFixed(0))}%</b>
      <small>reported → revised stability score,<br>not sampling error</small>
    </div>`;

  $('#reasonMetrics').innerHTML = [
    metric('Checks passed', `${crit.passed || 0}/${crit.total || 0}`, `${crit.failed || 0} failed · ${crit.warnings || 0} weak`, crit.failed ? 'metric--red' : 'metric--green', (crit.passed || 0) / Math.max(1, crit.total || 1)),
    metric('Verdict agreement', pct(st.verdict_agreement || 0, 0), `${st.runs || 0} seeds · replication`),
    metric('Conversion CV', Number(st.conversion_cv || 0).toFixed(2), `sd ${pct(st.conversion_sd || 0, 1)}`),
    metric('Stress flips', String(stress.verdict_flips ?? '—'), `max adoption delta ${signed(stress.max_adoption_delta_pct || 0, 1)}%`, stress.robust ? '' : 'metric--red'),
    metric('Order parameter', pct(st.order_parameter_end || 0, 0), `of addressable pool · ${st.phase_transition ? 'phase transition' : 'gradual'}`, st.phase_transition ? 'metric--red' : 'metric--green'),
    metric('Peak susceptibility', Number(st.peak_susceptibility || 0).toFixed(3), `phase-transition detector · ${st.phase_transition ? 'spike detected' : 'stable'}`,
      (st.peak_susceptibility || 0) > 0.05 ? 'metric--red' : 'metric--green'),
    metric('Temperature', Number(st.temperature_end || 1).toFixed(2), `annealed: exploration → commitment`),
    metric('Market trend', signed(st.market_trend_end || 0, 2), `TimesFM demand signal · ${st.market_trend_end > 0 ? 'tailwind' : st.market_trend_end < 0 ? 'headwind' : 'neutral'}`,
      st.market_trend_end > 0 ? 'metric--green' : st.market_trend_end < 0 ? 'metric--red' : ''),
  ].join('');

  $('#reasonMemo').innerHTML = `
    <p class="reason-memo__body">${esc(memo.body || '')}</p>
    <div class="reason-memo__decision"><span>Decision</span><p>${esc(memo.decision || '')}</p></div>
    <div class="reason-memo__mind">
      <span>What would change my mind</span>
      <ul>${(memo.what_would_change_my_mind || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    </div>
    <p class="reason-memo__conf">${esc(memo.confidence_story || '')}</p>`;

  $('#reasonHypotheses').innerHTML = (d.hypotheses || []).map((h, i) => `
    <div class="reason-hyp">
      <div class="reason-hyp__head"><b>${i + 1}. ${esc(h.label)}</b><span>${pct(h.share, 0)}</span></div>
      <div class="bar"><i style="width:${clamp(h.share * 100, 0, 100)}%"></i></div>
      <ul>${(h.evidence || []).map(e => `<li>${esc(e)}</li>`).join('')}</ul>
      <p><em>Falsifier:</em> ${esc(h.falsifier)}</p>
    </div>`).join('') + `<p class="causal-note">Weights are evidence shares from objections, category priors, trait correlations and retrieved precedents. They are a ranking of explanations, not measured effect sizes.</p>`;

  $('#reasonTrace').innerHTML = (d.trace || []).map((t, i) => `
    <div class="trace-step ${esc(t.status)}">
      <i>${String(i + 1).padStart(2, '0')}</i>
      <div><b>${esc(t.step)}</b><span>${esc(t.detail)}</span></div>
      <em>${Number(t.ms || 0)}ms</em>
    </div>`).join('');

  $('#reasonPassed').textContent = `${crit.passed || 0}/${crit.total || 0} passed`;
  $('#reasonChecks').innerHTML = (crit.checks || []).map(c => reasonCheck(c.id, c.ok, c.detail, c.level)).join('') +
    `<p class="causal-note">Failed error-level checks cap confidence. Weak checks are disclosed but do not invalidate the run.</p>`;

  $('#reasonRobust').innerHTML = `
    <div class="causal-row"><span>Verdict agreement</span><b class="${st.stable ? 'good' : 'warn'}">${pct(st.verdict_agreement || 0, 0)}</b></div>
    <div class="causal-row"><span>Conversion CV</span><b class="${(st.conversion_cv || 0) <= .3 ? 'good' : 'warn'}">${Number(st.conversion_cv || 0).toFixed(2)}</b></div>
    <div class="causal-row"><span>Best tier agreement</span><b>${pct(st.best_tier_agreement || 0, 0)}</b></div>
    <div class="reason-mini-table">
      <div class="reason-mini-row reason-mini-row--head"><span>Seed</span><span>Adoption</span><span>Conversion</span><span>Verdict</span></div>
      ${(st.rows || []).map(r => `<div class="reason-mini-row"><span>${r.seed}</span><span>${pct(r.adoption, 1)}</span><span>${pct(r.conversion, 1)}</span><span>${esc(r.verdict)}</span></div>`).join('')}
    </div>
    <div class="reason-mini-table">
      <div class="reason-mini-row reason-mini-row--head"><span>Perturbation</span><span>Adoption</span><span>Δ</span><span>Verdict</span></div>
      ${(stress.trials || []).map(t => `<div class="reason-mini-row"><span>${esc(t.name)}</span><span>${pct(t.adoption, 1)}</span><span class="${t.verdict !== rv.original_verdict ? 'warn' : ''}">${signed(t.delta_adoption_pct, 1)}%</span><span>${esc(t.verdict)}</span></div>`).join('')}
    </div>
    <p class="causal-note">${esc(stress.note || '')} ${esc(st.note || '')}</p>`;

  $('#reasonCausal').innerHTML = ca.ok ? `
    <div class="causal-row"><span>Category drift vs counterfactual</span><b>${signed(ca.relative_pct || 0, 1)}%</b></div>
    <div class="causal-row"><span>Conformal 90% band</span><b>${signed(ca.conformal_relative_low || 0, 1)}% → ${signed(ca.conformal_relative_high || 0, 1)}%</b></div>
    <div class="causal-row"><span>Placebo p</span><b class="${(ca.placebo_p ?? 1) < .1 ? 'good' : 'warn'}">${ca.placebo_p != null ? ca.placebo_p.toFixed(3) : '—'}</b></div>
    <div class="causal-row"><span>Synthetic control</span><b>${ca.synthetic_control_pct != null ? `${signed(ca.synthetic_control_pct, 1)}% · p=${ca.synthetic_control_p != null ? ca.synthetic_control_p.toFixed(3) : '—'}` : 'unavailable'}</b></div>
    <div class="causal-row"><span>Sign agreement</span><b class="${ca.opposite_sign ? 'bad' : 'good'}">${ca.opposite_sign ? 'opposite — reconcile' : 'same direction'}</b></div>
    <div class="causal-row"><span>Nominal coverage check</span><b>${pct(ca.validation_coverage || 0, 0)}</b></div>
    <p class="causal-note">${esc(ca.note || '')}</p>`
    : `<p class="small-copy">Causal check unavailable.</p><p class="causal-note">${esc(ca.error || '')}</p>`;

  const nx = d.next || {};
  $('#reasonNext').innerHTML = `
    <div class="reason-next-head"><span>Priority</span><b>${esc((nx.priority || '—').replace(/_/g, ' '))}</b></div>
    <ol class="reason-list">${(nx.tests || []).map(t => `<li>${esc(t)}</li>`).join('')}</ol>
    <div class="reason-next-head"><span>Protocol</span><b>Minimum discipline</b></div>
    <ul class="reason-list">${(nx.general || []).map(t => `<li>${esc(t)}</li>`).join('')}</ul>
    <div class="reason-next-head"><span>Missing</span><b>What the data cannot see</b></div>
    <ul class="reason-list reason-list--muted">${(nx.missing || []).map(t => `<li>${esc(t)}</li>`).join('')}</ul>`;

  $('#reasonLimits').innerHTML = (d.limits || []).map(x => `<li>${esc(x)}</li>`).join('');

  // --- System dynamics panel ---
  const dyn = $('#reasonDynamics');
  if (dyn) {
    const order = Number(st.order_parameter_end || 0);
    const susc = Number(st.peak_susceptibility || 0);
    const temp = Number(st.temperature_end || 1);
    const trend = Number(st.market_trend_end || 0);
    const phase = Boolean(st.phase_transition);
    dyn.innerHTML = `
      <div class="dynamics-row"><span class="dyn-label">Order parameter</span><div class="dyn-bar"><i style="width:${clamp(order * 100, 0, 100)}%"></i></div><b>${pct(order, 0)}</b><span class="dyn-note">${order > 0.5 ? 'majority adopted' : order > 0.2 ? 'early adoption' : 'pre-adoption'}</span></div>
      <div class="dynamics-row"><span class="dyn-label">Peak susceptibility</span><div class="dyn-bar"><i style="width:${clamp(susc * 1000, 0, 100)}%"></i></div><b>${susc.toFixed(3)}</b><span class="dyn-note">${phase ? 'phase transition detected' : 'no sharp tipping point'}</span></div>
      <div class="dynamics-row"><span class="dyn-label">Temperature (annealed)</span><div class="dyn-bar"><i style="width:${clamp((1 - temp / 2) * 100, 0, 100)}%"></i></div><b>${temp.toFixed(2)}</b><span class="dyn-note">${temp > 1.0 ? 'exploration' : temp > 0.5 ? 'transition' : 'commitment'}</span></div>
      <div class="dynamics-row"><span class="dyn-label">TimesFM market trend</span><div class="dyn-bar trend-bar ${trend > 0 ? 'trend-up' : trend < 0 ? 'trend-down' : 'trend-neutral'}"><i style="width:${clamp(Math.abs(trend) * 100, 0, 100)}%"></i></div><b>${signed(trend, 2)}</b><span class="dyn-note">${trend > 0.1 ? 'demand tailwind' : trend < -0.1 ? 'demand headwind' : 'neutral demand'}</span></div>
      <p class="causal-note">Order parameter = fraction of addressable pool adopted (magnetization). Susceptibility = variance spike near phase transitions. Temperature = annealed decision noise (high = exploratory, low = decisive). Market trend = TimesFM zero-shot demand forecast signal.</p>
    `;
  }
}

async function loadReasoning(force = false) {
  if (!S.run) { toast('Run a simulation first.'); return; }
  const key = `${S.run.brief}|${S.run.population}|${S.run.rounds}|${S.run.seed}|${S.run.scenario}|${S.run.focus_state || ''}`;
  if (!force && S.reasoningLoaded && S.reasoningKey === key) { renderReasoning(); return; }
  await runReasoning();
}

async function runReasoning() {
  if (!S.run) { toast('Run a simulation first.'); return; }
  if (S.reasoningBusy) return;
  S.reasoningBusy = true;
  const btn = $('#reasonRun');
  const label = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Deliberating…'; }
  $('#reasonPosture').innerHTML = '<div class="skeleton" style="height:88px"></div>';
  $('#reasonMetrics').innerHTML = '';
  toast('Running replication, stress and refutation…');
  try {
    const res = await fetch('/api/reason', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brief: S.run.brief,
        n_agents: clamp(S.run.population, 40, 800),
        rounds: clamp(S.run.rounds, 12, 96),
        seed: S.run.seed,
        scenario: S.run.scenario || 'base',
        focus_state: S.run.focus_state || null,
        question: S.run.question || null,
        replicates: 3,
      })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Reasoning failed');
    S.reasoning = d;
    S.reasoningLoaded = true;
    S.reasoningKey = `${S.run.brief}|${S.run.population}|${S.run.rounds}|${S.run.seed}|${S.run.scenario}|${S.run.focus_state || ''}`;
    renderReasoning();
    ops('reason', `deliberated → ${d.posture} · ${d.critique.passed}/${d.critique.total} checks`);
    toast(`Deliberated · ${d.posture} · ${d.critique.passed}/${d.critique.total} checks`);
  } catch (err) {
    toast(err.message);
    $('#reasonPosture').innerHTML = `<div class="reason-error">${esc(err.message)}</div>`;
  } finally {
    S.reasoningBusy = false;
    if (btn) { btn.disabled = false; btn.innerHTML = label; injectIcons(btn); }
  }
}

/* ---------- run ---------- */
async function runSimulation() {
  const brief = $('#briefInput').value.trim();
  if (!brief) { toast('Write a hypothesis first.'); return; }
  ops('simulate', `starting ${brief.slice(0,60)}`);
  const n = Number($('#agentsRange').value);
  const rounds = Number($('#roundsRange').value);
  const seedLock = $('#seedLock')?.checked;
  const seedRaw = $('#seedInput').value.trim();
  const seed = (!seedLock || !seedRaw) ? Math.floor(Math.random() * 1000000) : Number(seedRaw);
  $('#seedInput').value = seed;
  const tier_mix = {};
  $$('.tier-mini input').forEach(inp => { tier_mix[inp.dataset.tier] = Number(inp.value) / 100; });
  const btn = $('#runBtn');
  btn.disabled = true; btn.querySelector('.run-btn__label').textContent = 'Running the room…';
  $('#statusText').textContent = 'Running';
  $('#runDot').style.background = 'var(--amber)';
  try {
    const res = await fetch('/api/simulate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brief, n_agents: n, rounds, seed, tier_mix,
        scenario: S.scenario, focus_state: $('#stateSelect').value || null,
        question: $('#questionInput').value || null,
      })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Simulation failed');
    S.run = d;
    S.day = d.rounds;
    S.focusRounds = [{ question: d.question || $('#questionInput').value, group: d.focus_group }];
    S.social.limit = 40;
    S.agentLimit = 36;
    S.chats = {};
    S.forecast = null; S.scenarios = null;
    S.robust = null; S.sens = null;
    S.reasoning = null; S.reasoningLoaded = false; S.reasoningKey = '';
    townState.initialised = false;
    $('#crumbTopic').textContent = d.topic.label;
    $('#statusText').textContent = `Ready · ${d.population} agents`;
    $('#runDot').style.background = 'var(--green)';
    $('#runId').textContent = d.run_id;
    $('#tabsMeta').textContent = `${d.population} agents · ${d.rounds} rounds · seed ${d.seed}`;
    $('#forecastTopic').value = d.topic.id;
    renderAll();
    setupAgentField();
    renderVenn();
    townState.initialised = false; if (townState.raf) { cancelAnimationFrame(townState.raf); townState.raf = null; }
    initTownAgents(); townState.raf = requestAnimationFrame(drawTown);
    if (S.tab === 'world') setTimeout(() => { if (!S.playing) togglePlay(); }, 700);
    if (S.tab === 'forecast') loadForecast();
    if (S.tab === 'reasoning') loadReasoning();
    if (S.tab === 'calibration') loadCalibration();
    if (S.tab === 'debate') setTimeout(() => { if (!debatePlay) playDebate(); }, 400);
    ops('simulate', `ran ${d.population} agents · ${d.rounds} rounds · seed ${d.seed} · ${d.topic.label}`);
    toast(`Run ${d.run_id} · ${d.summary.verdict} · ${pct(d.summary.adoption)} penetration`);
  } catch (err) {
    $('#statusText').textContent = 'Error';
    $('#runDot').style.background = 'var(--red)';
    toast(err.message);
  } finally {
    btn.disabled = false; btn.querySelector('.run-btn__label').textContent = 'Run simulation';
  }
}

function renderAll() {
  if (!S.run) return;
  renderWorld();
  renderSocial();
  renderDebate();
  renderFocus();
  renderCognition();
  renderPerception();
  renderEvidence();
  renderResearch();
  renderReport();
  renderEncounters();
  if (S.validation) renderValidation();
}

/* ---------- playback ---------- */
function setDay(day) {
  if (!S.run) return;
  S.day = clamp(Math.round(day), 1, S.run.rounds);
  renderWorld();
}
function togglePlay() {
  const btn = $('#playBtn');
  if (S.playing) {
    clearInterval(S.playTimer); S.playing = false; btn.innerHTML = ICONS.play;
    return;
  }
  S.playing = true; btn.innerHTML = ICONS.pause;
  if (S.day >= S.run.rounds) S.day = 1;
  S.playTimer = setInterval(() => {
    if (!S.playing) return;
    if (S.day >= S.run.rounds) {
      clearInterval(S.playTimer); S.playing = false; btn.innerHTML = ICONS.play; return;
    }
    setDay(S.day + 1);
  }, 850);
}

/* ---------- age-of-empires style Indian village & bazaar, rich top-down ---------- */
const TOWN = {
  W: 920, H: 540,
  // Hand-placed buildings on a warm dusk village plan. kind drives flag logic.
  buildings: [
    // temple compound — north-east, red terracotta spire
    { x: 690, y: 48, w: 120, h: 66, roof: '#a8432c', wall: '#c47a52', kind: 'temple', label: 'SHIV MANDIR' },
    // school — south-west, blue-washed
    { x: 52, y: 400, w: 124, h: 62, roof: '#2e4152', wall: '#5d7891', kind: 'school', label: 'VIDYALAYA' },
    // EV charging point + Sharma Mobile — east side of bazaar
    { x: 700, y: 250, w: 132, h: 68, roof: '#26332b', wall: '#4d6658', kind: 'ev', label: 'SHARMA MOBILE · EV' },
    // chai + sabzi — along bazaar street
    { x: 268, y: 252, w: 96, h: 52, roof: '#544229', wall: '#8a7050', kind: 'chai', label: 'CHAI-WALA' },
    { x: 450, y: 248, w: 96, h: 50, roof: '#4e3e28', wall: '#8a7050', kind: 'sabzi', label: 'SABZI MANDI' },
    // residential — north row (mixed adobe / blue-wash / green-wash / plinth)
    { x: 56, y: 40, w: 88, h: 56, roof: '#5c402c', wall: '#a8836a', kind: 'house' },
    { x: 168, y: 34, w: 74, h: 52, roof: '#36455a', wall: '#5d7891', kind: 'house' },
    { x: 380, y: 40, w: 92, h: 54, roof: '#544229', wall: '#a8836a', kind: 'house' },
    { x: 560, y: 34, w: 66, h: 50, roof: '#475747', wall: '#68806a', kind: 'house' },
    // residential — south row
    { x: 300, y: 420, w: 92, h: 54, roof: '#54423d', wall: '#8a6a5a', kind: 'house' },
    { x: 440, y: 430, w: 84, h: 56, roof: '#655640', wall: '#a8836a', kind: 'house' },
    { x: 576, y: 424, w: 70, h: 50, roof: '#3e4046', wall: '#666a73', kind: 'house' },
    // smaller shops / homes along lane
    { x: 172, y: 262, w: 60, h: 38, roof: '#514227', wall: '#8a7050', kind: 'house' },
    { x: 600, y: 258, w: 56, h: 38, roof: '#514227', wall: '#8a7050', kind: 'house' },
    // far-west and far-east edge houses
    { x: 792, y: 420, w: 66, h: 52, roof: '#47443a', wall: '#7a7263', kind: 'house' },
    { x: 12, y: 250, w: 56, h: 40, roof: '#514227', wall: '#8a7050', kind: 'house' },
  ],
  trees: [
    { x: 120, y: 120, r: 26, kind: 'neem' }, { x: 224, y: 120, r: 18, kind: 'palm' },
    { x: 340, y: 128, r: 22, kind: 'neem' }, { x: 452, y: 118, r: 24, kind: 'palm' },
    { x: 250, y: 340, r: 20, kind: 'palm' }, { x: 380, y: 340, r: 18, kind: 'neem' },
    { x: 540, y: 338, r: 22, kind: 'neem' }, { x: 800, y: 168, r: 24, kind: 'neem' },
    { x: 60, y: 352, r: 16, kind: 'palm' }, { x: 860, y: 330, r: 18, kind: 'palm' },
    { x: 640, y: 130, r: 16, kind: 'palm' },
  ],
  hotspots: [
    { x: 0.08, y: 0.72, w: 0.13, h: 0.10, kind: 'school' },
    { x: 0.07, y: 0.09, w: 0.10, h: 0.09, kind: 'north' },
    { x: 0.29, y: 0.47, w: 0.10, h: 0.08, kind: 'bazaar' },
    { x: 0.46, y: 0.46, w: 0.10, h: 0.08, kind: 'bazaar' },
    { x: 0.72, y: 0.48, w: 0.13, h: 0.10, kind: 'ev' },
    { x: 0.76, y: 0.10, w: 0.12, h: 0.10, kind: 'temple' },
    { x: 0.28, y: 0.80, w: 0.13, h: 0.08, kind: 'south' },
    { x: 0.88, y: 0.78, w: 0.08, h: 0.08, kind: 'east' },
  ],
  chatLines: [
    'Service kaisa hai?', 'Price kitna hai?', 'Pehle charge point, phir baat.', 'Neighbour ne le liya…',
    'EMI chalega kya?', 'Warranty kitne saal?', 'Mere gaon mein nahi hai.', 'Ek dost se sunna hai.',
    'Thodi risky hai…', 'Dealer se baat karo, theek hai.', 'Festival pe discount?',
    'Demo dekh pehle.', 'Kya beta, service ki?', 'Volvo toh hota hi hai.',
  ],
};

let townState = { agents: [], raf: null, frame: 0, chatting: [], initialised: false };

function drawRoad(ctx) {
  // main bazaar — warm compacted earth with center stones
  const g = ctx.createLinearGradient(0, 225, 0, 315);
  g.addColorStop(0, '#544735'); g.addColorStop(0.5, '#6e5f47'); g.addColorStop(1, '#463b2d');
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.moveTo(0, 240); ctx.lineTo(920, 225); ctx.lineTo(920, 300); ctx.lineTo(0, 312); ctx.closePath(); ctx.fill();
  // road edge stones
  ctx.strokeStyle = 'rgba(230,205,150,.16)'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, 240); ctx.lineTo(920, 225); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, 312); ctx.lineTo(920, 300); ctx.stroke();
  // n-s lane
  const g2 = ctx.createLinearGradient(390, 0, 500, 0);
  g2.addColorStop(0, '#483d30'); g2.addColorStop(0.5, '#60513f'); g2.addColorStop(1, '#403427');
  ctx.fillStyle = g2;
  ctx.beginPath(); ctx.moveTo(400, 0); ctx.lineTo(495, 0); ctx.lineTo(530, 540); ctx.lineTo(425, 540); ctx.closePath(); ctx.fill();
  // shadowed lane edges
  ctx.strokeStyle = 'rgba(0,0,0,.35)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(400, 0); ctx.lineTo(425, 540); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(495, 0); ctx.lineTo(530, 540); ctx.stroke();
}

function drawPond(ctx) {
  // stepwell pond, top-left
  ctx.fillStyle = '#101d26';
  ctx.beginPath(); ctx.ellipse(105, 205, 72, 34, 0.15, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = 'rgba(110,175,215,.32)'; ctx.lineWidth = 1.4;
  ctx.beginPath(); ctx.ellipse(105, 205, 52, 24, 0.15, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = 'rgba(140,200,235,.18)';
  ctx.beginPath(); ctx.ellipse(95, 200, 28, 12, 0.2, 0, Math.PI * 2); ctx.fill();
}

function drawGround(ctx) {
  // dry grass base — warm dusk, NOT black
  const g = ctx.createRadialGradient(460, 220, 80, 460, 260, 620);
  g.addColorStop(0, '#332c21'); g.addColorStop(0.55, '#2b251d'); g.addColorStop(1, '#201c16');
  ctx.fillStyle = g; ctx.fillRect(0, 0, TOWN.W, TOWN.H);
  // grass patches
  for (let i = 0; i < 40; i++) {
    const rx = (i * 733 + 91) % TOWN.W, ry = (i * 397 + 137) % (TOWN.H * 0.78) + 16;
    ctx.fillStyle = i % 3 === 0 ? 'rgba(92,116,66,.42)' : 'rgba(72,82,52,.36)';
    ctx.beginPath(); ctx.ellipse(rx, ry, 34 + (i % 7) * 12, 13 + (i % 5) * 6, 0, 0, Math.PI * 2); ctx.fill();
  }
  // packed earth
  for (let i = 0; i < 24; i++) {
    const rx = (i * 557 + 201) % TOWN.W, ry = (i * 289 + 311) % (TOWN.H * 0.8) + 24;
    ctx.fillStyle = 'rgba(200,180,138,.11)';
    ctx.beginPath(); ctx.ellipse(rx, ry, 52 + (i % 5) * 16, 17 + (i % 4) * 7, 0, 0, Math.PI * 2); ctx.fill();
  }
  drawRoad(ctx);
  drawPond(ctx);
  // string lights
  for (let i = 0; i < 15; i++) {
    const x = 22 + i * 63, y = 237 + Math.sin(i * 1.8) * 5;
    ctx.fillStyle = i % 3 === 0 ? 'rgba(255,222,148,.95)' : 'rgba(255,196,148,.9)';
    ctx.beginPath(); ctx.arc(x, y, 2.3, 0, Math.PI * 2); ctx.fill();
  }
}

function drawTree(ctx, t, frame) {
  ctx.fillStyle = 'rgba(0,0,0,.35)';
  ctx.beginPath(); ctx.ellipse(t.x + 3, t.y + 2, t.r, t.r * 0.32, 0, 0, Math.PI * 2); ctx.fill();
  if (t.kind === 'palm') {
    ctx.strokeStyle = '#3e2e1e'; ctx.lineWidth = 3; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(t.x, t.y); ctx.quadraticCurveTo(t.x + 3, t.y - 16, t.x + 7, t.y - 30); ctx.stroke();
    ctx.strokeStyle = '#2f4a2e'; ctx.lineWidth = 2.4;
    const top = { x: t.x + 7, y: t.y - 30 };
    for (let k = 0; k < 7; k++) {
      const a = (k / 7) * Math.PI * 2 + 0.25;
      ctx.beginPath(); ctx.moveTo(top.x, top.y);
      ctx.quadraticCurveTo(top.x + Math.cos(a) * 12, top.y + Math.sin(a) * 7 - 4, top.x + Math.cos(a) * 21, top.y + Math.sin(a) * 12 - 8);
      ctx.stroke();
    }
  } else {
    ctx.fillStyle = '#2c3c2b'; ctx.beginPath(); ctx.arc(t.x, t.y - 14, t.r * 0.62, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#3a4f3a'; ctx.beginPath(); ctx.arc(t.x - 5, t.y - 19, t.r * 0.45, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#1e2a1e'; ctx.fillRect(t.x - 2, t.y - 9, 4, 10);
  }
}

function drawBuilding(ctx, b, flagOn) {
  // ground shadow
  ctx.fillStyle = 'rgba(0,0,0,.4)';
  ctx.beginPath(); ctx.ellipse(b.x + b.w / 2 + 6, b.y + b.h + 4, b.w * 0.62, 7, 0, 0, Math.PI * 2); ctx.fill();
  // walls
  ctx.fillStyle = b.wall;
  ctx.fillRect(b.x, b.y, b.w, b.h);
  // wall shading — left face darker
  ctx.fillStyle = 'rgba(0,0,0,.22)';
  ctx.fillRect(b.x, b.y, b.w * 0.32, b.h);
  // roof slab
  ctx.fillStyle = b.roof;
  ctx.beginPath(); ctx.moveTo(b.x - 6, b.y); ctx.lineTo(b.x + b.w + 6, b.y); ctx.lineTo(b.x + b.w, b.y - 12); ctx.lineTo(b.x, b.y - 12); ctx.closePath(); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,.12)';
  ctx.fillRect(b.x, b.y - 12, b.w, 2.4);
  // terracotta tile lines
  ctx.strokeStyle = 'rgba(0,0,0,.28)'; ctx.lineWidth = 1;
  for (let k = 1; k < 4; k++) {
    ctx.beginPath(); ctx.moveTo(b.x + (b.w / 4) * k - 6, b.y); ctx.lineTo(b.x + (b.w / 4) * k, b.y - 12); ctx.stroke();
  }
  // door
  ctx.fillStyle = 'rgba(22,14,9,.9)';
  const dw = Math.min(14, b.w * 0.16), dh = Math.min(16, b.h * 0.4);
  ctx.fillRect(b.x + b.w / 2 - dw / 2, b.y + b.h - dh, dw, dh);
  // lit windows
  ctx.fillStyle = 'rgba(255,222,140,.9)';
  ctx.fillRect(b.x + 8, b.y + 8, 6, 7);
  if (b.w > 70) ctx.fillRect(b.x + b.w - 14, b.y + 8, 6, 7);
  // label
  if (b.label) {
    ctx.fillStyle = 'rgba(240,228,205,.92)'; ctx.font = '600 6.5px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(b.label, b.x + b.w / 2, b.y + b.h / 2 + 2);
    ctx.textAlign = 'left';
  }
  // adoption bunting flag
  if (flagOn && (b.kind === 'ev' || b.kind === 'mobile' || b.kind === 'chai' || b.kind === 'sabzi')) {
    const fx = b.x + b.w / 2, fy = b.y - 12;
    ctx.strokeStyle = '#2c2c2c'; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(fx, fy - 14); ctx.stroke();
    ctx.fillStyle = '#57f2a4';
    ctx.beginPath(); ctx.moveTo(fx, fy - 14); ctx.lineTo(fx + 11, fy - 10); ctx.lineTo(fx, fy - 6); ctx.closePath(); ctx.fill();
  }
}

function drawFigure(ctx, x, y, col, bob) {
  ctx.fillStyle = 'rgba(0,0,0,.45)';
  ctx.beginPath(); ctx.ellipse(x, y + 1, 4.4, 1.7, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#141009'; ctx.lineWidth = 1.5; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(x, y - 4 + bob); ctx.lineTo(x - 2.2, y + 1); ctx.moveTo(x, y - 4 + bob); ctx.lineTo(x + 2.2, y + 1); ctx.stroke();
  ctx.strokeStyle = col; ctx.lineWidth = 3.2;
  ctx.beginPath(); ctx.moveTo(x, y - 10 + bob); ctx.lineTo(x, y - 4 + bob); ctx.stroke();
  ctx.fillStyle = '#d6b07a';
  ctx.beginPath(); ctx.arc(x, y - 13 + bob, 2.5, 0, Math.PI * 2); ctx.fill();
}

function initTownAgents() {
  const r = S.run; if (!r) return;
  const sample = r.agents.slice(0, 100);
  townState.agents = sample.map((a, idx) => {
    const hs = TOWN.hotspots[idx % TOWN.hotspots.length];
    return {
      a,
      x: Math.random() * TOWN.W,
      y: Math.random() * TOWN.H * 0.7 + 24,
      tx: hs.x * TOWN.W + Math.random() * hs.w * TOWN.W,
      ty: hs.y * TOWN.H + Math.random() * hs.h * TOWN.H,
      speed: 15 + Math.random() * 22,
      phase: Math.random() * Math.PI * 2,
      pauseUntil: 0,
      target: hs,
    };
  });
  townState.initialised = true;
  townState.frame = 0;
  townState.chatting = [];
}

function updateTownAgents() {
  if (!townState.agents.length) return;
  const step = 1 / 60;
  townState.agents.forEach((u, idx) => {
    if (u.pauseUntil > townState.frame) { u.pauseUntil--; return; }
    const dx = u.tx - u.x, dy = u.ty - u.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 14) {
      const hs = u.target;
      u.tx = hs.x * TOWN.W + Math.random() * hs.w * TOWN.W;
      u.ty = hs.y * TOWN.H + Math.random() * hs.h * TOWN.H;
      u.pauseUntil = townState.frame + 40 + Math.floor(Math.random() * 110);
      return;
    }
    const wob = Math.sin((townState.frame + idx * 11) * 0.05) * 0.4;
    const nx = dx / dist, ny = dy / dist;
    u.x += (nx * u.speed - ny * wob * u.speed * 0.35) * step * 2.2;
    u.y += (ny * u.speed + nx * wob * u.speed * 0.35) * step * 2.2;
  });
  townState.chatting = [];
  for (let i = 0; i < townState.agents.length && townState.chatting.length < 3; i += 2) {
    for (let j = i + 1; j < townState.agents.length && townState.chatting.length < 3; j += 4) {
      const a = townState.agents[i], b = townState.agents[j];
      if (Math.hypot(a.x - b.x, a.y - b.y) < 32) townState.chatting.push({ a, b, phase: Math.random() * 1000 });
    }
  }
}

function drawTown() {
  const canvas = $('#townCanvas'); if (!canvas || !S.run) return;
  const ctx = canvas.getContext('2d');
  const r = S.run, day = S.day;
  const timeline = (r.timeline || [])[day - 1] || {};
  townState.frame += 1;
  if (!townState.initialised) initTownAgents();
  updateTownAgents();

  drawGround(ctx);
  TOWN.trees.forEach(t => drawTree(ctx, t, townState.frame));
  const flagOn = day >= 5;
  const sortedB = TOWN.buildings.slice().sort((a, b) => a.y - b.y);
  sortedB.forEach(b => drawBuilding(ctx, b, flagOn));

  const agentDraw = townState.agents.slice().sort((a, b) => a.y - b.y);
  agentDraw.forEach(u => {
    const ad = u.a.adopt_day;
    const aware = u.a.aware_day && u.a.aware_day <= day;
    const col = ad && ad <= day ? '#4ADE80' : aware ? '#F2C14E' : '#CBB791';
    const bob = Math.sin((townState.frame + u.phase * 90) * 0.09) * 1.4;
    drawFigure(ctx, u.x, u.y, col, bob);
    if (ad && ad <= day) {
      const pulse = ((townState.frame + u.phase * 40) % 70) / 70;
      ctx.strokeStyle = `rgba(74,222,128,${0.9 * (1 - pulse)})`;
      ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(u.x, u.y - 10 + bob, 5 + pulse * 12, 0, Math.PI * 2); ctx.stroke();
    }
  });

  townState.chatting.forEach(c => {
    const mx = (c.a.x + c.b.x) / 2, my = Math.min(c.a.y, c.b.y) - 22;
    ctx.strokeStyle = 'rgba(255,255,255,.3)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(c.a.x, c.a.y - 14); ctx.lineTo(mx - 8, my + 7); ctx.moveTo(c.b.x, c.b.y - 14); ctx.lineTo(mx + 8, my + 7); ctx.stroke();
    ctx.fillStyle = 'rgba(20,17,13,.94)';
    ctx.strokeStyle = 'rgba(255,255,255,.25)';
    const bw = 118, bh = 16;
    ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(mx - bw / 2, my - bh / 2, bw, bh, 5); else ctx.rect(mx - bw / 2, my - bh / 2, bw, bh); ctx.fill(); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.92)'; ctx.font = '8.5px Inter, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(TOWN.chatLines[Math.floor(c.phase + townState.frame / 45) % TOWN.chatLines.length], mx, my);
    ctx.textAlign = 'left';
  });

  // soft dusk vignette
  const vg = ctx.createRadialGradient(460, 210, 120, 460, 230, 560);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.22)');
  ctx.fillStyle = vg; ctx.fillRect(0, 0, TOWN.W, TOWN.H);

  const ticker = $('#townTickerText');
  if (ticker && townState.frame % 150 === 0) {
    const adopted = (r.agents || []).filter(a => a.adopt_day && a.adopt_day <= day);
    if (adopted.length) {
      const s = adopted[townState.frame % adopted.length];
      ticker.textContent = `day ${day} — ${adopted.length} adopted · ${s.name} (${s.occupation}): “${(s.quote || '').slice(0, 66)}”`;
    } else {
      ticker.textContent = `day ${day} — bazaar is awake · awareness ${pct(timeline.awareness || 0)} · adoption ${pct(timeline.adoption || 0)}`;
    }
  }

  townState.raf = requestAnimationFrame(drawTown);
}

/* ---------- live agent field + venn ---------- */
function setupAgentField() {
  const canvas = $('#agentField');
  const r = S.run;
  if (!canvas || !r) return;
  if (S.agentField.raf) { cancelAnimationFrame(S.agentField.raf); S.agentField.raf = null; }
  const W = canvas.width, H = canvas.height;
  const byTierX = { 1: W * 0.16, 2: W * 0.38, 3: W * 0.62, 4: W * 0.84 };
  const sample = (r.agents || []).slice(0, 150);
  S.agentField.agents = sample.map((a, i) => ({
    a,
    x: (byTierX[a.tier] || W / 2) + (Math.random() - 0.5) * 96,
    y: 34 + (i % 11) * 20 + Math.random() * 6,
    phase: Math.random() * Math.PI * 2,
    speed: 0.35 + Math.random() * 0.55,
  }));
  S.agentField.raf = requestAnimationFrame(drawAgentField);
}

function drawAgentField() {
  const canvas = $('#agentField');
  const r = S.run;
  if (!canvas || !r) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const day = S.day;
  ctx.clearRect(0, 0, W, H);
  // grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 1;
  for (let x = 0; x < W; x += 48) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 0; y < H; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  const agents = S.agentField.agents || [];
  // edges
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 0.6;
  for (let i = 0; i < agents.length; i++) {
    for (let j = i + 1; j < agents.length; j++) {
      const a = agents[i], b = agents[j];
      if (a.a.city === b.a.city || a.a.tier === b.a.tier) {
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 108) { ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); }
      }
    }
  }
  const t = performance.now() / 1000;
  agents.forEach(ag => {
    const a = ag.a;
    const adopted = a.adopt_day != null && a.adopt_day <= day;
    const rejected = a.rejected && (a.adopt_day == null);
    const aware = a.aware_day != null && a.aware_day <= day;
    let color = '#3a3a3e';
    if (adopted) color = '#4ADE80';
    else if (rejected) color = '#f87171';
    else if (aware) color = '#fbbf24';
    const y = ag.y + Math.sin(t * ag.speed + ag.phase) * 2.4;
    if (adopted && a.adopt_day === day) {
      ctx.beginPath(); ctx.arc(ag.x, y, 13, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(74,222,128,0.16)'; ctx.fill();
    }
    ctx.beginPath(); ctx.arc(ag.x, y, 4.6, 0, Math.PI * 2);
    ctx.fillStyle = color; ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.22)'; ctx.lineWidth = 0.8; ctx.stroke();
  });
  // speech bubbles for today's posts
  const posts = (r.posts || []).filter(p => p.day === day).slice(0, 4);
  posts.forEach((p, i) => {
    const ag = agents[(i * 19 + 3) % Math.max(1, agents.length)];
    if (!ag) return;
    const x = ag.x, y = ag.y - 20;
    const txt = String(p.text || '').replace(/[#*]/g, '').slice(0, 44);
    ctx.font = '10px Inter, sans-serif';
    const tw = ctx.measureText(txt).width;
    const bw = Math.min(250, tw + 14);
    ctx.fillStyle = 'rgba(12,12,14,0.92)';
    ctx.strokeStyle = 'rgba(255,255,255,0.22)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x - 6, y - 24, bw, 22, 6);
    else ctx.rect(x - 6, y - 24, bw, 22);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.86)';
    ctx.textBaseline = 'middle';
    ctx.fillText(txt, x, y - 13);
  });
  S.agentField.raf = requestAnimationFrame(drawAgentField);
}

function renderVenn() {
  const r = S.run;
  const el = $('#vennDiagram');
  if (!el || !r) return;
  const defs = [
    { id: 'price', label: 'Price', color: '#fbbf24', keys: ['price', 'cost', 'emi', 'budget', 'expensive', 'value', 'resale', 'afford'] },
    { id: 'trust', label: 'Trust', color: '#4ADE80', keys: ['trust', 'quality', 'warranty', 'service', 'repair', 'safety', 'risk', 'fake', 'break'] },
    { id: 'supply', label: 'Supply', color: '#a8d8ff', keys: ['service network', 'charging', 'availability', 'delivery', 'stock', 'supply', 'wait', 'install', 'coverage', 'dealer'] },
  ];
  const corpus = ((r.posts || []).map(p => p.text).join(' ') + ' ' + ((r.report || {}).objections || []).map(o => o.reason).join(' ')).toLowerCase();
  const counts = defs.map(d => ({ ...d, n: Math.max(1, d.keys.reduce((a, k) => a + (corpus.includes(k) ? 1 : 0), 0)) }));
  const total = counts.reduce((a, c) => a + c.n, 0) || 1;
  const shares = counts.map(c => c.n / total);
  const radii = shares.map(s => 34 + s * 46);
  const cx = 180, cy = 128;
  const positions = [{ x: cx - 62, y: cy - 18 }, { x: cx + 62, y: cy - 18 }, { x: cx, y: cy + 52 }];
  let svg = '';
  counts.forEach((c, i) => {
    svg += `<circle cx="${positions[i].x}" cy="${positions[i].y}" r="${radii[i]}" fill="${c.color}" class="venn-circle" stroke="${c.color}"/>`;
  });
  counts.forEach((c, i) => {
    svg += `<text x="${positions[i].x}" y="${positions[i].y - 4}" text-anchor="middle" class="venn-label">${esc(c.label)}</text>`;
    svg += `<text x="${positions[i].x}" y="${positions[i].y + 12}" text-anchor="middle" class="venn-count">${Math.round(shares[i] * 100)}%</text>`;
  });
  const top = counts.slice().sort((a, b) => b.n - a.n)[0];
  svg += `<text x="${cx}" y="248" text-anchor="middle" class="venn-count">Largest driver in the objection set: ${esc(top.label)}</text>`;
  el.innerHTML = svg;
  const note = $('#vennNote');
  if (note) note.textContent = 'Circle size reflects how often each driver appears in posts and rejection reasons. Overlap is implied by co-occurrence, not a measured joint distribution.';
}

/* ---------- research ---------- */
function renderResearch() {
  const r = S.run; if (!r) return;
  const res = r.research || {};
  const status = $('#researchStatus');
  if (status) status.textContent = res.ok ? 'Researched' : 'No public summary';
  const llmChip = $('#llmStatus');
  if (llmChip) {
    fetch('/api/llm').then(r => r.json()).then(d => {
      llmChip.textContent = d.available ? `LLM: ${d.backend} · ${d.model}` : 'LLM: deterministic (no model)';
      llmChip.className = d.available ? 'chip chip--green' : 'chip chip--muted';
    }).catch(() => { llmChip.textContent = 'LLM: unknown'; });
  }
  const title = $('#researchTitle');
  if (title) title.textContent = res.ok ? (res.title || r.topic.label) : r.topic.label;
  const cached = $('#researchCached');
  if (cached) cached.textContent = res.cached ? 'cached' : (res.ok ? 'live fetch' : '');
  const extract = $('#researchExtract');
  if (extract) extract.textContent = res.ok ? (res.extract || '') : (res.error || 'No research available for this phrase.');
  const links = $('#researchLinks');
  if (links) links.innerHTML = (res.ok && res.url) ? `<a href="${esc(res.url)}" target="_blank" rel="noopener">Open source ↗</a>` : '';
  const notes = $('#researchNotes');
  if (notes) {
    const items = [];
    if (res.ok) {
      items.push(`Pulled a public summary for “${res.title}” and attached it to the generic priors.`);
      items.push(`Motion set to: “${r.topic.motion}”.`);
      if (r.topic.price && r.topic.price !== 1000) items.push(`Price extracted from brief: ₹${Number(r.topic.price).toLocaleString('en-IN')}.`);
    } else {
      items.push('No public summary found; simulated with generic Indian priors.');
      items.push('Add a price in the brief (e.g. ₹45,000) and a category word to improve the run.');
    }
    items.push(`Topic label: ${r.topic.label}. Category: ${r.topic.category}.`);
    notes.innerHTML = items.map(x => `<li>${esc(x)}</li>`).join('');
  }
  const note = $('#researchNote');
  if (note) note.textContent = res.ok ? 'Research is cached by brief text. Re-running the same phrase is instant.' : 'Network or no match; the simulation still runs on generic priors.';
}

/* ---------- validation & research audit ---------- */
function valRow(cells, head = false, cls = '') {
  return `<div class="val-row ${head ? 'val-row--head' : ''} ${cls}">${cells.map((c, i) =>
    `<span${i ? ' class="num"' : ''}>${c}</span>`).join('')}</div>`;
}

function renderValidation() {
  const v = S.validation;
  const mc = S.modelcard;
  if (!v) return;
  const sum = v.summary || {};
  const bt = v.backtest || {};
  const ka = v.known_answer || {};
  const r = S.robust;

  if (mc?.identity) {
    $('#valEngine').textContent = `${mc.identity.engine} · v${mc.identity.version}`;
    $('#valCardMeta').textContent = mc.identity.generated_at?.slice(0, 10) || '';
  }

  $('#valMetrics').innerHTML = [
    metric('Known-answer', `${sum.known_answer_passed || '—'}`, 'analytic identities', sum.known_answer_score === 1 ? 'metric--green' : '', sum.known_answer_score || 0),
    metric('Forecast skill', (bt.median_vs_drift_timesfm_aug3 ?? bt.median_vs_drift_timesfm) != null ? Number(bt.median_vs_drift_timesfm_aug3 ?? bt.median_vs_drift_timesfm).toFixed(2) : '—', 'aug3 vs drift · below 1 adds value', ((bt.median_vs_drift_timesfm_aug3 ?? bt.median_vs_drift_timesfm) != null && (bt.median_vs_drift_timesfm_aug3 ?? bt.median_vs_drift_timesfm) < 1) ? 'metric--green' : ''),
    metric('Band coverage', bt.median_coverage_timesfm_reasoned != null ? pct(bt.median_coverage_timesfm_reasoned, 0) : '—', '80% interval · reasoned path'),
    metric('Trend skill', bt.median_trend_skill_timesfm_aug3 != null ? signed(bt.median_trend_skill_timesfm_aug3, 2) : (bt.median_trend_skill != null ? signed(bt.median_trend_skill, 2) : '—'), 'beyond an always-up rule'),
    metric('Ensemble runs', r ? String(r.runs) : '—', r ? `${r.seeds} seeds × ${r.param_draws} draws` : 'not run yet'),
    metric('Model card', mc ? `${(mc.limitations || []).length} limits` : '—', mc ? `${mc.population.counts.topics} categories · ${mc.population.counts.evidence} evidence cards` : ''),
  ].join('');

  $('#valBatteryMeta').textContent = `${ka.passed || 0}/${ka.total || 0} passed`;
  $('#valBattery').innerHTML = (ka.checks || []).map(c =>
    reasonCheck(c.label, c.ok, c.detail)
  ).join('') || '<p class="small-copy">Battery unavailable.</p>';

  $('#valBacktestMeta').textContent = bt.n_topics ? `${bt.n_topics} categories · horizon ${bt.horizon}m` : '';
  const rows = (bt.topics || []).slice(0, 9);
  $('#valBacktest').innerHTML = rows.length ? (
    valRow(['Category', 'MASE', 'Raw', 'Aug3', 'vs drift', 'Cover'], true, 'val-row--wide') +
    rows.map(t => valRow([
      `<b>${esc(t.label)}</b>`,
      t.mase != null ? Number(t.mase).toFixed(2) : '—',
      t.mase_timesfm != null ? Number(t.mase_timesfm).toFixed(2) : '—',
      t.mase_timesfm_aug3 != null ? Number(t.mase_timesfm_aug3).toFixed(2) : '—',
      t.vs_drift_timesfm_aug3 != null ? `<span style="color:${t.vs_drift_timesfm_aug3 < 1 ? 'var(--green)' : 'var(--amber)'}">${Number(t.vs_drift_timesfm_aug3).toFixed(2)}</span>` : '—',
      t.coverage_timesfm_reasoned != null ? pct(t.coverage_timesfm_reasoned, 0) : '—',
    ], false, 'val-row--wide')).join('')
  ) : '<p class="small-copy">No category history was long enough to backtest.</p>';
  $('#valBacktestNote').textContent = [bt.note, bt.augmentation_verdict].filter(Boolean).join(' ');
  if (bt.verdict) $('#valBacktestMeta').textContent += ` · ${bt.verdict.split(';')[0]}`;

  renderEnsemble();
  renderSensitivity();
  renderModelCard();
  renderExport();
}

function renderEnsemble() {
  const r = S.robust;
  const box = $('#valEnsemble');
  if (!r) {
    box.innerHTML = '<p class="small-copy">Run the ensemble to see the interval, the decision probabilities and whether the spread comes from assumptions or from seed noise.</p>';
    return;
  }
  const c = r.conversion || {};
  const d = r.decision || {};
  const span = (c.p90 != null && c.p10 != null) ? Math.max(0.01, c.p90 - c.p10) : 0;
  const left = clamp((c.p10 || 0) * 100, 0, 100);
  const width = clamp(span * 100, 1, 100);
  const mid = clamp((c.p50 || 0) * 100, 0, 100);
  const target = clamp((d.target_conversion || 0) * 100, 0, 100);
  $('#valEnsembleMeta').textContent = `${r.runs} runs · seed ${r.rows?.[0]?.seed ?? ''}`;
  box.innerHTML = `
    <div class="val-fan">
      <div class="val-fan__head"><span>p10 ${pct(c.p10)}</span><span class="val-fan__mid">p50 ${pct(c.p50)}</span><span>p90 ${pct(c.p90)}</span></div>
      <div class="val-fan__track">
        <span class="val-fan__range" style="left:${left}%;width:${width}%"></span>
        <span class="val-fan__median" style="left:${mid}%"></span>
        <span class="val-fan__target" style="left:${target}%"></span>
      </div>
      <div class="val-fan__foot"><span>0%</span><span>target ${pct(d.target_conversion, 0)}</span><span>100%</span></div>
    </div>
    ${valRow(['Decision', 'Probability'], true)}
    ${valRow(['Conversion ≥ target', pct(d.p_at_or_above_target, 0)])}
    ${valRow(['Verdict SCALE', pct(d.p_scale, 0)])}
    ${valRow(['SCALE or TEST', pct(d.p_scale_or_test, 0)])}
    ${valRow(['Robust call', r.robust ? '<span style="color:var(--green)">yes</span>' : '<span style="color:var(--amber)">no</span>'])}
    <div class="val-split">
      <div><span class="panel__eyebrow">Epistemic</span><b>${pct(r.variance.epistemic_share, 0)}</b><small>assumption risk</small></div>
      <div><span class="panel__eyebrow">Aleatoric</span><b>${pct(1 - r.variance.epistemic_share, 0)}</b><small>seed noise</small></div>
    </div>
    <div class="val-corr">${(r.param_corr || []).map(p =>
      `<span class="chip ${Math.abs(p.corr) > .5 ? 'chip--warn' : 'chip--muted'}">${esc(p.param.replace(/_/g, ' '))} ${signed(p.corr, 2)}</span>`).join('')}</div>`;
  $('#valEnsembleNote').textContent = r.note || '';
}

function renderSensitivity() {
  const se = S.sens;
  const box = $('#valSensitivity');
  const note = $('#valSensNote');
  if (!se) {
    box.innerHTML = '<p class="small-copy">A total-order variance decomposition tells you which parameters are worth tuning and which are theatre.</p>';
    note.textContent = '';
    return;
  }
  if (!se.available) {
    box.innerHTML = `<p class="small-copy">${esc(se.note || 'No variance in the output at this setting.')}</p>`;
    note.textContent = '';
    return;
  }
  box.innerHTML = `<div class="param-lab">${se.indices.map(i => `
    <div class="param-row" title="ST ${i.st} · linear ${i.linear_share} · interaction ${i.interaction}">
      <span class="name">${esc(i.param.replace(/_/g, ' '))}</span>
      <div class="track"><div class="fill" style="width:${clamp(i.st, 0, 1) * 100}%"></div></div>
      <span class="val">${Number(i.st).toFixed(2)}</span>
    </div>`).join('')}</div>
    <p class="small-copy">Linear fit R² ${se.linear_fit_r2} · ${se.evaluations} simulations · most influential: <b>${esc((se.most_influential || '').replace(/_/g, ' '))}</b>${se.inert?.length ? ` · inert: ${se.inert.map(x => esc(x.replace(/_/g, ' '))).join(', ')}` : ''}</p>`;
  note.textContent = se.note || '';
  $('#valSensitivity').querySelectorAll('.param-row').forEach((row, idx) => {
    const i = se.indices[idx];
    row.querySelector('.track').title = `ST ${i.st} · linear share ${i.linear_share} · interaction ${i.interaction}`;
  });
}

function renderModelCard() {
  const mc = S.modelcard;
  if (!mc) return;
  const list = (items, cls = '') => `<ul class="reason-limits ${cls}">${(items || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
  $('#valCard').innerHTML = `
    <span class="panel__eyebrow">Intended use</span>${list(mc.intended_use)}
    <span class="panel__eyebrow">Out of scope</span>${list(mc.out_of_scope)}
    <span class="panel__eyebrow">Limitations</span>${list(mc.limitations)}
    <div class="val-corr">${['timesfm', 'llm'].map(k => {
      const s = mc.systems?.[k] || {};
      const ok = k === 'timesfm' ? s.loaded : s.available;
      return `<span class="chip ${ok ? 'chip--green' : 'chip--warn'}">${k}: ${ok ? (k === 'timesfm' ? 'loaded' : (s.backend || 'available')) : 'fallback'}</span>`;
    }).join('')}</div>`;
}

function renderExport() {
  const r = S.run;
  const box = $('#valExport');
  if (!r) {
    box.innerHTML = '<p class="small-copy">Run a simulation to make it citable. Every run stores its provenance, timeline and parameters for export.</p>';
    $('#valProvenance').textContent = '';
    return;
  }
  const p = r.provenance || {};
  $('#valProvenance').textContent = p.fingerprint ? `fingerprint ${p.fingerprint}` : '';
  box.innerHTML = `
    <div class="val-export">
      <div><b>${esc(r.topic?.label || 'Run')}</b><br><span>${esc(r.run_id)} · seed ${r.seed} · ${r.population} agents · ${r.rounds} rounds</span></div>
      <div class="val-export__actions">
        <a class="btn btn--ghost btn--sm" href="/api/runs/${encodeURIComponent(r.run_id)}/export?format=md" download>Markdown memo</a>
        <a class="btn btn--ghost btn--sm" href="/api/runs/${encodeURIComponent(r.run_id)}/export?format=json" download>JSON bundle</a>
        <a class="btn btn--ghost btn--sm" href="/api/runs/${encodeURIComponent(r.run_id)}/export?format=csv" download>Timeline CSV</a>
        <a class="btn btn--ghost btn--sm" href="/api/runs/${encodeURIComponent(r.run_id)}" target="_blank" rel="noopener">Open bundle</a>
      </div>
    </div>
    <p class="causal-note">${esc(p.replay || 'Same brief + seed + parameters + engine version reproduces the run.')}</p>`;
}

async function loadValidation(force = false) {
  if (S.validationLoading) return;
  S.validationLoading = true;
  try {
    const [v, mc] = await Promise.all([
      fetch('/api/validation').then(r => r.json()),
      fetch('/api/model-card').then(r => r.json()),
    ]);
    S.validation = v;
    S.modelcard = mc;
    renderValidation();
  } catch (err) {
    $('#valBattery').innerHTML = `<p class="small-copy">Validation unavailable: ${esc(err.message)}</p>`;
  } finally {
    S.validationLoading = false;
  }
}

async function runEnsemble() {
  const btn = $('#valEnsembleRun');
  if (!S.run) { toast('Run a simulation first.'); return; }
  btn.disabled = true; const label = btn.innerHTML;
  btn.textContent = 'Running 25 simulations…';
  $('#valEnsembleMeta').textContent = 'working';
  try {
    const res = await fetch('/api/robustness', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brief: S.run.brief, n_agents: 150, rounds: 20, seed: S.run.seed,
        scenario: S.run.scenario || 'base', focus_state: S.run.focus_state || null,
        tier_mix: S.run.tier_mix || null,
      }),
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Ensemble failed');
    S.robust = d; renderValidation();
    toast(`Ensemble · conv ${pct(d.conversion.p10, 0)}–${pct(d.conversion.p90, 0)} · P(SCALE) ${pct(d.decision.p_scale, 0)}`);
  } catch (err) {
    toast(err.message);
    $('#valEnsembleMeta').textContent = 'failed';
  } finally {
    btn.disabled = false; btn.innerHTML = label; injectIcons(btn);
  }
}

async function runSensitivity() {
  const btn = $('#valSensRun');
  if (!S.run) { toast('Run a simulation first.'); return; }
  btn.disabled = true; const label = btn.innerHTML;
  btn.textContent = 'Scanning…';
  try {
    const res = await fetch('/api/sensitivity', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brief: S.run.brief, n_agents: 140, rounds: 18, seed: S.run.seed,
        scenario: S.run.scenario || 'base', focus_state: S.run.focus_state || null,
        tier_mix: S.run.tier_mix || null, metric: 'conversion', n_base: 6,
      }),
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || 'Sensitivity failed');
    S.sens = d; renderSensitivity();
    toast(`Sensitivity · ${d.most_influential?.replace(/_/g, ' ')} dominates`);
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false; btn.innerHTML = label; injectIcons(btn);
  }
}

/* ---------- command palette ---------- */
const CMD_ITEMS = [
  ...['world','social','debate','focus','cognition','forecast','evidence','research','atlas','precedents','causal','calibration','validation','reasoning','report'].map(t => ({ label: `Go to ${t}`, kind: 'tab', value: t, hint: 'tab' })),
  { label: 'Run simulation', kind: 'action', value: 'run', hint: 'Enter' },
  { label: 'Play / pause timeline', kind: 'action', value: 'play', hint: 'Space' },
  { label: 'Deep reason', kind: 'action', value: 'reason', hint: 'R' },
  { label: 'Export run JSON', kind: 'action', value: 'export', hint: 'E' },
  { label: 'Show help', kind: 'action', value: 'help', hint: '?' },
];

function openCmdPalette() {
  const m = $('#cmdPalette'); if (!m) return;
  m.classList.add('open'); m.setAttribute('aria-hidden', 'false');
  const inp = $('#cmdInput'); if (inp) { inp.value = ''; inp.focus(); }
  renderCmdList('');
}
function closeCmdPalette() {
  const m = $('#cmdPalette'); if (!m) return;
  m.classList.remove('open'); m.setAttribute('aria-hidden', 'true');
}
function renderCmdList(q) {
  const list = $('#cmdList'); if (!list) return;
  const ql = (q || '').toLowerCase();
  const items = CMD_ITEMS.filter(i => i.label.toLowerCase().includes(ql));
  list.innerHTML = items.map((i, idx) => `<div class="cmd-item ${idx === 0 ? 'active' : ''}" data-cmd="${esc(i.value)}" data-kind="${esc(i.kind)}"><span>${esc(i.label)}</span><kbd>${esc(i.hint)}</kbd></div>`).join('');
  list.querySelectorAll('.cmd-item').forEach(el => {
    el.addEventListener('click', () => execCmd(el.dataset.kind, el.dataset.cmd));
  });
}
function execCmd(kind, value) {
  closeCmdPalette();
  if (kind === 'tab') switchTab(value);
  else if (value === 'run') runSimulation();
  else if (value === 'play') togglePlay();
  else if (value === 'reason') { switchTab('reasoning'); setTimeout(runReasoning, 200); }
  else if (value === 'export') $('#exportBtn')?.click();
  else if (value === 'help') $('#helpModal')?.classList.add('open');
}

/* ---------- operations console ---------- */
function ops(kind, msg) {
  if (S.opsPaused) return;
  const t = new Date().toLocaleTimeString('en-IN', { hour12: false }).slice(0, 8);
  const entry = { kind, msg, time: t, id: Math.random().toString(36).slice(2, 8) };
  S.opsLog.unshift(entry);
  if (S.opsLog.length > 200) S.opsLog.pop();
  renderOps();
}

function renderOps() {
  const el = $('#opsStream');
  if (!el) return;
  el.innerHTML = S.opsLog.slice(0, 12).map(e => `
    <div class="ops-event ops-event--${e.kind}">
      <span class="ops-kind">${esc(e.kind)}</span>
      <span class="ops-msg">${esc(e.msg)}</span>
      <span class="ops-time">${e.time}</span>
    </div>`).join('');
}

function updateSysChips() {
  fetch('/api/health').then(r => r.json()).then(d => {
    const fc = $('#sysForecast'); const llm = $('#sysLLM'); const ctx = $('#sysContext');
    if (fc) fc.innerHTML = `TimesFM: <b>${d.forecast && d.forecast.loaded ? 'loaded' : 'down'}</b>`;
    if (llm) {
      const l = d.llm || {};
      llm.innerHTML = `LLM: <b>${l.available ? l.backend : 'offline'}</b>`;
      llm.className = l.available ? 'sys-chip' : 'sys-chip';
    }
    if (ctx) ctx.innerHTML = `Context: <b>${d.context && d.context.nodes ? d.context.nodes + ' nodes' : '—'}</b>`;
  }).catch(() => {});
}

async function fetchRuns() {
  try {
    const d = await fetch('/api/runs').then(r => r.json());
    return (d.runs || []).slice(0, 50);
  } catch (e) { return []; }
}

function runToMetricRow(r) {
  const s = r.summary || {};
  return `<div class="compare-metric"><span>adoption</span><b>${pct(s.adoption || 0)}</b></div>
    <div class="compare-metric"><span>conversion</span><b>${pct(s.conversion || 0)}</b></div>
    <div class="compare-metric"><span>sentiment</span><b>${signed(s.sentiment || 0, 2)}</b></div>
    <div class="compare-metric"><span>verdict</span><b style="font-size:8px">${esc(s.verdict || '—')}</b></div>
    <div class="compare-metric"><span>confidence</span><b>${pct(s.confidence || 0)}</b></div>`;
}

/* ---------- comparison ---------- */
async function openCompare() {
  const modal = $('#compareModal');
  if (!modal) return;
  modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false');
  const runs = await fetchRuns();
  S.compareRuns = runs;
  const sel = (id, el) => {
    el.innerHTML = `<select class="select select--sm" style="width:100%"><option value="">select run</option>${runs.map(r => `<option value="${esc(r.run_id)}">${esc(r.run_id)} · ${esc(r.brief || '').slice(0,24)}</option>`).join('')}</select>`;
    const selEl = el.querySelector('select');
    if (id) { selEl.value = id; selEl.dispatchEvent(new Event('change')); }
    selEl.addEventListener('change', () => renderCompare());
  };
  sel(null, $('#compareSelA'));
  sel(null, $('#compareSelB'));
  renderCompare();
}

function closeCompare() {
  const modal = $('#compareModal');
  if (modal) { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
}

function renderCompare() {
  const aId = $('#compareSelA select')?.value; const bId = $('#compareSelB select')?.value;
  const a = S.compareRuns.find(r => r.run_id === aId); const b = S.compareRuns.find(r => r.run_id === bId);
  $('#compareMetricsA').innerHTML = a ? runToMetricRow(a) : '<span style="color:rgba(255,255,255,.3)">no run selected</span>';
  $('#compareMetricsB').innerHTML = b ? runToMetricRow(b) : '<span style="color:rgba(255,255,255,.3)">no run selected</span>';
  const diff = $('#compareDiff');
  if (a && b) {
    const sa = a.summary || {}; const sb = b.summary || {};
    const rows = [
      ['adoption', sa.adoption, sb.adoption],
      ['conversion', sa.conversion, sb.conversion],
      ['sentiment', sa.sentiment, sb.sentiment],
      ['confidence', sa.confidence, sb.confidence],
    ];
    diff.innerHTML = rows.map(([k, va, vb]) => {
      const d = (va || 0) - (vb || 0);
      const cls = Math.abs(d) < 0.0001 ? 'neutral' : (d > 0 ? 'up' : 'down');
      return `<div class="diff-row"><span>${esc(k)}</span><span class="delta ${cls}">${signed(d, 3)}</span></div>`;
    }).join('');
  } else {
    diff.innerHTML = '<span style="color:rgba(255,255,255,.3)">Select two runs to diff.</span>';
  }
}

/* ---------- run buttons ---------- */
async function runReasoningBtn() {
  if (!S.run) { toast('Run a simulation first.'); return; }
  switchTab('reasoning');
  setTimeout(() => runReasoning(), 200);
}

function renderParamLab() {
  const el = $('#paramLab');
  if (!el) return;
  fetch('/api/calibration').then(r => r.json()).then(d => {
    const params = d.params || {};
    const specs = d.specs || {};
    const order = ['ceiling_mult','price_sensitivity','social_mult','trust_weight','hazard_mult','atlas_strength'];
    el.innerHTML = order.map(k => {
      const v = Number(params[k] || 1);
      const sp = specs[k] || { low: 0.2, high: 2 };
      const pct = clamp(((v - sp.low) / (sp.high - sp.low || 1)) * 100, 0, 100);
      return `<div class="param-row" data-key="${esc(k)}">
        <span class="name">${esc(k.replace(/_/g,' '))}</span>
        <div class="track"><div class="fill" style="width:${pct}%"></div><div class="thumb" style="left:${pct}%"></div></div>
        <span class="val">${v.toFixed(2)}</span>
      </div>`;
    }).join('');
    el.querySelectorAll('.param-row').forEach(row => {
      const key = row.dataset.key; const track = row.querySelector('.track'); const thumb = row.querySelector('.thumb'); const fill = row.querySelector('.fill'); const val = row.querySelector('.val');
      const sp = (d.specs || {})[key] || { low: 0.2, high: 2 };
      let dragging = false;
      const setPos = (x) => {
        const rect = track.getBoundingClientRect();
        let p = clamp((x - rect.left) / rect.width, 0, 1);
        p = Math.round(p * 100) / 100;
        const v = sp.low + p * (sp.high - sp.low);
        thumb.style.left = `${p * 100}%`; fill.style.width = `${p * 100}%`;
        val.textContent = v.toFixed(2);
        row.dataset.val = v.toFixed(4);
      };
      track.addEventListener('mousedown', () => { dragging = true; });
      track.addEventListener('mousemove', e => { if (dragging) setPos(e.clientX); });
      window.addEventListener('mouseup', () => { dragging = false; });
      track.addEventListener('click', e => setPos(e.clientX));
    });
  }).catch(() => { el.innerHTML = '<span style="color:rgba(255,255,255,.3)">params unavailable</span>'; });
}

async function applyParams() {
  const rows = $$('#paramLab .param-row');
  const params = {};
  rows.forEach(row => { params[row.dataset.key] = Number(row.dataset.val || 1); });
  const btn = $('#paramApply');
  const label = btn.innerHTML;
  btn.disabled = true; btn.textContent = 'Applying…';
  try {
    const res = await fetch('/api/calibration', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ params }) });
    if (!res.ok) throw new Error('apply failed');
    ops('params', `applied ${Object.keys(params).join(', ')}`);
    toast('Parameters applied. Re-run to see effect.');
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; btn.innerHTML = label; }
}

/* ---------- generative encounters ---------- */
function renderEncounters() {
  const r = S.run;
  const wrap = $('#worldEncounters');
  if (!wrap) return;
  const list = $('#encountersList');
  const encs = (r && r.encounters) || [];
  if (!encs.length) { wrap.hidden = true; return; }
  wrap.hidden = false;
  const mode = $('#encountersMode');
  if (mode) mode.textContent = 'Concordia GM · ' + (encs[0].gm_mode === 'llm' ? 'LLM-adjudicated' : 'template');
  list.innerHTML = encs.map(e => `
    <div class="encounter-card">
      <div class="encounter-head"><b>${esc(e.a.name)} × ${esc(e.b.name)}</b><span class="encounter-outcome ${esc(e.outcome)}">${esc(e.outcome)}</span></div>
      <div class="encounter-dialogue">${esc((e.dialogue || e.reason || '').slice(0, 500))}</div>
      <div class="encounter-foot">${esc(e.setting || '')} · stance ${e.stance_delta >= 0 ? '+' : ''}${Math.round((e.stance_delta || 0) * 100)}%</div>
    </div>`).join('');
}

/* ---------- tabs ---------- */
function switchTab(name) {
  S.tab = name;
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
  if (name === 'forecast' && S.run) {
    populateForecastTopics();
    if (!S.forecast) loadForecast();
  }
  if (name === 'evidence') renderEvidence();
  if (name === 'research') renderResearch();
  if (name === 'cognition') renderCognition();
  if (name === 'perception') renderPerception();
  if (name === 'atlas') loadAtlas();
  if (name === 'precedents') loadPrecedents();
  if (name === 'causal') loadCausal();
  if (name === 'calibration') loadCalibration();
  if (name === 'validation') loadValidation();
  if (name === 'reasoning') loadReasoning();
  if (name === 'world' && S.run) { initTownAgents(); if (townState.raf) cancelAnimationFrame(townState.raf); townState.raf = requestAnimationFrame(drawTown); }
  if (name !== 'world') { if (townState.raf) { cancelAnimationFrame(townState.raf); townState.raf = null; } if (S.agentField && S.agentField.raf) { cancelAnimationFrame(S.agentField.raf); S.agentField.raf = null; } }
  if (name === 'debate' && S.run) setTimeout(() => { if (!debatePlay) playDebate(); }, 400);
}

/* ---------- boot ---------- */
async function boot() {
  injectIcons();
  // Populate tier mix controls.
  const mix = [10, 15, 28, 47];
  $('#tierMix').innerHTML = [1, 2, 3, 4].map((t, i) => `<label class="tier-mini"><span>T${t}</span><input data-tier="${t}" type="number" min="0" max="100" value="${mix[i]}"/><b>%</b></label>`).join('');
  const updateTierTotal = () => {
    const total = $$('.tier-mini input').reduce((a, el) => a + (Number(el.value) || 0), 0);
    $('#tierTotal').textContent = `${total}%`;
    $('#tierTotal').style.color = total === 100 ? 'rgba(255,255,255,.35)' : 'var(--amber)';
  };
  $$('.tier-mini input').forEach(el => el.addEventListener('input', updateTierTotal));
  updateTierTotal();

  $('#agentsRange').addEventListener('input', e => $('#agentsVal').textContent = e.target.value);
  $('#roundsRange').addEventListener('input', e => $('#roundsVal').textContent = e.target.value);
  $('#runBtn').addEventListener('click', runSimulation);
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); runSimulation(); }
    if (e.key === 'Escape') { closeDrawer(); $('#helpModal').classList.remove('open'); }
  });
  $('#tabs').addEventListener('click', e => { const t = e.target.closest('.tab'); if (t) switchTab(t.dataset.tab); });
  $('#playBtn').addEventListener('click', togglePlay);
  $('#dayRange').addEventListener('input', e => { if (S.playing) { clearInterval(S.playTimer); S.playing = false; $('#playBtn').innerHTML = ICONS.play; } setDay(Number(e.target.value)); });
  $('#playDebate').addEventListener('click', playDebate);
  $('#challengeDebate').addEventListener('click', challengeDebate);
  $('#cmdBtn')?.addEventListener('click', openCmdPalette);
  $('#railCollapse').addEventListener('click', () => { $('.st-layout').classList.toggle('rail-collapsed'); setTimeout(() => { renderWorld(); }, 300); });

  $('#topicSelect').addEventListener('change', e => {
    const t = S.meta.topics.find(x => x.id === e.target.value);
    if (t) {
      $('#briefInput').value = `${t.motion} Test: ${t.label.toLowerCase()} in India.`;
      $('#topicCategory').textContent = t.category;
      $('#crumbTopic').textContent = t.label;
      $('#forecastTopic').value = t.id;
      if (S.tab === 'forecast') loadForecast();
    }
  });
  $('#scenarioGrid').addEventListener('click', e => {
    const b = e.target.closest('.scenario'); if (!b) return;
    S.scenario = b.dataset.id;
    $$('.scenario').forEach(x => x.classList.toggle('active', x === b));
  });
  $('#platformFilters').addEventListener('click', e => {
    const b = e.target.closest('[data-platform]'); if (!b) return;
    S.social.platform = b.dataset.platform; S.social.limit = 40; renderSocial();
  });
  $('#tierFilter').addEventListener('change', e => { S.social.tier = e.target.value; S.social.limit = 40; renderPostList(); });
  $('#sortFilter').addEventListener('change', e => { S.social.sort = e.target.value; S.social.limit = 40; renderPostList(); });
  $('#loadMorePosts').addEventListener('click', () => { S.social.limit += 30; renderPostList(); });
  $('#socialFeed').addEventListener('click', e => {
    const thread = e.target.closest('[data-thread]');
    if (thread) { const t = $(`#thread-${CSS.escape(thread.dataset.thread)}`); if (t) { t.classList.toggle('open'); } return; }
  });
  $('#focusForm').addEventListener('submit', async e => {
    e.preventDefault();
    const q = $('#focusInput').value.trim(); if (!q || !S.run) return;
    $('#focusInput').value = '';
    $('#focusMeta').textContent = 'The room is thinking…';
    try {
      const res = await fetch('/api/focus-group', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ brief: S.run.brief, question: q, seed: S.run.seed, state: $('#stateSelect').value || null }) });
      const d = await res.json();
      S.focusRounds.push({ question: q, group: d.group });
      renderFocus();
      $('#focusMeta').textContent = `${d.group.length} participants · ${S.focusRounds.length} rounds`;
    } catch (err) { toast('The room did not answer. Try again.'); }
  });
  $('#focusChat').addEventListener('click', e => {
    const b = e.target.closest('[data-mono]'); if (!b) return;
    const el = $(`#mono-${CSS.escape(b.dataset.mono)}`); if (el) el.classList.toggle('open');
  });
  $('#agentSearch').addEventListener('input', () => { S.agentLimit = 36; renderAgents(); });
  $('#agentTier').addEventListener('change', () => { S.agentLimit = 36; renderAgents(); });
  $('#loadMoreAgents').addEventListener('click', () => { S.agentLimit += 36; renderAgents(); });
  $('#forecastRun').addEventListener('click', loadForecast);
  $('#forecastHorizon').addEventListener('change', loadForecast);
  $('#forecastTopic').addEventListener('change', loadForecast);
  $('#scenarioRun').addEventListener('click', loadScenarios);
  $('#evidenceSearch').addEventListener('input', e => { S.evidenceQuery = e.target.value; renderEvidence(); });
  $('#domainChips').addEventListener('click', e => { const b = e.target.closest('[data-domain]'); if (!b) return; S.evidenceDomain = b.dataset.domain; renderEvidence(); });
  $('#atlasSearch').addEventListener('input', e => {
    S.atlasQuery = e.target.value;
    clearTimeout(S.atlasTimer);
    S.atlasTimer = setTimeout(searchAtlas, 220);
  });
  $('#atlasDims').addEventListener('click', e => {
    const b = e.target.closest('[data-atlas-dim]'); if (!b) return;
    S.atlasDimension = b.dataset.atlasDim;
    $$('#atlasDims .chip').forEach(x => x.classList.toggle('active', x === b));
    searchAtlas();
  });
  $('#causalRun').addEventListener('click', runCausal);
  $('#causalTopic').addEventListener('change', runCausal);
  $('#calibrationRun').addEventListener('click', runCalibration);
  $('#valEnsembleRun').addEventListener('click', runEnsemble);
  $('#valSensRun').addEventListener('click', runSensitivity);
  $('#reasonRun').addEventListener('click', () => runReasoning());
  $('#compareBtn')?.addEventListener('click', openCompare);
  $('#reasonBtn')?.addEventListener('click', runReasoningBtn);
  $('#compareClose')?.addEventListener('click', closeCompare);
  $('#opsPause')?.addEventListener('click', () => { S.opsPaused = !S.opsPaused; $('#opsPause').innerHTML = S.opsPaused ? `${ICONS.play}Resume` : `${ICONS.pause}Pause`; });
  $('#opsClear')?.addEventListener('click', () => { S.opsLog = []; renderOps(); });
  $('#paramApply')?.addEventListener('click', applyParams);

  document.addEventListener('click', e => {
    const el = e.target.closest('[data-agent-open]');
    if (el) { e.preventDefault(); openAgent(el.dataset.agentOpen); }
  });
  $('#drawerClose').addEventListener('click', closeDrawer);
  $('#drawerBackdrop').addEventListener('click', closeDrawer);
  $('#cmdInput')?.addEventListener('input', e => renderCmdList(e.target.value));
  $('#cmdInput')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const first = $('#cmdList .cmd-item'); if (first) execCmd(first.dataset.kind, first.dataset.cmd);
    }
    if (e.key === 'Escape') closeCmdPalette();
  });
  $('#cmdPalette')?.addEventListener('click', e => { if (e.target === $('#cmdPalette')) closeCmdPalette(); });

  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openCmdPalette(); return; }
    if (e.key === 'Escape') { closeCmdPalette(); }
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === ' ') { e.preventDefault(); togglePlay(); }
    if (e.key.toLowerCase() === 'r') runSimulation();
  });
  $('#helpClose').addEventListener('click', () => $('#helpModal').classList.remove('open'));
  $('#helpModal').addEventListener('click', e => { if (e.target === $('#helpModal')) $('#helpModal').classList.remove('open'); });
  $('#exportBtn').addEventListener('click', () => {
    if (!S.run) { toast('Run a simulation first.'); return; }
    const blob = new Blob([JSON.stringify(S.run, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `imprint-bharat-${S.run.topic.id}-${S.run.run_id}.json`; a.click(); URL.revokeObjectURL(a.href);
    toast('Run exported as JSON');
  });

  try {
    const [meta, map] = await Promise.all([
      fetch('/api/meta').then(r => r.json()),
      fetch('/static/data/india_map.json').then(r => r.json()).catch(() => null)
    ]);
    S.meta = meta; S.map = map;
    $('#topicSelect').innerHTML = meta.topics.map(t => `<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('');
    $('#topicSelect').value = 'ev-scooter';
    $('#topicCategory').textContent = 'Mobility';
    $('#topicChips').innerHTML = meta.topics.slice(0, 7).map(t => `<button class="chip" data-topic="${esc(t.id)}">${esc(t.label.replace('Premium ', '').replace(' for homes', ''))}</button>`).join('');
    $('#topicChips').addEventListener('click', e => {
      const b = e.target.closest('[data-topic]'); if (!b) return;
      $('#topicSelect').value = b.dataset.topic;
      $('#topicSelect').dispatchEvent(new Event('change'));
    });
    $$('.tier-mini input').forEach(el => el.addEventListener('input', updateTierTotal));
    $('#scenarioGrid').innerHTML = meta.scenarios.map(s => `<button class="scenario ${s.id === 'base' ? 'active' : ''}" data-id="${s.id}"><span class="scenario__icon">${s.icon}</span><span class="scenario__label">${esc(s.label)}</span></button>`).join('');
    $('#forecastTopic').innerHTML = meta.topics.map(t => `<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('');
    $('#stateSelect').innerHTML = `<option value="">All India</option>` + meta.states.map(s => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
    if (map) renderMap();
    renderEvidence();
    updateSysChips();
    renderParamLab();
    await runSimulation();
  } catch (err) {
    $('#statusText').textContent = 'Offline';
    toast('Could not reach the simulation API.');
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded', boot);
})();
