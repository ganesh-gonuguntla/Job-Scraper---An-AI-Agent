import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Brain, 
  Search, 
  Filter, 
  Award, 
  CheckCircle2, 
  Circle, 
  Loader2, 
  UserCheck, 
  Layers, 
  Sliders, 
  ShieldCheck,
} from 'lucide-react';
import { getApiConfig } from '../api';

export default function ProgressStepperScreen({ completedNodes, currentNode, statusNote, nodeSummaries }) {
  const [modelConfig, setModelConfig] = useState({
    research_model: 'Groq Research Engine',
    scoring_model: 'Groq Reasoning Engine',
  });

  useEffect(() => {
    getApiConfig()
      .then(cfg => {
        if (cfg) {
          setModelConfig({
            research_model: cfg.research_model || 'Groq Research Engine',
            scoring_model: cfg.scoring_model || 'Groq Reasoning Engine',
          });
        }
      })
      .catch(() => {});
  }, []);

  const STEPS = [
    {
      id: 'extract_text',
      label: 'Document Ingestion',
      desc: 'Extracting PDF layout, stripping noise, and preparing resume corpus',
      icon: FileText,
    },
    {
      id: 'profile_and_queries',
      label: 'Profile & Queries',
      desc: `${modelConfig.research_model}: extracting skills, seniority & synthesizing targeted API query angles`,
      icon: Brain,
    },
    {
      id: 'human_review',
      label: 'Human Review',
      desc: 'Review and refine extracted skills and search query angles',
      icon: UserCheck,
    },
    {
      id: 'search',
      matchNodes: ['search_dispatcher', 'search_one'],
      label: 'Multi-Source Job Fetch',
      desc: 'Concurrent live query across JSearch (OpenWeb Ninja), Adzuna, Remotive, Arbeitnow & ATS feeds',
      icon: Search,
    },
    {
      id: 'rule_filter',
      label: 'Dedup + Liveness',
      desc: 'Deduplicating cross-source URLs and enforcing hard validation guards',
      icon: Filter,
    },
    {
      id: 'batch_builder',
      label: 'Pre-Score',
      desc: 'Packaging candidate postings within token budgets for parallel scoring',
      icon: Layers,
    },
    {
      id: 'score_jobs',
      label: 'Insights',
      desc: `${modelConfig.scoring_model}: 100-pt rubric fit evaluation, why-fit evidence bullets & interview tips`,
      icon: Award,
    },
    {
      id: 'ranker',
      label: 'Ranking',
      desc: 'Applying soft preferences (job type, location, salary boosts) and deterministic ordering',
      icon: Sliders,
    },
    {
      id: 'quality_gate',
      matchNodes: ['quality_gate', 'query_refiner'],
      label: 'Quality Gate',
      desc: 'Verifying minimum 15-match threshold and orchestrating expansion loop if needed',
      icon: ShieldCheck,
    },
  ];

  const getStepStatus = (step) => {
    const isStepCurrent = step.matchNodes 
      ? step.matchNodes.includes(currentNode)
      : step.id === currentNode;

    const isStepCompleted = step.matchNodes
      ? step.matchNodes.some(n => completedNodes.includes(n))
      : completedNodes.includes(step.id);

    if (isStepCurrent) return 'current';
    if (isStepCompleted) return 'completed';
    return 'pending';
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.99 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className="max-w-3xl mx-auto py-8 px-4"
    >
      <div className="glass-panel p-6 sm:p-8">
        <div className="border-b border-[#2A303C] pb-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-[#E5E7EB] flex items-center gap-2.5">
                <Loader2 className="w-5 h-5 text-[#D4C4A8] animate-spin" />
                Pipeline In Progress
              </h2>
              <p className="text-xs text-[#9CA3AF] mt-1">
                LangGraph is streaming execution events live via Server-Sent Events (SSE)
              </p>
            </div>
            {statusNote && (
              <span className="hidden sm:inline-block text-xs px-3 py-1.5 rounded-lg bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25 max-w-xs truncate">
                {statusNote}
              </span>
            )}
          </div>
        </div>

        {/* Stepper list */}
        <div className="relative pl-6 sm:pl-8 space-y-7 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#2A303C]">
          {STEPS.map((step) => {
            const status = getStepStatus(step);
            const Icon = step.icon;
            const summary = nodeSummaries[step.id] || (step.matchNodes && step.matchNodes.map(n => nodeSummaries[n]).filter(Boolean)[0]);

            return (
              <div key={step.id} className="relative flex items-start gap-4">
                {/* Node icon / indicator */}
                <div className="absolute -left-6 sm:-left-8 top-0.5 flex items-center justify-center">
                  {status === 'completed' ? (
                    <div className="w-6 h-6 rounded-full bg-[#D4C4A8] text-[#0A0C10] flex items-center justify-center ring-4 ring-[#14171E] shadow-md shadow-[#D4C4A8]/20">
                      <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                    </div>
                  ) : status === 'current' ? (
                    <div className="w-6 h-6 rounded-full bg-[#E2D4BE] text-[#0A0C10] flex items-center justify-center ring-4 ring-[#D4C4A8]/30 animate-pulse">
                      <Loader2 className="w-4 h-4 animate-spin stroke-[2.5]" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-[#1B1F28] text-[#4B5563] flex items-center justify-center ring-4 ring-[#14171E] border border-[#2A303C]">
                      <Circle className="w-3 h-3 fill-[#2A303C]" />
                    </div>
                  )}
                </div>

                {/* Step content */}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-sm font-semibold flex items-center gap-2 ${
                      status === 'current' ? 'text-[#D4C4A8]' : status === 'completed' ? 'text-[#E5E7EB]' : 'text-[#6B7280]'
                    }`}>
                      <Icon className="w-4 h-4" />
                      {step.label}
                    </h3>

                    {summary && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#1B1F28] text-[#D4C4A8] border border-[#2A303C]">
                        {summary}
                      </span>
                    )}
                  </div>

                  <p className={`text-xs mt-0.5 ${
                    status === 'current' ? 'text-[#E5E7EB]' : 'text-[#9CA3AF]'
                  }`}>
                    {step.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Live Status Note Footer */}
        {statusNote && (
          <div className="mt-8 pt-4 border-t border-[#2A303C] flex items-center gap-2 text-xs text-[#9CA3AF]">
            <span className="w-2 h-2 rounded-full bg-[#D4C4A8] animate-ping" />
            <span>Current Status: <strong className="text-[#E5E7EB]">{statusNote}</strong></span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
