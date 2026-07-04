/**
 * Smart City Gas & Air Safety Monitoring Platform
 * Dashboard v7.0 — Full Data Consistency
 *
 * Changes vs v6.1:
 *  - REFRESH_MS: 5000 → 120000 (2 minutes, matches Grafana refresh)
 *  - Gov bar chart tooltip: shows ONLY governorate name + avg_risk_score (not incidentRate etc.)
 *  - Gov bar chart colors: match Grafana thresholds exactly
 *      green  (#32CD32) = avg_risk_score < 8
 *      orange (#FF8C00) = avg_risk_score >= 8  and < 12
 *      red    (#FF0000) = avg_risk_score >= 12
 *  - Gov bar chart dataKey: avgRisk (not incidentRate) — same unit as Grafana Y-axis
 *  - Gov bar chart shows ALL govs from /api/risk-by-gov (no .slice(0,10))
 *  - Insight banner "Highest cluster": uses riskByGov[0] from gold.gov_stats — same as Grafana
 *  - Map markers: deduplicated at API level (ROW_NUMBER in backend) so one house = one marker
 *  - Threat Distribution (PieChart) tooltip: white text on dark background, clearly readable
 *  - methane trend uses last-3-min data from backend (matches Grafana)
 *
 * Data source consistency (all three: React, Grafana, ChatBot):
 *  KPIs           → gold.active_alerts   WHERE batch_id = MAX(batch_id)
 *  Map markers    → gold.active_alerts   WHERE batch_id = MAX(batch_id), deduplicated
 *  Incident feed  → gold.active_alerts   WHERE batch_id = MAX(batch_id), deduplicated
 *  CH4 trend      → gold.zone_stats      WHERE snapshot_time >= DATEADD(MINUTE,-3,GETDATE())
 *  Gov ranking    → gold.gov_stats       WHERE batch_id = MAX(batch_id), ALL govs
 */

import React, {
  useState, useEffect, useCallback, useMemo, useRef
} from 'react';
import Map, { Marker, Popup } from 'react-map-gl/maplibre';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer, ReferenceLine,
  PieChart, Pie, Legend
} from 'recharts';
import {
  Activity, AlertTriangle, Flame, Target,
  ShieldAlert, Wifi, Radio, Cpu, Info,
  MessageSquare, X, Send, Bot, User, Loader, Sparkles,
  BarChart2, AlertOctagon, TrendingUp, Map as MapIcon
} from 'lucide-react';
import axios from 'axios';

// ─────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────
const API_URL    = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API        = `${API_URL}/api`;
const MAP_STYLE  = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// 30 second — matches Grafana refresh interval
const REFRESH_MS = 30000;

// Absolute sensor thresholds (matches backend metadata_config.py)
const THRESHOLDS = {
  methane:     { warning: 50,  critical: 150 },
  temperature: { warning: 42,  critical: 55  },
  smoke:       { warning: 20,  critical: 45  },
  co:          { warning: 9,   critical: 35  },
};

// Maps API primary_trigger → sensor key in sensors object
const TRIGGER_SENSOR = {
  GAS_LEAK:      'methane',
  HIGH_TEMP:     'temperature',
  SMOKE_SPIKE:   'smoke',
  CO_HAZARD:     'co',
  ELEVATED_RISK: null,
};

// ─────────────────────────────────────────────────────────────
// Gov bar color — matches Grafana thresholds exactly:
//   green  (#32CD32) for avg_risk_score < 8
//   orange (#FF8C00) for avg_risk_score >= 8 and < 12
//   red    (#FF0000) for avg_risk_score >= 12
// ─────────────────────────────────────────────────────────────
function govBarColor(avgRisk) {
  if (avgRisk >= 12) return '#FF0000';  // Grafana red threshold
  if (avgRisk >= 8)  return '#FF8C00';  // Grafana orange threshold
  return '#32CD32';                      // Grafana green baseline
}

// ─────────────────────────────────────────────────────────────
// Pure helpers
// ─────────────────────────────────────────────────────────────
function sensorBoxClass(key, trigger, status) {
  const hit = TRIGGER_SENSOR[trigger] === key;
  if (!hit) return 'bg-slate-800/50 border-slate-700/60';
  return status === 'CRITICAL'
    ? 'bg-rose-500/20 border-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]'
    : 'bg-amber-500/20 border-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.35)]';
}
function sensorLabelClass(key, trigger, status) {
  if (TRIGGER_SENSOR[trigger] !== key) return 'text-slate-500';
  return status === 'CRITICAL' ? 'text-rose-300 font-bold' : 'text-amber-300 font-bold';
}
function sensorValueClass(key, trigger, status) {
  if (TRIGGER_SENSOR[trigger] !== key) return 'text-slate-200';
  return status === 'CRITICAL' ? 'text-rose-400 font-bold' : 'text-amber-400 font-bold';
}

function DeltaBadge({ delta }) {
  if (delta === null || delta === undefined || delta === 0) return null;
  const color = delta > 0 ? 'text-rose-400' : 'text-emerald-400';
  const sign  = delta > 0 ? '+' : '';
  return <span className={`text-[9px] font-mono ml-1 ${color}`}>{sign}{delta}</span>;
}

