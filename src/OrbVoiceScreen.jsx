import React, { useState, useEffect } from "react";
import {
  ChevronLeft,
  MoreVertical,
  Mic,
  MicOff,
  X,
  Sparkles,
  ArrowUpRight,
  Volume2,
  Cpu,
  Layers,
  Activity
} from "lucide-react";

export default function OrbVoiceScreen() {
  const [isListening, setIsListening] = useState(true);
  const [audioLevel, setAudioLevel] = useState(1);

  // Simulate subtle real-time audio reactivity for the 3D sphere
  useEffect(() => {
    if (!isListening) return;
    const interval = setInterval(() => {
      setAudioLevel(1 + Math.random() * 0.08); // dynamic scale shift
    }, 180);
    return () => clearInterval(interval);
  }, [isListening]);

  return (
    <div className="flex justify-center items-center min-h-screen bg-[#F3EDF2] p-4 font-sans antialiased text-[#2D2638]">
      {/* Phone Canvas Frame */}
      <div className="w-full max-w-[390px] h-[844px] bg-gradient-to-b from-[#FDFBFD] via-[#F9F3F7] to-[#F1E8F2] rounded-[48px] border-[8px] border-[#1C1A22] shadow-[0_25px_70px_rgba(45,38,56,0.18)] flex flex-col justify-between overflow-hidden relative">
        
        {/* Dynamic Island / Top Notch */}
        <div className="pt-3 px-7 flex justify-between items-center z-30">
          <span className="text-xs font-semibold tracking-tight text-[#1C1A22]">9:30 PM</span>
          <div className="w-24 h-6 bg-[#1C1A22] rounded-full mx-auto" />
          <div className="flex items-center space-x-1.5 text-xs text-[#1C1A22]">
            <span className="text-[10px] font-bold">5G</span>
            <div className="w-5 h-2.5 border border-[#1C1A22] rounded-[3px] p-0.5">
              <div className="w-full h-full bg-[#1C1A22] rounded-[1px]" />
            </div>
          </div>
        </div>

        {/* Top Header Navigation */}
        <header className="px-5 pt-3 flex items-center justify-between z-20">
          <button className="w-9 h-9 rounded-full bg-white/70 backdrop-blur-md border border-white/60 flex items-center justify-center text-[#2D2638] shadow-xs active:scale-95 transition">
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Mini Orb Indicator */}
          <div className="flex items-center space-x-2 bg-white/70 backdrop-blur-md border border-white/80 px-3.5 py-1.5 rounded-full shadow-xs">
            <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-tr from-[#00F0FF] via-[#F44EAE] to-[#FFA7E5] shadow-xs animate-spin-slow" />
            <span className="text-xs font-medium text-[#2D2638]">Voice Pulse</span>
          </div>

          <button className="w-9 h-9 rounded-full bg-white/70 backdrop-blur-md border border-white/60 flex items-center justify-center text-[#2D2638] shadow-xs active:scale-95 transition">
            <MoreVertical className="w-4 h-4" />
          </button>
        </header>

        {/* Main Content Stage */}
        <main className="flex-1 flex flex-col items-center justify-center px-6 relative z-10 -mt-6">
          <h2 className="text-xl font-medium tracking-tight text-[#2B2338] mb-8">
            AI Voice Recognition
          </h2>

          {/* ========================================================
              3D IRIDESCENT LIQUID GLASS SPHERE (PURE CSS / SVG)
             ======================================================== */}
          <div
            className="relative flex items-center justify-center transition-transform duration-200"
            style={{ transform: `scale(${audioLevel})` }}
          >
            {/* Ambient Multi-Hue Chromatic Glow Behind Orb */}
            <div className="absolute w-72 h-72 rounded-full bg-gradient-to-tr from-[#00E5FF]/35 via-[#F740A5]/30 to-[#FFA5E4]/40 blur-3xl pointer-events-none" />

            {/* Inner Spherical Body */}
            <div
              className="relative w-56 h-56 rounded-full overflow-hidden shadow-[0_20px_50px_rgba(244,78,174,0.3),inset_0_-15px_30px_rgba(0,229,255,0.45)] border border-white/40 cursor-pointer"
              style={{
                background: `
                  radial-gradient(circle at 50% 115%, #00F2FE 0%, #4FACFE 18%, transparent 55%),
                  radial-gradient(circle at 50% -15%, #FFA7E5 0%, #F44EAE 40%, #762464 85%)
                `
              }}
              onClick={() => setIsListening(!isListening)}
            >
              {/* Internal Swirling Fluid Waves */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#00F5D4]/40 via-transparent to-[#F15BB5]/30 mix-blend-screen opacity-90 animate-pulse" />

              {/* Sub-surface Violet Shadow Band */}
              <div className="absolute inset-x-0 top-1/2 h-16 bg-[#3C0932]/40 blur-md transform -rotate-12" />

              {/* Primary Top Specular Glass Crescent Highlight */}
              <div
                className="absolute top-2 left-6 right-6 h-28 rounded-[50%] bg-gradient-to-b from-white/95 via-white/40 to-transparent pointer-events-none transform -rotate-6 blur-[0.6px]"
                style={{
                  clipPath: "ellipse(48% 35% at 50% 30%)"
                }}
              />

              {/* Secondary Lower Cyan Rim Reflection */}
              <div className="absolute bottom-2 left-8 right-8 h-10 rounded-full bg-gradient-to-t from-white/80 via-[#A7F3D0]/60 to-transparent blur-xs pointer-events-none" />

              {/* Pinpoint Glare Dot */}
              <div className="absolute top-8 left-12 w-3.5 h-2 rounded-full bg-white blur-[0.4px] transform -rotate-45" />
            </div>

            {/* Outer Soft Ring Accents */}
            <div className="absolute w-[240px] h-[240px] rounded-full border border-white/50 pointer-events-none opacity-40 animate-ping" />
          </div>

          {/* Real-time Subtitle or Pulse Frequency */}
          <div className="mt-8 flex items-center space-x-2 bg-white/60 backdrop-blur-md border border-white/80 px-4 py-1.5 rounded-full shadow-xs">
            <span className="w-2 h-2 rounded-full bg-[#F44EAE] animate-ping" />
            <span className="text-xs font-medium text-[#655A75]">
              {isListening ? "Listening to query in real-time..." : "Tap mic to speak"}
            </span>
          </div>
        </main>

        {/* Action Suggestion Cards (Bottom Half) */}
        <div className="px-6 grid grid-cols-2 gap-3 z-10 mb-4">
          <div className="bg-white/75 backdrop-blur-md p-3.5 rounded-2xl border border-white/80 shadow-xs flex flex-col justify-between h-24 hover:bg-white transition cursor-pointer">
            <div className="flex justify-between items-center text-[#2D2638]">
              <div className="w-7 h-7 rounded-lg bg-[#F5EAF2] flex items-center justify-center text-[#F44EAE]">
                <Activity className="w-4 h-4" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-[#A195B0]" />
            </div>
            <p className="text-xs font-semibold text-[#2D2638] leading-tight">
              Voice Clarity<br />Boost
            </p>
          </div>

          <div className="bg-white/75 backdrop-blur-md p-3.5 rounded-2xl border border-white/80 shadow-xs flex flex-col justify-between h-24 hover:bg-white transition cursor-pointer">
            <div className="flex justify-between items-center text-[#2D2638]">
              <div className="w-7 h-7 rounded-lg bg-[#EBF7F8] flex items-center justify-center text-[#00BFB2]">
                <Sparkles className="w-4 h-4" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-[#A195B0]" />
            </div>
            <p className="text-xs font-semibold text-[#2D2638] leading-tight">
              Instant Speech<br />Capture
            </p>
          </div>
        </div>

        {/* Bottom Floating Control Pill */}
        <footer className="px-6 pb-6 pt-2 z-20">
          <div className="bg-white/90 backdrop-blur-xl border border-white p-2 rounded-full shadow-[0_8px_30px_rgba(0,0,0,0.06)] flex items-center justify-between">
            {/* AI Assistant Mode */}
            <button className="w-11 h-11 rounded-full flex items-center justify-center text-[#6A5E7A] hover:bg-slate-100 transition text-xs font-bold font-mono">
              AI
            </button>

            {/* Central Animated Mic Orb */}
            <button
              onClick={() => setIsListening(!isListening)}
              className={`w-13 h-13 rounded-full flex items-center justify-center text-white transition-all shadow-md active:scale-95 ${
                isListening
                  ? "bg-gradient-to-tr from-[#F44EAE] to-[#FFA7E5] shadow-[0_0_20px_rgba(244,78,174,0.4)]"
                  : "bg-[#2D2638]"
              }`}
            >
              {isListening ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
            </button>

            {/* Cancel Action */}
            <button
              onClick={() => setIsListening(false)}
              className="w-11 h-11 rounded-full flex items-center justify-center text-[#6A5E7A] hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </footer>

        {/* Home Screen Bottom Handle */}
        <div className="pb-2 flex justify-center">
          <div className="w-32 h-1 bg-[#1C1A22]/30 rounded-full" />
        </div>
      </div>
    </div>
  );
}