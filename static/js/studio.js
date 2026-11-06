/* Imprint Bharat — Palantir-style simulation console */
(() => {
'use strict';

/* ═══════ DOM helpers ═══════ */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (tag, cls, html = '') => { const e = document.createElement(tag); if (cls) e.className = cls; e.innerHTML = html; return e; };

/* ═══════ State ═══════ */
let running = false;
let lastResult = null;
let allAgents = [];

/* ═══════ Clock ═══════ */
function tickClock() {
  const c = $('#topbarClock');
  if (c) c.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

/* ═══════ Toast ═══════ */
function toast(msg, type = 'info') {
  const wrap = $('#toastWrap');
  if (!wrap) return;
  const t = el('div', `toast ${type}`, msg);
  wrap.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* ═══════ Status pill ═══════ */
function setStatus(mode, text) {
  const dot = $('#statusDot');
  const lbl = $('#statusText');
  if (dot) dot.className = 'status-dot ' + mode;
  if (lbl) lbl.textContent = text;
}

/* ═══════ Nav tabs ═══════ */
const VIEW_MAP = { reason: 'reasonView', emerge: 'emergeView', forecast: 'forecastView', atlas: 'atlasView' };

function showView(view) {
  Object.values(VIEW_MAP).forEach(id => {
    const v = $('#' + id);
    if (v) v.style.display = 'none';
  });
  if (VIEW_MAP[view]) {
    const v = $('#' + VIEW_MAP[view]);
    if (v) v.style.display = 'flex';
  }
}

$$('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.nav-tab').forEach(t => t.classList.toggle('active', t === tab));
    showView(tab.dataset.view);
  });
});

$$('.close-view-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    showView('sim');
    $$('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.view === 'sim'));
  });
});

/* ═══════ Sliders ═══════ */
$('#agentsRange')?.addEventListener('input', e => { const v = $('#agentsVal'); if (v) v.textContent = e.target.value; });
$('#roundsRange')?.addEventListener('input', e => { const v = $('#roundsVal'); if (v) v.textContent = e.target.value; });

/* ═══════ Scenario grid — populate ═══════ */
const SCENARIOS = [
  'Rural Bengal', 'Metro Delhi', 'Tier-2 Gujarat', 'Coastal Kerala',
  'UP Hinterland', 'Chennai Urban', 'Bangalore Tech', 'Rajasthan Semi-urban',
];
function populateScenarios() {
  const grid = $('#scenarioGrid');
  if (!grid) return;
  grid.innerHTML = '';
  SCENARIOS.forEach(s => {
    const chip = el('button', 'scenario-chip', s);
    chip.dataset.scenario = s;
    chip.addEventListener('click', () => {
      $$('.scenario-chip').forEach(c => c.classList.toggle('active', c === chip));
      const box = $('#briefInput');
      if (box && box.value === box.defaultValue) {
        const filter = $('#stateSelect');
        if (filter) {
          for (const opt of filter.options) {
            if (opt.text.includes(s.split(' ').pop())) { filter.value = opt.value; break; }
          }
        }
      }
    });
    grid.appendChild(chip);
  });
}

/* ═══════ Topic pack ═══════ */
const TOPIC_PACKS = {
  'Consumer Electronics': ['Smartphones', 'Earbuds', 'Smart TV', 'Laptop'],
  'FMCG / Beauty': ['Fairness cream', 'Protein powder', 'Premium shampoo', 'Deodorant'],
  'Mobility': ['EV scooter', 'Shared cab', 'Bicycle', 'Two-wheeler'],
  'Digital / Fintech': ['UPI adoption', 'Crypto', 'Digital loan', 'OTT'],
  'Policy / Social': ['CAA', 'Reservation policy', 'Article 370', 'Farm laws'],
};
function populateTopics() {
  const sel = $('#topicSelect');
  const tags = $('#topicTags');
  if (!sel || !tags) return;
  Object.keys(TOPIC_PACKS).forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat; opt.textContent = cat;
    sel.appendChild(opt);
  });
  function renderTags(cat) {
    tags.innerHTML = '';
    (TOPIC_PACKS[cat] || []).forEach(t => {
      const tag = el('span', 'topic-tag', t);
      tag.style.cursor = 'pointer';
      tag.addEventListener('click', () => {
        const box = $('#briefInput');
        if (box) box.value = `${t} — will it scale in India?`;
      });
      tags.appendChild(tag);
    });
  }
  renderTags(sel.value);
  sel.addEventListener('change', () => renderTags(sel.value));
}