// ─────────────────────────────────────────────────────────────
// KPI Card
// ─────────────────────────────────────────────────────────────
function KPICard({ title, value, icon, color, subtitle, pulse, delta }) {
  const palette = {
    cyan:  { border:'border-cyan-500/20',  text:'text-cyan-400',  glow:'shadow-[0_0_24px_rgba(6,182,212,0.1)]',   bg:'bg-cyan-500/8'   },
    rose:  { border:'border-rose-500/20',  text:'text-rose-400',  glow:'shadow-[0_0_24px_rgba(244,63,94,0.1)]',   bg:'bg-rose-500/8'   },
    amber: { border:'border-amber-500/20', text:'text-amber-400', glow:'shadow-[0_0_24px_rgba(245,158,11,0.1)]',  bg:'bg-amber-500/8'  },
    blue:  { border:'border-blue-500/20',  text:'text-blue-400',  glow:'shadow-[0_0_24px_rgba(59,130,246,0.1)]',  bg:'bg-blue-500/8'   },
  };
  const c = palette[color] || palette.cyan;
  return (
    <div className={`relative flex items-center justify-between p-5 rounded-2xl bg-[#07111f] border ${c.border} ${c.glow} overflow-hidden`}>
      <div className={`absolute -top-8 -right-8 w-28 h-28 rounded-full blur-3xl ${c.bg} opacity-50`} />
      <div className="relative z-10">
        <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500 mb-1">{title}</p>
        <div className="flex items-baseline gap-1">
          <p className={`text-[2.35rem] font-black leading-none tracking-tight ${c.text} ${pulse && Number(value) > 0 ? 'drop-shadow-[0_0_8px_currentColor]' : ''}`}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          <DeltaBadge delta={delta} />
        </div>
        {subtitle && <p className="text-[9px] text-slate-500 font-mono mt-1">{subtitle}</p>}
      </div>
      <div className={`relative z-10 p-3 rounded-xl border ${c.border} ${c.bg} ${c.text}`}>{icon}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Map Marker
// ─────────────────────────────────────────────────────────────
function MapMarker({ alertStatus, isFaded, onEnter, onLeave, onClick }) {
  const cfg = alertStatus === 'CRITICAL'
    ? { core: 10, ring: 32, color: '#f43f5e', dur: '1.1s' }
    : alertStatus === 'WARNING'
    ? { core: 8,  ring: 24, color: '#f59e0b', dur: '1.9s' }
    : { core: 4,  ring: 14, color: '#10b981', dur: '4s'   };

  return (
    <div
      className="relative flex items-center justify-center cursor-pointer"
      style={{ width: cfg.ring, height: cfg.ring, opacity: isFaded ? 0.1 : 1, transition: 'opacity 0.3s' }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
    >
      {alertStatus !== 'NORMAL' && (
        <div className="absolute rounded-full"
          style={{ width: cfg.ring, height: cfg.ring, border: `1.5px solid ${cfg.color}`,
            animation: `mPing ${cfg.dur} ease-out infinite` }} />
      )}
      {alertStatus === 'NORMAL' && (
        <div className="absolute rounded-full"
          style={{ width: cfg.ring, height: cfg.ring,
            background: `radial-gradient(circle, ${cfg.color}22 0%, transparent 70%)` }} />
      )}
      <div className="relative z-10 rounded-full"
        style={{ width: cfg.core, height: cfg.core, backgroundColor: cfg.color,
          boxShadow: `0 0 ${alertStatus === 'CRITICAL' ? 10 : 5}px ${cfg.color}` }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Map Popup Tooltip
// ─────────────────────────────────────────────────────────────
function MapPopup({ d }) {
  const isCrit = d.alert_status === 'CRITICAL';
  const s = d.sensors || {};
  const trigger = d.primary_trigger;
  const status  = d.alert_status;

  return (
    <div className="bg-[#080f1e]/97 backdrop-blur-2xl border border-slate-700/70 rounded-2xl p-4 shadow-[0_24px_70px_rgba(0,0,0,0.85)] w-[250px] pointer-events-none mb-2">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="text-white font-black text-sm uppercase tracking-wide">{d.governorate}</p>
          <p className="text-slate-400 text-[10px] font-mono">{d.zone}{d.house_id ? ` · ${d.house_id}` : ''}</p>
        </div>
        <span className={`text-[9px] font-black px-2.5 py-0.5 rounded border uppercase tracking-wider ${
          isCrit ? 'bg-rose-500/20 text-rose-400 border-rose-500/50' : 'bg-amber-500/20 text-amber-400 border-amber-500/50'
        }`}>{status}</span>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-[9px] text-slate-500 uppercase tracking-widest w-14">Risk</span>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${isCrit ? 'bg-rose-500' : 'bg-amber-400'}`}
            style={{ width: `${Math.min(d.risk_score || 0, 100)}%` }} />
        </div>
        <span className="text-[10px] font-mono text-white font-bold">{d.risk_score}</span>
      </div>

      <div className="grid grid-cols-2 gap-1.5 mb-3">
        {[
          { key: 'methane',     label: 'CH4',   val: s.methane != null ? `${s.methane} ppm` : '—' },
          { key: 'temperature', label: 'TEMP',  val: s.temp    != null ? `${s.temp}°C`       : '—' },
          { key: 'smoke',       label: 'SMOKE', val: s.smoke   != null ? `${s.smoke}`         : '—' },
          { key: 'co',          label: 'CO',    val: s.co      != null ? `${s.co} ppm`        : '—' },
        ].map(({ key, label, val }) => (
          <div key={key} className={`flex flex-col items-center p-1.5 rounded-lg border ${sensorBoxClass(key, trigger, status)}`}>
            <span className={`text-[8px] uppercase tracking-widest ${sensorLabelClass(key, trigger, status)}`}>{label}</span>
            <span className={`text-[11px] font-mono mt-0.5 ${sensorValueClass(key, trigger, status)}`}>{val}</span>
          </div>
        ))}
      </div>

      <div className="flex justify-between text-[9px] border-t border-slate-700/40 pt-2">
        <span className="text-slate-500">Trigger: <span className="text-slate-300 font-mono">{trigger?.replace(/_/g,' ') || '—'}</span></span>
        <span className="text-slate-500 font-mono">live</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Incident Card
// ─────────────────────────────────────────────────────────────
function IncidentCard({ alert, onClick }) {
  const isCrit  = alert.alert_status === 'CRITICAL';
  const trigger = alert.primary_trigger;
  const status  = alert.alert_status;
  const s       = alert.sensors || {};

  return (
    <div onClick={() => onClick(alert)}
      className={`relative p-3 rounded-xl border cursor-pointer transition-all hover:scale-[1.01] overflow-hidden ${
        isCrit ? 'border-rose-500/35 bg-rose-500/6 hover:border-rose-400/60'
               : 'border-amber-500/35 bg-amber-500/6 hover:border-amber-400/60'
      }`}
    >
      <div className={`absolute left-0 inset-y-0 w-[3px] rounded-l-xl ${isCrit ? 'bg-rose-500' : 'bg-amber-400'}`} />
      <div className="pl-3">
        <div className="flex justify-between items-start mb-2">
          <div>
            <p className="text-white font-black text-sm uppercase tracking-wide leading-none">{alert.governorate}</p>
            <p className="text-slate-400 text-[10px] font-mono mt-0.5">{alert.zone} · {alert.house_id}</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className={`text-[9px] font-black px-2 py-0.5 rounded border uppercase ${
              isCrit ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                     : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
            }`}>{status}</span>
            {trigger === 'ELEVATED_RISK' ? (
              <span className="text-[8px] text-slate-400 font-semibold">⚠ Multi-sensor</span>
            ) : (
              <span className="text-[8px] text-slate-500 font-semibold uppercase">{trigger?.replace(/_/g,' ')}</span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-1.5">
          {[
            { key:'methane',     label:'CH4',   val: s.methane != null ? String(s.methane) : '—' },
            { key:'temperature', label:'TEMP',  val: s.temp    != null ? `${s.temp}°`      : '—' },
            { key:'smoke',       label:'SMOKE', val: s.smoke   != null ? String(s.smoke)   : '—' },
            { key:'co',          label:'CO',    val: s.co      != null ? String(s.co)      : '—' },
          ].map(({ key, label, val }) => (
            <div key={key} className={`flex flex-col items-center py-1.5 px-1 rounded-lg border ${sensorBoxClass(key, trigger, status)}`}>
              <span className={`text-[7px] uppercase tracking-widest leading-none ${sensorLabelClass(key, trigger, status)}`}>{label}</span>
              <span className={`text-[10px] font-mono font-bold mt-0.5 leading-none ${sensorValueClass(key, trigger, status)}`}>{val}</span>
            </div>
          ))}
        </div>

        {trigger === 'ELEVATED_RISK' && (
          <p className="text-[8px] text-slate-500 font-mono mt-1.5">
            ⚠ Combined CO · LPG · AQI factors elevated
          </p>
        )}

        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${isCrit ? 'bg-rose-500' : 'bg-amber-400'}`}
              style={{ width: `${Math.min(alert.risk_score || 0, 100)}%` }} />
          </div>
          <span className="text-[9px] font-mono text-slate-400">{alert.risk_score}/100</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// CH4 Chart
// ─────────────────────────────────────────────────────────────
function CH4Chart({ data, color }) {
  const yMax = Math.max(...data.map(d => d.value || 0), 10);
  const warnPct = Math.max(0, Math.min(100, (1 - (50  / yMax)) * 100));
  const critPct = Math.max(0, Math.min(100, (1 - (150 / yMax)) * 100));
  const showWarn = yMax >= 40;
  const showCrit = yMax >= 120;

  return (
    <div className="relative flex-1 p-2">
      {showWarn && (
        <div className="absolute left-2 right-2 pointer-events-none z-10"
          style={{ top: `${warnPct}%`, height: 0 }}>
          <div style={{ borderTop: '1px dashed #f59e0b66', position:'relative' }}>
            <span className="absolute right-0 -top-3.5 text-[8px] font-mono text-amber-500/80 bg-[#05101d] px-1">
              WARN 50
            </span>
          </div>
        </div>
      )}
      {showCrit && (
        <div className="absolute left-2 right-2 pointer-events-none z-10"
          style={{ top: `${critPct}%`, height: 0 }}>
          <div style={{ borderTop: '1px dashed #f43f5e66', position:'relative' }}>
            <span className="absolute right-0 -top-3.5 text-[8px] font-mono text-rose-500/80 bg-[#05101d] px-1">
              CRIT 150
            </span>
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 6, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="ch4grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor={color} stopOpacity={0.5} />
              <stop offset="90%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
            <filter id="ch4glow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={color} floodOpacity="0.85" />
              <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor={color} floodOpacity="0.35" />
            </filter>
          </defs>
          <CartesianGrid strokeDasharray="2 6" stroke="#0d2540" vertical={false} />
          <XAxis dataKey="time" hide />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 8, fill: '#334155' }} width={30} />
          <RechartsTooltip
            contentStyle={{ background:'#06101e', border:`1px solid ${color}50`, fontSize:'10px', borderRadius:'8px' }}
            formatter={v => [`${Number(v).toFixed(2)} ppm`, 'Avg CH4']}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#ffffff' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={3}
            fill="url(#ch4grad)"
            filter="url(#ch4glow)"
            dot={false}
            activeDot={{ r:4, fill:color, stroke:'#020a16', strokeWidth:2 }}
            isAnimationActive
            animationDuration={600}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Alert Distribution Donut
// Tooltip fix: explicit white text so it's readable on dark background
// ─────────────────────────────────────────────────────────────
function AlertDonut({ kpis }) {
  const total    = kpis.TOTAL_HOUSES || 3000;
  const critical = kpis.CRITICAL     || 0;
  const warning  = kpis.WARNING      || 0;
  const normal   = Math.max(total - critical - warning, 0);
  const atRisk   = ((critical + warning) / total * 100).toFixed(1);

  const data = [
    { name:'Normal',   value:normal,   fill:'#22c55e' },
    { name:'Warning',  value:warning,  fill:'#f59e0b' },
    { name:'Critical', value:critical, fill:'#f43f5e' },
  ];

  // Custom tooltip with guaranteed white text on dark background
  const CustomDonutTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const item = payload[0];
    const pct  = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0.0';
    return (
      <div style={{
        background: '#06101e',
        border: `1px solid ${item.payload.fill}60`,
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '11px',
        color: '#ffffff',
        boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
      }}>
        <div style={{ fontWeight: 900, color: item.payload.fill, marginBottom: '4px' }}>
          {item.name}
        </div>
        <div style={{ color: '#ffffff', marginBottom: '2px' }}>
          {item.value.toLocaleString()} houses
        </div>
        <div style={{ color: '#94a3b8', fontSize: '10px' }}>
          {pct}% of total
        </div>
      </div>
    );
  };

  return (
    <div className="relative w-full h-full">
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ paddingBottom:'28px' }}>
        <span className="text-white font-black text-[22px] leading-none">{atRisk}%</span>
        <span className="font-mono text-[8px] text-slate-500 mt-0.5 uppercase tracking-widest">AT RISK</span>
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%" cy="44%"
            innerRadius="50%" outerRadius="70%"
            paddingAngle={3}
            dataKey="value"
            labelLine={false}
            isAnimationActive
            animationDuration={800}
          >
            {data.map((d, i) => (
              <Cell key={i} fill={d.fill} stroke="transparent"
                style={{ filter:`drop-shadow(0 0 5px ${d.fill}70)` }} />
            ))}
          </Pie>
          <Legend
            iconType="circle" iconSize={7}
            wrapperStyle={{ fontSize:'9px', color:'#64748b', paddingTop:'2px' }}
            formatter={(name, entry) => (
              <span style={{ color:'#94a3b8' }}>{name} ({entry.payload.value.toLocaleString()})</span>
            )}
          />
          <RechartsTooltip content={<CustomDonutTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// ARIA ChatBot
// ─────────────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: 'System Status',   icon: <BarChart2 size={11}/>,    text: 'Give me a quick summary of the current system status.' },
  { label: 'Critical Alerts', icon: <AlertOctagon size={11}/>, text: 'What are the most critical incidents right now?' },
  { label: 'Top Risk Govs',   icon: <MapIcon size={11}/>,      text: 'Which governorates have the highest risk right now?' },
  { label: 'Methane Trend',   icon: <TrendingUp size={11}/>,   text: 'What is the current methane trend across all houses?' },
  { label: 'Daily Summary',   icon: <Sparkles size={11}/>,     text: 'Generate an executive summary of the system today.' },
  { label: 'Safety Advice',   icon: <ShieldAlert size={11}/>,  text: 'What safety actions should operators take right now?' },
];

function ChatBot({ API_URL }) {
  const [open,     setOpen]     = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'model',
      text: "مرحباً! أنا ARIA، مساعدك الذكي لمراقبة سلامة المدن. 🏙️\n\nأستطيع مساعدتك في:\n• تحليل الحوادث الحرجة\n• مقارنة مستويات الخطر بين المحافظات\n• شرح أسباب التنبيهات\n• توليد ملخصات تنفيذية\n\nاكتب **أي سؤال** أو اختر أحد الاقتراحات أدناه.",
    }
  ]);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const inputRef2   = useRef('');
  const messagesRef = useRef([]);

  useEffect(() => { inputRef2.current = input; },     [input]);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  useEffect(() => {
    if (open) setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  }, [messages, open]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 200);
  }, [open]);

  const sendMessage = useCallback(async (text) => {
    const msg = (text || inputRef2.current || '').trim();
    if (!msg || loading) return;

    setInput('');
    inputRef2.current = '';

    const userMsg = { role: 'user', text: msg };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const history = messagesRef.current
      .slice(1)
      .map(m => ({ role: m.role, text: m.text }));

    try {
      const res = await axios.post(`${API_URL}/api/chat`, { message: msg, history: history, batch_id: window.currentBatchId || 0});
      const reply = res.data?.response || '⚠️ لم يتم استلام رد من الخادم.';
      setMessages(prev => [...prev, { role: 'model', text: reply }]);
    } catch (err) {
      const errMsg = err?.response?.status === 429
        ? '⚠️ الخدمة مشغولة حالياً. يرجى الانتظار لحظة والمحاولة مجدداً.'
        : '⚠️ تعذّر الاتصال بخدمة الذكاء الاصطناعي. تأكد إن الـ backend شغال.';
      setMessages(prev => [...prev, { role: 'model', text: errMsg }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [loading, API_URL]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const formatText = (text) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**'))
          return <strong key={j} className="text-white font-bold">{part.slice(2,-2)}</strong>;
        return part;
      });
      return <span key={i}>{parts}{i < text.split('\n').length - 1 && <br />}</span>;
    });
  };

  return (
    <>
      <button
        onClick={() => setOpen(v => !v)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-2xl flex items-center justify-center
          shadow-[0_8px_32px_rgba(0,0,0,0.6)] transition-all duration-300 hover:scale-110 active:scale-95
          ${open
            ? 'bg-rose-600 border border-rose-500/60 shadow-[0_0_24px_rgba(244,63,94,0.5)]'
            : 'bg-gradient-to-br from-cyan-500 to-blue-600 border border-cyan-400/40 shadow-[0_0_24px_rgba(6,182,212,0.4)]'
          }`}
        aria-label="Open AI Assistant"
      >
        {open ? <X size={22} className="text-white" /> : <MessageSquare size={22} className="text-white" />}
        {!open && messages.length > 1 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 border border-[#020a16] flex items-center justify-center text-[8px] text-white font-black">
            {messages.filter(m => m.role === 'model').length - 1}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[400px] flex flex-col rounded-2xl overflow-hidden
          bg-[#040c1a] border border-slate-700/60
          shadow-[0_24px_80px_rgba(0,0,0,0.9),0_0_0_1px_rgba(6,182,212,0.1)]
          animate-[fadeSlideUp_0.25s_ease-out]"
          style={{ height: '580px' }}>

          {/* Header */}
          <div className="shrink-0 flex items-center gap-3 px-4 py-3
            bg-gradient-to-r from-[#05101d] to-[#040c1a] border-b border-slate-700/50">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20
              border border-cyan-500/30 flex items-center justify-center shrink-0">
              <Bot size={18} className="text-cyan-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-black text-[13px] uppercase tracking-widest leading-none">ARIA</p>
              <p className="text-slate-500 text-[9px] font-mono mt-0.5">AI Operations Assistant · Smart City Egypt</p>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[9px] text-emerald-400 font-mono font-bold">LIVE</span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 scroll-smooth
            [scrollbar-width:thin] [scrollbar-color:#1e3a60_transparent]">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`shrink-0 w-7 h-7 rounded-xl flex items-center justify-center
                  ${msg.role === 'user'
                    ? 'bg-cyan-500/20 border border-cyan-500/40'
                    : 'bg-blue-600/20 border border-blue-500/40'
                  }`}>
                  {msg.role === 'user' ? <User size={13} className="text-cyan-400" /> : <Bot size={13} className="text-blue-400" />}
                </div>
                <div className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed
                  ${msg.role === 'user'
                    ? 'bg-cyan-500/15 border border-cyan-500/30 text-slate-200 rounded-tr-sm'
                    : 'bg-[#07111f] border border-slate-700/60 text-slate-300 rounded-tl-sm'
                  }`}>
                  {msg.role === 'model'
                    ? <span className="whitespace-pre-wrap">{formatText(msg.text)}</span>
                    : <span>{msg.text}</span>
                  }
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2 flex-row">
                <div className="shrink-0 w-7 h-7 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center">
                  <Bot size={13} className="text-blue-400" />
                </div>
                <div className="bg-[#07111f] border border-slate-700/60 rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1.5 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:300ms]" />
                    <span className="text-[10px] text-slate-500 ml-1 font-mono">Analyzing live data...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick Actions */}
          <div className="shrink-0 px-3 py-2 border-t border-slate-800/60">
            <div className="flex gap-1.5 flex-wrap">
              {QUICK_ACTIONS.map((qa, i) => (
                <button key={i} onClick={() => sendMessage(qa.text)} disabled={loading}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-bold uppercase
                    tracking-wider transition-all bg-slate-800/60 border border-slate-700/60 text-slate-400
                    hover:bg-cyan-500/10 hover:border-cyan-500/40 hover:text-cyan-400
                    disabled:opacity-40 disabled:cursor-not-allowed">
                  {qa.icon}{qa.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="shrink-0 flex gap-2 p-3 border-t border-slate-700/50 bg-[#030b16]">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => { setInput(e.target.value); inputRef2.current = e.target.value; }}
              onKeyDown={handleKey}
              placeholder="اكتب سؤالك هنا... (Enter للإرسال)"
              rows={1}
              disabled={loading}
              className="flex-1 bg-[#06101e] border border-slate-700/60 rounded-xl px-3.5 py-2.5
                text-[12px] text-slate-200 placeholder-slate-600 resize-none
                focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_0_2px_rgba(6,182,212,0.1)]
                transition-all disabled:opacity-50 font-[inherit]"
              style={{ minHeight: '42px', maxHeight: '100px' }}
            />
            <button onClick={() => sendMessage(undefined)} disabled={!input.trim() || loading}
              className="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
                bg-gradient-to-br from-cyan-500 to-blue-600 border border-cyan-400/30
                shadow-[0_0_16px_rgba(6,182,212,0.3)] transition-all
                hover:shadow-[0_0_24px_rgba(6,182,212,0.5)] hover:scale-105
                disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100">
              {loading ? <Loader size={16} className="text-white animate-spin" /> : <Send size={16} className="text-white" />}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Main App
// ─────────────────────────────────────────────────────────────
export default function App() {
  const [kpis,         setKpis]         = useState({ CRITICAL:0, WARNING:0, avg_risk:0, TOTAL_HOUSES:3000 });
  const [prevKpis,     setPrevKpis]     = useState(null);
  const [trendData,    setTrendData]    = useState([]);
  const [activeAlerts, setActiveAlerts] = useState([]);
  // riskByGov: ALL govs from gold.gov_stats ordered by avg_risk_score DESC — same as Grafana
  const [riskByGov,    setRiskByGov]    = useState([]);
  const [selectedGov,  setSelectedGov]  = useState(null);
  const [hoverInfo,    setHoverInfo]    = useState(null);
  const [clock,        setClock]        = useState(new Date());
  const [lastFetch,    setLastFetch]    = useState(null);
  const [viewState,    setViewState]    = useState({
    longitude: 30.8, latitude: 26.8, zoom: 5.2, pitch: 0, bearing: 0
  });

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

// Fetch all data from backend — every 2 minutes (matches Grafana)
  const fetchData = useCallback(async () => {
    try {
      const [kpiRes, trendRes, alertsRes, govRes] = await Promise.all([
        axios.get(`${API}/kpis`),
        axios.get(`${API}/methane-trend`),
        axios.get(`${API}/active-alerts`),
        axios.get(`${API}/risk-by-gov`),
      ]);

      window.currentBatchId = kpiRes.data?.batch_id;

      setKpis(prev => { setPrevKpis(prev); return kpiRes.data || prev; });

      setTrendData((trendRes.data || []).map(r => ({
        ...r,
        value: (r.value > 0 && r.value < 2000) ? r.value : 0
      })));

      setActiveAlerts(alertsRes.data || []);
      
      // Build riskByGov — colors match Grafana thresholds exactly
      const govData = (govRes.data || []).map(g => ({
        ...g,
        barColor: govBarColor(g.avgRisk),
      }));
      setRiskByGov(govData);
      setLastFetch(new Date());
    } catch (e) { console.error('Fetch error:', e); }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  // Map markers: backend already deduplicates (ROW_NUMBER), one marker per house
  const mapData = useMemo(() =>
    activeAlerts
      .filter(a => a.latitude != null && a.longitude != null)
      .map(a => ({
        coordinates:     [a.longitude, a.latitude],
        alert_status:    a.alert_status,
        governorate:     a.governorate,
        zone:            a.zone,
        house_id:        a.house_id,
        risk_score:      a.risk_score,
        primary_trigger: a.primary_trigger,
        sensors:         a.sensors,
      })),
    [activeAlerts]
  );

  // Feed filtered by selected governorate
  const filteredAlerts = useMemo(() =>
    selectedGov ? activeAlerts.filter(a => a.governorate === selectedGov) : activeAlerts,
    [activeAlerts, selectedGov]
  );

  const latestMethane = trendData[trendData.length - 1]?.value ?? 0;
  const prevMethane   = trendData[trendData.length - 2]?.value ?? 0;
  const methaneDir    = latestMethane > prevMethane ? '↑' : latestMethane < prevMethane ? '↓' : '→';
  const ch4Color      = latestMethane >= 150 ? '#f43f5e' : latestMethane >= 50 ? '#f59e0b' : '#06b6d4';

  const critDelta = prevKpis ? (kpis.CRITICAL - prevKpis.CRITICAL) : null;
  const warnDelta = prevKpis ? (kpis.WARNING  - prevKpis.WARNING)  : null;

  const totalNodes = kpis.TOTAL_HOUSES || 3000;
  const onlinePct  = ((totalNodes - Math.floor(totalNodes * 0.018)) / totalNodes * 100).toFixed(1);

  const handleGovClick = useCallback((name) => {
    setSelectedGov(p => p === name ? null : name);
  }, []);

  const flyToAlert = useCallback((alert) => {
    const lon = alert.longitude ?? alert.coordinates?.[0];
    const lat = alert.latitude  ?? alert.coordinates?.[1];
    if (lon && lat) setViewState(v => ({ ...v, longitude: lon, latitude: lat, zoom: 11 }));
    setSelectedGov(alert.governorate);
  }, []);

  // Insight banner: highest_gov from riskByGov[0] (gold.gov_stats) — same source as Grafana bar chart
  const insight = useMemo(() => {
    // riskByGov[0] is the highest avg_risk_score governorate — same as leftmost bar in Grafana
    const topGov     = riskByGov[0]?.name    || '—';
    const topRisk    = riskByGov[0]?.avgRisk  ?? '—';
    const topLevel   = riskByGov[0]?.riskLevel || 'LOW';

    if (kpis.CRITICAL > 0) {
      return {
        text:  `CRITICAL: ${kpis.CRITICAL} nodes at risk. Highest cluster: ${topGov} (avg risk ${topRisk}). Immediate response required.`,
        color: 'text-rose-400',
        icon:  '🔴',
      };
    }
    if (kpis.WARNING > 5) {
      const elevatedCount = riskByGov.filter(g => g.avgRisk >= 8).length;
      return {
        text:  `WARNING: ${kpis.WARNING} nodes elevated. ${elevatedCount} governorate${elevatedCount !== 1 ? 's' : ''} above threshold. Highest: ${topGov} (avg risk ${topRisk}).`,
        color: 'text-amber-400',
        icon:  '🟡',
      };
    }
    return {
      text:  `STABLE: All 27 governorates within normal parameters. Avg risk ${kpis.avg_risk}/100. Highest: ${topGov} (${topRisk}).`,
      color: 'text-emerald-400',
      icon:  '🟢',
    };
  }, [kpis, riskByGov]);

  // Next refresh countdown
  const [countdown, setCountdown] = useState(REFRESH_MS / 1000);
  useEffect(() => {
    setCountdown(REFRESH_MS / 1000);
    const id = setInterval(() => setCountdown(c => c > 0 ? c - 1 : REFRESH_MS / 1000), 1000);
    return () => clearInterval(id);
  }, [lastFetch]);

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className="h-screen w-full bg-[#020a16] text-slate-300 flex flex-col overflow-hidden">

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .mono { font-family: 'JetBrains Mono', monospace !important; }
        @keyframes mPing  { 0%{transform:scale(0.5);opacity:0.9} 100%{transform:scale(2.6);opacity:0} }
        @keyframes liveDot{ 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.35;transform:scale(0.75)} }
        @keyframes scanFx {
          0%   { top:-80px; opacity:0.6 }
          50%  { opacity:0.3 }
          100% { top:100%;  opacity:0 }
        }
        @keyframes fadeSlideUp {
          from { opacity:0; transform:translateY(20px) scale(0.97); }
          to   { opacity:1; transform:translateY(0)    scale(1);    }
        }
        .panel { background:#05101d; border:1px solid rgba(20,50,90,0.6); border-radius:16px; overflow:hidden; }
        .ph { padding:9px 14px; border-bottom:1px solid rgba(20,50,90,0.6); background:rgba(2,8,18,0.6);
              display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }
        .ph-t { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:0.18em; color:#64748b; }
        .ld { width:6px; height:6px; border-radius:50%; animation:liveDot 2s ease-in-out infinite; }
        .scroll::-webkit-scrollbar { width:3px; }
        .scroll::-webkit-scrollbar-thumb { background:#1a3a60; border-radius:4px; }
        .mp .maplibregl-popup-content { background:transparent!important; padding:0!important; box-shadow:none!important; }
        .mp .maplibregl-popup-tip { display:none!important; }
      `}</style>

      {/* ── Top bar ─────────────────────────────────────────── */}
      <div className="shrink-0 flex items-center justify-between px-5 py-2.5 border-b border-slate-800/60 bg-[#02080f]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
            <ShieldAlert size={15} className="text-cyan-400" />
          </div>
          <div>
            <p className="text-[13px] font-black text-white uppercase tracking-widest leading-none">Smart City Gas & Air Safety</p>
            <p className="mono text-[9px] text-slate-500">DEPI · EGYPT · 27 GOVERNORATES · 3,000 NODES</p>
          </div>
        </div>

        <div className="flex items-center gap-5">
          {[
            { icon:<Wifi size={11} className="text-emerald-400"/>, label:'NODES ONLINE', val:onlinePct+'%', vc:'text-emerald-400' },
            { icon:<Radio size={11} className="text-cyan-400"/>,   label:'STREAM',       val:'LIVE',         vc:'text-cyan-400'   },
            { icon:<Cpu  size={11} className="text-blue-400"/>,    label:'REFRESH',      val:`${countdown}s`, vc:'text-blue-400'  },
          ].map(({ icon, label, val, vc }, i) => (
            <React.Fragment key={i}>
              {i > 0 && <div className="w-px h-6 bg-slate-700/60" />}
              <div className="flex items-center gap-2">
                {icon}
                <div>
                  <p className="mono text-[9px] text-slate-500 leading-none">{label}</p>
                  <p className={`mono text-[11px] font-bold leading-none ${vc}`}>{val}</p>
                </div>
              </div>
            </React.Fragment>
          ))}
          <div className="w-px h-6 bg-slate-700/60" />
          <div className="flex items-center gap-1.5">
            <span className="ld bg-emerald-400" />
            <span className="mono text-[11px] text-slate-400">{clock.toLocaleTimeString()}</span>
          </div>
          {selectedGov && (
            <button onClick={() => setSelectedGov(null)}
              className="ml-2 px-3 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/40 text-cyan-400 mono text-[9px] font-bold uppercase hover:bg-rose-500/10 hover:border-rose-500/40 hover:text-rose-400 transition-all">
              {selectedGov} ✕
            </button>
          )}
        </div>
      </div>

      {/* ── KPI row ─────────────────────────────────────────── */}
      <div className="shrink-0 grid grid-cols-4 gap-3 px-5 py-3">
        <KPICard title="Total Monitored Houses" value={kpis.TOTAL_HOUSES||3000}
          icon={<Target size={19}/>} color="cyan" subtitle="Online & Active" />
        <KPICard title="Critical Threats" value={kpis.CRITICAL||0}
          icon={<Flame size={19}/>} color="rose"
          subtitle={kpis.CRITICAL > 0 ? 'Immediate Action Required' : 'All Clear'}
          pulse delta={critDelta} />
        <KPICard title="Warning Signals" value={kpis.WARNING||0}
          icon={<AlertTriangle size={19}/>} color="amber"
          subtitle="Under Monitoring" delta={warnDelta} />
        <KPICard title="Grid Risk Level" value={Number(kpis.avg_risk||0).toFixed(1)}
          icon={<Activity size={19}/>} color="blue" subtitle="Avg risk score · scale 0-100" />
      </div>

      {/* ── Insight banner ───────────────────────────────────── */}
      <div className={`shrink-0 mx-5 mb-3 px-4 py-2 rounded-xl border flex items-center gap-2 ${
        kpis.CRITICAL > 0 ? 'border-rose-500/25 bg-rose-500/6'
        : kpis.WARNING > 5 ? 'border-amber-500/25 bg-amber-500/6'
        : 'border-emerald-500/25 bg-emerald-500/6'
      }`}>
        <Info size={13} className={insight.color} />
        <p className={`mono text-[10px] font-bold uppercase tracking-widest ${insight.color}`}>
          {insight.icon} {insight.text}
        </p>
      </div>

      {/* ── Main workspace ────────────────────────────────────── */}
      <div className="flex-1 flex gap-3 px-5 pb-3 min-h-0">

        {/* Left column */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">

          {/* Map */}
          <div className="flex-1 panel relative min-h-0">
            <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-2xl">
              <div className="absolute w-full"
                style={{ height:80, background:'linear-gradient(180deg,transparent 0%,rgba(6,182,212,0.06) 50%,transparent 100%)',
                  animation:'scanFx 6s linear infinite' }} />
            </div>

            <div className="ph relative z-10">
              <div className="flex items-center gap-2">
                <span className="ld bg-cyan-400" />
                <span className="ph-t">Live Topology Map — Egypt</span>
              </div>
              <div className="flex items-center gap-4 mono text-[9px] text-slate-500">
                {[['#f43f5e','Critical'],['#f59e0b','Warning'],['#10b981','Normal']].map(([c,l])=>(
                  <span key={l} className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full inline-block" style={{background:c}}/>
                    {l}
                  </span>
                ))}
              </div>
            </div>

            <div className="absolute inset-0 z-10" style={{top:38}}
              onClick={() => setHoverInfo(null)}>
              <Map {...viewState} onMove={e => setViewState(e.viewState)}
                mapLib={maplibregl} mapStyle={MAP_STYLE}
                style={{width:'100%',height:'100%'}} attributionControl={false} interactive>

                {mapData.map((d, i) => (
                  <Marker key={i} longitude={d.coordinates[0]} latitude={d.coordinates[1]} anchor="center">
                    <MapMarker
                      alertStatus={d.alert_status}
                      isFaded={!!selectedGov && selectedGov !== d.governorate}
                      onEnter={() => setHoverInfo(d)}
                      onLeave={() => setHoverInfo(null)}
                      onClick={e => { e?.stopPropagation?.(); handleGovClick(d.governorate); setHoverInfo(d); }}
                    />
                  </Marker>
                ))}

                {hoverInfo && (!selectedGov || hoverInfo.governorate === selectedGov) && (
                  <Popup longitude={hoverInfo.coordinates[0]} latitude={hoverInfo.coordinates[1]}
                    anchor="bottom" offset={20} closeButton={false} closeOnClick={false} className="mp">
                    <MapPopup d={hoverInfo} />
                  </Popup>
                )}
              </Map>
            </div>
          </div>

          {/* Bottom analytics row */}
          <div className="shrink-0 h-[205px] grid grid-cols-3 gap-3">

            {/* CH4 Trajectory — last 3 min, matches Grafana */}
            <div className="panel flex flex-col">
              <div className="ph">
                <span className="ph-t">CH4 Live Trajectory</span>
                <span className={`mono text-[9px] px-2 py-0.5 rounded border ${
                  latestMethane >= 150 ? 'text-rose-400 border-rose-500/40 bg-rose-500/10'
                  : latestMethane >= 50 ? 'text-amber-400 border-amber-500/40 bg-amber-500/10'
                  : 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10'
                }`}>
                  {latestMethane.toFixed(2)} ppm {methaneDir}
                </span>
              </div>
              <CH4Chart data={trendData} color={ch4Color} />
            </div>

            {/* Top Risk Governorates — ALL govs, colors match Grafana, tooltip shows only name + avgRisk */}
            <div className="panel flex flex-col">
              <div className="ph">
                <span className="ph-t">Risk by Governorate</span>
                <span className="mono text-[9px] text-slate-500">avg risk score · click to filter</span>
              </div>
              <div className="flex-1 p-1.5">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={riskByGov} margin={{top:8,right:4,left:-22,bottom:0}}>
                    <CartesianGrid strokeDasharray="2 6" stroke="#0d2540" vertical={false} />
                    <XAxis dataKey="name" tick={{fill:'#475569',fontSize:7}} axisLine={false} tickLine={false}
                      angle={-38} textAnchor="end" height={36} interval={0} />
                    <YAxis axisLine={false} tickLine={false} tick={{fill:'#334155',fontSize:8}} />
                    {/* Simple tooltip: only name + avgRisk — no extra info */}
                    <RechartsTooltip
                      cursor={{fill:'rgba(6,182,212,0.05)'}}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d   = payload[0].payload;
                        const col = d.barColor || '#32CD32';
                        return (
                          <div style={{
                            background: '#06101e',
                            border: `1px solid ${col}60`,
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '11px',
                            color: '#ffffff',
                            boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
                          }}>
                            <div style={{ fontWeight: 900, color: '#ffffff', marginBottom: '4px' }}>
                              {d.name}
                            </div>
                            <div style={{ color: col, fontWeight: 700 }}>
                              Avg Risk: {d.avgRisk}
                            </div>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="avgRisk" radius={[3,3,0,0]} cursor="pointer" maxBarSize={32}
                      onClick={d => handleGovClick(d.name)}>
                      {riskByGov.map((entry, i) => {
                        const col     = entry.barColor || '#32CD32';
                        const opacity = selectedGov ? (selectedGov === entry.name ? 1 : 0.18) : 1;
                        return (
                          <Cell key={i} fill={col} fillOpacity={opacity}
                            style={{ filter: opacity > 0.5 ? `drop-shadow(0 0 4px ${col}60)` : 'none' }} />
                        );
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Threat Distribution — fixed tooltip text color */}
            <div className="panel flex flex-col">
              <div className="ph">
                <span className="ph-t">Threat Distribution</span>
                <span className="mono text-[9px] text-slate-500">
                  {(((kpis.CRITICAL||0)+(kpis.WARNING||0))/(kpis.TOTAL_HOUSES||3000)*100).toFixed(1)}% affected
                </span>
              </div>
              <div className="flex-1">
                <AlertDonut kpis={kpis} />
              </div>
            </div>

          </div>
        </div>

        {/* Right: Incident Feed */}
        <div className="w-[370px] shrink-0 panel flex flex-col">
          <div className="ph">
            <div className="flex items-center gap-2">
              <span className="ld bg-rose-400" />
              <span className="ph-t">Active Incident Feed</span>
            </div>
            <div className="flex items-center gap-2">
              {selectedGov && (
                <span className="mono text-[9px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded">
                  {selectedGov}
                </span>
              )}
              <span className="mono text-[9px] text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded">
                {filteredAlerts.length} Events
              </span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 scroll">
            {filteredAlerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3">
                  <ShieldAlert size={20} className="text-emerald-400" />
                </div>
                <p className="mono text-[10px] font-bold text-emerald-400 uppercase tracking-widest">All Clear</p>
                <p className="mono text-[9px] text-slate-500 mt-1">
                  {selectedGov ? `No incidents in ${selectedGov}` : 'No active incidents'}
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {filteredAlerts.map((alert, i) => (
                  <IncidentCard key={i} alert={alert} onClick={flyToAlert} />
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* ── ARIA AI ChatBot ─────────────────────────────────── */}
      <ChatBot API_URL={API_URL} />

    </div>
  );
}
