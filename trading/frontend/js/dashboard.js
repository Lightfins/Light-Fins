/**
 * Trading Command Center — Dashboard Controller
 * Polls API endpoints and updates the cockpit UI in real-time.
 */

const API_BASE = '/api';
const POLL_INTERVAL = 5000; // 5 seconds
const ALERT_MAX = 50;

let equityChart = null;
const alerts = [];

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
    equityChart = new EquityChart('equityCanvas');
    initVolMeter();
    startClock();
    addAlert('info', 'Command Center initialized');
    addAlert('info', 'Polling server for data...');
    pollAll();
    setInterval(pollAll, POLL_INTERVAL);
});

// --- Clock ---
function startClock() {
    const el = document.getElementById('clock');
    function tick() {
        const now = new Date();
        const utc = now.toISOString().slice(11, 19);
        el.textContent = utc + ' UTC';
    }
    tick();
    setInterval(tick, 1000);
}

// --- Volatility Meter ---
function initVolMeter() {
    const container = document.getElementById('volMeter');
    if (!container) return;
    for (let i = 0; i < 20; i++) {
        const bar = document.createElement('div');
        bar.className = 'vol-bar';
        bar.style.height = '2px';
        container.appendChild(bar);
    }
}

function updateVolMeter(level) {
    // level: 0-100
    const bars = document.querySelectorAll('#volMeter .vol-bar');
    const activeBars = Math.round((level / 100) * bars.length);
    bars.forEach((bar, i) => {
        if (i < activeBars) {
            const h = 4 + (i / bars.length) * 20;
            bar.style.height = h + 'px';
            bar.className = 'vol-bar ' + (i > bars.length * 0.75 ? 'hot' : 'active');
        } else {
            bar.style.height = '2px';
            bar.className = 'vol-bar';
        }
    });
}

// --- Alert Log ---
function addAlert(type, msg) {
    const now = new Date().toISOString().slice(11, 19);
    alerts.unshift({ type, msg, time: now });
    if (alerts.length > ALERT_MAX) alerts.pop();
    renderAlerts();
}

function renderAlerts() {
    const container = document.getElementById('alertLog');
    if (!container) return;
    container.innerHTML = alerts.map(a => `
        <div class="alert-entry ${a.type}">
            <span class="alert-time">${a.time}</span>
            <span class="alert-msg">${a.msg}</span>
        </div>
    `).join('');
    document.getElementById('alertCount').textContent = alerts.length;
}

// --- Data Polling ---
async function pollAll() {
    await Promise.allSettled([
        pollStatus(),
        pollJournal(),
        pollStrategies(),
        pollMetrics(),
        pollEquity(),
        pollSessions(),
        pollMonteCarlo(),
        pollNews(),
    ]);
    document.getElementById('lastUpdate').textContent = new Date().toISOString().slice(11, 19);
}

async function apiFetch(endpoint) {
    try {
        const res = await fetch(API_BASE + endpoint);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        return null;
    }
}

