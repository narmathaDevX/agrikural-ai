import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  MicOff,
  Send,
  Volume2,
  FileText,
  Radio,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { Device, RAGQueryResponse, SourceCitation } from '../types';
import { api } from '../services/api';

interface AssistantProps {
  device: Device | null;
  initialPrompt?: string;
}

export const Assistant: React.FC<AssistantProps> = ({ device, initialPrompt }) => {
  const [inputText, setInputText] = useState(initialPrompt || '');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const [languageOverride, setLanguageOverride] = useState<string>('');
  const [playingAudioUrl, setPlayingAudioUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const deviceId = device?.id || 'AGRI-DEV-001';

  useEffect(() => {
    if (initialPrompt) {
      setInputText(initialPrompt);
    }
  }, [initialPrompt]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Audio Recording (Microphone via MediaRecorder API)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await handleSendAudio(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.warn('Microphone permission not granted or unsupported:', err);
      // Fallback voice simulation
      setInputText('என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleSendAudio = async (blob: Blob) => {
    setIsLoading(true);
    const formData = new FormData();
    formData.append('audio_file', blob, 'recording.webm');
    formData.append('device_id', deviceId);
    if (languageOverride) formData.append('language_override', languageOverride);
    if (device?.crop_type) formData.append('crop', device.crop_type);

    try {
      const res: RAGQueryResponse = await api.sendVoiceChat(formData);
      appendMessagePair(res);
    } catch (err: any) {
      alert(`Voice consultation error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendText = async () => {
    if (!inputText.trim()) return;

    const textToSend = inputText.trim();
    setInputText('');
    setIsLoading(true);

    const formData = new FormData();
    formData.append('text', textToSend);
    formData.append('device_id', deviceId);
    if (languageOverride) formData.append('language_override', languageOverride);
    if (device?.crop_type) formData.append('crop', device.crop_type);

    try {
      const res: RAGQueryResponse = await api.sendVoiceChat(formData);
      appendMessagePair(res);
    } catch (err: any) {
      alert(`Consultation error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const appendMessagePair = (res: RAGQueryResponse) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `msg_u_${Date.now()}`,
        role: 'user',
        text: res.original_question,
        detected_language: res.detected_language,
        translated_question: res.translated_question,
      },
      {
        id: res.message_id || `msg_a_${Date.now()}`,
        role: 'assistant',
        text: res.translated_answer || res.answer,
        original_english: res.answer,
        sources: res.sources,
        sensor_context: res.sensor_context,
        audio_url: res.audio_url,
        language: res.language,
      },
    ]);

    // Auto-play synthesized voice if audio URL is provided
    if (res.audio_url) {
      playAudio(res.audio_url);
    }
  };

  const playAudio = (url: string) => {
    if (!url) return;
    if (audioPlayerRef.current) {
      audioPlayerRef.current.src = url;
      audioPlayerRef.current.play().catch((e) => console.log('Autoplay prevented:', e));
      setPlayingAudioUrl(url);
    }
  };

  const toggleSourceExpand = (id: string) => {
    setExpandedSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getLanguageLabel = (code: string) => {
    switch (code) {
      case 'ta':
        return 'Tamil (தமிழ்)';
      case 'ml':
        return 'Malayalam (മലയാളം)';
      default:
        return 'English';
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col h-[calc(100vh-4rem)]">
      {/* Hidden audio element for speech playback */}
      <audio
        ref={audioPlayerRef}
        onEnded={() => setPlayingAudioUrl(null)}
        onError={() => setPlayingAudioUrl(null)}
      />

      {/* Top Banner with Device & Language Context */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              Agrikural Multilingual AI Assistant
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 font-mono px-2 py-0.5 rounded">
                RAG + Hardware Telemetry
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Active Context: <strong className="text-slate-200">{device?.crop_type || 'Tomato'}</strong> ({device?.name || 'Sector A'})
            </p>
          </div>
        </div>

        {/* Language Override Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Speech Language:</span>
          <select
            value={languageOverride}
            onChange={(e) => setLanguageOverride(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
          >
            <option value="">Auto-Detect (தானியங்கி)</option>
            <option value="ta">Tamil (தமிழ்)</option>
            <option value="ml">Malayalam (മലയാളം)</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>

      {/* Messages Conversation Stream */}
      <div className="flex-1 overflow-y-auto my-4 space-y-4 pr-1">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Mic className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100">Ask Your Agricultural AI Agronomist</h3>
              <p className="text-xs text-slate-400 max-w-md mt-1">
                Speak or type in Tamil, Malayalam, or English. The AI combines live IoT sensor readings (soil moisture, temperature) with verified ICAR & TNAU documentation to provide grounded answers.
              </p>
            </div>

            {/* Quick Prompt Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-xl w-full text-left pt-2">
              <button
                onClick={() => setInputText('என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?')}
                className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 text-xs transition"
              >
                <div className="font-semibold text-slate-200">தமிழ் (Tamil)</div>
                <div className="text-slate-400 mt-0.5 truncate">என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?</div>
              </button>
              <button
                onClick={() => setInputText('തക്കാളി ചെടികൾക്ക് ഈ മണ്ണിലെ ഈർപ്പം മതിയോ?')}
                className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 text-xs transition"
              >
                <div className="font-semibold text-slate-200">മലയാളം (Malayalam)</div>
                <div className="text-slate-400 mt-0.5 truncate">തക്കാളി ചെടികൾക്ക് ഈ മണ്ണിലെ ഈർപ്പം മതിയോ?</div>
              </button>
              <button
                onClick={() => setInputText('Is my current soil moisture sufficient for the tomato crop?')}
                className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 text-xs transition"
              >
                <div className="font-semibold text-slate-200">English</div>
                <div className="text-slate-400 mt-0.5 truncate">Is my current soil moisture sufficient for the tomato crop?</div>
              </button>
              <button
                onClick={() => setInputText('What is the recommended fertilizer schedule for hybrid tomatoes?')}
                className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 text-xs transition"
              >
                <div className="font-semibold text-slate-200">Fertilizer Advisory</div>
                <div className="text-slate-400 mt-0.5 truncate">What is the recommended fertilizer schedule for hybrid tomatoes?</div>
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}
            >
              {/* Message Header Badges */}
              <div className="flex items-center gap-2 text-[11px] text-slate-400 px-1">
                <span className="font-semibold">{isUser ? 'Farmer Query' : 'Agrikural AI'}</span>
                {msg.detected_language && (
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                    {getLanguageLabel(msg.detected_language)}
                  </span>
                )}
                {isUser && msg.translated_question && msg.detected_language !== 'en' && (
                  <span className="text-slate-500 italic">
                    (Translated: &quot;{msg.translated_question}&quot;)
                  </span>
                )}
              </div>

              {/* Message Bubble */}
              <div
                className={`p-4 rounded-2xl max-w-2xl text-sm leading-relaxed ${
                  isUser
                    ? 'bg-emerald-600 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none shadow-md'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.text}</div>

                {/* Assistant Additions: Audio Playback Button */}
                {!isUser && msg.audio_url && (
                  <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
                    <button
                      onClick={() => playAudio(msg.audio_url)}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-semibold transition"
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                      <span>{playingAudioUrl === msg.audio_url ? 'Playing Audio...' : 'Listen in Spoken Voice'}</span>
                    </button>
                    <span className="text-[10px] text-slate-500 font-mono uppercase">
                      TTS ({msg.language})
                    </span>
                  </div>
                )}

                {/* Current Sensor Telemetry Snapshot Used for this answer */}
                {!isUser && msg.sensor_context?.readings && (
                  <div className="mt-3 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs">
                    <div className="font-semibold text-slate-300 flex items-center gap-1.5 text-[11px] mb-1.5">
                      <Cpu className="w-3 h-3 text-cyan-400" />
                      Hardware Telemetry In Context:
                    </div>
                    <div className="flex flex-wrap gap-2 text-[11px] font-mono">
                      {Object.entries(msg.sensor_context.readings).map(([stype, sinfo]: any) => (
                        <span key={stype} className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                          {stype.replace('_', ' ')}: <strong className="text-emerald-400">{sinfo.value}{sinfo.unit}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Verified Source Document Citations */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                    <button
                      onClick={() => toggleSourceExpand(msg.id)}
                      className="flex items-center justify-between w-full text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
                    >
                      <span className="flex items-center gap-1.5 text-emerald-400">
                        <FileText className="w-3.5 h-3.5" />
                        Verified Sources Used ({msg.sources.length}):
                      </span>
                      {expandedSources[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {expandedSources[msg.id] && (
                      <div className="space-y-1.5 pt-1">
                        {msg.sources.map((src: SourceCitation, idx: number) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-200">{src.title}</span>
                              <span className="text-[10px] text-emerald-400 font-mono">
                                Match: {(src.relevance_score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-2">
                              <span>Org: <strong className="text-slate-300">{src.organization}</strong></span>
                              <span>•</span>
                              <span>Page: {src.page || 1}</span>
                            </div>
                            {src.snippet && (
                              <p className="mt-1 text-[11px] text-slate-400 italic bg-slate-900/50 p-1.5 rounded">
                                &quot;{src.snippet}&quot;
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex items-center gap-2.5 text-xs text-emerald-400 p-3 rounded-xl bg-slate-900 border border-slate-800 max-w-sm">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Analyzing soil telemetry & ICAR knowledge base...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Voice / Text Input Box */}
      <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          {/* Push-to-Talk Recording Button */}
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            title={isRecording ? 'Release to send speech' : 'Hold to speak in Tamil / Malayalam / English'}
            className={`p-3 rounded-xl transition flex items-center gap-2 font-medium text-xs ${
              isRecording
                ? 'bg-rose-500 text-white animate-pulse shadow-lg shadow-rose-900/50'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
            }`}
          >
            {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4 text-emerald-400" />}
            <span className="hidden sm:inline">
              {isRecording ? 'Listening (Release to Send)...' : 'Hold to Speak'}
            </span>
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendText()}
            placeholder="Type your agricultural question in Tamil, Malayalam, or English..."
            className="flex-1 bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />

          {/* Send Button */}
          <button
            onClick={handleSendText}
            disabled={!inputText.trim() || isLoading}
            className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white transition"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
