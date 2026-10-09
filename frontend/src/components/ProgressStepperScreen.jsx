import React from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  Loader2, 
  Circle, 
  FileText, 
  Brain, 
  UserCheck, 
  Search, 
  Filter, 
  Layers, 
  Cpu, 
  Award, 
  Sliders, 
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';

const STEPS = [
  {
    id: 'extract_text',
    label: 'Extract Resume Text',
    desc: 'Extracting PDF layout, stripping noise, computing cache hash',
    icon: FileText,
  },
  {
    id: 'profile_and_queries',
    label: 'Synthesize Profile & Queries',
    desc: 'Gemini Flash: extracting skills, seniority & search queries',
    icon: Brain,
  },
  {
    id: 'human_review',
    label: 'Human-in-the-Loop Review',
    desc: 'Paused for your feedback on skills, titles, and queries',
    icon: UserCheck,
  },
  {
    id: 'search',
    matchNodes: ['search_dispatcher', 'search_one'],
    label: 'Parallel Web Search',
    desc: 'Searching Exa with DuckDuckGo fallback in parallel',
    icon: Search,
  },
  {
    id: 'rule_filter',
    label: 'Rule Filter & Deduplication',
    desc: 'Filtering out non-postings, stale jobs, and computing skill overlap',
    icon: Filter,
  },
  {
    id: 'batch_builder',
    label: 'Batch Builder',
    desc: 'Trimming postings and packaging within token budgets',
    icon: Layers,
  },
  {
    id: 'extract_jobs',
    label: 'Structured Job Extraction',
    desc: 'Groq 8B: extracting real postings, salaries, and requirements',
    icon: Cpu,
  },
  {
    id: 'score_jobs',
    label: 'Rubric Fit Evaluation',
    desc: 'Gemini Flash: scoring candidate fit on 100-point rubric',
    icon: Award,
  },
  {
    id: 'ranker',
    label: 'Deterministic Ranking',
    desc: 'Filtering by preferences and sorting top jobs in code',
    icon: Sliders,
  },
  {
    id: 'quality_gate',
    matchNodes: ['quality_gate', 'query_refiner'],
    label: 'Quality Gate & Verification',
    desc: 'Ensuring strong match threshold (>= 5 jobs with score >= 50)',
    icon: ShieldCheck,
  },
];

export default function ProgressStepperScreen({ completedNodes, currentNode, statusNote, nodeSummaries }) {
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
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="max-w-3xl mx-auto py-10 px-4"
    >
      <div className="glass-panel rounded-2xl p-6 sm:p-8">
        <div className="border-b border-slate-800 pb-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
                Pipeline In Progress
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                LangGraph is streaming execution events live via Server-Sent Events (SSE)
              </p>
            </div>
            {statusNote && (
              <span className="hidden sm:inline-block text-xs px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 max-w-xs truncate">
                {statusNote}
              </span>
            )}
          </div>
        </div>

        {/* Stepper list */}
        <div className="relative pl-6 sm:pl-8 space-y-7 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
          {STEPS.map((step, idx) => {
            const status = getStepStatus(step);
            const Icon = step.icon;
            const summary = nodeSummaries[step.id] || (step.matchNodes && step.matchNodes.map(n => nodeSummaries[n]).filter(Boolean)[0]);

            return (
              <div key={step.id} className="relative flex items-start gap-4">
                {/* Node icon / indicator */}
                <div className="absolute -left-6 sm:-left-8 top-0.5 flex items-center justify-center">
                  {status === 'completed' ? (
                    <div className="w-6 h-6 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center ring-4 ring-slate-900 shadow-md shadow-emerald-500/20">
                      <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                    </div>
                  ) : status === 'current' ? (
                    <div className="w-6 h-6 rounded-full bg-emerald-400 text-slate-950 flex items-center justify-center ring-4 ring-emerald-500/20 animate-pulse">
                      <Loader2 className="w-4 h-4 animate-spin stroke-[2.5]" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center ring-4 ring-slate-900">
                      <Circle className="w-3 h-3 fill-slate-700" />
                    </div>
                  )}
                </div>

                {/* Step content */}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-sm font-semibold flex items-center gap-2 ${
                      status === 'current' ? 'text-emerald-400' : status === 'completed' ? 'text-white' : 'text-slate-500'
                    }`}>
                      <Icon className="w-4 h-4" />
                      {step.label}
                    </h3>

                    {summary && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-emerald-300 border border-slate-700">
                        {summary}
                      </span>
                    )}
                  </div>

                  <p className={`text-xs mt-0.5 ${
                    status === 'current' ? 'text-slate-300' : 'text-slate-500'
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
          <div className="mt-8 pt-4 border-t border-slate-800 flex items-center gap-2 text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Current Status: <strong className="text-slate-200">{statusNote}</strong></span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
