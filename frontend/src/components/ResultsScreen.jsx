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
  Sparkles,
  ShieldCheck,
  Target,
  Globe
} from 'lucide-react';

export default function ResultsScreen({ 
  jobs, 
  statusNote, 
  sourceCounts,
  sourceStatuses,
  funnel,
  countriesUsed,
  expansionAction,
  onRerank, 
  isReranking, 
  onReset,
  currentPreferences 
}) {
  const [showFunnelDetails, setShowFunnelDetails] = useState(false);
  const [sortBy, setSortBy] = useState(currentPreferences?.sort_by || 'match');
  const [minSalaryLPA, setMinSalaryLPA] = useState(
    currentPreferences?.min_salary_inr_annual 
      ? Math.round(currentPreferences.min_salary_inr_annual / 100000) 
      : 0
  );
  const [selectedJobTypes, setSelectedJobTypes] = useState(
    currentPreferences?.job_types || ['fte', 'intern', 'contract', 'part_time']
  );
  // Min Score Filter (default 20% fit, range 20-100)
  const [minScore, setMinScore] = useState(20);

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

  // Grand Tourer Champagne Intensity Score Colors
  const getChampagneScoreStyle = (score) => {
    if (score >= 80) {
      return { 
        stroke: '#D4C4A8', 
        text: 'text-[#D4C4A8]', 
        badgeBg: 'bg-[#D4C4A8]/15',
        badgeBorder: 'border-[#D4C4A8]/40',
        badgeText: 'text-[#D4C4A8]',
        glow: 'shadow-[0_0_12px_rgba(212,196,168,0.35)]',
        label: 'Exceptional Fit'
      };
    }
    if (score >= 60) {
      return { 
        stroke: '#C5B293', 
        text: 'text-[#C5B293]', 
        badgeBg: 'bg-[#D4C4A8]/10',
        badgeBorder: 'border-[#D4C4A8]/25',
        badgeText: 'text-[#C5B293]',
        glow: '',
        label: 'Strong Match'
      };
    }
    if (score >= 40) {
      return { 
        stroke: '#9CA3AF', 
        text: 'text-[#9CA3AF]', 
        badgeBg: 'bg-[#1B1F28]',
        badgeBorder: 'border-[#374151]',
        badgeText: 'text-[#9CA3AF]',
        glow: '',
        label: 'Moderate Alignment'
      };
    }
    return { 
      stroke: '#4B5563', 
      text: 'text-[#6B7280]', 
      badgeBg: 'bg-[#14171E]',
      badgeBorder: 'border-[#2A303C]',
      badgeText: 'text-[#6B7280]',
      glow: '',
      label: 'Adjacent Role'
    };
  };

  // Filter jobs dynamically by client-side minScore slider
  const displayedJobs = jobs.filter((job) => (job.score || 0) >= minScore);

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Execution Summary Banner */}
      {statusNote && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl glass-panel border border-[#2A303C] flex items-start sm:items-center justify-between gap-3 shadow-lg"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#D4C4A8]/15 text-[#D4C4A8] shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-[#E5E7EB]">Agent Execution Summary</h4>
              <p className="text-xs text-[#9CA3AF]">{statusNote}</p>
            </div>
          </div>
          <button
            onClick={onReset}
            className="btn-secondary text-xs px-3 py-1.5 rounded-lg shrink-0 flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Search
          </button>
        </motion.div>
      )}

      {/* Per-Source Feeds Queried Bar */}
      <div className="glass-panel px-4 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-[#D4C4A8]" />
          <span className="font-semibold text-[#E5E7EB]">Multi-Source Feed Audited:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          {['Adzuna', 'JSearch', 'Remotive', 'Arbeitnow', 'Greenhouse'].map((src) => {
            const statusInfo = sourceStatuses?.[src];
            const fallbackCount = sourceCounts?.[src] ?? jobs.filter(j => j.source === src).length;
            const count = statusInfo ? statusInfo.count : fallbackCount;
            const status = statusInfo ? statusInfo.status : (fallbackCount > 0 ? 'ok' : 'ok');
            const reason = statusInfo?.reason || (count > 0 ? `ok (${count} jobs)` : 'ok (0 jobs for these queries)');
            const elapsed = statusInfo?.elapsed_s ? ` • ${statusInfo.elapsed_s}s` : '';
            const tooltip = `${reason}${elapsed}`;

            let labelText = '';
            let badgeClasses = 'bg-[#0A0C10] border-[#2A303C] text-[#E5E7EB]';
            let iconDot = null;

            if (status === 'ok') {
              if (count > 0) {
                labelText = `${src}: ok (${count} jobs)`;
                badgeClasses = 'bg-[#14171E] border-[#D4C4A8]/30 text-[#E5E7EB]';
                iconDot = <span className="w-1.5 h-1.5 rounded-full bg-[#D4C4A8]" />;
              } else {
                labelText = `${src}: ok (0 jobs for these queries)`;
                badgeClasses = 'bg-[#0A0C10] border-[#374151] text-[#9CA3AF]';
                iconDot = <span className="w-1.5 h-1.5 rounded-full bg-[#4B5563]" />;
              }
            } else if (status === 'auth failed') {
              labelText = `${src}: auth failed`;
              badgeClasses = 'bg-rose-950/40 border-rose-700/50 text-rose-300';
              iconDot = <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />;
            } else if (status === 'rate limited') {
              labelText = `${src}: rate limited`;
              badgeClasses = 'bg-amber-950/40 border-amber-700/50 text-amber-300';
              iconDot = <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />;
            } else if (status === 'not configured') {
              labelText = `${src}: not configured`;
              badgeClasses = 'bg-[#14171E] border-[#374151] text-[#9CA3AF]';
              iconDot = <span className="w-1.5 h-1.5 rounded-full bg-[#4B5563]" />;
            } else if (status === 'timeout') {
              labelText = `${src}: timeout`;
              badgeClasses = 'bg-orange-950/40 border-orange-700/50 text-orange-300';
              iconDot = <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />;
            } else {
              labelText = `${src}: ${status}`;
              badgeClasses = 'bg-rose-950/40 border-rose-700/50 text-rose-300';
              iconDot = <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />;
            }

            return (
              <span
                key={src}
                title={tooltip}
                className={`group relative inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-all cursor-help ${badgeClasses}`}
              >
                {iconDot}
                <span>{labelText}</span>
                {statusInfo?.elapsed_s > 0 && (
                  <span className="text-[9px] text-[#9CA3AF]/70 font-mono">({statusInfo.elapsed_s}s)</span>
                )}
              </span>
            );
          })}
          <span 
            title="Total verified deduplicated real job opportunities"
            className="px-2.5 py-1 rounded-lg bg-[#D4C4A8]/15 border border-[#D4C4A8]/30 text-[#D4C4A8] cursor-help"
          >
            Deduped: <strong className="text-white">{sourceCounts?.deduped ?? jobs.length}</strong>
          </span>
        </div>
      </div>

      {/* Worldwide Coverage & Quality Gate Expansion Alerts */}
      <div className="flex flex-wrap items-center gap-3">
        {countriesUsed && countriesUsed.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono text-[#D4C4A8] bg-[#D4C4A8]/10 px-3.5 py-2 rounded-xl border border-[#D4C4A8]/25">
            <Globe className="w-3.5 h-3.5" />
            <span>Search Geographic Scope: <strong>{countriesUsed.map(c => c.toUpperCase()).join(', ')}</strong> + Remote</span>
          </div>
        )}
        {expansionAction && (
          <div className="flex items-center gap-2 text-xs text-amber-200 bg-amber-950/30 px-3.5 py-2 rounded-xl border border-amber-500/30">
            <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
            <span><strong>Quality Gate Expanded Search:</strong> {expansionAction}</span>
          </div>
        )}
      </div>

      {/* Ingestion & Filtering Funnel Card */}
      {funnel && (
        <div className="glass-panel p-4 rounded-2xl border border-[#2A303C]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-[#D4C4A8]" />
              <h4 className="text-xs font-bold text-[#E5E7EB] uppercase tracking-wider">
                Pipeline Funnel Counter & Audit Verification
              </h4>
            </div>
            <button
              onClick={() => setShowFunnelDetails(!showFunnelDetails)}
              className="text-[11px] font-semibold text-[#D4C4A8] hover:underline flex items-center gap-1"
            >
              {showFunnelDetails ? 'Hide Drop Reasons' : 'View Drop Reasons & Details'}
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-center text-xs">
            <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              <span className="text-[10px] text-[#9CA3AF] block uppercase">1. Fetched</span>
              <strong className="text-sm text-[#E5E7EB]">{funnel.fetched?.total ?? 0}</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              <span className="text-[10px] text-[#9CA3AF] block uppercase">2. Normalized</span>
              <strong className="text-sm text-[#E5E7EB]">{funnel.normalized?.count ?? 0}</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              <span className="text-[10px] text-[#9CA3AF] block uppercase">3. Deduped</span>
              <strong className="text-sm text-[#E5E7EB]">{funnel.deduped?.count ?? 0}</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              <span className="text-[10px] text-[#9CA3AF] block uppercase">4. Hard Filters</span>
              <strong className="text-sm text-[#E5E7EB]">{funnel.hard_filters?.passed ?? 0}</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              <span className="text-[10px] text-[#9CA3AF] block uppercase">5. Scored (≥20)</span>
              <strong className="text-sm text-[#D4C4A8]">{funnel.scored?.passed_threshold ?? jobs.length}</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-[#14171E] border border-[#D4C4A8]/30">
              <span className="text-[10px] text-[#D4C4A8] block uppercase">6. Displayed</span>
              <strong className="text-sm text-[#D4C4A8] font-bold">{displayedJobs.length}</strong>
            </div>
          </div>

          {/* Expandable Drop Breakdown */}
          {(showFunnelDetails || displayedJobs.length === 0) && funnel.hard_filters?.drop_reasons && (
            <div className="mt-3 pt-3 border-t border-[#2A303C] space-y-2 text-xs">
              <span className="text-[11px] font-semibold text-[#9CA3AF] block">
                Hard Filter Drops & Reasons:
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                {Object.entries(funnel.hard_filters.drop_reasons).map(([reason, data]) => {
                  if (!data || data.count === 0) return null;
                  return (
                    <div key={reason} className="p-2 rounded-lg bg-[#0A0C10] border border-[#2A303C]/80">
                      <div className="flex items-center justify-between text-amber-300 font-semibold mb-1">
                        <span>{reason.replace(/_/g, ' ')}</span>
                        <span>{data.count} dropped</span>
                      </div>
                      {data.examples && data.examples.length > 0 && (
                        <ul className="text-[#9CA3AF] text-[10px] list-disc list-inside space-y-0.5">
                          {data.examples.slice(0, 5).map((ex, idx) => (
                            <li key={idx} className="truncate">{ex}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
                {funnel.deduped?.dropped > 0 && (
                  <div className="p-2 rounded-lg bg-[#0A0C10] border border-[#2A303C]/80">
                    <div className="flex items-center justify-between text-blue-300 font-semibold mb-1">
                      <span>duplicate links/companies</span>
                      <span>{funnel.deduped.dropped} dropped</span>
                    </div>
                    {funnel.deduped.examples_dropped && (
                      <ul className="text-[#9CA3AF] text-[10px] list-disc list-inside space-y-0.5">
                        {funnel.deduped.examples_dropped.slice(0, 5).map((ex, idx) => (
                          <li key={idx} className="truncate">{ex}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {funnel.scored?.below_threshold > 0 && (
                  <div className="p-2 rounded-lg bg-[#0A0C10] border border-[#2A303C]/80">
                    <div className="flex items-center justify-between text-rose-300 font-semibold mb-1">
                      <span>score below 20%</span>
                      <span>{funnel.scored.below_threshold} below</span>
                    </div>
                    {funnel.scored.examples_below && (
                      <ul className="text-[#9CA3AF] text-[10px] list-disc list-inside space-y-0.5">
                        {funnel.scored.examples_below.slice(0, 5).map((ex, idx) => (
                          <li key={idx} className="truncate">{ex}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filter Controls Bar */}
      <div className="glass-panel p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4 sm:gap-6">
          {/* Sort By Dropdown */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-[#D4C4A8]" />
            <span className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="bg-[#0A0C10] border border-[#2A303C] rounded-xl px-3 py-1.5 text-xs font-semibold text-[#E5E7EB] focus:outline-none focus:border-[#D4C4A8]"
            >
              <option value="match">Fit Score (Best Match)</option>
              <option value="salary">Salary (Highest First)</option>
              <option value="recency">Posting Date (Newest)</option>
            </select>
          </div>

          {/* Min Fit Score Slider (Default 20) */}
          <div className="flex items-center gap-2 pl-2 lg:border-l lg:border-[#2A303C]">
            <Target className="w-3.5 h-3.5 text-[#D4C4A8]" />
            <span className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider">Min Score:</span>
            <input
              type="range"
              min="20"
              max="95"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-20 sm:w-28 h-1.5 bg-[#222733] rounded-lg appearance-none cursor-pointer accent-[#D4C4A8]"
            />
            <span className="text-xs font-mono font-bold text-[#D4C4A8] min-w-[42px]">
              {minScore}%+
            </span>
          </div>

          {/* Min Salary Filter Slider */}
          <div className="flex items-center gap-2 pl-2 lg:border-l lg:border-[#2A303C]">
            <span className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider">Min Pay:</span>
            <input
              type="range"
              min="0"
              max="40"
              step="1"
              value={minSalaryLPA}
              onChange={(e) => handleSalaryChange(Number(e.target.value))}
              className="w-20 sm:w-28 h-1.5 bg-[#222733] rounded-lg appearance-none cursor-pointer accent-[#D4C4A8]"
            />
            <span className="text-xs font-mono font-bold text-[#D4C4A8] min-w-[48px]">
              {minSalaryLPA === 0 ? 'Any' : `₹${minSalaryLPA}L`}
            </span>
          </div>

          {/* Job Types Chips */}
          <div className="flex items-center gap-1.5 pl-2 lg:border-l lg:border-[#2A303C]">
            {['fte', 'intern', 'contract', 'part_time'].map((type) => {
              const active = selectedJobTypes.includes(type);
              return (
                <button
                  key={type}
                  onClick={() => handleJobTypeToggle(type)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg uppercase font-semibold transition-all ${
                    active ? 'chip-selected' : 'chip-unselected'
                  }`}
                >
                  {type === 'part_time' ? 'PT' : type}
                </button>
              );
            })}
          </div>
        </div>

        {/* Counter and Zero LLM token badge */}
        <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 lg:pt-0 border-t lg:border-t-0 border-[#2A303C]">
          <div className="text-right">
            <span className="text-xs font-bold text-[#E5E7EB]">{displayedJobs.length} Ranked Openings</span>
            <span className="block text-[10px] text-[#D4C4A8]">Instant local filter • 0 LLM spend</span>
          </div>
          {isReranking && (
            <div className="w-4 h-4 border-2 border-[#D4C4A8]/30 border-t-[#D4C4A8] rounded-full animate-spin" />
          )}
        </div>
      </div>

      {/* Jobs Grid */}
      {displayedJobs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {displayedJobs.map((job, idx) => {
            const scoreStyle = getChampagneScoreStyle(job.score);
            const radius = 22;
            const circumference = 2 * Math.PI * radius;
            const strokeDashoffset = circumference - ((job.score || 50) / 100) * circumference;
            const isVerified = Boolean(job.url && (job.url.startsWith('http') || job.is_real_posting));

            return (
              <motion.div
                key={job.url || idx}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.22, delay: idx * 0.03 }}
                className="glass-card rounded-2xl p-5 flex flex-col justify-between relative group overflow-hidden"
              >
                <div>
                  {/* Top Bar: Company, Verified Badge & Score Ring */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#9CA3AF] truncate block max-w-[140px]">
                          {job.company || 'Direct Employer'}
                        </span>
                        {/* Source Feed Badge */}
                        <span 
                          className="inline-flex items-center text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-[#0A0C10] text-[#D4C4A8] border border-[#2A303C] shrink-0"
                          title={`Direct feed via ${job.source || 'Adzuna'}`}
                        >
                          {job.source || 'Adzuna'}
                        </span>
                        {/* Verified Open Status Badge */}
                        {isVerified ? (
                          <span 
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#D4C4A8]/12 text-[#D4C4A8] border border-[#D4C4A8]/30 shrink-0"
                            title="Verified active job posting"
                          >
                            <ShieldCheck className="w-3 h-3 text-[#D4C4A8]" />
                            Verified Open
                          </span>
                        ) : (
                          <span 
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#1B1F28] text-[#9CA3AF] border border-[#2A303C] shrink-0"
                            title="Direct web listing"
                          >
                            <Clock className="w-3 h-3 text-[#6B7280]" />
                            Web Listing
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-bold text-[#E5E7EB] group-hover:text-white transition-colors line-clamp-2">
                        {job.title || 'Software Position'}
                      </h3>
                    </div>

                    {/* Circular Score Ring (Champagne Intensity) */}
                    <div className={`relative w-14 h-14 shrink-0 flex items-center justify-center rounded-full ${scoreStyle.glow}`}>
                      <svg className="w-14 h-14 transform -rotate-90">
                        <circle
                          cx="28"
                          cy="28"
                          r={radius}
                          stroke="#222733"
                          strokeWidth="3.5"
                          fill="transparent"
                        />
                        <circle
                          cx="28"
                          cy="28"
                          r={radius}
                          stroke={scoreStyle.stroke}
                          strokeWidth="3.5"
                          strokeDasharray={circumference}
                          strokeDashoffset={strokeDashoffset}
                          strokeLinecap="round"
                          fill="transparent"
                          className="transition-all duration-700 ease-out"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={`text-xs font-black ${scoreStyle.text}`}>
                          {job.score}
                        </span>
                        <span className="text-[8px] text-[#9CA3AF] font-bold uppercase tracking-tighter">FIT</span>
                      </div>
                    </div>
                  </div>

                  {/* Badges: Salary, Job Type, Location */}
                  <div className="flex flex-wrap gap-1.5 mb-4 text-[11px]">
                    <span 
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-[#0A0C10] text-[#D4C4A8] font-mono font-semibold border border-[#2A303C]"
                      title={job.salary_is_predicted ? "Estimated by source, not employer-published" : "Published compensation"}
                    >
                      <DollarSign className="w-3 h-3" />
                      {formatSalary(job)}
                      {job.salary_is_predicted && (
                        <span className="text-[9px] text-[#9CA3AF] ml-0.5 font-normal">(Est.)</span>
                      )}
                    </span>

                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-[#0A0C10] text-[#E5E7EB] capitalize border border-[#2A303C]">
                      <Briefcase className="w-3 h-3 text-[#9CA3AF]" />
                      {job.job_type === 'fte' ? 'Full Time' : job.job_type || 'Full Time'}
                    </span>

                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-[#0A0C10] text-[#E5E7EB] border border-[#2A303C]">
                      <MapPin className="w-3 h-3 text-[#9CA3AF]" />
                      {job.location || 'Remote'}
                    </span>
                  </div>

                  {/* AI Fit Reasoning */}
                  {job.reason && (
                    <div className="p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C] mb-3 text-xs text-[#E5E7EB]/90 leading-relaxed italic">
                      "{job.reason}"
                    </div>
                  )}

                  {/* Why You're a Fit Bullets */}
                  {job.why_fit && job.why_fit.length > 0 && (
                    <div className="mb-3 p-2.5 rounded-xl bg-[#1B1F28] border border-[#2A303C]">
                      <span className="text-[10px] uppercase font-bold text-[#D4C4A8] tracking-wider flex items-center gap-1 mb-1.5">
                        <Sparkles className="w-3 h-3" />
                        Why You're a Fit
                      </span>
                      <ul className="space-y-1">
                        {job.why_fit.map((point, pIdx) => (
                          <li key={pIdx} className="text-xs text-[#E5E7EB] flex items-start gap-1.5">
                            <span className="text-[#D4C4A8] mt-0.5">•</span>
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Matched Skills */}
                  {job.matched_skills && job.matched_skills.length > 0 && (
                    <div className="mb-2">
                      <span className="text-[10px] uppercase font-bold text-[#9CA3AF] tracking-wider block mb-1">
                        Matched Skills
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.matched_skills.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25"
                          >
                            <CheckCircle className="w-2.5 h-2.5 text-[#D4C4A8]" />
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Skill Gaps (Muted Amber) */}
                  {job.missing_skills && job.missing_skills.length > 0 && (
                    <div className="mb-3">
                      <span className="text-[10px] uppercase font-bold text-[#9CA3AF] tracking-wider block mb-1">
                        Skill Gaps
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.missing_skills.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-[#FBBF24]/10 text-[#FBBF24] border border-[#FBBF24]/20"
                          >
                            <AlertCircle className="w-2.5 h-2.5 text-[#FBBF24]" />
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Technical Interview Tip */}
                  {job.interview_tip && (
                    <div className="mb-4 p-2.5 rounded-xl bg-[#0A0C10] border border-[#2A303C] text-xs">
                      <span className="text-[10px] uppercase font-bold text-[#D4C4A8] tracking-wider flex items-center gap-1 mb-1">
                        <Info className="w-3 h-3" />
                        Interview Prep Tip
                      </span>
                      <p className="text-[#9CA3AF] text-[11px] leading-relaxed">
                        {job.interview_tip}
                      </p>
                    </div>
                  )}
                </div>

                {/* Card Footer: Apply Link */}
                <div className="pt-3 border-t border-[#2A303C] flex items-center justify-between mt-auto">
                  <span className="text-[10px] text-[#6B7280] flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {job.posted_date ? 'Active' : 'Live Opening'}
                  </span>

                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-champagne px-4 py-2 text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-sm"
                  >
                    <span>Apply Online</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        <div className="glass-panel p-12 text-center">
          <ShieldAlert className="w-12 h-12 text-[#D4C4A8] mx-auto mb-3" />
          <h3 className="text-lg font-bold text-[#E5E7EB] mb-1">No Jobs Matched Active Filter Criteria</h3>
          <p className="text-xs text-[#9CA3AF] max-w-md mx-auto mb-6">
            Current minimum score threshold ({minScore}%) or salary filter may be too restrictive. Lower the score threshold or reset filters to display all ranked opportunities.
          </p>
          <button
            onClick={() => {
              setMinSalaryLPA(0);
              setMinScore(20);
              setSelectedJobTypes(['fte', 'intern', 'contract', 'part_time']);
              triggerRerank(sortBy, 0, ['fte', 'intern', 'contract', 'part_time']);
            }}
            className="btn-champagne px-5 py-2.5 text-xs font-semibold"
          >
            Reset Filters & View All
          </button>
        </div>
      )}
    </div>
  );
}
