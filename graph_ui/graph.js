/* YemekTest — Token Flow Graph
 * Obsidian-style force-directed graph of agent pipeline token usage.
 * Data source: GET /api/graph  →  { nodes: [...], edges: [...] }
 */

const STAGE_COLORS = {
  PLAN:    '#4a9eff',
  EXECUTE: '#43e97b',
  REVIEW:  '#ff9f43',
  FIX:     '#ff6b6b',
  ANALYZE: '#a29bfe',
};

const DEFAULT_COLOR = '#58a6ff';

// ── State ──────────────────────────────────────────────────────────────────
let rawData    = { nodes: [], edges: [] };
let activeStages = new Set(['PLAN', 'EXECUTE', 'REVIEW', 'FIX', 'ANALYZE']);
let nodeScale  = 1.0;
let linkScale  = 1.0;
let textFade   = 60;
let autoRefresh = true;
let refreshTimer = null;
let graphInstance = null;
let animating  = false;

// ── Graph init ─────────────────────────────────────────────────────────────
const container = document.getElementById('graph-container');

function buildGraph() {
  if (graphInstance) graphInstance._destructor && graphInstance._destructor();

  graphInstance = ForceGraph()(container)
    .backgroundColor('#0d1117')
    .nodeId('id')
    .nodeLabel(() => '')                      // tooltip handled manually
    .nodeColor(n => STAGE_COLORS[n.label] ?? DEFAULT_COLOR)
    .nodeVal(n => Math.max(4, Math.sqrt(n.total_tok || 0) / 15) * nodeScale)
    .nodeCanvasObject((node, ctx, globalScale) => {
      const r   = Math.max(4, Math.sqrt(node.total_tok || 0) / 15) * nodeScale;
      const col = STAGE_COLORS[node.label] ?? DEFAULT_COLOR;

      // glow
      const grd = ctx.createRadialGradient(node.x, node.y, r * 0.3, node.x, node.y, r * 2);
      grd.addColorStop(0, col + '55');
      grd.addColorStop(1, 'transparent');
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r * 2, 0, 2 * Math.PI);
      ctx.fill();

      // core
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fill();

      // label (fade with zoom)
      if (globalScale >= textFade / 100) {
        const fontSize = Math.max(8, 12 / globalScale);
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#e6edf3';
        ctx.fillText(node.label, node.x, node.y + r + fontSize);
      }
    })
    .nodeCanvasObjectMode(() => 'replace')
    .linkColor(() => '#30363d')
    .linkWidth(l => Math.max(0.5, (l.weight || 1) * 0.5 * linkScale))
    .linkDirectionalArrowLength(6)
    .linkDirectionalArrowRelPos(1)
    .linkDirectionalArrowColor(() => '#58a6ff')
    .linkDirectionalParticles(l => l.weight > 1 ? 2 : 0)
    .linkDirectionalParticleSpeed(0.004)
    .linkDirectionalParticleColor(() => '#58a6ff')
    .onNodeHover(showTooltip)
    .onNodeClick(node => {
      graphInstance.centerAt(node.x, node.y, 600);
      graphInstance.zoom(3, 600);
    })
    .d3Force('charge', d3 ? null : undefined); // will be configured below

  applyForces();
  loadData();
}

// ── Data fetch ─────────────────────────────────────────────────────────────
async function loadData() {
  const badge = document.getElementById('refresh-badge');
  try {
    const res = await fetch('/api/graph');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    rawData = await res.json();
    badge.textContent = `Refreshed ${new Date().toLocaleTimeString()}`;
    badge.className = 'live';
    renderGraph();
    updateStats();
    toggleEmptyState(rawData.nodes.length === 0);
  } catch (e) {
    badge.textContent = 'Connection error';
    badge.className = '';
  }
}

function renderGraph() {
  const nodes = rawData.nodes.filter(n => activeStages.has(n.label));
  const nodeIds = new Set(nodes.map(n => n.id));
  const links = (rawData.edges || [])
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map(e => ({ ...e }));

  graphInstance.graphData({ nodes: nodes.map(n => ({ ...n })), links });
}

