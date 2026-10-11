import React, { useEffect, useState } from 'react';
import { Briefcase, Cpu, Layers } from 'lucide-react';
import { getConfig } from '../api';

export default function Navbar({ onReset, isProcessing }) {
  const [sysConfig, setSysConfig] = useState({
    llm_provider: 'Groq Llama 3',
    llm_healthy: true,
    job_sources: 'JSearch + Live Feeds',
    sources_healthy: true,
  });

  useEffect(() => {
    getConfig().then((cfg) => {
      if (cfg) {
        setSysConfig({
          llm_provider: cfg.llm_provider || 'Groq Llama 3',
          llm_healthy: cfg.llm_healthy ?? true,
          job_sources: cfg.job_sources || 'JSearch + Live Feeds',
          sources_healthy: cfg.sources_healthy ?? true,
        });
      }
    });
  }, []);

  return (
    <header className="border-b border-[#2A303C] bg-[#0A0C10]/90 backdrop-blur-md sticky top-0 z-40 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div 
          onClick={!isProcessing ? onReset : undefined} 
          className="flex items-center gap-3 cursor-pointer group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !isProcessing) onReset();
          }}
          aria-label="JobPulse Home"
        >
          {/* Champagne Silk Accent Tile */}
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#E2D4BE] to-[#D4C4A8] flex items-center justify-center shadow-lg shadow-[#D4C4A8]/15 group-hover:shadow-[#D4C4A8]/30 transition-all">
            <Briefcase className="w-5 h-5 text-[#0A0C10]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-[#E5E7EB] tracking-tight group-hover:text-white transition-colors">
                JobPulse
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25">
                LangGraph Agent
              </span>
            </div>
            <p className="text-xs text-[#9CA3AF] hidden sm:block">
              Executive Multi-Agent Job Discovery & Precision Fit
            </p>
          </div>
        </div>

        {/* Dynamic Provider Badges */}
        <div className="flex items-center gap-3">
          {/* LLM Engine Badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#14171E] border border-[#2A303C] text-xs text-[#E5E7EB]">
            <Cpu className="w-3.5 h-3.5 text-[#D4C4A8]" />
            <span className="font-medium">{sysConfig.llm_provider}</span>
            <span 
              className={`w-1.5 h-1.5 rounded-full ml-1 ${
                sysConfig.llm_healthy 
                  ? 'bg-[#D4C4A8] shadow-[0_0_8px_rgba(212,196,168,0.8)]' 
                  : 'bg-[#EF4444]'
              }`}
              title={sysConfig.llm_healthy ? 'LLM Engine Active' : 'Key Missing'}
            />
          </div>

          {/* Live Sources Badge */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#14171E] border border-[#2A303C] text-xs text-[#E5E7EB]">
            <Layers className="w-3.5 h-3.5 text-[#D4C4A8]" />
            <span className="font-medium">{sysConfig.job_sources}</span>
            <span 
              className={`w-1.5 h-1.5 rounded-full ml-1 ${
                sysConfig.sources_healthy 
                  ? 'bg-[#D4C4A8] shadow-[0_0_8px_rgba(212,196,168,0.8)]' 
                  : 'bg-[#EF4444]'
              }`}
              title={sysConfig.sources_healthy ? 'Live Feeds Active' : 'API Unconfigured'}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
