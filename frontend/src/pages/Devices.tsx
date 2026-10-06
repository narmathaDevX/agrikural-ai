import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Plus,
  Radio,
  MapPin,
  Trash2,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
} from 'lucide-react';
import { Device } from '../types';
import { api } from '../services/api';

interface DevicesProps {
  onSelectDevice: (id: string) => void;
  onRefreshDevices: () => void;
}

export const Devices: React.FC<DevicesProps> = ({ onSelectDevice, onRefreshDevices }) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newDevice, setNewDevice] = useState({
    id: `AGRI-DEV-00${Math.floor(Math.random() * 90) + 10}`,
    name: 'Sector C - Coconut & Banana Grove',
    farm_name: 'Vaigai Agro Farms',
    location: 'Palakkad, Kerala',
    crop_type: 'Coconut',
    ip_address: '192.168.1.105',
    firmware_version: 'v2.4.1',
  });

  const loadDevices = async () => {
    setIsLoading(true);
    try {
      const list = await api.getDevices();
      setDevices(list);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();
  }, []);

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createDevice(newDevice);
      setShowAddModal(false);
      loadDevices();
      onRefreshDevices();
    } catch (err: any) {
      alert(`Registration error: ${err.message}`);
    }
  };

  const handleDeleteDevice = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to deactivate hardware gateway ${id}?`)) return;
    try {
      await api.deleteDevice(id);
      loadDevices();
      onRefreshDevices();
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-400" />
            IoT Hardware Gateway Management
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Registered microcontrollers, field gateways (ESP32-S3, LTE, REST / WS), and calibrated sensor arrays.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-md shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Device</span>
        </button>
      </div>

      {/* Devices Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {devices.map((dev) => (
          <div
            key={dev.id}
            onClick={() => onSelectDevice(dev.id)}
            className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-emerald-500/40 transition-all cursor-pointer flex flex-col justify-between group space-y-4 shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20">
                  {dev.id}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  ONLINE
                </span>
              </div>

              <h3 className="font-bold text-base text-slate-100 mt-3 group-hover:text-emerald-300 transition">
                {dev.name}
              </h3>

              <div className="mt-2 space-y-1 text-xs text-slate-400">
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  <span>{dev.location}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-slate-500" />
                  <span>Crop: <strong className="text-slate-300">{dev.crop_type}</strong></span>
                </div>
              </div>
            </div>

            {/* Sensors count & Firmware badge */}
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
              <span>{dev.sensors?.length || 5} Active Sensors</span>
              <span className="font-mono text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                {dev.firmware_version}
              </span>
              <button
                onClick={(e) => handleDeleteDevice(dev.id, e)}
                className="text-slate-500 hover:text-rose-400 transition p-1"
                title="Deactivate"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Device Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Plus className="w-4 h-4 text-emerald-400" /> Register Physical Hardware Gateway
            </h3>

            <form onSubmit={handleCreateDevice} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 font-semibold block mb-1">Device ID</label>
                <input
                  type="text"
                  required
                  value={newDevice.id}
                  onChange={(e) => setNewDevice({ ...newDevice, id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Station Name</label>
                <input
                  type="text"
                  required
                  value={newDevice.name}
                  onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Crop Type</label>
                  <input
                    type="text"
                    required
                    value={newDevice.crop_type}
                    onChange={(e) => setNewDevice({ ...newDevice, crop_type: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Location</label>
                  <input
                    type="text"
                    required
                    value={newDevice.location}
                    onChange={(e) => setNewDevice({ ...newDevice, location: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition"
                >
                  Register Gateway
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