/* ═══════ State select ═══════ */
const INDIA_STATES = [
  '', 'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa',
  'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Nagaland', 'Odisha',
  'Punjab', 'Rajasthan', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'Uttarakhand',
  'West Bengal',
];
function populateStateSelect() {
  const sel = $('#stateSelect');
  if (!sel) return;
  sel.innerHTML = '';
  INDIA_STATES.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s || 'All India';
    sel.appendChild(opt);
  });
}

/* ═══════ Export ═══════ */
$('#exportBtn')?.addEventListener('click', () => {
  if (!lastResult) { toast('No simulation result to export', 'error'); return; }
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `imprint_${Date.now()}.json`;
  a.click();
  toast('Exported', 'success');
});

/* ═══════ Main run ═══════ */
async function runSimulation() {
  if (running) return;
  const hypothesis = $('#briefInput')?.value?.trim();
  if (!hypothesis) { toast('Enter a hypothesis', 'error'); return; }

  running = true;
  setStatus('running', 'RUNNING');
  setBtnRunning(true);
  clearPanels();
  pushSignal('type-info', `▶ Simulation started`);

  const n      = parseInt($('#agentsRange')?.value || '240');
  const rounds = parseInt($('#roundsRange')?.value || '36');
  const state  = $('#stateSelect')?.value || '';

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hypothesis, n_agents: n, rounds, state: state || undefined }),
    });
    if (!res.ok) throw new Error(await res.text());
    lastResult = await res.json();
    renderResult(lastResult);
    setStatus('done', 'COMPLETE');
    toast('Simulation complete', 'success');
  } catch (e) {
    setStatus('error', 'ERROR');
    toast('Error: ' + e.message, 'error');
    pushSignal('type-tipping', '✗ ' + e.message);
  } finally {
    running = false;
    setBtnRunning(false);
  }
}

/* ═══════ Universal query ═══════ */
async function runUniversalQuery() {
  const q = $('#queryInput')?.value?.trim();
  if (!q) return;
  const deepReason   = $('#optDeepReason')?.checked || false;
  const allScenarios = $('#optAllScenarios')?.checked || false;
  closeModal();

  if (running) return;
  running = true;
  setStatus('running', 'INTERPRETING');
  setBtnRunning(true);
  clearPanels();
  pushSignal('type-info', `▶ Query: ${q}`);

  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, seed: 42, deep_reason: deepReason, all_scenarios: allScenarios }),
    });
    if (!res.ok) throw new Error(await res.text());
    lastResult = await res.json();
    if (lastResult.spec?.brief) {
      const box = $('#briefInput');
      if (box) box.value = lastResult.spec.brief;
    }
    renderResult(lastResult);
    setStatus('done', 'COMPLETE');
    toast('Query simulation complete', 'success');
  } catch (e) {
    setStatus('error', 'ERROR');
    toast('Error: ' + e.message, 'error');
    pushSignal('type-tipping', '✗ ' + e.message);
  } finally {
    running = false;
    setBtnRunning(false);
  }
}

function setBtnRunning(isRunning) {
  const btn = $('#runBtn');
  if (!btn) return;
  if (isRunning) {
    btn.classList.add('running');
    btn.innerHTML = '<span>⏳</span> SIMULATING…';
  } else {
    btn.classList.remove('running');
    btn.innerHTML = '<svg viewBox="0 0 16 16" fill="currentColor" class="btn-icon"><path d="M3 2l10 6-10 6V2z"/></svg> RUN SIMULATION';
  }
}

