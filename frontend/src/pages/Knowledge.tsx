import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Upload,
  Search,
  Bug,
  Trash2,
  FileText,
  CheckCircle2,
  RefreshCw,
  Plus,
  Sparkles,
} from 'lucide-react';
import { DocumentItem } from '../types';
import { api } from '../services/api';

export const Knowledge: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'search' | 'debug'>('catalog');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Upload Form State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMeta, setUploadMeta] = useState({
    title: '',
    crop: 'Tomato',
    crop_type: 'Horticulture',
    organization: 'TNAU - Tamil Nadu Agricultural University',
    region: 'South India',
    topic: 'Irrigation & Disease Management',
    language: 'English',
  });

  // Search Tool State
  const [searchQuery, setSearchQuery] = useState('soil moisture threshold tomato');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Debug Panel State
  const [debugQuery, setDebugQuery] = useState('என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?');
  const [debugResults, setDebugResults] = useState<any | null>(null);
  const [isDebugRunning, setIsDebugRunning] = useState(false);

  const loadDocs = async () => {
    setIsLoading(true);
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    const fd = new FormData();
    fd.append('file', uploadFile);
    fd.append('title', uploadMeta.title || uploadFile.name);
    fd.append('crop', uploadMeta.crop);
    fd.append('crop_type', uploadMeta.crop_type);
    fd.append('organization', uploadMeta.organization);
    fd.append('region', uploadMeta.region);
    fd.append('topic', uploadMeta.topic);
    fd.append('language', uploadMeta.language);

    setIsLoading(true);
    try {
      await api.uploadDocument(fd);
      setShowUploadModal(false);
      setUploadFile(null);
      loadDocs();
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document from ChromaDB vector store?')) return;
    try {
      await api.deleteDocument(id);
      loadDocs();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await api.searchKnowledge(searchQuery, undefined, 5);
      setSearchResults(res.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleDebug = async () => {
    if (!debugQuery.trim()) return;
    setIsDebugRunning(true);
    try {
      const res = await api.debugRAG(debugQuery, 'AGRI-DEV-001', 'Tomato');
      setDebugResults(res);
    } catch (e) {
      console.error(e);
    } finally {
      setIsDebugRunning(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Agricultural Knowledge Base & ChromaDB Admin
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Verified agricultural university manuals, intelligent section chunking, and semantic vector embeddings.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-md shrink-0"
        >
          <Upload className="w-4 h-4" />
          <span>Ingest New Document (PDF / TXT / DOCX)</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('catalog')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'catalog'
              ? 'bg-slate-800 text-emerald-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Document Catalog ({documents.length})
        </button>
        <button
          onClick={() => setActiveTab('search')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'search'
              ? 'bg-slate-800 text-emerald-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Search className="w-4 h-4" />
          Semantic Search Tool
        </button>
        <button
          onClick={() => setActiveTab('debug')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'debug'
              ? 'bg-slate-800 text-emerald-400 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bug className="w-4 h-4" />
          RAG Debugging & Evaluation Panel
        </button>
      </div>

      {/* TAB 1: Document Catalog */}
      {activeTab === 'catalog' && (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px] font-bold">
              <tr>
                <th className="p-3.5">Document Title</th>
                <th className="p-3.5">Organization</th>
                <th className="p-3.5">Crop</th>
                <th className="p-3.5">Region</th>
                <th className="p-3.5">Chunks</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {documents.map((d) => (
                <tr key={d.document_id} className="hover:bg-slate-800/40 transition">
                  <td className="p-3.5 font-semibold text-slate-100">
                    <div>{d.title}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{d.document_id} • {d.document_type}</div>
                  </td>
                  <td className="p-3.5 text-slate-300">{d.organization}</td>
                  <td className="p-3.5">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold text-[11px]">
                      {d.crop}
                    </span>
                  </td>
                  <td className="p-3.5 text-slate-400">{d.region}</td>
                  <td className="p-3.5 font-mono font-bold text-cyan-400">{d.chunk_count}</td>
                  <td className="p-3.5">
                    <span className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Indexed
                    </span>
                  </td>
                  <td className="p-3.5 text-right">
                    <button
                      onClick={() => handleDelete(d.document_id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 transition"
                      title="Delete from vector database"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 2: Semantic Search Tool */}
      {activeTab === 'search' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search agricultural vector database..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-lg transition flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              <span>{isSearching ? 'Searching...' : 'Search Chunks'}</span>
            </button>
          </div>

          <div className="space-y-3">
            {searchResults.map((r, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-slate-200 text-sm">{r.metadata?.title}</div>
                  <div className="text-[11px] font-mono font-bold text-emerald-400">
                    Relevance Score: {(r.relevance_score * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="text-slate-400 text-[11px] flex gap-3">
                  <span>Crop: <strong>{r.metadata?.crop}</strong></span>
                  <span>Section: <strong>{r.metadata?.section}</strong></span>
                  <span>Page: {r.metadata?.page_number || 1}</span>
                </div>
                <p className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-slate-300 font-serif leading-relaxed whitespace-pre-wrap">
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: Developer RAG Debugger */}
      {activeTab === 'debug' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
            <label className="text-xs font-semibold text-slate-300 block">
              Enter User Query in Any Language (Tamil, Malayalam, English):
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={debugQuery}
                onChange={(e) => setDebugQuery(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={handleDebug}
                disabled={isDebugRunning}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-lg transition flex items-center gap-2"
              >
                <Bug className="w-4 h-4" />
                <span>{isDebugRunning ? 'Evaluating...' : 'Run RAG Diagnostic'}</span>
              </button>
            </div>
          </div>

          {debugResults && (
            <div className="space-y-4">
              {/* Query Translation Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1">
                  <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">1. Detected Script</span>
                  <div className="font-semibold text-slate-100">{debugResults.detected_language?.toUpperCase()}</div>
                  <div className="text-slate-300 italic mt-1">&quot;{debugResults.original_query}&quot;</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1">
                  <span className="font-mono text-[10px] text-emerald-400 uppercase font-bold">2. English Query Projection</span>
                  <div className="text-slate-100 font-semibold">{debugResults.translated_query}</div>
                </div>
              </div>

              {/* Retrieved Chunks with Similarity Scores */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-3">
                <div className="font-bold text-slate-200 text-sm flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-cyan-400" />
                  Retrieved Vector Chunks ({debugResults.retrieved_chunks?.length || 0})
                </div>

                <div className="space-y-2">
                  {debugResults.retrieved_chunks?.map((chk: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="font-bold text-slate-200">{chk.metadata?.title}</span>
                        <span className="font-mono text-emerald-400">Score: {chk.relevance_score}</span>
                      </div>
                      <p className="text-slate-400 text-[11px] line-clamp-3">{chk.text}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Synthesized System Prompt */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-2">
                <div className="font-bold text-slate-200">Synthesized LLM Prompt Context:</div>
                <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {debugResults.final_prompt}
                </pre>
              </div>

              {/* LLM Raw Output */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-2">
                <div className="font-bold text-emerald-400">Ground Truth Model Reasoning:</div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {debugResults.llm_raw_response}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Upload className="w-5 h-5 text-emerald-400" />
              Ingest Agricultural Knowledge Document
            </h3>

            <form onSubmit={handleUpload} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 font-semibold block mb-1">Document File (PDF, DOCX, TXT)</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-500 cursor-pointer"
                />
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Document Title</label>
                <input
                  type="text"
                  placeholder="e.g. TNAU Tomato Integrated Pest Management Manual"
                  value={uploadMeta.title}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Crop</label>
                  <input
                    type="text"
                    value={uploadMeta.crop}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, crop: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Organization</label>
                  <input
                    type="text"
                    value={uploadMeta.organization}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, organization: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Region</label>
                  <input
                    type="text"
                    value={uploadMeta.region}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, region: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Topic</label>
                  <input
                    type="text"
                    value={uploadMeta.topic}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, topic: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 text-slate-300 font-semibold hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition disabled:opacity-50"
                >
                  Start Ingestion
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
