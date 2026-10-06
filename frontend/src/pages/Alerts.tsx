import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert, Filter, Clock } from 'lucide-react';
import { Alert } from '../types';
import { api } from '../services/api';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterResolved, setFilterResolved] = useState<boolean | undefined>(false);
  const [isLoading, setIsLoading] = useState(false);

  const loadAlerts = async () => {
    setIsLoading(true);
    try {
      const list = await api.getAlerts({
        severity: filterSeverity || undefined,
        isResolved: filterResolved,
      });
      setAlerts(list);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [filterSeverity, filterResolved]);

  const handleResolve = async (id: string) => {
    try {
      await api.resolveAlert(id);
      loadAlerts();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Agronomic Alert & Anomaly Engine
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time threshold breaches evaluated against verified university crop standards.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 text-xs">
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>

          <select
            value={filterResolved === undefined ? 'all' : filterResolved ? 'resolved' : 'active'}
            onChange={(e) => {
              const val = e.target.value;
              setFilterResolved(val === 'all' ? undefined : val === 'resolved');
            }}
            className="bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none"
          >
            <option value="active">Active Only</option>
            <option value="resolved">Resolved Only</option>
            <option value="all">All Alerts</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-200">No Alerts Found</h3>
            <p className="text-xs text-slate-400">All field sensors are operating safely within defined limits.</p>
          </div>
        ) : (
          alerts.map((a) => (
            <div
              key={a.id}
              className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition ${
                a.is_resolved
                  ? 'bg-slate-950/40 border-slate-800/60 opacity-60'
                  : a.severity === 'critical'
                  ? 'bg-rose-500/10 border-rose-500/30'
                  : 'bg-amber-500/10 border-amber-500/30'
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className={`w-5 h-5 shrink-0 mt-0.5 ${
                    a.severity === 'critical' ? 'text-rose-400' : 'text-amber-400'
                  }`}
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-slate-100">{a.title}</span>
                    <span
                      className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                        a.severity === 'critical'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {a.severity}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                      {a.device_id}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">{a.message}</p>
                  <div className="text-[10px] text-slate-500 mt-2 flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    <span>Triggered: {new Date(a.created_at).toLocaleString()}</span>
                    {a.resolved_at && (
                      <span className="text-emerald-400">
                        • Resolved: {new Date(a.resolved_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {!a.is_resolved && (
                <button
                  onClick={() => handleResolve(a.id)}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 shrink-0 transition"
                >
                  Mark Resolved
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