/* ═══════ Normalize API response shapes ═══════ */
function normalize(data) {
  // Handle both /api/simulate (nested summary/report) and /api/query (flat) responses
  const s = data.summary || {};
  const r = data.report  || {};

  return {
    _raw: data,
    verdict:           s.verdict   || r.verdict   || data.verdict   || 'HOLD',
    adoption_pct:      (s.adoption  != null ? s.adoption * 100  : (data.adoption_rate_pct  ?? null)),
    rejection_pct:     (s.rejected  != null ? (s.rejected / (data.params?.n || data.population?.length || 100)) * 100 : (data.rejection_rate_pct ?? null)),
    confidence:        s.confidence ?? data.confidence,
    tipping_point:     s.tipping_point ?? data.tipping_round,
    headline:          s.headline  || r.headline   || data.memo     || data.summary,
    tier_mix:          data.tier_mix || data.tier_distribution,
    n_agents:          data.population?.length || data.n_agents,
    agents:            data.agents  || [],
    encounters:        data.encounters || [],
    objections:        r.objections || data.objections || [],
    binding_constraints: data.binding_constraints || [],
    round_data:        data.round_data || null,
    rounds:            typeof data.rounds === 'number' ? data.rounds : null,
    awi:               data.awi,
    emergence_events:  data.emergence_events || [],
    claude_analysis:   data.claude_analysis,
    run_id:            data.run_id  || data.sim_id,
    domain:            data.domain  || 'market',
    spec:              data.spec,
  };
}

/* ═══════ Render result ═══════ */
function renderResult(raw) {
  if (!raw) return;
  const data = normalize(raw);

  renderVerdict(data);
  renderKVMetrics(data);
  renderPopulation(data);
  if (data.awi) renderAWI(data.awi);
  renderBindingConstraints(data);
  if (data.encounters.length) renderEncounters(data.encounters);
  renderObjections(data);
  renderChart(data);
  if (data.agents.length) {
    allAgents = data.agents;
    renderAgentsTable(allAgents);
  }
  renderSignals(data);
  if (data.emergence_events.length) {
    renderEmergenceEvents(data.emergence_events);
    const eSidebar = $('#emergenceSidebar');
    if (eSidebar) eSidebar.style.display = '';
  }
  if (data.claude_analysis) populateReasoningView(raw);
  updateSimId(data);
}

function updateSimId(data) {
  const eId = $('#simId');
  if (eId && data.run_id) eId.textContent = String(data.run_id).slice(0, 8).toUpperCase();
  const dtag = $('#domainTag');
  if (dtag) dtag.textContent = `INDIA · ${(data.domain || 'market').toUpperCase()}`;
}

/* ─── Verdict ─── */
function renderVerdict(data) {
  const badge = $('#verdictBadge');
  const conf  = $('#verdictConf');
  const memo  = $('#verdictMemo');

  if (badge) { badge.textContent = data.verdict; badge.dataset.verdict = data.verdict; }
  const confVal = data.confidence != null ? (data.confidence > 1 ? data.confidence.toFixed(1) : (data.confidence * 100).toFixed(0)) : '—';
  if (conf) conf.textContent = `confidence: ${confVal}%`;
  if (memo) memo.textContent = data.headline || 'See encounter feed for detail.';
}

