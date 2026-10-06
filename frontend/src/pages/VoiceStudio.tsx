import React, { useState, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  Cpu,
  FileText,
  Languages,
  CheckCircle2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { Device, RAGQueryResponse } from '../types';
import { api } from '../services/api';

interface VoiceStudioProps {
  device: Device | null;
}

export const VoiceStudio: React.FC<VoiceStudioProps> = ({ device }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [languageOverride, setLanguageOverride] = useState<string>('');
  const [result, setResult] = useState<RAGQueryResponse | null>(null);
  const [activeStage, setActiveStage] = useState<number>(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const deviceId = device?.id || 'AGRI-DEV-001';

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
        await processAudio(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setActiveStage(1);
    } catch (err) {
      console.warn('Microphone permission not granted or unsupported:', err);
      // Demo voice simulation
      simulateVoiceQuery();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const simulateVoiceQuery = async () => {
    setIsProcessing(true);
    setActiveStage(1);
    const formData = new FormData();
    const demoPrompt = languageOverride === 'ml'
      ? 'തക്കാളി ചെടികൾക്ക് ഈ മണ്ണിലെ ഈർപ്പം മതിയോ?'
      : 'என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?';
    formData.append('text', demoPrompt);
    formData.append('device_id', deviceId);
    if (languageOverride) formData.append('language_override', languageOverride);
    if (device?.crop_type) formData.append('crop', device.crop_type);

    try {
      setActiveStage(2);
      setTimeout(() => setActiveStage(3), 300);
      const res = await api.sendVoiceChat(formData);
      setActiveStage(6);
      setResult(res);
      if (res.audio_url && audioPlayerRef.current) {
        audioPlayerRef.current.src = res.audio_url;
        audioPlayerRef.current.play().catch(() => {});
      }
    } catch (err: any) {
      alert(`Voice processing error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const processAudio = async (blob: Blob) => {
    setIsProcessing(true);
    setActiveStage(2);
    const formData = new FormData();
    formData.append('audio_file', blob, 'audio.webm');
    formData.append('device_id', deviceId);
    if (languageOverride) formData.append('language_override', languageOverride);
    if (device?.crop_type) formData.append('crop', device.crop_type);

    try {
      setActiveStage(3);
      const res = await api.sendVoiceChat(formData);
      setActiveStage(6);
      setResult(res);
      if (res.audio_url && audioPlayerRef.current) {
        audioPlayerRef.current.src = res.audio_url;
        audioPlayerRef.current.play().catch(() => {});
      }
    } catch (err: any) {
      alert(`Voice processing error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const playSynthesizedVoice = () => {
    if (result?.audio_url && audioPlayerRef.current) {
      audioPlayerRef.current.currentTime = 0;
      audioPlayerRef.current.play();
    }
  };

  const pipelineStages = [
    { num: 1, title: 'Speech-to-Text', desc: 'Whisper / Local Acoustic STT' },
    { num: 2, title: 'Language Detection', desc: 'Tamil / Malayalam / English' },
    { num: 3, title: 'Translation to English', desc: 'Agricultural IndicTrans Engine' },
    { num: 4, title: 'Hybrid Context Engine', desc: 'Live IoT Telemetry + ChromaDB RAG' },
    { num: 5, title: 'Grounded AI Reasoning', desc: 'ICAR & TNAU Verification' },
    { num: 6, title: 'Target Translation & TTS', desc: 'Native Spoken Audio Generation' },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <audio ref={audioPlayerRef} />

      {/* Header */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Voice Pipeline Studio
            </span>
            <span className="text-xs text-slate-400 font-mono">
              STT → RAG → TTS
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 mt-2">
            Multilingual Voice Agricultural Interaction
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time vocal consultation in Tamil (தமிழ்), Malayalam (മലയാളം), or English with automated speech synthesis.
          </p>
        </div>

        {/* Language Override */}
        <div className="flex items-center gap-2 bg-slate-950/80 p-2 rounded-xl border border-slate-800 text-xs">
          <Languages className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Language:</span>
          <select
            value={languageOverride}
            onChange={(e) => setLanguageOverride(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2 py-1 focus:outline-none"
          >
            <option value="">Auto-Detect Script</option>
            <option value="ta">Tamil (தமிழ்)</option>
            <option value="ml">Malayalam (മലയാളം)</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>

      {/* Central Microphone Console */}
      <div className="p-8 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col items-center justify-center text-center relative overflow-hidden">
        {/* Pulsing ring visualizer when recording */}
        {isRecording && (
          <div className="absolute w-64 h-64 rounded-full bg-rose-500/10 border border-rose-500/30 animate-pulse-ring" />
        )}

        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          disabled={isProcessing}
          className={`w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all shadow-2xl relative z-10 ${
            isRecording
              ? 'bg-rose-500 text-white scale-110 shadow-rose-900/60'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/60 hover:scale-105'
          }`}
        >
          {isRecording ? <MicOff className="w-10 h-10 animate-bounce" /> : <Mic className="w-10 h-10" />}
          <span className="text-[10px] font-bold uppercase mt-1 tracking-wider">
            {isRecording ? 'Listening' : 'Hold To Talk'}
          </span>
        </button>

        <p className="mt-4 text-xs text-slate-300 font-medium">
          {isRecording
            ? 'Release button to automatically transcribe, retrieve documents, and synthesize answer.'
            : isProcessing
            ? 'Running neural multilingual speech, RAG, and reasoning pipeline...'
            : 'Press and hold button to speak in Tamil, Malayalam, or English.'}
        </p>

        {/* Quick Sample Clickers */}
        <div className="mt-6 flex flex-wrap justify-center gap-2 text-xs">
          <button
            onClick={() => {
              setLanguageOverride('ta');
              simulateVoiceQuery();
            }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            Test Tamil Voice: &quot;மண் ஈரப்பதம் போதுமா?&quot;
          </button>
          <button
            onClick={() => {
              setLanguageOverride('ml');
              simulateVoiceQuery();
            }}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            Test Malayalam Voice: &quot;ഈർപ്പം മതിയോ?&quot;
          </button>
        </div>
      </div>

      {/* 6-Stage Pipeline Progress Tracker */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
          Autonomous Voice Pipeline Execution Stages
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-2.5">
          {pipelineStages.map((stage) => {
            const isCompleted = activeStage >= stage.num;
            const isCurrent = activeStage === stage.num && isProcessing;
            return (
              <div
                key={stage.num}
                className={`p-3 rounded-xl border text-xs transition ${
                  isCurrent
                    ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-300'
                    : isCompleted
                    ? 'bg-slate-950/80 border-emerald-500/20 text-slate-300'
                    : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] font-bold">Stage 0{stage.num}</span>
                  {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                  {isCurrent && <RefreshCw className="w-3.5 h-3.5 text-emerald-400 animate-spin" />}
                </div>
                <div className="font-semibold">{stage.title}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">{stage.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Results Display */}
      {result && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-base text-slate-100">Consultation Pipeline Results</h3>
            </div>
            {result.audio_url && (
              <button
                onClick={playSynthesizedVoice}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition"
              >
                <Volume2 className="w-4 h-4" />
                <span>Replay Spoken Voice ({result.language.toUpperCase()})</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Input Transcription & Translation */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <span className="text-[10px] font-mono font-bold uppercase text-slate-400">
                Transcribed User Speech ({result.detected_language})
              </span>
              <p className="text-sm font-semibold text-slate-200">{result.original_question}</p>
              {result.translated_question && result.detected_language !== 'en' && (
                <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-400">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase">English Query:</span>
                  <p className="mt-0.5 italic text-slate-300">&quot;{result.translated_question}&quot;</p>
                </div>
              )}
            </div>

            {/* Synthesized Response */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <span className="text-[10px] font-mono font-bold uppercase text-emerald-400">
                Grounded Agronomic Output ({result.language})
              </span>
              <p className="text-sm font-medium text-slate-200 leading-relaxed whitespace-pre-wrap">
                {result.translated_answer || result.answer}
              </p>
            </div>
          </div>

          {/* Sources and Context Snapshot */}
          <div className="pt-2 flex flex-col md:flex-row gap-4 text-xs">
            {/* Sensor Context */}
            {result.sensor_context?.readings && (
              <div className="flex-1 p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5 mb-2">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" /> Sensor Context Applied:
                </span>
                <div className="flex flex-wrap gap-2 font-mono text-[11px]">
                  {Object.entries(result.sensor_context.readings).map(([k, v]: any) => (
                    <span key={k} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                      {k.replace('_', ' ')}: <strong className="text-emerald-400">{v.value}{v.unit}</strong>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Citations */}
            {result.sources && result.sources.length > 0 && (
              <div className="flex-1 p-3.5 rounded-xl bg-slate-950/50 border border-slate-800">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5 mb-2">
                  <FileText className="w-3.5 h-3.5 text-emerald-400" /> Verified Agricultural Source:
                </span>
                <div className="text-slate-300 text-xs font-semibold">
                  {result.sources[0].title}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {result.sources[0].organization} • Page {result.sources[0].page || 1}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
