import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Droplets,
  Thermometer,
  CloudRain,
  Sun,
  Waves,
  Calendar,
  Layers,
} from 'lucide-react';
import { Device } from '../types';
import { api } from '../services/api';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

interface AnalyticsProps {
  device: Device | null;
}

export const Analytics: React.FC<AnalyticsProps> = ({ device }) => {
  const [selectedSensor, setSelectedSensor] = useState('soil_moisture');
  const [selectedRange, setSelectedRange] = useState('24h');
  const [data, setData] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [isLoading, setIsLoading] = useState(false);

  const deviceId = device?.id || 'AGRI-DEV-001';

  const sensorTypes = [
    { id: 'soil_moisture', label: 'Soil Moisture', unit: '%', color: '#06b6d4', icon: Droplets },
    { id: 'temperature', label: 'Temperature', unit: '°C', color: '#f59e0b', icon: Thermometer },
    { id: 'humidity', label: 'Humidity', unit: '%', color: '#3b82f6', icon: CloudRain },
    { id: 'light_lux', label: 'Solar Lux', unit: 'lux', color: '#eab308', icon: Sun },
    { id: 'water_level_pct', label: 'Tank Water Level', unit: '%', color: '#6366f1', icon: Waves },
  ];

  const timeRanges = [
    { id: '1h', label: '1 Hour' },
    { id: '6h', label: '6 Hours' },
    { id: '24h', label: '24 Hours' },
    { id: '7d', label: '7 Days' },
    { id: '30d', label: '30 Days' },
  ];

  const currentSensorInfo = sensorTypes.find((s) => s.id === selectedSensor) || sensorTypes[0];

  useEffect(() => {
    async function fetchAnalytics() {
      setIsLoading(true);
      try {
        const res = await api.getTimeseries(deviceId, selectedSensor, selectedRange);
        setData(res.data || []);
        setStats(res.stats || {});
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    }
    fetchAnalytics();
  }, [deviceId, selectedSensor, selectedRange]);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Controls Bar */}
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <LineChart className="w-5 h-5 text-emerald-400" />
            Field Telemetry & Historical Trends
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Timeseries agronomic analysis for {device?.name || 'Greenhouse Sector A'} ({device?.crop_type || 'Tomato'})
          </p>
        </div>

        {/* Range Buttons */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800 text-xs">
          {timeRanges.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelectedRange(r.id)}
              className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                selectedRange === r.id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sensor Metric Selector Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {sensorTypes.map((s) => {
          const Icon = s.icon;
          const isSelected = selectedSensor === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setSelectedSensor(s.id)}
              className={`p-3.5 rounded-xl border text-left transition flex items-center gap-3 ${
                isSelected
                  ? 'bg-slate-800 border-emerald-500/50 shadow-sm'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ backgroundColor: `${s.color}20`, color: s.color }}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="overflow-hidden">
                <div className="text-xs font-semibold text-slate-200 truncate">{s.label}</div>
                <div className="text-[10px] text-slate-400 font-mono">Unit: {s.unit}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Latest Value</span>
          <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">
            {stats.current !== undefined ? stats.current : '--'}{' '}
            <span className="text-xs font-normal text-slate-400">{currentSensorInfo.unit}</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Average (Mean)</span>
          <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">
            {stats.avg !== undefined ? stats.avg : '--'}{' '}
            <span className="text-xs font-normal text-slate-400">{currentSensorInfo.unit}</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Period Minimum</span>
          <div className="text-2xl font-bold text-rose-400 mt-1 font-mono">
            {stats.min !== undefined ? stats.min : '--'}{' '}
            <span className="text-xs font-normal text-slate-400">{currentSensorInfo.unit}</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Period Maximum</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
            {stats.max !== undefined ? stats.max : '--'}{' '}
            <span className="text-xs font-normal text-slate-400">{currentSensorInfo.unit}</span>
          </div>
        </div>
      </div>

      {/* Interactive Main Graph */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="font-bold text-slate-100 text-sm">
              {currentSensorInfo.label} Timeseries Curve ({selectedRange})
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Continuously logged via FastAPI hardware gateway into PostgreSQL
            </p>
          </div>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="metricGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentSensorInfo.color} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={currentSensorInfo.color} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time_label" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} unit={currentSensorInfo.unit} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={currentSensorInfo.color}
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#metricGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