// --- Status ---
async function pollStatus() {
    const data = await apiFetch('/status');
    if (!data) return;

    const risk = data.risk || {};
    const kill = data.kill_switch || {};

    // System status
    const dot = document.getElementById('systemDot');
    const sysEl = document.getElementById('sysStatus');
    if (kill.killed) {
        dot.className = 'dot killed';
        sysEl.textContent = 'KILLED';
        sysEl.style.color = '#ff1744';
        document.getElementById('killStatus').textContent = 'ACTIVE';
        document.getElementById('killStatus').style.color = '#ff1744';
        addAlert('error', `KILL SWITCH: ${kill.reasons?.join('; ')}`);
    } else {
        dot.className = 'dot';
        sysEl.textContent = 'OPERATIONAL';
        sysEl.style.color = '';
        document.getElementById('killStatus').textContent = 'OFF';
        document.getElementById('killStatus').style.color = '';
    }

    // Capital & P&L
    setText('capital', '$' + (risk.capital || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }));
    const pnl = risk.pnl || 0;
    const pnlEl = document.getElementById('pnl');
    pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
    pnlEl.className = 'stat-value ' + (pnl >= 0 ? 'positive' : 'negative');

    // Drawdown
    const dd = risk.drawdown_pct || 0;
    setText('drawdown', dd.toFixed(2) + '%');
    const ddGauge = document.getElementById('ddGauge');
    ddGauge.style.width = Math.min(dd / 15 * 100, 100) + '%';
    ddGauge.className = 'risk-gauge-fill ' + (dd < 5 ? 'low' : dd < 10 ? 'medium' : 'high');

    // Exposure
    const exp = risk.exposure_pct || 0;
    setText('exposure', exp.toFixed(2) + '%');
    const expGauge = document.getElementById('expGauge');
    expGauge.style.width = Math.min(exp / 20 * 100, 100) + '%';
    expGauge.className = 'risk-gauge-fill ' + (exp < 5 ? 'low' : exp < 15 ? 'medium' : 'high');

    // Risk badge
    const badge = document.getElementById('riskBadge');
    if (dd >= 10 || kill.killed) {
        badge.textContent = 'CRITICAL';
        badge.className = 'panel-badge badge-red';
    } else if (dd >= 5 || exp >= 10) {
        badge.textContent = 'ELEVATED';
        badge.className = 'panel-badge badge-amber';
    } else {
        badge.textContent = 'NOMINAL';
        badge.className = 'panel-badge badge-green';
    }

    setText('openPositions', risk.open_positions || 0);
    const dp = risk.daily_pnl || 0;
    const dpEl = document.getElementById('dailyPnl');
    dpEl.textContent = (dp >= 0 ? '+' : '') + '$' + dp.toFixed(2);
    dpEl.className = 'stat-value ' + (dp >= 0 ? 'positive' : 'negative');
    setText('dailyTrades', risk.daily_trades || 0);

    // Strategy counts
    if (data.strategies) {
        document.getElementById('stratCount').textContent = data.strategies.active + ' ACTIVE';
    }
}

// --- Journal ---
async function pollJournal() {
    const data = await apiFetch('/journal?days=30&limit=20');
    if (!data) return;

    const trades = data.trades || [];
    document.getElementById('tradeCount').textContent = data.total + ' TRADES';

    const tbody = document.getElementById('journalBody');
    if (!tbody) return;

    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-dim);padding:20px">No trades recorded yet</td></tr>';
        return;
    }

    tbody.innerHTML = trades.map(t => {
        const pnlColor = (t.net_pnl || 0) >= 0 ? 'positive' : 'negative';
        const rColor = (t.r_multiple || 0) >= 0 ? 'positive' : 'negative';
        return `<tr>
            <td>${(t.timestamp_open || '').slice(5, 16)}</td>
            <td>${t.pair || '--'}</td>
            <td style="color:${t.direction === 'long' ? 'var(--green)' : 'var(--red)'}">${(t.direction || '').toUpperCase()}</td>
            <td>${t.strategy || '--'}</td>
            <td>${(t.entry_price || 0).toFixed(4)}</td>
            <td>${t.exit_price ? t.exit_price.toFixed(4) : '--'}</td>
            <td class="${rColor}">${(t.r_multiple || 0).toFixed(1)}R</td>
            <td class="${pnlColor}">${(t.net_pnl || 0) >= 0 ? '+' : ''}$${(t.net_pnl || 0).toFixed(2)}</td>
            <td>${t.exit_reason || t.status || '--'}</td>
        </tr>`;
    }).join('');
}

// --- Strategies ---
async function pollStrategies() {
    const data = await apiFetch('/strategies');
    if (!data) return;

    const strategies = data.strategies || [];
    const container = document.getElementById('strategyList');
    if (!container) return;

    if (strategies.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-dim);padding:20px;font-family:var(--font-mono);font-size:11px">Strategy data populates after trades are logged</div>';
        return;
    }

    container.innerHTML = strategies.map((s, i) => {
        const wr = ((s.win_rate || 0) * 100).toFixed(0);
        const exp = (s.expectancy || 0).toFixed(2);
        const barColor = s.expectancy > 0.2 ? 'var(--green)' : s.expectancy > 0 ? 'var(--amber)' : 'var(--red)';
        const barWidth = Math.min(Math.abs(s.win_rate || 0) * 100, 100);
        const status = s.eval_status || 'unknown';
        const statusColor = status === 'healthy' ? 'var(--green)' : status === 'failing' ? 'var(--red)' : 'var(--amber)';

        return `<div class="strategy-row">
            <span class="strategy-rank">#${i + 1}</span>
            <span class="strategy-name">${s.strategy || 'Unknown'}</span>
            <span class="strategy-stat" style="color:${statusColor}">${wr}%</span>
            <span class="strategy-stat" style="color:${barColor}">${exp}E</span>
            <div class="strategy-bar">
                <div class="strategy-bar-fill" style="width:${barWidth}%;background:${barColor}"></div>
            </div>
        </div>`;
    }).join('');
}

