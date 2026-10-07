import {
  User,
  Device,
  SensorReading,
  Alert,
  RAGQueryResponse,
  DocumentItem,
  Conversation,
} from '../types';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('agrikural_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeader(),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errorMsg;
    } catch (_) {}
    throw new Error(errorMsg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    return request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  },

  async register(data: { email: string; password: string; full_name: string; role?: string; preferred_language?: string }): Promise<{ access_token: string; user: User }> {
    return request('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  async getMe(): Promise<User> {
    return request('/auth/me');
  },

  // Devices
  async getDevices(): Promise<Device[]> {
    return request('/devices');
  },

  async getDevice(id: string): Promise<Device> {
    return request(`/devices/${id}`);
  },

  async createDevice(device: Partial<Device>): Promise<Device> {
    return request('/devices', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(device),
    });
  },

  async deleteDevice(id: string): Promise<void> {
    return request(`/devices/${id}`, { method: 'DELETE' });
  },

  // Sensors & Telemetry
  async postSensorReading(reading: any): Promise<SensorReading> {
    return request('/sensors/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reading),
    });
  },

  async getLatestReadings(deviceId?: string): Promise<SensorReading[]> {
    const q = deviceId ? `?device_id=${deviceId}` : '';
    return request(`/sensors/latest${q}`);
  },

  async getSensorAgronomicStatus(deviceId?: string, crop?: string): Promise<any> {
    const q = new URLSearchParams();
    if (deviceId) q.append('device_id', deviceId);
    if (crop) q.append('crop', crop);
    return request(`/sensors/status?${q.toString()}`);
  },

  // Analytics
  async getTimeseries(deviceId?: string, sensorType?: string, range: string = '24h'): Promise<any> {
    const params = new URLSearchParams();
    if (deviceId) params.append('device_id', deviceId);
    if (sensorType) params.append('sensor_type', sensorType);
    params.append('range', range);
    return request(`/analytics/timeseries?${params.toString()}`);
  },

  async getFarmSummary(deviceId?: string): Promise<any> {
    const q = deviceId ? `?device_id=${deviceId}` : '';
    return request(`/analytics/summary${q}`);
  },

  // Alerts
  async getAlerts(params: { deviceId?: string; isResolved?: boolean; severity?: string } = {}): Promise<Alert[]> {
    const q = new URLSearchParams();
    if (params.deviceId) q.append('device_id', params.deviceId);
    if (params.isResolved !== undefined) q.append('is_resolved', String(params.isResolved));
    if (params.severity) q.append('severity', params.severity);
    return request(`/alerts?${q.toString()}`);
  },

  async resolveAlert(alertId: string): Promise<Alert> {
    return request(`/alerts/${alertId}/resolve`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_resolved: true }),
    });
  },

  // Voice & AI Chat Pipeline
  async sendVoiceChat(formData: FormData): Promise<RAGQueryResponse> {
    const headers = getAuthHeader();
    const response = await fetch(`${API_BASE}/voice/chat`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Voice chat failed' }));
      throw new Error(err.detail || 'Voice chat failed');
    }
    return response.json();
  },

  // Knowledge Base Management
  async getDocuments(): Promise<DocumentItem[]> {
    return request('/knowledge/documents');
  },

  async uploadDocument(formData: FormData): Promise<DocumentItem> {
    const headers = getAuthHeader();
    const response = await fetch(`${API_BASE}/knowledge/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return response.json();
  },

  async deleteDocument(id: string): Promise<void> {
    return request(`/knowledge/documents/${id}`, { method: 'DELETE' });
  },

  async searchKnowledge(query: string, crop?: string, top_k: number = 5): Promise<any> {
    return request('/knowledge/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, crop, top_k }),
    });
  },

  async debugRAG(question: string, deviceId?: string, crop?: string): Promise<any> {
    return request('/knowledge/rag-debug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, device_id: deviceId, crop }),
    });
  },

  // Conversations & History
  async getConversations(): Promise<Conversation[]> {
    return request('/conversations');
  },

  async getConversation(id: string): Promise<Conversation> {
    return request(`/conversations/${id}`);
  },

  async deleteConversation(id: string): Promise<void> {
    return request(`/conversations/${id}`, { method: 'DELETE' });
  },
};