/* ─── KV metrics ─── */
function renderKVMetrics(data) {
  const block = $('#keyMetricsBlock');
  const grid  = $('#kvGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (block) block.style.display = '';

  const kv = [
    { label: 'ADOPTION',   val: data.adoption_pct  != null ? data.adoption_pct.toFixed(1)  + '%' : '—', cls: 'pos' },
    { label: 'REJECTION',  val: data.rejection_pct != null ? data.rejection_pct.toFixed(1) + '%' : '—', cls: 'neg' },
    { label: 'TIPPING',    val: data.tipping_point  != null ? `Rd ${data.tipping_point}` : '—', cls: 'neu' },
    { label: 'ENCOUNTERS', val: data.encounters.length || '—', cls: '' },
  ];
  kv.forEach(({ label, val, cls }) => {
    const item = el('div', 'kv-item');
    item.innerHTML = `<span class="kv-label">${label}</span><span class="kv-value ${cls}">${val}</span>`;
    grid.appendChild(item);
  });
}
function fmt(v, unit = '') { return v != null ? (typeof v === 'number' ? v.toFixed(1) : v) + unit : '—'; }

/* ─── Population ─── */
function renderPopulation(data) {
  const grid = $('#popGrid');
  if (!grid) return;
  const tiers = data.tier_mix;
  if (!tiers) return;
  grid.innerHTML = '';

  const TIER_LABELS = { '1': 'Metro Elite', '2': 'Urban Middle', '3': 'Semi-urban', '4': 'Rural / BOP' };
  const TIER_CLS    = { '1': 'tier1', '2': 'tier2', '3': 'tier3', '4': 'tier4' };
  Object.entries(tiers).forEach(([tier, pct]) => {
    const seg = el('div', `pop-segment pop-segment-${TIER_CLS[tier] || 'tier1'}`);
    seg.innerHTML = `
      <div class="pop-segment-label"><span>${TIER_LABELS[tier] || `Tier ${tier}`}</span><span class="pct">${(pct * 100).toFixed(1)}%</span></div>
      <div class="pop-bar-bg"><div class="pop-bar-fill" style="width:${pct * 100}%"></div></div>
      <div class="pop-segment-sub">Tier ${tier}</div>`;
    grid.appendChild(seg);
  });

  const sub = $('#popSubtitle');
  if (sub && data.n_agents) sub.textContent = `${data.n_agents} agents`;
}

/* ─── AWI ─── */
const AWI_DIMS = [
  ['population_health', 'Pop Health'], ['safety', 'Safety'], ['exploration', 'Exploration'],
  ['governance_conformity', 'Governance'], ['expression', 'Expression'],
  ['social_fabric', 'Social Fabric'], ['economic_vitality', 'Economic'],
  ['constitutional_growth', 'Const. Growth'], ['emergence_index', 'Emergence'],
];
const AWI_COLS = ['#22c55e','#00b4d8','#a855f7','#f59e0b','#f97316','#ec4899','#06b6d4','#84cc16','#8b5cf6'];

function renderAWI(awi) {
  const scoreEl = $('#awiScore');
  const labelEl = $('#awiLabel');
  if (scoreEl) scoreEl.textContent = typeof awi.composite === 'number' ? awi.composite.toFixed(2) : '—';
  if (labelEl) labelEl.textContent = awi.status_label || '';

  const bars = $('#awiBars');
  if (!bars) return;
  bars.innerHTML = '';
  AWI_DIMS.forEach(([key, label], i) => {
    const val = awi[key] ?? 0;
    const pct = Math.min(100, Math.max(0, val * 100));
    const row = el('div', 'awi-row');
    row.innerHTML = `
      <span class="awi-row-label">${label}</span>
      <div class="awi-row-bar"><div class="awi-row-fill" style="width:${pct}%;background:${AWI_COLS[i]}"></div></div>
      <span class="awi-row-val">${pct.toFixed(0)}</span>`;
    bars.appendChild(row);
  });
}

/* ─── Binding constraints ─── */
function renderBindingConstraints(data) {
  const bars = $('#bindingBars');
  if (!bars) return;
  bars.innerHTML = '';
  const constraints = data.binding_constraints || [];
  if (!constraints.length) {
    bars.innerHTML = '<div class="panel-idle">No binding constraints detected</div>';
    return;
  }
  constraints.slice(0, 5).forEach(c => {
    const label = typeof c === 'string' ? c : (c.label || c.constraint || JSON.stringify(c));
    const share = typeof c === 'object' ? (c.share || c.weight || 0.2) : 0.2;
    const falsifier = typeof c === 'object' ? c.falsifier : '';
    const row = el('div', 'binding-row');
    row.innerHTML = `
      <div class="binding-row-head">
        <span class="binding-row-label">${label}</span>
        <span class="binding-row-share">${(share * 100).toFixed(0)}%</span>
      </div>
      <div class="binding-bar-bg"><div class="binding-bar-fill" style="width:${share * 100}%"></div></div>
      ${falsifier ? `<div class="binding-falsifier">↳ ${falsifier}</div>` : ''}`;
    bars.appendChild(row);
  });
}

/* ─── Encounters ─── */
function renderEncounters(encounters) {
  const list    = $('#encountersList');
  const countEl = $('#encCount');
  if (!list) return;
  list.innerHTML = '';
  if (countEl) countEl.textContent = encounters.length + ' encounters';

  encounters.slice(0, 20).forEach(enc => {
    // normalize: /api/simulate uses {a, b, day} while /api/query might use {agent_a, agent_b, round}
    const aName = enc.a || enc.agent_a || 'A';
    const bName = enc.b || enc.agent_b || 'B';
    const round = enc.round || enc.day || '?';
    const cls   = enc.outcome === 'convinced' ? 'convinced' : enc.outcome === 'sceptical' ? 'sceptical' : 'indifferent';
    const card  = el('div', 'encounter-card');
    card.innerHTML = `
      <div class="enc-meta">
        <span>${aName}</span><span>→</span><span>${bName}</span>
        <span>Day ${round}</span>
        <span class="enc-outcome ${cls}">${enc.outcome || '?'}</span>
      </div>
      ${enc.dialogue ? `<div class="enc-dialogue">${enc.dialogue}</div>` : ''}
      ${enc.reason   ? `<div class="enc-reason">${enc.reason}</div>` : ''}`;
    list.appendChild(card);
    pushSignal('type-encounter', `${aName} → ${bName}: ${enc.outcome}`);
  });
}

/* ─── Objections ─── */
function renderObjections(data) {
  const list = $('#objectionsList');
  if (!list) return;
  list.innerHTML = '';
  const objs = data.objections || data.binding_constraints || [];
  if (!objs.length) {
    list.innerHTML = '<div class="panel-idle">No rejection patterns</div>';
    return;
  }
  objs.slice(0, 8).forEach(obj => {
    const label = typeof obj === 'string' ? obj : (obj.label || obj.constraint || '');
    const share = typeof obj === 'object' ? (obj.share || obj.weight || 0.2) : 0.2;
    const row = el('div', 'obj-row');
    row.innerHTML = `
      <div class="obj-head"><span class="obj-reason">${label}</span><span class="obj-share">${(share * 100).toFixed(0)}%</span></div>
      <div class="obj-bar-bg"><div class="obj-bar-fill" style="width:${share * 100}%"></div></div>`;
    list.appendChild(row);
  });
}

/* ─── Chart ─── */
let chartInst = null;
function renderChart(data) {
  const canvas = $('#mainChart');
  if (!canvas || typeof Chart === 'undefined') return;
  const idleOverlay = $('#chartIdleOverlay');
  if (idleOverlay) idleOverlay.style.display = 'none';

  const rounds = data.round_data || buildFallbackRounds(data);
  if (!rounds.length) return;

  if (chartInst) { chartInst.destroy(); chartInst = null; }

  const labels = rounds.map((_, i) => `R${i + 1}`);
  const adoptS = rounds.map(r => r.adoption ?? r.adopted_pct ?? 0);
  const rejS   = rounds.map(r => r.rejection ?? r.rejected_pct ?? null);

  const datasets = [
    { label: 'Adoption', data: adoptS, borderColor: '#00b4d8', backgroundColor: 'rgba(0,180,216,.08)', tension: 0.4, fill: true, pointRadius: 2 },
  ];
  if (rejS.some(v => v != null)) {
    datasets.push({ label: 'Rejection', data: rejS, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,.06)', tension: 0.4, fill: true, pointRadius: 1, borderDash: [3, 2] });
  }

  chartInst = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: { legend: { labels: { color: '#8891a8', font: { family: "'JetBrains Mono'" }, boxWidth: 10 } } },
      scales: {
        x: { ticks: { color: '#515b72', font: { family: "'JetBrains Mono'", size: 9 } }, grid: { color: '#1b2030' } },
        y: { min: 0, max: 1, ticks: { color: '#515b72', font: { family: "'JetBrains Mono'", size: 9 }, callback: v => (v * 100).toFixed(0) + '%' }, grid: { color: '#1b2030' } },
      },
    },
  });

  const footer = $('#chartFooter');
  if (footer) {
    const a = data.adoption_pct != null ? data.adoption_pct.toFixed(1) + '%' : '—';
    footer.textContent = `Final adoption: ${a}  |  ${rounds.length} rounds  |  ${data.n_agents ?? '?'} agents`;
  }
}

