import React, { useState, useEffect } from 'react';
import { History as HistoryIcon, Clock, MessageSquare, Volume2, Cpu, FileText, Trash2, ArrowRight } from 'lucide-react';
import { Conversation } from '../types';
import { api } from '../services/api';
import { SafeMarkdown } from '../components/SafeMarkdown';

export const History: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      const list = await api.getConversations();
      setConversations(list);
      if (list.length > 0 && !selectedConv) {
        setSelectedConv(list[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this consultation from history?')) return;
    try {
      await api.deleteConversation(id);
      if (selectedConv?.id === id) setSelectedConv(null);
      loadConversations();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <HistoryIcon className="w-5 h-5 text-emerald-400" />
            Agricultural Consultation History
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Audit log of all voice and text interactions, language translations, citations, and sensor states.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left List of Conversations */}
        <div className="space-y-2.5 overflow-y-auto max-h-[70vh] pr-1">
          {conversations.length === 0 ? (
            <div className="p-8 text-center rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              No recorded consultations yet.
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedConv(c)}
                className={`p-3.5 rounded-xl border transition cursor-pointer flex flex-col justify-between space-y-2 ${
                  selectedConv?.id === c.id
                    ? 'bg-slate-800 border-emerald-500/50'
                    : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-slate-200 line-clamp-1">{c.title}</span>
                  <span className="uppercase text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-950 text-emerald-400 border border-slate-800">
                    {c.language}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/80">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={(e) => handleDelete(c.id, e)}
                    className="p-1 text-slate-500 hover:text-rose-400 transition"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right Detail Viewer */}
        <div className="md:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          {selectedConv ? (
            <div>
              <div className="border-b border-slate-800 pb-3 mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-base text-slate-100">{selectedConv.title}</h3>
                  <p className="text-xs text-slate-400">
                    Recorded on {new Date(selectedConv.created_at).toLocaleString()} • Language: {selectedConv.language.toUpperCase()}
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {selectedConv.messages?.map((m, idx) => {
                  const isUser = m.role === 'user';
                  return (
                    <div key={idx} className={`p-4 rounded-xl border text-xs leading-relaxed space-y-2 ${
                      isUser
                        ? 'bg-slate-950/70 border-slate-800 text-slate-200'
                        : 'bg-emerald-950/20 border-emerald-500/20 text-slate-100'
                    }`}>
                      <div className="flex items-center justify-between text-[10px] font-bold uppercase text-slate-400">
                        <span>{isUser ? 'Farmer Message' : 'Grounded AI Output'}</span>
                        <span className="font-mono text-emerald-400">{m.detected_language}</span>
                      </div>

                      {isUser ? (
                        <div className="whitespace-pre-wrap text-sm">{m.original_text}</div>
                      ) : (
                        <SafeMarkdown content={m.original_text} />
                      )}

                      {m.translated_output_text && m.translated_output_text !== m.original_text && (
                        <div className="pt-2 border-t border-slate-800 text-slate-300">
                          <span className="text-[10px] text-slate-400 font-bold block mb-0.5">Spoken Translation:</span>
                          <SafeMarkdown content={m.translated_output_text} />
                        </div>
                      )}

                      {/* Sources used */}
                      {m.retrieved_documents_json && m.retrieved_documents_json.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/80">
                          <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1 mb-1">
                            <FileText className="w-3 h-3" /> Sources Referenced ({m.retrieved_documents_json.length}):
                          </span>
                          <div className="space-y-1">
                            {m.retrieved_documents_json.map((src: any, sIdx: number) => (
                              <div key={sIdx} className="text-[11px] text-slate-300 bg-slate-950/60 p-1.5 rounded">
                                • {src.title} ({src.organization})
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="py-20 text-center text-slate-400 text-xs">
              Select a consultation on the left to inspect detailed telemetry, translation, and RAG sources.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
