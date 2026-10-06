import React from 'react';
import { Languages, Database, RefreshCw } from 'lucide-react';
import { Device } from '../types';

interface HeaderProps {
  devices: Device[];
  selectedDeviceId: string;
  onSelectDevice: (id: string) => void;
  selectedLanguage: string;
  onSelectLanguage: (lang: string) => void;
  onRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  devices,
  selectedDeviceId,
  onSelectDevice,
  selectedLanguage,
  onSelectLanguage,
  onRefresh,
}) => {
  const currentDevice = devices.find((d) => d.id === selectedDeviceId);

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-4">
        {/* Device Station Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-400">Active Field Unit:</span>
          <select
            value={selectedDeviceId}
            onChange={(e) => onSelectDevice(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.crop_type})
              </option>
            ))}
          </select>
        </div>

        {currentDevice && (
          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400 border-l border-slate-800 pl-4">
            <span>Crop: <strong className="text-slate-200">{currentDevice.crop_type}</strong></span>
            <span>•</span>
            <span>Location: <span className="text-slate-300">{currentDevice.location}</span></span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Language Override / Indicator */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-lg p-1 text-xs">
          <Languages className="w-3.5 h-3.5 text-emerald-400 ml-1.5" />
          <button
            onClick={() => onSelectLanguage('ta')}
            className={`px-2 py-1 rounded font-medium transition ${
              selectedLanguage === 'ta' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            தமிழ்
          </button>
          <button
            onClick={() => onSelectLanguage('ml')}
            className={`px-2 py-1 rounded font-medium transition ${
              selectedLanguage === 'ml' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            മലയാളം
          </button>
          <button
            onClick={() => onSelectLanguage('en')}
            className={`px-2 py-1 rounded font-medium transition ${
              selectedLanguage === 'en' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            EN
          </button>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            title="Refresh Farm Data"
            className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>
    </header>
  );
};