function buildFallbackRounds(data) {
  const n = data.rounds || 10;
  const finalAdopt  = (data.adoption_pct  || 0) / 100;
  const finalReject = (data.rejection_pct || 0) / 100;
  return Array.from({ length: n }, (_, i) => {
    const t = (i + 1) / n;
    return {
      adoption:  finalAdopt  * Math.pow(t, 0.55),
      rejection: finalReject * Math.pow(t, 0.7),
    };
  });
}

/* ─── Agents table ─── */
function renderAgentsTable(agents) {
  const tbody = $('#agentsTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  agents.slice(0, 100).forEach(agent => {
    const stance    = ((agent.stance || 0) + 1) / 2;
    const stanceW   = Math.max(2, Math.min(100, stance * 100));
    const stanceCol = agent.stance > 0.3 ? '#22c55e' : agent.stance < -0.3 ? '#ef4444' : '#f59e0b';
    const statusCls = agent.adopted ? 'adopted' : agent.rejected ? 'rejected' : 'pending';
    const statusLbl = agent.adopted ? 'ADOPTED' : agent.rejected ? 'REJECTED' : 'PENDING';
    const tr = el('tr', '');
    tr.innerHTML = `
      <td>${agent.name || agent.id}</td>
      <td>${agent.tier || '—'}</td>
      <td>${agent.occupation || '—'}</td>
      <td><div class="stance-bar"><div class="stance-fill" style="width:${stanceW}%;background:${stanceCol}"></div></div></td>
      <td><span class="status-pill-sm ${statusCls}">${statusLbl}</span></td>`;
    tr.addEventListener('click', () => openAgentDrawer(agent));
    tbody.appendChild(tr);
  });
}

