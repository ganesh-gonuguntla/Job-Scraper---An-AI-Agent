import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Briefcase, 
  MapPin, 
  ExternalLink, 
  CheckCircle, 
  AlertCircle, 
  DollarSign, 
  Clock, 
  RotateCcw, 
  SlidersHorizontal,
  Info,
  ShieldAlert,
  Sparkles
} from 'lucide-react';

export default function ResultsScreen({ 
  jobs, 
  statusNote, 
  onRerank, 
  isReranking, 
  onReset,
  currentPreferences 
}) {
  const [sortBy, setSortBy] = useState(currentPreferences?.sort_by || 'match');
  const [minSalaryLPA, setMinSalaryLPA] = useState(
    currentPreferences?.min_salary_inr_annual 
      ? Math.round(currentPreferences.min_salary_inr_annual / 100000) 
      : 0
  );
  const [selectedJobTypes, setSelectedJobTypes] = useState(
    currentPreferences?.job_types || ['fte', 'intern', 'contract', 'part_time']
  );

  const handleSortChange = (newSort) => {
    setSortBy(newSort);
    triggerRerank(newSort, minSalaryLPA, selectedJobTypes);
  };

  const handleSalaryChange = (newLPA) => {
    setMinSalaryLPA(newLPA);
    triggerRerank(sortBy, newLPA, selectedJobTypes);
  };

  const handleJobTypeToggle = (type) => {
    let updated;
    if (selectedJobTypes.includes(type)) {
      if (selectedJobTypes.length > 1) {
        updated = selectedJobTypes.filter((t) => t !== type);
      } else {
        return;
      }
    } else {
      updated = [...selectedJobTypes, type];
    }
    setSelectedJobTypes(updated);
    triggerRerank(sortBy, minSalaryLPA, updated);
  };

  const triggerRerank = (sortVal, salLPA, types) => {
    onRerank({
      ...currentPreferences,
      sort_by: sortVal,
      min_salary_inr_annual: salLPA > 0 ? salLPA * 100000 : null,
      job_types: types,
    });
  };

  const formatSalary = (job) => {
    if (job.salary_annual_inr) {
      const lpa = (job.salary_annual_inr / 100000).toFixed(1);
      return `₹${lpa} LPA`;
    }
    if (job.salary_min && job.salary_max) {
      return `${job.salary_currency || ''} ${job.salary_min} - ${job.salary_max} / ${job.salary_period || 'yr'}`;
    }
    if (job.salary_min) {
      return `${job.salary_currency || ''} ${job.salary_min} / ${job.salary_period || 'yr'}`;
    }
    return 'Not listed';
  };

  const getScoreColor = (score) => {
    if (score >= 85) return { stroke: '#10b981', text: 'text-emerald-400', bg: 'bg-emerald-500/10' };
    if (score >= 70) return { stroke: '#14b8a6', text: 'text-teal-400', bg: 'bg-teal-500/10' };
    if (score >= 50) return { stroke: '#3b82f6', text: 'text-blue-400', bg: 'bg-blue-500/10' };
    return { stroke: '#f59e0b', text: 'text-amber-400', bg: 'bg-amber-500/10' };
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Status Note Banner */}
      {statusNote && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-slate-900/90 border border-emerald-500/30 flex items-start sm:items-center justify-between gap-3 shadow-lg"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">Agent Execution Summary</h4>
              <p className="text-xs text-slate-300">{statusNote}</p>
            </div>
          </div>
          <button
            onClick={onReset}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0 flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Search
          </button>
        </motion.div>
      )}

      {/* Instant Controls & Filters Bar */}
      <div className="glass-panel rounded-2xl p-4 sm:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Sort By Dropdown */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs font-semibold text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="match">Fit Score (Best Match)</option>
              <option value="salary">Salary (Highest First)</option>
              <option value="recency">Posting Date (Newest)</option>
            </select>
          </div>

          {/* Min Salary Filter Slider */}
          <div className="flex items-center gap-2 pl-2 md:border-l md:border-slate-800">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Min Pay:</span>
            <input
              type="range"
              min="0"
              max="40"
              step="1"
              value={minSalaryLPA}
              onChange={(e) => handleSalaryChange(Number(e.target.value))}
              className="w-24 sm:w-32 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <span className="text-xs font-mono font-bold text-emerald-400 min-w-[55px]">
              {minSalaryLPA === 0 ? 'Any' : `₹${minSalaryLPA}L`}
            </span>
          </div>

          {/* Job Types Chips */}
          <div className="flex items-center gap-1.5 pl-2 md:border-l md:border-slate-800">
            {['fte', 'intern', 'contract', 'part_time'].map((type) => {
              const active = selectedJobTypes.includes(type);
              return (
                <button
                  key={type}
                  onClick={() => handleJobTypeToggle(type)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg uppercase font-semibold transition-all ${
                    active
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-slate-900 text-slate-500 border border-slate-800 hover:text-slate-400'
                  }`}
                >
                  {type === 'part_time' ? 'PT' : type}
                </button>
              );
            })}
          </div>
        </div>

        {/* Counter and Zero LLM token badge */}
        <div className="flex items-center justify-between sm:justify-end gap-3">
          <div className="text-right">
            <span className="text-xs font-bold text-white">{jobs.length} Matching Jobs</span>
            <span className="block text-[10px] text-emerald-400">0 LLM calls on rerank</span>
          </div>
          {isReranking && (
            <div className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
          )}
        </div>
      </div>

      {/* Jobs Grid */}
      {jobs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {jobs.map((job, idx) => {
            const scoreColor = getScoreColor(job.score);
            const radius = 22;
            const circumference = 2 * Math.PI * radius;
            const strokeDashoffset = circumference - (job.score / 100) * circumference;

            return (
              <motion.div
                key={job.url || idx}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: idx * 0.04 }}
                className="glass-card rounded-2xl p-5 flex flex-col justify-between relative group overflow-hidden"
              >
                <div>
                  {/* Top Bar: Company + Score Ring */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block truncate">
                        {job.company || 'Direct Employer'}
                      </span>
                      <h3 className="text-base font-bold text-white group-hover:text-emerald-400 transition-colors line-clamp-2 mt-0.5">
                        {job.title || 'Software Position'}
                      </h3>
                    </div>

                    {/* Circular Score Ring */}
                    <div className="relative w-14 h-14 shrink-0 flex items-center justify-center">
                      <svg className="w-14 h-14 transform -rotate-90">
                        <circle
                          cx="28"
                          cy="28"
                          r={radius}
                          stroke="#1e293b"
                          strokeWidth="3.5"
                          fill="transparent"
                        />
                        <circle
                          cx="28"
                          cy="28"
                          r={radius}
                          stroke={scoreColor.stroke}
                          strokeWidth="3.5"
                          strokeDasharray={circumference}
                          strokeDashoffset={strokeDashoffset}
                          strokeLinecap="round"
                          fill="transparent"
                          className="transition-all duration-700 ease-out"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={`text-xs font-black ${scoreColor.text}`}>
                          {job.score}
                        </span>
                        <span className="text-[8px] text-slate-500 font-bold uppercase">FIT</span>
                      </div>
                    </div>
                  </div>

                  {/* Badges: Salary, Job Type, Location */}
                  <div className="flex flex-wrap gap-1.5 mb-4 text-[11px]">
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-800/90 text-emerald-300 font-mono font-semibold border border-slate-700">
                      <DollarSign className="w-3 h-3" />
                      {formatSalary(job)}
                    </span>

                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-800 text-slate-300 capitalize border border-slate-700">
                      <Briefcase className="w-3 h-3 text-slate-400" />
                      {job.job_type === 'fte' ? 'Full Time' : job.job_type}
                    </span>

                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      {job.location || 'Remote'}
                    </span>
                  </div>

                  {/* AI Fit Reasoning */}
                  {job.reason && (
                    <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/80 mb-4 text-xs text-slate-300 leading-relaxed italic">
                      "{job.reason}"
                    </div>
                  )}

                  {/* Matched Skills */}
                  {job.matched_skills && job.matched_skills.length > 0 && (
                    <div className="mb-2">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">
                        Matched Skills
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.matched_skills.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/25"
                          >
                            <CheckCircle className="w-2.5 h-2.5 text-emerald-400" />
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Missing Skills */}
                  {job.missing_skills && job.missing_skills.length > 0 && (
                    <div className="mb-4">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">
                        Skill Gaps
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.missing_skills.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/25"
                          >
                            <AlertCircle className="w-2.5 h-2.5 text-amber-400" />
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Footer: Apply Link */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between mt-auto">
                  <span className="text-[10px] text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {job.posted_date ? 'Active' : 'Recently scraped'}
                  </span>

                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-emerald-600 text-white font-semibold text-xs transition-colors group-hover:bg-emerald-600 shadow-md"
                  >
                    <span>Apply Now</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-12 text-center">
          <ShieldAlert className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-white mb-1">No Jobs Matched Active Filter Criteria</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Try lowering your minimum salary threshold, enabling additional job types (e.g. Intern / Contract), or sorting by Best Match.
          </p>
          <button
            onClick={() => {
              setMinSalaryLPA(0);
              setSelectedJobTypes(['fte', 'intern', 'contract', 'part_time']);
              triggerRerank(sortBy, 0, ['fte', 'intern', 'contract', 'part_time']);
            }}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
          >
            Reset Filters
          </button>
        </div>
      )}
    </div>
  );
}
