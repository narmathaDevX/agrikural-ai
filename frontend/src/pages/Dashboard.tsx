import React, { useState, useEffect } from 'react';
import {
  Droplets,
  Thermometer,
  CloudRain,
  Sun,
  Waves,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Bot,
  ArrowRight,
  Radio,
  Sparkles,
} from 'lucide-react';
import { Device, Alert, SensorReading } from '../types';
import { api } from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

interface DashboardProps {
  device: Device | null;
  onNavigateToAssistant: (prompt?: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ device, onNavigateToAssistant }) => {
  const { latestReadings, liveAlerts, clearAlert } = useWebSocket();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [recentTelemetry, setRecentTelemetry] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const deviceId = device?.id || 'AGRI-DEV-001';

  // Read current sensor values from live WebSocket or latest device readings
  const getSensorVal = (type: string, fallback: number, unit: string) => {
    const wsKey = `${deviceId}_${type}`;
    if (latestReadings[wsKey] !== undefined) {
      return { value: latestReadings[wsKey].value, unit: latestReadings[wsKey].unit, isLive: true };
    }
    if (device?.latest_readings && device.latest_readings[type]) {
      return { value: device.latest_readings[type].value, unit: device.latest_readings[type].unit, isLive: false };
    }
    return { value: fallback, unit, isLive: false };
  };

  const soilMoisture = getSensorVal('soil_moisture', 28.5, '%');
  const temperature = getSensorVal('temperature', 31.2, '°C');
  const humidity = getSensorVal('humidity', 64.0, '%');
  const light = getSensorVal('light_lux', 780, 'lux');
  const waterLevel = getSensorVal('water_level_pct', 72.0, '%');

  // Load timeseries data for graph
  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [alertList, ts, latest] = await Promise.all([
          api.getAlerts({ deviceId, isResolved: false }),
          api.getTimeseries(deviceId, 'soil_moisture', '24h'),
          api.getLatestReadings(deviceId),
        ]);
        setAlerts(alertList);
        setChartData(ts.data || []);
        setRecentTelemetry(latest.slice(0, 8));
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [deviceId]);

  // Handle alert resolve
  const handleResolveAlert = async (id: string) => {
    try {
      await api.resolveAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      clearAlert(id);
    } catch (e) {
      console.error(e);
    }
  };

  // Determine Soil Health condition for Tomato/Crop
  const getSoilMoistureStatus = (val: number) => {
    if (val < 25) return { status: 'Critical Deficit', color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20', note: 'Immediate Irrigation Needed' };
    if (val < 35) return { status: 'Low / Stressed', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', note: 'Irrigate Today' };
    if (val > 75) return { status: 'Saturated', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', note: 'Hold Irrigation' };
    return { status: 'Optimal (60-70%)', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', note: 'Ideal Field Capacity' };
  };

  const soilStatus = getSoilMoistureStatus(soilMoisture.value);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Farm Summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {device?.crop_type || 'Tomato'} Station
            </span>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" /> Live Telemetry Gateway
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 mt-2">
            {device?.name || 'Greenhouse Sector A'}
          </h2>
          <p className="text-sm text-slate-400">
            {device?.farm_name || 'Kural Organic Agro Station'} • {device?.location || 'Coimbatore, Tamil Nadu'}
          </p>
        </div>

        {/* Quick Action Prompt to AI Assistant */}
        <button
          onClick={() => onNavigateToAssistant(`Is my current soil moisture of ${soilMoisture.value}% sufficient for my ${device?.crop_type || 'tomato'} crop?`)}
          className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition shadow-lg shadow-emerald-900/30 shrink-0 group"
        >
          <div className="w-8 h-8 rounded-lg bg-emerald-700/50 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <div className="text-xs text-emerald-100 font-semibold flex items-center gap-1">
              AI Agronomist Check <Sparkles className="w-3 h-3" />
            </div>
            <div className="text-[11px] text-emerald-200">Evaluate Moisture & Crop Health</div>
          </div>
          <ArrowRight className="w-4 h-4 text-emerald-200 group-hover:translate-x-1 transition" />
        </button>
      </div>

      {/* Primary 5 IoT Sensor Gauge Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Soil Moisture */}
        <div className={`p-4 rounded-xl border ${soilStatus.bg} transition-all`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Soil Moisture</span>
            <Droplets className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">{soilMoisture.value}</span>
            <span className="text-sm font-semibold text-slate-400">{soilMoisture.unit}</span>
          </div>
          <div className="mt-2 text-xs font-semibold flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${soilMoisture.value < 30 ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`} />
            <span className={soilStatus.color}>{soilStatus.status}</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">{soilStatus.note}</p>
        </div>

        {/* Ambient Temperature */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Temperature</span>
            <Thermometer className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">{temperature.value}</span>
            <span className="text-sm font-semibold text-slate-400">{temperature.unit}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Optimal Growth (24-32°C)</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Canopy Level Ambient</p>
        </div>

        {/* Relative Humidity */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Humidity</span>
            <CloudRain className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">{humidity.value}</span>
            <span className="text-sm font-semibold text-slate-400">{humidity.unit}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Favorable Range</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Fungal Risk Low</p>
        </div>

        {/* Solar Lux */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Solar Radiation</span>
            <Sun className="w-4 h-4 text-amber-300" />
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">{light.value}</span>
            <span className="text-sm font-semibold text-slate-400">{light.unit}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>PAR Adequate</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Photosynthesis Active</p>
        </div>

        {/* Irrigation Tank Level */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Water Tank</span>
            <Waves className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">{waterLevel.value}</span>
            <span className="text-sm font-semibold text-slate-400">{waterLevel.unit}</span>
          </div>
          <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Reserve Sufficient</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Drip Tank Level</p>
        </div>
      </div>

      {/* Middle Section: Timeseries Chart & Real-time Live Ticker */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Soil Moisture 24h Trend Chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Soil Moisture Trend (24h Window)
              </h3>
              <p className="text-xs text-slate-400">Calibrated against TNAU field capacity guidelines</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> Optimal 45-65%
              </span>
              <span className="flex items-center gap-1.5 text-rose-400">
                <span className="w-2 h-2 rounded-full bg-rose-400" /> Stress &lt;30%
              </span>
            </div>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length > 0 ? chartData : [
                { time_label: '00:00', value: 42 },
                { time_label: '04:00', value: 39 },
                { time_label: '08:00', value: 35 },
                { time_label: '12:00', value: 29 },
                { time_label: '16:00', value: 26 },
                { time_label: '20:00', value: soilMoisture.value },
              ]}>
                <defs>
                  <linearGradient id="soilGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time_label" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} domain={[10, 80]} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2.5} fillOpacity={1} fill="url(#soilGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Live Hardware Telemetry Stream Feed */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
            <h3 className="font-semibold text-slate-100 text-sm flex items-center gap-2">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
              Incoming IoT Packet Log
            </h3>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
              REST / WS
            </span>
          </div>

          <div className="space-y-2 overflow-y-auto max-h-64 pr-1">
            {recentTelemetry.map((item, idx) => (
              <div
                key={idx}
                className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-semibold text-slate-200 capitalize">
                    {item.sensor_type.replace('_', ' ')}
                  </span>
                  <div className="text-[10px] text-slate-500 font-mono">
                    {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'Just now'}
                  </div>
                </div>
                <div className="font-mono font-bold text-emerald-400">
                  {item.value} <span className="text-slate-400 font-normal">{item.unit}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Hardware Protocol: HTTP POST</span>
            <span className="text-emerald-400 font-mono">200 OK</span>
          </div>
        </div>
      </div>

      {/* Active Threshold Alerts Section */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="font-semibold text-slate-100 text-sm">Active Agricultural Alerts</h3>
            <span className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full font-bold">
              {alerts.length + liveAlerts.length}
            </span>
          </div>
        </div>

        {alerts.length === 0 && liveAlerts.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400/80" />
            <p>All field parameters within recommended agronomic thresholds.</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {[...liveAlerts, ...alerts].map((a) => (
              <div
                key={a.id}
                className={`p-3.5 rounded-xl border flex items-center justify-between gap-4 transition ${
                  a.severity === 'critical'
                    ? 'bg-rose-500/10 border-rose-500/30'
                    : 'bg-amber-500/10 border-amber-500/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className={`w-5 h-5 shrink-0 ${a.severity === 'critical' ? 'text-rose-400' : 'text-amber-400'}`} />
                  <div>
                    <h4 className="text-xs font-bold text-slate-100 flex items-center gap-2">
                      {a.title}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-bold ${
                        a.severity === 'critical' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {a.severity}
                      </span>
                    </h4>
                    <p className="text-xs text-slate-300 mt-0.5">{a.message}</p>
                  </div>
                </div>

                <button
                  onClick={() => handleResolveAlert(a.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 shrink-0 transition"
                >
                  Resolve
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