$('#agentSearch')?.addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  $$('#agentsTbody tr').forEach(tr => { tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none'; });
});

/* ─── Signal feed ─── */
function pushSignal(type, msg) {
  const list = $('#signalList');
  if (!list) return;
  const idle = list.querySelector('.signal-idle');
  if (idle) idle.remove();
  const item = el('div', `signal-item ${type}`, msg);
  list.prepend(item);
  if (list.children.length > 100) list.lastChild?.remove();
}

function renderSignals(data) {
  if (data.adoption_pct  != null) pushSignal('type-adopt',   `✓ Adoption: ${data.adoption_pct.toFixed(1)}%`);
  if (data.rejection_pct != null) pushSignal('type-reject',  `✗ Rejection: ${data.rejection_pct.toFixed(1)}%`);
  if (data.tipping_point != null) pushSignal('type-tipping', `⚡ Tipping: day ${data.tipping_point}`);
  if (data.awi?.emergence_index > 0.5) pushSignal('type-tipping', `🌊 Emergence: ${(data.awi.emergence_index * 100).toFixed(0)}`);
  if (data.verdict) pushSignal('type-info', `◎ Verdict: ${data.verdict}`);
}

/* ─── Emergence events ─── */
function renderEmergenceEvents(events) {
  const list   = $('#emergenceList');
  const countE = $('#emergeCount');
  if (!list) return;
  list.innerHTML = '';
  if (countE) countE.textContent = events.length;
  events.forEach(evt => {
    const e = el('div', `emergence-event ${evt.type || 'tipping_point'}`);
    e.innerHTML = `
      <div class="emergence-event-type">${(evt.type || 'EVENT').replace(/_/g,' ').toUpperCase()}</div>
      <div class="emergence-event-desc">${evt.description || evt.detail || JSON.stringify(evt)}</div>`;
    list.appendChild(e);
    pushSignal('type-tipping', `⚡ ${evt.type}: ${evt.description || ''}`);
  });
}

/* ═══════ Agent Drawer ═══════ */
function openAgentDrawer(agent) {
  const drawer = $('#agentDrawer');
  const title  = $('#drawerTitle');
  const body   = $('#agentDrawerBody');
  if (!drawer) return;

  if (title) title.textContent = agent.name || agent.id;
  if (body) {
    const bio = [agent.occupation, agent.state || agent.region, agent.tier ? `Tier ${agent.tier}` : null, agent.community, agent.religion].filter(Boolean).join(' · ');
    const traits = Object.entries(agent.traits || {}).slice(0, 8).map(([k, v]) => {
      const pct = Math.max(0, Math.min(100, (v + 1) * 50));
      return `<div class="drawer-trait"><span class="drawer-trait-label">${k}</span><div class="drawer-trait-bar-bg"><div class="drawer-trait-bar" style="width:${pct}%"></div></div></div>`;
    }).join('');
    const memories = (agent.memories || agent.memory_stream || []).slice(0, 10).map(m =>
      `<div class="memory-item ${m.type === 'reflection' ? 'reflection' : ''}">${typeof m === 'string' ? m : (m.description || m.content || '')}</div>`
    ).join('');
    body.innerHTML = `
      <div class="drawer-agent-name">${agent.name || agent.id}</div>
      <div class="drawer-agent-bio">${bio}</div>
      ${traits ? `<div class="drawer-section-label">TRAITS</div><div class="drawer-traits">${traits}</div>` : ''}
      ${memories ? `<div class="drawer-section-label">MEMORY</div><div class="drawer-memories">${memories}</div>` : ''}`;
  }
  drawer.classList.add('open');
}

