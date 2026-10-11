import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  UserCheck, 
  Tag, 
  Search, 
  X, 
  Plus, 
  ArrowRight, 
  Briefcase
} from 'lucide-react';

export default function HumanReviewModal({ interruptData, onResume, isResuming }) {
  const initialProfile = interruptData?.profile || {};
  const initialQueries = interruptData?.queries || [];

  const [skills, setSkills] = useState(initialProfile.top_skills || []);
  const [newSkill, setNewSkill] = useState('');
  const [targetTitles, setTargetTitles] = useState(initialProfile.target_titles || []);
  const [newTitle, setNewTitle] = useState('');
  const [queries, setQueries] = useState(initialQueries);

  const handleAddSkill = (e) => {
    if ((e.key === 'Enter' || e.type === 'click') && newSkill.trim()) {
      e.preventDefault();
      const s = newSkill.trim().toLowerCase();
      if (!skills.includes(s)) {
        setSkills([...skills, s]);
      }
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const handleAddTitle = (e) => {
    if ((e.key === 'Enter' || e.type === 'click') && newTitle.trim()) {
      e.preventDefault();
      const t = newTitle.trim();
      if (!targetTitles.includes(t)) {
        setTargetTitles([...targetTitles, t]);
      }
      setNewTitle('');
    }
  };

  const handleRemoveTitle = (titleToRemove) => {
    setTargetTitles(targetTitles.filter((t) => t !== titleToRemove));
  };

  const handleQueryChange = (index, field, value) => {
    const updated = [...queries];
    updated[index] = { ...updated[index], [field]: value };
    setQueries(updated);
  };

  const handleRemoveQuery = (index) => {
    if (queries.length > 1) {
      setQueries(queries.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const updatedProfile = {
      ...initialProfile,
      top_skills: skills,
      target_titles: targetTitles,
    };
    onResume({
      profile: updatedProfile,
      queries: queries,
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="max-w-4xl mx-auto py-8 px-4"
    >
      <div className="glass-panel p-6 sm:p-8 border border-[#2A303C] shadow-2xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#2A303C] gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25 text-xs font-semibold mb-2">
              <UserCheck className="w-3.5 h-3.5" />
              <span>LangGraph Interrupt • Strategy Review Point</span>
            </div>
            <h2 className="text-2xl font-extrabold text-[#E5E7EB] tracking-tight">
              Review & Fine-Tune Your Strategy
            </h2>
            <p className="text-xs text-[#9CA3AF] mt-1">
              Review inferred profile competencies and query plan before live search executes.
            </p>
          </div>

          <button
            onClick={handleSubmit}
            disabled={isResuming}
            className="btn-champagne px-6 py-3 text-xs sm:text-sm font-semibold shadow-md flex items-center justify-center gap-2 self-start sm:self-center"
          >
            {isResuming ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-[#0A0C10] border-t-transparent rounded-full animate-spin" />
                Resuming...
              </span>
            ) : (
              <>
                <span>Looks Good, Search</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 pt-6">
          {/* Candidate Overview Card */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-[#0A0C10] border border-[#2A303C] text-xs">
            <div>
              <span className="text-[#6B7280] block text-[11px]">Seniority</span>
              <strong className="text-[#D4C4A8] capitalize">{initialProfile.seniority || 'Entry'}</strong>
            </div>
            <div>
              <span className="text-[#6B7280] block text-[11px]">Experience</span>
              <strong className="text-[#E5E7EB]">{initialProfile.years_experience || 0} years</strong>
            </div>
            <div>
              <span className="text-[#6B7280] block text-[11px]">Location</span>
              <strong className="text-[#E5E7EB] truncate block">{initialProfile.location || 'Worldwide'}</strong>
            </div>
            <div>
              <span className="text-[#6B7280] block text-[11px]">Education</span>
              <strong className="text-[#E5E7EB] truncate block">{initialProfile.education || 'Degree'}</strong>
            </div>
          </div>

          {/* Editable Skills */}
          <div>
            <label className="block text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-2">
              Top Skills ({skills.length}/12)
            </label>
            <div className="flex flex-wrap gap-2 p-3 rounded-xl bg-[#0A0C10] border border-[#2A303C] min-h-[48px]">
              {skills.map((skill) => (
                <span 
                  key={skill}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25"
                >
                  <Tag className="w-3 h-3 text-[#D4C4A8]" />
                  {skill}
                  <button 
                    type="button" 
                    onClick={() => handleRemoveSkill(skill)}
                    className="hover:text-red-400 ml-0.5"
                    aria-label={`Remove skill ${skill}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            {skills.length < 12 && (
              <div className="flex gap-2 mt-2">
                <input
                  type="text"
                  placeholder="Add skill (e.g. docker, kubernetes, redis)..."
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyDown={handleAddSkill}
                  className="flex-1 bg-[#0A0C10] border border-[#374151] rounded-xl px-4 py-2 text-xs text-[#E5E7EB] placeholder-[#6B7280] focus:outline-none focus:border-[#D4C4A8]"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="btn-secondary px-4 py-2 rounded-xl text-xs flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add
                </button>
              </div>
            )}
          </div>

          {/* Target Job Titles */}
          <div>
            <label className="block text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-2">
              Inferred Target Titles
            </label>
            <div className="flex flex-wrap gap-2 p-3 rounded-xl bg-[#0A0C10] border border-[#2A303C]">
              {targetTitles.map((title) => (
                <span 
                  key={title}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-[#1B1F28] text-[#E5E7EB] border border-[#374151]"
                >
                  <Briefcase className="w-3.5 h-3.5 text-[#D4C4A8]" />
                  {title}
                  <button 
                    type="button" 
                    onClick={() => handleRemoveTitle(title)}
                    className="hover:text-red-400 ml-1"
                    aria-label={`Remove title ${title}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            {targetTitles.length < 5 && (
              <div className="flex gap-2 mt-2">
                <input
                  type="text"
                  placeholder="Add target title..."
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  onKeyDown={handleAddTitle}
                  className="flex-1 bg-[#0A0C10] border border-[#374151] rounded-xl px-4 py-2 text-xs text-[#E5E7EB] placeholder-[#6B7280] focus:outline-none focus:border-[#D4C4A8]"
                />
                <button
                  type="button"
                  onClick={handleAddTitle}
                  className="btn-secondary px-4 py-2 rounded-xl text-xs flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Title
                </button>
              </div>
            )}
          </div>

          {/* Search Queries */}
          <div>
            <label className="block text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-2">
              Generated Search Queries ({queries.length} Parallel Queries)
            </label>
            <div className="space-y-2.5">
              {queries.map((q, idx) => (
                <div 
                  key={idx}
                  className="p-3.5 rounded-xl bg-[#0A0C10] border border-[#2A303C] flex flex-col sm:flex-row sm:items-center gap-3"
                >
                  <div className="flex items-center gap-2 sm:w-44 shrink-0">
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono uppercase bg-[#14171E] text-[#D4C4A8] border border-[#2A303C]">
                      {q.angle}
                    </span>
                    {q.site && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#1B1F28] text-[#9CA3AF] border border-[#374151]">
                        {q.site}
                      </span>
                    )}
                  </div>

                  <input
                    type="text"
                    value={q.q}
                    onChange={(e) => handleQueryChange(idx, 'q', e.target.value)}
                    className="flex-1 bg-[#14171E] border border-[#2A303C] rounded-lg px-3 py-1.5 text-xs text-[#E5E7EB] focus:outline-none focus:border-[#D4C4A8] font-mono"
                  />

                  {queries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuery(idx)}
                      className="text-[#6B7280] hover:text-red-400 self-end sm:self-center"
                      aria-label="Remove query"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Action buttons footer */}
          <div className="pt-4 border-t border-[#2A303C] flex items-center justify-end gap-3">
            <button
              type="submit"
              disabled={isResuming}
              className="btn-champagne w-full sm:w-auto px-8 py-3.5 text-sm font-semibold shadow-xl flex items-center justify-center gap-2"
            >
              {isResuming ? 'Launching Multi-Source Search...' : 'Looks good, search'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