// ── Forces ─────────────────────────────────────────────────────────────────
function applyForces() {
  if (!graphInstance) return;
  const center = parseFloat(document.getElementById('ctrl-center').value);
  const repel  = parseFloat(document.getElementById('ctrl-repel').value);
  const link   = parseFloat(document.getElementById('ctrl-link').value);

  graphInstance
    .d3Force('center', null)
    .d3Force('x', null)
    .d3Force('y', null);

  // Use built-in d3 force accessors
  try {
    const fg = graphInstance;
    fg.d3Force('charge').strength(repel);
    fg.d3Force('link').strength(link);
    // Center force via virtual node
    fg.d3Force('center', window.d3
      ? window.d3.forceCenter().strength(center)
      : null
    );
    fg.d3ReheatSimulation();
  } catch (_) {}
}

// ── Stats ──────────────────────────────────────────────────────────────────
function updateStats() {
  const nodes = rawData.nodes || [];
  const edges = rawData.edges || [];
  const totalTok  = nodes.reduce((s, n) => s + (n.total_tok || 0), 0);
  const totalCost = nodes.reduce((s, n) => s + (n.total_cost || 0), 0);

  document.getElementById('stat-nodes').textContent = nodes.length;
  document.getElementById('stat-edges').textContent = edges.length;
  document.getElementById('stat-tokens').textContent = totalTok.toLocaleString();
  document.getElementById('stat-cost').textContent = `$${totalCost.toFixed(4)}`;
}

// ── Tooltip ────────────────────────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');

function showTooltip(node) {
  if (!node) {
    tooltip.classList.remove('visible');
    return;
  }
  document.getElementById('tt-title').textContent = node.label;
  document.getElementById('tt-model').textContent = node.model || '';
  document.getElementById('tt-tokens').textContent = (node.total_tok || 0).toLocaleString();
  document.getElementById('tt-cost').textContent = `$${(node.total_cost || 0).toFixed(6)}`;
  document.getElementById('tt-calls').textContent = node.call_count || 0;
  tooltip.classList.add('visible');
}

container.addEventListener('mousemove', e => {
  tooltip.style.left = (e.clientX + 16) + 'px';
  tooltip.style.top  = (e.clientY - 10) + 'px';
});

container.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));

// ── Empty state ────────────────────────────────────────────────────────────
function toggleEmptyState(show) {
  document.getElementById('empty-state').style.display = show ? 'flex' : 'none';
}

// ── Controls wiring ────────────────────────────────────────────────────────
function wire(id, valId, onchange) {
  const el  = document.getElementById(id);
  const val = document.getElementById(valId);
  el.addEventListener('input', () => { val.textContent = el.value; onchange(parseFloat(el.value)); });
}

wire('ctrl-node-size',  'val-node-size',  v => { nodeScale = v; renderGraph(); });
wire('ctrl-link-thick', 'val-link-thick', v => { linkScale = v; renderGraph(); });
wire('ctrl-text-fade',  'val-text-fade',  v => { textFade  = v; });
wire('ctrl-center',     'val-center',     () => applyForces());
wire('ctrl-repel',      'val-repel',      () => applyForces());
wire('ctrl-link',       'val-link',       () => applyForces());

// Stage filters
document.querySelectorAll('[data-stage]').forEach(cb => {
  cb.addEventListener('change', () => {
    if (cb.checked) activeStages.add(cb.dataset.stage);
    else            activeStages.delete(cb.dataset.stage);
    renderGraph();
  });
});

// Animate button
document.getElementById('btn-animate').addEventListener('click', function () {
  animating = !animating;
  this.textContent = animating ? 'Stop' : 'Animate';
  this.classList.toggle('active', animating);
  if (animating && graphInstance) graphInstance.d3ReheatSimulation();
});

// Auto-refresh button
document.getElementById('btn-refresh').addEventListener('click', function () {
  autoRefresh = !autoRefresh;
  this.textContent = `Auto-refresh: ${autoRefresh ? 'ON' : 'OFF'}`;
  this.classList.toggle('active', autoRefresh);
  if (autoRefresh) scheduleRefresh();
  else clearTimeout(refreshTimer);
});

function scheduleRefresh() {
  clearTimeout(refreshTimer);
  if (autoRefresh) refreshTimer = setTimeout(async () => {
    await loadData();
    scheduleRefresh();
  }, 10_000);
}

// ── Boot ───────────────────────────────────────────────────────────────────
buildGraph();
scheduleRefresh();
