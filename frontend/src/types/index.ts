export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'farmer' | 'viewer';
  preferred_language: 'ta' | 'ml' | 'en';
  is_active: boolean;
  created_at: string;
}

export interface SensorInfo {
  id: string;
  device_id: string;
  sensor_type: string;
  name: string;
  unit: string;
  min_threshold?: number;
  max_threshold?: number;
  critical_min?: number;
  critical_max?: number;
  is_active: boolean;
  current_value?: number;
}

export interface Device {
  id: string;
  name: string;
  farm_name: string;
  location: string;
  crop_type: string;
  status: 'online' | 'offline' | 'disconnected' | 'warning' | 'maintenance';
  last_seen?: string;
  connection_status?: string;
  last_seen_human?: string;
  is_online?: boolean;
  age_seconds?: number;
  ip_address: string;
  firmware_version: string;
  metadata_json?: Record<string, any>;
  sensors: SensorInfo[];
  latest_readings?: Record<string, {
    value: number;
    unit: string;
    timestamp: string;
    sensor_id?: string;
    age_seconds?: number;
    is_stale?: boolean;
    last_updated_text?: string;
  }>;
}

export interface SensorReading {
  id: number;
  device_id: string;
  sensor_id: string;
  sensor_type: string;
  value: number;
  unit: string;
  timestamp: string;
  location?: string;
  metadata_json?: Record<string, any>;
}

export interface Alert {
  id: string;
  device_id: string;
  sensor_id?: string;
  sensor_type: string;
  severity: 'warning' | 'critical' | 'info';
  title: string;
  message: string;
  value?: number;
  threshold?: number;
  is_resolved: boolean;
  created_at: string;
  resolved_at?: string;
}

export interface SourceCitation {
  title: string;
  organization: string;
  page?: number;
  section?: string;
  document_id: string;
  relevance_score: number;
  crop?: string;
  topic?: string;
  snippet?: string;
}

export interface RAGQueryResponse {
  answer: string;
  translated_answer?: string;
  original_question: string;
  detected_language: string;
  translated_question?: string;
  sources: SourceCitation[];
  sensor_context?: {
    device_id?: string;
    crop_type?: string;
    location?: string;
    readings?: Record<string, { value: number; unit: string; timestamp: string }>;
  };
  language: string;
  confidence_score: number;
  audio_url?: string;
  conversation_id?: string;
  message_id?: string;
}

export interface DocumentItem {
  document_id: string;
  title: string;
  source: string;
  organization: string;
  author?: string;
  publication_date?: string;
  crop: string;
  crop_type: string;
  state: string;
  district: string;
  region: string;
  soil_type: string;
  topic: string;
  language: string;
  document_type: string;
  file_path?: string;
  file_size: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  original_text: string;
  detected_language: string;
  translated_english_text?: string;
  translated_output_text?: string;
  audio_url?: string;
  retrieved_documents_json?: SourceCitation[];
  sensor_context_json?: any;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id?: string;
  device_id?: string;
  title: string;
  language: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}
