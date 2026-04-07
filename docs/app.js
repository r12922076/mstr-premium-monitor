let premiumChart = null;
let cachedPayload = null;
let activeRange = '30D';

async function loadData() {
  const response = await fetch('./data/indicator.json', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load indicator data: ${response.status}`);
  }
  return response.json();
}

function formatPercent(value) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatMultiple(value) {
  return `${value.toFixed(2)}x`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatTimestamp(value) {
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  });
}

function getLatestRow(series) {
  return series[series.length - 1];
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setClassName(id, className) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('positive', 'negative', 'neutral');
  if (className) el.classList.add(className);
}

function renderCards(meta, series) {
  const latest = getLatestRow(series);
  const premiumClass = latest.premium_to_nav > 0 ? 'positive' : latest.premium_to_nav < 0 ? 'negative' : 'neutral';

  setText('premiumValue', formatPercent(latest.premium_to_nav));
  setText('premiumSubtext', `${latest.date} · ${latest.premium_to_nav > 0 ? 'Premium' : latest.premium_to_nav < 0 ? 'Discount' : 'At parity'}`);
  setClassName('premiumValue', premiumClass);

  setText('mnavValue', formatMultiple(latest.mnav));
  setText('btcValue', formatCurrency(latest.btc_close));
  setText('mstrValue', formatCurrency(latest.mstr_close));
  setText('updatedValue', formatTimestamp(meta.last_updated));

  const notes = [meta.notes, meta.source_note].filter(Boolean).join(' ');
  setText('metaNotes', notes);
}

function getFilteredSeries(series, range) {
  if (range === 'ALL') return series;

  const daysMap = { '30D': 30, '90D': 90, '1Y': 365 };
  const horizon = daysMap[range];
  if (!horizon) return series;

  const latestDate = new Date(series[series.length - 1].date);
  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - (horizon - 1));

  return series.filter((row) => new Date(row.date) >= cutoff);
}

function renderInsight(latest) {
  const insightEl = document.getElementById('insightText');
  let text = '';
  if (latest.premium_to_nav > 0.5) {
    text = 'MSTR is trading at a substantial premium to the Bitcoin-backed NAV proxy. This often suggests that investors are valuing more than just spot BTC exposure.';
  } else if (latest.premium_to_nav > 0) {
    text = 'MSTR is trading at a moderate premium to the Bitcoin-backed NAV proxy, indicating positive market valuation beyond simple spot BTC backing.';
  } else if (latest.premium_to_nav < 0) {
    text = 'MSTR is trading at a discount to the Bitcoin-backed NAV proxy. The market price is below the simple BTC-backed estimate implied by this model.';
  } else {
    text = 'MSTR is trading close to the Bitcoin-backed NAV proxy under this simplified methodology.';
  }
  insightEl.textContent = text;
}

function buildChartConfig(filtered) {
  return {
    type: 'line',
    data: {
      labels: filtered.map((row) => row.date),
      datasets: [
        {
          label: 'Premium to NAV',
          data: filtered.map((row) => row.premium_to_nav),
          borderColor: '#74b9ff',
          backgroundColor: 'rgba(116, 185, 255, 0.18)',
          tension: 0.2,
          pointRadius: 0,
          fill: true,
          borderWidth: 2,
        },
        {
          label: 'Parity Line',
          data: filtered.map(() => 0),
          borderColor: 'rgba(255,255,255,0.35)',
          borderDash: [6, 6],
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: '#eef2ff' },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${(ctx.raw * 100).toFixed(2)}%`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#aab4d1', maxTicksLimit: 8 },
          grid: { color: 'rgba(255,255,255,0.06)' },
        },
        y: {
          ticks: {
            color: '#aab4d1',
            callback: (value) => `${(value * 100).toFixed(0)}%`,
          },
          grid: { color: 'rgba(255,255,255,0.06)' },
        },
      },
    },
  };
}

function renderChart(series, range) {
  const filtered = getFilteredSeries(series, range);
  const ctx = document.getElementById('premiumChart');
  if (!ctx) return;

  if (premiumChart) premiumChart.destroy();
  premiumChart = new Chart(ctx, buildChartConfig(filtered));
}

function updateActiveButtons(range) {
  document.querySelectorAll('.range-button').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.range === range);
  });
}

function bindButtons() {
  document.querySelectorAll('.range-button').forEach((btn) => {
    btn.addEventListener('click', () => {
      activeRange = btn.dataset.range;
      updateActiveButtons(activeRange);
      renderChart(cachedPayload.series, activeRange);
    });
  });
}

async function main() {
  try {
    cachedPayload = await loadData();
    renderCards(cachedPayload.meta, cachedPayload.series);
    renderChart(cachedPayload.series, activeRange);
    renderInsight(getLatestRow(cachedPayload.series));
    bindButtons();
  } catch (error) {
    console.error(error);
    setText('premiumValue', 'Load error');
    setText('premiumSubtext', 'Check docs/data/indicator.json');
    setText('insightText', error.message);
  }
}

document.addEventListener('DOMContentLoaded', main);
