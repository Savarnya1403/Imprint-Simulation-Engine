/* Landing page: iconography + a live default rehearsal. */
const ICONS = {
  reddit: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="13" r="7.2"/><circle cx="9" cy="13" r=".9" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r=".9" fill="currentColor" stroke="none"/><path d="M9.2 16c.8.9 1.7 1.3 2.8 1.3s2-.4 2.8-1.3"/><circle cx="18.6" cy="7.2" r="1.5"/><path d="M12 5.9l.8-3 2.3.5"/></svg>`,
  youtube: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="6" width="18" height="12" rx="3.2"/><path d="M10.4 9.3l4.4 2.7-4.4 2.7z" fill="currentColor" stroke="none"/></svg>`,
  whatsapp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M20 11.6a8 8 0 0 1-11.8 7L4 20l1.4-4.1A8 8 0 1 1 20 11.6z"/><path d="M8.8 8.7c.2-.5.4-.5.7-.5h.4c.2 0 .4 0 .5.4l.6 1.4c.1.2 0 .4-.1.5l-.5.6c-.1.1-.2.3 0 .5.4.7 1.1 1.4 1.9 1.8.2.1.3.1.5-.1l.6-.7c.1-.1.3-.2.5-.1l1.3.6c.2.1.4.3.4.5 0 .6-.3 1.4-.7 1.7-.4.4-1.1.6-2.1.3-1-.3-2.5-1-3.7-2.2-1.2-1.2-2-2.5-2.2-3.4-.2-.8.1-1.5.5-1.9z" fill="currentColor" stroke="none" opacity=".9"/></svg>`,
  news: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4.5h12.5A1.5 1.5 0 0 1 19 6v13.5H6.5A1.5 1.5 0 0 1 5 18z"/><path d="M5 17.5H3.8A1.3 1.3 0 0 1 2.5 16V7.2h2.5"/><path d="M8 8h8M8 11h8M8 14h5"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>`,
  field: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M5 4.5h3l1.6 4-2 1.4a12 12 0 0 0 6.5 6.5l1.4-2 4 1.6v3a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 3 6.7 2 2 0 0 1 5 4.5z"/></svg>`,
  spark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/></svg>`,
  book: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21V5.5z"/><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20"/></svg>`,
  grid: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/></svg>`,
  compass: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M15.5 8.5l-2.1 4.9-4.9 2.1 2.1-4.9z"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.2 15.2L21 21"/></svg>`,
  bars: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 20h16"/><path d="M6.5 17V11M11 17V5M15.5 17v-4M20 17V8"/></svg>`,
  prism: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><path d="M12 3l7.5 16.5h-15z"/><path d="M12 3v16.5M4.5 19.5L12 12l7.5 7.5"/></svg>`,
  bolt: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><path d="M13 2.5L5 13.5h6L10 21.5l8-11h-6z"/></svg>`
};

document.querySelectorAll('[data-icon]').forEach(el => {
  const svg = ICONS[el.dataset.icon];
  if (svg) el.innerHTML = svg;
});

function setChart(values) {
  if (!values || values.length < 2) return;
  const w = 280, h = 56, pad = 4;
  const max = Math.max(...values), min = Math.min(...values);
  const span = (max - min) || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - pad - ((v - min) / span) * (h - pad * 2);
    return [x, y];
  });
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area = `${line} L${w} ${h} L0 ${h} Z`;
  const lineEl = document.querySelector('.spark__line');
  const areaEl = document.querySelector('.spark__area');
  const dot = document.querySelector('.spark__dot');
  if (lineEl) lineEl.setAttribute('d', line);
  if (areaEl) areaEl.setAttribute('d', area);
  if (dot) { dot.setAttribute('cx', w); dot.setAttribute('cy', pts.at(-1)[1]); }
}

fetch('/api/simulate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ brief: 'electric scooter for tier-2 India', n_agents: 220, rounds: 36, seed: 42 })
}).then(r => r.json()).then(d => {
  if (!d || !d.summary) return;
  const s = d.summary, topic = d.topic;
  const obj = (s.top_rejections && s.top_rejections[0] && s.top_rejections[0].reason) || 'the failure mode';
  const sentiment = s.sentiment > .15 ? 'warming' : s.sentiment < -.15 ? 'cooling' : 'split';
  const text = document.getElementById('insightText');
  if (text) text.innerHTML = `Consumer sentiment towards <strong>${topic.label.toLowerCase()}</strong> is ${sentiment} — but the purchase is blocked by one thing: <strong>${obj.toLowerCase()}.</strong>`;
  const badge = document.getElementById('insightBadge');
  if (badge) badge.textContent = `+${Math.round(s.conversion * 100)}%`;
  const foot = document.getElementById('insightFoot');
  if (foot) foot.textContent = `of the addressable pool adopted · ${Math.round(s.confidence * 100)}% model confidence`;
  const live = document.getElementById('insightLive');
  if (live) live.textContent = `${d.population} agents · ${d.rounds} rounds`;
  setChart(d.timeline.map(x => x.adoption));
}).catch(() => {});