// --- Metrics ---
async function pollMetrics() {
    const data = await apiFetch('/metrics?days=30');
    if (!data || data.error) return;

    setText('metricSharpe', (data.sharpe_ratio || 0).toFixed(2));
    setText('metricSortino', (data.sortino_ratio || 0).toFixed(2));

    const profDays = data.profitable_days || 0;
    const totalDays = data.total_days || 1;
    setText('metricWinRate', ((profDays / totalDays) * 100).toFixed(0) + '%');
    setText('metricMaxDD', (data.max_drawdown_pct || 0).toFixed(1) + '%');
}

// --- Equity Curve ---
async function pollEquity() {
    const data = await apiFetch('/equity?days=90');
    if (!data) return;

    const curve = data.equity_curve || [];
    if (curve.length > 0 && equityChart) {
        equityChart.setData(curve.map(d => ({ equity: d.capital_eod || 10000 })));
    }
}

// --- Sessions ---
async function pollSessions() {
    const data = await apiFetch('/sessions');
    if (!data) return;

    const current = data.current_session;
    ['Asia', 'London', 'NY'].forEach(name => {
        const el = document.getElementById('session' + name);
        if (el) {
            const key = name.toLowerCase();
            if (current === key || (key === 'ny' && current === 'ny')) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        }
    });
}

// --- Monte Carlo ---
async function pollMonteCarlo() {
    const data = await apiFetch('/montecarlo?n_sims=2000&n_trades=100');
    if (!data || data.error) return;

    const ruin = data.risk?.ruin_probability || 0;
    setText('metricRuin', (ruin * 100).toFixed(1) + '%');

    const exp = data.risk?.expected_return_pct || 0;
    setText('metricExpectancy', (exp >= 0 ? '+' : '') + exp.toFixed(1) + '%');

    // Update confidence meter based on MC results
    const confScore = Math.max(0, Math.min(100, (1 - ruin) * 100));
    updateConfidence(confScore);

    // Update volatility meter (rough proxy from drawdown)
    const volLevel = Math.min(100, (data.drawdown?.mean_max_dd_pct || 0) * 5);
    updateVolMeter(volLevel);
}

// --- Confidence Meter ---
function updateConfidence(score) {
    const fill = document.getElementById('confFill');
    const label = document.getElementById('confLabel');
    if (!fill || !label) return;

    fill.style.width = score + '%';
    label.textContent = Math.round(score);

    if (score >= 80) {
        fill.style.background = 'var(--green)';
        label.style.color = 'var(--green)';
    } else if (score >= 50) {
        fill.style.background = 'var(--amber)';
        label.style.color = 'var(--amber)';
    } else {
        fill.style.background = 'var(--red)';
        label.style.color = 'var(--red)';
    }
}

// --- News Filter ---
async function pollNews() {
    const data = await apiFetch('/news');
    if (!data) return;

    const el = document.getElementById('newsStatus');
    if (!el) return;

    if (!data.safe_to_trade) {
        el.textContent = `BLACKOUT (${data.next_event})`;
        el.style.color = '#ff1744';
        addAlert('error', `NEWS BLACKOUT: ${data.next_event} in ${Math.abs(data.minutes_to_event).toFixed(0)}min`);
    } else if (data.caution) {
        el.textContent = `CAUTION ${Math.abs(data.minutes_to_event).toFixed(0)}m`;
        el.style.color = '#ffb300';
    } else if (data.next_event) {
        const mins = Math.abs(data.minutes_to_event || 0);
        el.textContent = mins > 120 ? 'CLEAR' : `${mins.toFixed(0)}m to ${data.impact}`;
        el.style.color = '';
    } else {
        el.textContent = 'CLEAR';
        el.style.color = '';
    }
}

// --- Helpers ---
function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}
