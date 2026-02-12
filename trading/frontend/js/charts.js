/**
 * Lightweight Canvas Chart Library
 * No dependencies. Renders equity curves, bars, and gauges
 * with the Starfighter cockpit aesthetic.
 */

const CHART_COLORS = {
    cyan: '#00e5ff',
    cyanDim: '#00a0b0',
    cyanGlow: 'rgba(0, 229, 255, 0.08)',
    green: '#00e676',
    red: '#ff1744',
    amber: '#ffb300',
    grid: '#1e2a42',
    gridDim: 'rgba(30, 42, 66, 0.5)',
    text: '#8892a8',
    textDim: '#4a5568',
    bg: '#151d2e',
};

class EquityChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.data = [];
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.ctx.scale(dpr, dpr);
        this.width = rect.width;
        this.height = rect.height;
        if (this.data.length) this.render();
    }

    setData(equityCurve) {
        this.data = equityCurve;
        this.render();
    }

    render() {
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;
        const pad = { top: 20, right: 16, bottom: 28, left: 60 };

        ctx.clearRect(0, 0, w, h);

        if (!this.data || this.data.length < 2) {
            this._renderEmpty(ctx, w, h);
            return;
        }

        const values = this.data.map(d => d.equity || d);
        const minVal = Math.min(...values);
        const maxVal = Math.max(...values);
        const range = maxVal - minVal || 1;

        const chartW = w - pad.left - pad.right;
        const chartH = h - pad.top - pad.bottom;

        const xScale = chartW / (values.length - 1);
        const yScale = chartH / range;

        // Grid lines
        ctx.strokeStyle = CHART_COLORS.gridDim;
        ctx.lineWidth = 0.5;
        const gridLines = 5;
        for (let i = 0; i <= gridLines; i++) {
            const y = pad.top + (chartH / gridLines) * i;
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(w - pad.right, y);
            ctx.stroke();

            // Y-axis labels
            const val = maxVal - (range / gridLines) * i;
            ctx.fillStyle = CHART_COLORS.textDim;
            ctx.font = '10px "JetBrains Mono", monospace';
            ctx.textAlign = 'right';
            ctx.fillText('$' + val.toFixed(0), pad.left - 8, y + 3);
        }

        // Gradient fill under the curve
        const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
        const isPositive = values[values.length - 1] >= values[0];
        if (isPositive) {
            gradient.addColorStop(0, 'rgba(0, 230, 118, 0.15)');
            gradient.addColorStop(1, 'rgba(0, 230, 118, 0)');
        } else {
            gradient.addColorStop(0, 'rgba(255, 23, 68, 0.15)');
            gradient.addColorStop(1, 'rgba(255, 23, 68, 0)');
        }

        // Fill area
        ctx.beginPath();
        ctx.moveTo(pad.left, h - pad.bottom);
        for (let i = 0; i < values.length; i++) {
            const x = pad.left + i * xScale;
            const y = pad.top + (maxVal - values[i]) * yScale;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(pad.left + (values.length - 1) * xScale, h - pad.bottom);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // Line
        ctx.beginPath();
        ctx.strokeStyle = isPositive ? CHART_COLORS.green : CHART_COLORS.red;
        ctx.lineWidth = 1.5;
        ctx.lineJoin = 'round';
        for (let i = 0; i < values.length; i++) {
            const x = pad.left + i * xScale;
            const y = pad.top + (maxVal - values[i]) * yScale;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Glow effect
        ctx.strokeStyle = isPositive ? 'rgba(0, 230, 118, 0.3)' : 'rgba(255, 23, 68, 0.3)';
        ctx.lineWidth = 4;
        ctx.stroke();

        // Current value dot
        const lastX = pad.left + (values.length - 1) * xScale;
        const lastY = pad.top + (maxVal - values[values.length - 1]) * yScale;
        ctx.beginPath();
        ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
        ctx.fillStyle = isPositive ? CHART_COLORS.green : CHART_COLORS.red;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(lastX, lastY, 8, 0, Math.PI * 2);
        ctx.fillStyle = isPositive ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 23, 68, 0.2)';
        ctx.fill();

        // Current value label
        ctx.fillStyle = CHART_COLORS.text;
        ctx.font = 'bold 12px "JetBrains Mono", monospace';
        ctx.textAlign = 'right';
        ctx.fillText('$' + values[values.length - 1].toFixed(2), w - pad.right, pad.top - 4);

        // Initial value reference line
        const initY = pad.top + (maxVal - values[0]) * yScale;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = CHART_COLORS.textDim;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(pad.left, initY);
        ctx.lineTo(w - pad.right, initY);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    _renderEmpty(ctx, w, h) {
        ctx.fillStyle = CHART_COLORS.textDim;
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText('AWAITING TRADE DATA', w / 2, h / 2 - 10);
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillText('Equity curve renders after first closed trade', w / 2, h / 2 + 10);

        // Decorative grid
        ctx.strokeStyle = CHART_COLORS.gridDim;
        ctx.lineWidth = 0.5;
        for (let i = 0; i < 6; i++) {
            const y = 30 + (h - 60) / 5 * i;
            ctx.beginPath();
            ctx.moveTo(50, y);
            ctx.lineTo(w - 20, y);
            ctx.stroke();
        }
    }
}

// Monte Carlo mini-chart (renders percentile fan)
class MCFanChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
    }

    render(percentileCurves) {
        if (!this.canvas || !percentileCurves) return;
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        ctx.clearRect(0, 0, w, h);

        const curves = percentileCurves;
        const keys = Object.keys(curves).sort();
        if (keys.length < 2) return;

        const allValues = keys.flatMap(k => curves[k]);
        const minV = Math.min(...allValues);
        const maxV = Math.max(...allValues);
        const range = maxV - minV || 1;
        const len = curves[keys[0]].length;

        const xScale = w / (len - 1);
        const yScale = h / range;

        // Fan fill between p5 and p95
        if (curves.p5 && curves.p95) {
            ctx.fillStyle = 'rgba(0, 229, 255, 0.05)';
            ctx.beginPath();
            for (let i = 0; i < len; i++) {
                ctx.lineTo(i * xScale, (maxV - curves.p95[i]) * yScale);
            }
            for (let i = len - 1; i >= 0; i--) {
                ctx.lineTo(i * xScale, (maxV - curves.p5[i]) * yScale);
            }
            ctx.closePath();
            ctx.fill();
        }

        // Median line
        if (curves.p50) {
            ctx.strokeStyle = CHART_COLORS.cyan;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let i = 0; i < len; i++) {
                const x = i * xScale;
                const y = (maxV - curves.p50[i]) * yScale;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
    }
}

// Export
window.EquityChart = EquityChart;
window.MCFanChart = MCFanChart;
