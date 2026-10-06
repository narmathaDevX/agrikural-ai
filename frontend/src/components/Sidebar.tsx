import React from 'react';
import {
  LayoutDashboard,
  Bot,
  Mic,
  Cpu,
  LineChart,
  Bell,
  History,
  BookOpen,
  LogOut,
  Radio,
  Sprout,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout, isAdmin } = useAuth();
  const { isConnected, liveAlerts } = useWebSocket();

  const activeAlertsCount = liveAlerts.length;

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'assistant', label: 'AI Assistant', icon: Bot, badge: 'RAG' },
    { id: 'voice', label: 'Voice Studio', icon: Mic, badge: 'Voice' },
    { id: 'devices', label: 'IoT Devices', icon: Cpu },
    { id: 'analytics', label: 'Analytics', icon: LineChart },
    { id: 'alerts', label: 'Alerts', icon: Bell, count: activeAlertsCount },
    { id: 'history', label: 'History', icon: History },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen, adminOnly: true },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 min-h-screen">
      {/* Brand & Hardware status */}
      <div>
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-100 tracking-wide flex items-center gap-1.5">
                AGRIKURAL <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono font-medium">AI</span>
              </h1>
              <p className="text-xs text-slate-400">Agri IoT & Multilingual RAG</p>
            </div>
          </div>
        </div>

        {/* Live Hardware Gateway Indicator */}
        <div className="mx-4 mt-4 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Radio className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400 animate-pulse' : 'text-rose-400'}`} />
            <span className="text-slate-300 font-medium">Hardware Stream</span>
          </div>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
            isConnected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
          }`}>
            {isConnected ? 'LIVE WS' : 'OFFLINE'}
          </span>
        </div>

        {/* Navigation list */}
        <nav className="p-3 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-semibold">
                    {item.badge}
                  </span>
                )}
                {item.count !== undefined && item.count > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500 text-white font-bold">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User profile & Logout */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              {user?.full_name?.charAt(0) || 'F'}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || 'Farmer Account'}</p>
              <p className="text-[10px] text-slate-400 flex items-center gap-1">
                {isAdmin ? (
                  <span className="text-emerald-400 flex items-center gap-0.5">
                    <ShieldCheck className="w-3 h-3" /> Admin
                  </span>
                ) : (
                  'Farmer'
                )}
                <span>•</span>
                <span className="uppercase text-slate-400">{user?.preferred_language || 'TA'}</span>
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