function closeDrawer() { $('#agentDrawer')?.classList.remove('open'); }

/* ═══════ Query Modal ═══════ */
function openModal() {
  const m = $('#queryModal');
  if (m) m.classList.add('open');
  setTimeout(() => $('#queryInput')?.focus(), 50);
}
function closeModal() { $('#queryModal')?.classList.remove('open'); }

$('#cmdBtn')?.addEventListener('click', openModal);
$('#universalQueryBtn')?.addEventListener('click', openModal);

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openModal(); }
  if (e.key === 'Escape') closeModal();
});

$('#queryInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') runUniversalQuery();
});

function setQueryExample(btn) {
  const input = $('#queryInput');
  if (input) input.value = btn.textContent.trim();
}

/* ═══════ Reasoning view ═══════ */
function populateReasoningView(data) {
  const analysis = data.claude_analysis || data.deliberation;
  if (!analysis) return;
  const panels = $('#reasoningPanels');
  if (!panels) return;
  panels.innerHTML = '';

  const steps = [
    { name: 'Top Explanation',  val: analysis.top_explanation,                    cls: 'done' },
    { name: 'Critique',         val: analysis.critique,                            cls: 'weak' },
    { name: 'Blind Spots',      val: (analysis.blind_spots || []).join(' · '),     cls: 'weak' },
    { name: 'Priority Test',    val: analysis.priority_test,                       cls: 'done' },
    { name: 'Confidence',       val: `${analysis.confidence_pct ?? '?'}% — ${analysis.confidence_reasoning || ''}`, cls: 'done' },
  ].filter(s => s.val);

  const traceBlock = el('div', 'reason-block');
  traceBlock.style.padding = '12px';
  traceBlock.style.display = 'flex';
  traceBlock.style.flexDirection = 'column';
  traceBlock.style.gap = '8px';

  const hdr = el('div', 'rail-label', 'CLAUDE OPUS ANALYSIS');
  traceBlock.appendChild(hdr);

  steps.forEach((s, i) => {
    const step = el('div', `trace-step ${s.cls}`);
    step.innerHTML = `
      <span class="trace-step-num">${String(i + 1).padStart(2, '0')}</span>
      <div><div class="trace-step-name">${s.name}</div><div class="trace-step-detail">${s.val}</div></div>`;
    traceBlock.appendChild(step);
  });
  panels.appendChild(traceBlock);
}

/* ═══════ Clear panels ═══════ */
function clearPanels() {
  const signalList = $('#signalList');
  if (signalList) signalList.innerHTML = '<div class="signal-idle">Running simulation…</div>';
  const encList = $('#encountersList');
  if (encList) encList.innerHTML = '<div class="panel-idle">Simulating…</div>';
  const tbody = $('#agentsTbody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="agents-idle">Simulating…</td></tr>`;
  if (chartInst) { chartInst.destroy(); chartInst = null; }
  const idleOverlay = $('#chartIdleOverlay');
  if (idleOverlay) idleOverlay.style.display = '';
}

/* ═══════ Health check ═══════ */
async function healthCheck() {
  try {
    const res = await fetch('/api/health');
    const d   = await res.json();
    const topicTag = $('#topicTag');
    if (topicTag && d.llm_backend) topicTag.textContent = d.llm_backend.toUpperCase();
    const domainTag = $('#domainTag');
    if (domainTag && d.capabilities?.universal_query) domainTag.textContent = 'INDIA · UNIVERSAL';
    setStatus('done', 'READY');
  } catch {
    setStatus('error', 'OFFLINE');
  }
}

/* ═══════ Run button ═══════ */
$('#runBtn')?.addEventListener('click', runSimulation);

/* ═══════ INIT ═══════ */
function init() {
  populateScenarios();
  populateTopics();
  populateStateSelect();
  healthCheck();
  $('#briefInput')?.focus();
}
init();

/* ═══════ Global exposure for inline HTML onclick ═══════ */
window.closeModal = closeModal;
window.openModal  = openModal;
window.runUniversalQuery = runUniversalQuery;
window.setQueryExample   = setQueryExample;
window.closeDrawer       = closeDrawer;
window._imprint = { renderResult, pushSignal, renderEmergenceEvents };

})();
