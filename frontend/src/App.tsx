import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Assistant } from './pages/Assistant';
import { VoiceStudio } from './pages/VoiceStudio';
import { Devices } from './pages/Devices';
import { Analytics } from './pages/Analytics';
import { Alerts } from './pages/Alerts';
import { History } from './pages/History';
import { Knowledge } from './pages/Knowledge';
import { Login } from './pages/Login';
import { Device } from './types';
import { api } from './services/api';

const AppContent: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('AGRI-DEV-001');
  const [selectedLanguage, setSelectedLanguage] = useState('ta');
  const [assistantPrompt, setAssistantPrompt] = useState<string | undefined>(undefined);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDevices(list);
      if (list.length > 0 && !list.find((d) => d.id === selectedDeviceId)) {
        setSelectedDeviceId(list[0].id);
      }
    } catch (err) {
      console.warn('Failed to fetch devices', err);
    }
  };

  useEffect(() => {
    if (user) {
      loadDevices();
    }
  }, [user]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-emerald-400 font-mono text-sm">
        Initializing Agrikural AI System...
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const selectedDevice = devices.find((d) => d.id === selectedDeviceId) || devices[0] || null;

  const handleNavigateToAssistant = (prompt?: string) => {
    setAssistantPrompt(prompt);
    setActiveTab('assistant');
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          devices={devices}
          selectedDeviceId={selectedDeviceId}
          onSelectDevice={setSelectedDeviceId}
          selectedLanguage={selectedLanguage}
          onSelectLanguage={setSelectedLanguage}
          onRefresh={loadDevices}
        />

        <main className="flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <Dashboard
              device={selectedDevice}
              onNavigateToAssistant={handleNavigateToAssistant}
            />
          )}
          {activeTab === 'assistant' && (
            <Assistant
              device={selectedDevice}
              initialPrompt={assistantPrompt}
            />
          )}
          {activeTab === 'voice' && (
            <VoiceStudio device={selectedDevice} />
          )}
          {activeTab === 'devices' && (
            <Devices
              onSelectDevice={(id) => {
                setSelectedDeviceId(id);
                setActiveTab('dashboard');
              }}
              onRefreshDevices={loadDevices}
            />
          )}
          {activeTab === 'analytics' && (
            <Analytics device={selectedDevice} />
          )}
          {activeTab === 'alerts' && <Alerts />}
          {activeTab === 'history' && <History />}
          {activeTab === 'knowledge' && <Knowledge />}
        </main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <AppContent />
      </WebSocketProvider>
    </AuthProvider>
  );
}

export default App;
