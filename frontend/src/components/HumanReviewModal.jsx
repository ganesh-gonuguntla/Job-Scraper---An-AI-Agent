import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  UserCheck, 
  Sparkles, 
  Tag, 
  Search, 
  X, 
  Plus, 
  ArrowRight, 
  Briefcase, 
  GraduationCap, 
  MapPin, 
  Clock 
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
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="max-w-4xl mx-auto py-8 px-4"
    >
      <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-emerald-500/40 shadow-2xl shadow-emerald-500/10">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 text-xs font-semibold mb-2">
              <UserCheck className="w-3.5 h-3.5" />
              <span>LangGraph Interrupt • Human Review Point</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white">
              Review & Fine-Tune Your Strategy
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Our AI built this candidate profile and query plan. You can edit skills, target titles, or queries before search starts.
            </p>
          </div>

          <button
            onClick={handleSubmit}
            disabled={isResuming}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm shadow-lg shadow-emerald-500/25 flex items-center justify-center gap-2 transition-all self-start sm:self-center"
          >
            {isResuming ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
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
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
            <div>
              <span className="text-slate-500 block">Seniority</span>
              <strong className="text-emerald-400 capitalize">{initialProfile.seniority || 'Entry'}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Experience</span>
              <strong className="text-white">{initialProfile.years_experience || 0} years</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Location</span>
              <strong className="text-white truncate block">{initialProfile.location || 'Remote'}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Education</span>
              <strong className="text-white truncate block">{initialProfile.education || 'Degree'}</strong>
            </div>
          </div>

          {/* Editable Skills */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Top Skills ({skills.length}/12)
            </label>
            <div className="flex flex-wrap gap-2 p-3 rounded-xl bg-slate-900/40 border border-slate-800 min-h-[48px]">
              {skills.map((skill) => (
                <span 
                  key={skill}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                >
                  <Tag className="w-3 h-3 text-emerald-400" />
                  {skill}
                  <button 
                    type="button" 
                    onClick={() => handleRemoveSkill(skill)}
                    className="hover:text-red-400 ml-0.5"
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
                  className="flex-1 bg-slate-900/60 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white font-medium flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add
                </button>
              </div>
            )}
          </div>

          {/* Target Job Titles */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Inferred Target Titles
            </label>
            <div className="flex flex-wrap gap-2 p-3 rounded-xl bg-slate-900/40 border border-slate-800">
              {targetTitles.map((title) => (
                <span 
                  key={title}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30"
                >
                  <Briefcase className="w-3.5 h-3.5 text-blue-400" />
                  {title}
                  <button 
                    type="button" 
                    onClick={() => handleRemoveTitle(title)}
                    className="hover:text-red-400 ml-1"
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
                  className="flex-1 bg-slate-900/60 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={handleAddTitle}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white font-medium flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Title
                </button>
              </div>
            )}
          </div>

          {/* Search Queries */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Generated Search Queries ({queries.length} Parallel Queries)
            </label>
            <div className="space-y-3">
              {queries.map((q, idx) => (
                <div 
                  key={idx}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center gap-3"
                >
                  <div className="flex items-center gap-2 sm:w-44 shrink-0">
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono uppercase bg-slate-800 text-teal-400 border border-slate-700">
                      {q.angle}
                    </span>
                    {q.site && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                        {q.site}
                      </span>
                    )}
                  </div>

                  <input
                    type="text"
                    value={q.q}
                    onChange={(e) => handleQueryChange(idx, 'q', e.target.value)}
                    className="flex-1 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />

                  {queries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuery(idx)}
                      className="text-slate-500 hover:text-red-400 self-end sm:self-center"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Action buttons footer */}
          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="submit"
              disabled={isResuming}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm shadow-xl shadow-emerald-500/25 flex items-center justify-center gap-2"
            >
              {isResuming ? 'Launching Parallel Searches...' : 'Looks good, search'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
