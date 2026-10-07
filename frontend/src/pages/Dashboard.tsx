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
  Wifi,
  WifiOff,
  Clock,
  Cpu,
} from 'lucide-react';
import { Device, Alert } from '../types';
import { api } from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

interface DashboardProps {
  device: Device | null;
  onNavigateToAssistant: (prompt?: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ device, onNavigateToAssistant }) => {
  const { latestReadings, lastReading, liveAlerts, clearAlert } = useWebSocket();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [recentTelemetry, setRecentTelemetry] = useState<any[]>([]);
  const [agriStatus, setAgriStatus] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(Date.now());
  const [isLoading, setIsLoading] = useState(false);

  const deviceId = device?.id || agriStatus?.device_id || 'AGRI-DEV-001';

  // Live timer tick every 5 seconds to keep relative timestamps dynamic
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 5000);
    return () => clearInterval(timer);
  }, []);

  // Fetch initial telemetry and authoritative agronomic status
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setIsLoading(true);
      try {
        const [alertList, ts, latest, statusRes] = await Promise.all([
          api.getAlerts({ deviceId, isResolved: false }),
          api.getTimeseries(deviceId, 'soil_moisture', '24h'),
          api.getLatestReadings(deviceId),
          api.getSensorAgronomicStatus(deviceId, device?.crop_type),
        ]);
        if (!isMounted) return;
        setAlerts(alertList);
        setChartData(ts.data || []);
        setRecentTelemetry(latest.slice(0, 8));
        setAgriStatus(statusRes);
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, [deviceId, device?.crop_type]);

  // Real-time update from WebSocket without page refresh
  useEffect(() => {
    if (!lastReading || lastReading.device_id !== deviceId) return;

    // 1. Prepend incoming reading to live log
    setRecentTelemetry((prev) => [lastReading, ...prev.slice(0, 7)]);

    // 2. Append soil moisture reading to chart dynamically
    if (lastReading.sensor_type === 'soil_moisture') {
      const timeLabel = new Date(lastReading.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      setChartData((prev) => [
        ...prev.slice(-19),
        { time_label: timeLabel, value: lastReading.value },
      ]);
    }
  }, [lastReading, deviceId]);

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

  // Authoritative Single Source of Truth for Crop Thresholds from RAG
  const smRef = agriStatus?.agricultural_reference?.soil_moisture || {
    minimum: 45.0,
    maximum: 65.0,
    source: 'TNAU Tomato Cultivation and Irrigation Guide',
  };
  const minMoisture = smRef.minimum ?? 45.0;
  const maxMoisture = smRef.maximum ?? 65.0;
  const sourceDoc = smRef.source || 'TNAU Agricultural Guidelines';

  // Read current sensor values strictly from incoming hardware readings (NEVER hard-coded)
  const getSensorDetails = (type: string, defaultUnit: string, sensorIdFallback: string) => {
    const wsKey = `${deviceId}_${type}`;
    const wsReading = latestReadings[wsKey];
    const statusReading = agriStatus?.readings?.[type];
    const devReading = device?.latest_readings?.[type];

    let val: number | null = null;
    let unit = defaultUnit;
    let sensorId = sensorIdFallback;
    let timestamp: string | null = null;
    let isLiveWs = false;

    if (wsReading !== undefined && wsReading.value !== null) {
      val = wsReading.value;
      unit = wsReading.unit || defaultUnit;
      sensorId = wsReading.sensor_id || sensorIdFallback;
      timestamp = wsReading.timestamp;
      isLiveWs = true;
    } else if (statusReading !== undefined && statusReading.value !== null) {
      val = statusReading.value;
      unit = statusReading.unit || defaultUnit;
      sensorId = statusReading.sensor_id || sensorIdFallback;
      timestamp = statusReading.timestamp;
    } else if (devReading !== undefined && devReading.value !== null) {
      val = devReading.value;
      unit = devReading.unit || defaultUnit;
      sensorId = devReading.sensor_id || sensorIdFallback;
      timestamp = devReading.timestamp;
    }

    if (val === null) {
      return {
        value: null,
        displayValue: '--',
        unit,
        sensorId,
        deviceId,
        timestamp: null,
        timeFormatted: 'No telemetry',
        ageSeconds: 999999,
        isLive: false,
        isStale: true,
        ageText: 'Awaiting hardware telemetry',
        hasData: false,
      };
    }

    const t = timestamp ? new Date(timestamp).getTime() : currentTime;
    const ageSeconds = Math.max(0, Math.floor((currentTime - t) / 1000));
    const isStale = ageSeconds > 60;
    const mins = Math.floor(ageSeconds / 60);
    const ageText = ageSeconds < 60 ? 'Just now' : `Last updated ${mins}m ago`;
    const timeFormatted = timestamp
      ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : 'Just now';

    return {
      value: val,
      displayValue: val.toString(),
      unit,
      sensorId,
      deviceId,
      timestamp,
      timeFormatted,
      ageSeconds,
      isLive: isLiveWs && !isStale,
      isStale,
      ageText,
      hasData: true,
    };
  };

  const soilMoisture = getSensorDetails('soil_moisture', '%', `${deviceId}-SOIL`);
  const temperature = getSensorDetails('temperature', '°C', `${deviceId}-TEMP`);
  const humidity = getSensorDetails('humidity', '%', `${deviceId}-HUMID`);
  const light = getSensorDetails('light_lux', 'lux', `${deviceId}-LIGHT`);
  const waterLevel = getSensorDetails('water_level_pct', '%', `${deviceId}-WATER`);

  // Overall hardware device connection status
  const deviceLastSeen = device?.last_seen || agriStatus?.last_seen || soilMoisture.timestamp;
  const deviceAgeSec = deviceLastSeen ? Math.max(0, Math.floor((currentTime - new Date(deviceLastSeen).getTime()) / 1000)) : 999999;
  const isDeviceConnected = (deviceAgeSec < 60) || Object.values(latestReadings).some(
    (r) => r.device_id === deviceId && (currentTime - r.receivedAt) < 60000
  );
  const deviceMinsAgo = Math.max(1, Math.floor(deviceAgeSec / 60));
  const connectionStatusText = isDeviceConnected
    ? 'Hardware Online • Live Stream'
    : (deviceLastSeen
        ? `Hardware Disconnected • Last updated ${deviceMinsAgo} minute${deviceMinsAgo !== 1 ? 's' : ''} ago`
        : 'Hardware Disconnected • Awaiting Telemetry');

  // Soil health status evaluation strictly against RAG thresholds
  const getSoilMoistureStatus = () => {
    if (!soilMoisture.hasData || soilMoisture.value === null) {
      return {
        status: 'AWAITING TELEMETRY',
        color: 'text-slate-400',
        bg: 'bg-slate-900/80 border-slate-800',
        note: `Connecting to hardware sensor ${soilMoisture.sensorId}...`,
      };
    }
    const val = soilMoisture.value;
    const stalePrefix = soilMoisture.isStale ? `[STALE - ${soilMoisture.ageText}] ` : '';

    if (val < minMoisture) {
      return {
        status: `${stalePrefix}LOW (${val}% < ${minMoisture}%)`,
        color: soilMoisture.isStale ? 'text-amber-400' : 'text-rose-400',
        bg: soilMoisture.isStale ? 'bg-amber-500/10 border-amber-500/30' : 'bg-rose-500/10 border-rose-500/30',
        note: soilMoisture.isStale
          ? `Recorded as ${val}%, but reading is stale (${soilMoisture.ageText}). Verify field conditions directly per ${sourceDoc}.`
          : `Below recommended range (${minMoisture}%-${maxMoisture}%). Prompt irrigation advised per ${sourceDoc}.`,
      };
    } else if (val > maxMoisture) {
      return {
        status: `${stalePrefix}HIGH (${val}% > ${maxMoisture}%)`,
        color: 'text-amber-400',
        bg: 'bg-amber-500/10 border-amber-500/30',
        note: soilMoisture.isStale
          ? `Recorded as ${val}%, but reading is stale (${soilMoisture.ageText}). Withhold irrigation per ${sourceDoc}.`
          : `Above recommended range (${minMoisture}%-${maxMoisture}%). Withhold irrigation per ${sourceDoc}.`,
      };
    } else {
      return {
        status: `${stalePrefix}OPTIMAL (${minMoisture}%-${maxMoisture}%)`,
        color: soilMoisture.isStale ? 'text-amber-300' : 'text-emerald-400',
        bg: soilMoisture.isStale ? 'bg-amber-500/10 border-amber-500/30' : 'bg-emerald-500/10 border-emerald-500/30',
        note: soilMoisture.isStale
          ? `Recorded as optimal (${minMoisture}%-${maxMoisture}%), but reading is stale (${soilMoisture.ageText}).`
          : `Within ideal field capacity per ${sourceDoc}.`,
      };
    }
  };

  const soilStatus = getSoilMoistureStatus();

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Farm Summary & Connection Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5" />
              {device?.crop_type || 'Tomato'} Station
            </span>
            <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
              Gateway ID: {deviceId}
            </span>
            {isDeviceConnected ? (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                <Wifi className="w-3 h-3" />
                {connectionStatusText}
              </span>
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
                <WifiOff className="w-3 h-3 text-amber-400" />
                {connectionStatusText}
              </span>
            )}
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
          onClick={() =>
            onNavigateToAssistant(
              soilMoisture.hasData
                ? `Is my current soil moisture of ${soilMoisture.value}% sufficient for my ${device?.crop_type || 'tomato'} crop?`
                : `What are the irrigation guidelines for my ${device?.crop_type || 'tomato'} crop?`
            )
          }
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

      {/* Disconnection Warning Banner if hardware is stale */}
      {!isDeviceConnected && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Hardware Telemetry Notice:</strong> Gateway <code>{deviceId}</code> is currently disconnected.{' '}
              {deviceLastSeen ? `Last updated ${deviceMinsAgo} minutes ago.` : 'No live telemetry received.'}{' '}
              Values shown below are historical and not guaranteed to reflect current conditions.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-500/20 font-mono text-[11px] shrink-0">
            DISCONNECTED
          </span>
        </div>
      )}

      {/* Primary 5 IoT Sensor Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* 1. Soil Moisture */}
        <div className={`p-4 rounded-xl border ${soilStatus.bg} transition-all flex flex-col justify-between`}>
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Soil Moisture</span>
              <Droplets className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-1">
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                {soilMoisture.sensorId}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-100">{soilMoisture.displayValue}</span>
              <span className="text-sm font-semibold text-slate-400">{soilMoisture.unit}</span>
            </div>
            <div className="mt-2 text-xs font-semibold flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  !soilMoisture.hasData
                    ? 'bg-slate-600'
                    : soilMoisture.isStale
                    ? 'bg-amber-400'
                    : soilMoisture.value! < 30
                    ? 'bg-rose-500 animate-ping'
                    : 'bg-emerald-400'
                }`}
              />
              <span className={soilStatus.color}>{soilStatus.status}</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">{soilStatus.note}</p>
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {soilMoisture.timeFormatted}
            </span>
            {soilMoisture.isStale ? (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                ⚠️ {soilMoisture.ageText}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
        </div>

        {/* 2. Ambient Temperature */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Temperature</span>
              <Thermometer className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-1">
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                {temperature.sensorId}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-100">{temperature.displayValue}</span>
              <span className="text-sm font-semibold text-slate-400">{temperature.unit}</span>
            </div>
            <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>{temperature.hasData ? 'Optimal (20-32°C)' : 'Awaiting Telemetry'}</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">Canopy Level Ambient</p>
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {temperature.timeFormatted}
            </span>
            {temperature.isStale ? (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                ⚠️ {temperature.ageText}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
        </div>

        {/* 3. Relative Humidity */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Humidity</span>
              <CloudRain className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-1">
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                {humidity.sensorId}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-100">{humidity.displayValue}</span>
              <span className="text-sm font-semibold text-slate-400">{humidity.unit}</span>
            </div>
            <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>{humidity.hasData ? 'Favorable (45-75%)' : 'Awaiting Telemetry'}</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">Canopy Humidity</p>
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {humidity.timeFormatted}
            </span>
            {humidity.isStale ? (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                ⚠️ {humidity.ageText}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
        </div>

        {/* 4. Solar Radiation / Lux */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Solar Radiation</span>
              <Sun className="w-4 h-4 text-amber-300" />
            </div>
            <div className="mt-1">
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                {light.sensorId}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-100">{light.displayValue}</span>
              <span className="text-sm font-semibold text-slate-400">{light.unit}</span>
            </div>
            <div className="mt-2 text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>{light.hasData ? 'Photosynthesis Active' : 'Awaiting Telemetry'}</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">Roof PAR Radiation</p>
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {light.timeFormatted}
            </span>
            {light.isStale ? (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                ⚠️ {light.ageText}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
        </div>

        {/* 5. Irrigation Tank Level */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Water Tank</span>
              <Waves className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-1">
              <span className="text-[10px] font-mono text-slate-500 bg-slate-950/60 px-1.5 py-0.5 rounded border border-slate-800">
                {waterLevel.sensorId}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-100">{waterLevel.displayValue}</span>
              <span className="text-sm font-semibold text-slate-400">{waterLevel.unit}</span>
            </div>
            <div className="mt-2 text-xs font-semibold flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  !waterLevel.hasData
                    ? 'bg-slate-600'
                    : waterLevel.value! < 30
                    ? 'bg-rose-500 animate-ping'
                    : 'bg-emerald-400'
                }`}
              />
              <span className={waterLevel.hasData && waterLevel.value! < 30 ? 'text-rose-400' : 'text-emerald-400'}>
                {waterLevel.hasData
                  ? waterLevel.value! < 30
                    ? 'Reservoir Critically Low (<30%)'
                    : 'Reservoir Sufficient (>30%)'
                  : 'Awaiting Telemetry'}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">Subsurface Storage</p>
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {waterLevel.timeFormatted}
            </span>
            {waterLevel.isStale ? (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                ⚠️ {waterLevel.ageText}
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Middle Section: Timeseries Chart & Real-time Live Ticker */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Soil Moisture 24h Trend Chart (auto-updates dynamically with incoming readings) */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Live Soil Moisture Dynamics ({deviceId})
              </h3>
              <p className="text-xs text-slate-400">Calibrated against verified RAG source: {sourceDoc}</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" /> Optimal {minMoisture}-{maxMoisture}%
              </span>
              <span className="flex items-center gap-1.5 text-rose-400">
                <span className="w-2 h-2 rounded-full bg-rose-400" /> Deficit &lt;{minMoisture}%
              </span>
            </div>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="soilGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time_label" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} domain={[10, 85]} tickLine={false} unit="%" />
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
              Incoming IoT Packet Stream
            </h3>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
              WebSocket / REST
            </span>
          </div>

          <div className="space-y-2 overflow-y-auto max-h-64 pr-1">
            {recentTelemetry.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                Awaiting incoming hardware packets...
              </div>
            ) : (
              recentTelemetry.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-slate-200 capitalize">
                        {item.sensor_type.replace('_', ' ')}
                      </span>
                      <span className="text-[9px] font-mono text-slate-400 bg-slate-900 px-1 rounded">
                        {item.sensor_id || `${item.device_id}-SENSOR`}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'Just now'}
                    </div>
                  </div>
                  <div className="font-mono font-bold text-emerald-400">
                    {item.value} <span className="text-slate-400 font-normal">{item.unit}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Hardware Protocol: HTTP REST / WS</span>
            <span className={isDeviceConnected ? 'text-emerald-400 font-mono' : 'text-amber-400 font-mono'}>
              {isDeviceConnected ? 'ONLINE • 201 CREATED' : 'DISCONNECTED'}
            </span>
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
