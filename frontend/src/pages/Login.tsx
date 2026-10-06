import React, { useState } from 'react';
import { Sprout, Lock, Mail, User, ShieldCheck, Sparkles, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('farmer');
  const [language, setLanguage] = useState('ta');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      if (isRegister) {
        await register({
          email,
          password,
          full_name: fullName,
          role,
          preferred_language: language,
        });
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setIsRegister(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
        {/* Brand */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto shadow-inner">
            <Sprout className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-slate-100 tracking-wide">
            AGRIKURAL <span className="text-emerald-400">AI</span>
          </h1>
          <p className="text-xs text-slate-400">
            Autonomous Multilingual Agricultural IoT & RAG Assistant
          </p>
        </div>

        {/* Demo Fast Fill Buttons */}
        <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
          <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-emerald-400" /> Instant Demo Access:
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin('admin@agrikural.ai', 'admin123')}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-left transition"
            >
              <div className="font-bold text-[11px] text-emerald-400">Dr. Ramanathan</div>
              <div className="text-[10px] text-slate-400">Agronomist (Admin)</div>
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('farmer@agrikural.ai', 'farmer123')}
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-left transition"
            >
              <div className="font-bold text-[11px] text-cyan-400">Muthu Velan</div>
              <div className="text-[10px] text-slate-400">Tomato Farmer</div>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {isRegister && (
            <>
              <div>
                <label className="text-slate-400 font-semibold block mb-1">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Muthu Velan"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Role</label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="farmer">Farmer</option>
                    <option value="admin">Admin / Agronomist</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ta">Tamil (தமிழ்)</option>
                    <option value="ml">Malayalam (മലയാളം)</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <div>
            <label className="text-slate-400 font-semibold block mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="farmer@agrikural.ai"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="text-slate-400 font-semibold block mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition shadow-lg shadow-emerald-950/40 flex items-center justify-center gap-2"
          >
            <span>{isRegister ? 'Create Agricultural Account' : 'Sign In to Dashboard'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center pt-2">
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="text-xs text-slate-400 hover:text-emerald-400 transition"
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register farmer profile"}
          </button>
        </div>
      </div>
    </div>
  );
};
