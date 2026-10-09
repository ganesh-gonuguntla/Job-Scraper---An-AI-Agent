import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  MapPin, 
  Sliders, 
  ArrowRight, 
  Globe, 
  DollarSign, 
  Briefcase, 
  Sparkles,
  X
} from 'lucide-react';

export default function UploadPreferencesScreen({ onSubmit, isSubmitting }) {
  const [file, setFile] = useState(null);
  const [useSample, setUseSample] = useState(false);
  const [jobTypes, setJobTypes] = useState(['fte', 'intern']);
  const [minSalaryLPA, setMinSalaryLPA] = useState(10);
  const [enableMinSalary, setEnableMinSalary] = useState(false);
  const [locations, setLocations] = useState(['Bangalore', 'remote']);
  const [locationInput, setLocationInput] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [sortBy, setSortBy] = useState('match');
  const [maxAgeDays, setMaxAgeDays] = useState(30);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0]);
        setUseSample(false);
      }
    },
  });

  const handleToggleJobType = (type) => {
    if (jobTypes.includes(type)) {
      if (jobTypes.length > 1) {
        setJobTypes(jobTypes.filter((t) => t !== type));
      }
    } else {
      setJobTypes([...jobTypes, type]);
    }
  };

  const handleAddLocation = (e) => {
    if (e.key === 'Enter' && locationInput.trim()) {
      e.preventDefault();
      const loc = locationInput.trim();
      if (!locations.includes(loc)) {
        setLocations([...locations, loc]);
      }
      setLocationInput('');
    }
  };

  const handleRemoveLocation = (locToRemove) => {
    setLocations(locations.filter((l) => l !== locToRemove));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalLocations = remoteOnly 
      ? ['remote'] 
      : (locations.length > 0 ? locations : ['India', 'remote']);

    const preferences = {
      job_types: jobTypes,
      min_salary_inr_annual: enableMinSalary ? minSalaryLPA * 100000 : null,
      locations: finalLocations,
      sort_by: sortBy,
      max_age_days: maxAgeDays,
    };

    onSubmit({
      file: useSample ? null : file,
      preferences,
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto py-8 px-4"
    >
      {/* Hero Banner */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Next-Gen LangGraph Architecture</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
          Find High-Fit Jobs Tailored to <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-400">Your Resume</span>
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-base sm:text-lg">
          Upload your resume and set your criteria. Our AI agent extracts your competencies, searches live across the web in parallel, scores each opening against your profile, and ranks matches deterministically.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Step 1: Resume Upload */}
        <div className="glass-panel rounded-2xl p-6 sm:p-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              1. Upload Your Resume (PDF)
            </h2>
            <button
              type="button"
              onClick={() => {
                setUseSample(!useSample);
                if (!useSample) setFile(null);
              }}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                useSample 
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' 
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
              }`}
            >
              {useSample ? '✓ Using Sample Developer Resume' : 'Use Sample Resume (Instant Test)'}
            </button>
          </div>

          {!useSample ? (
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                isDragActive
                  ? 'border-emerald-500 bg-emerald-500/10'
                  : file
                  ? 'border-emerald-500/40 bg-emerald-950/20'
                  : 'border-slate-700/80 hover:border-slate-600 bg-slate-900/40 hover:bg-slate-900/70'
              }`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{file.name}</p>
                    <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB • PDF Ready for Analysis</p>
                  </div>
                  <span className="text-xs text-emerald-400 underline mt-1">Click or drag another file to replace</span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">Drag & drop your resume PDF here</p>
                    <p className="text-xs text-slate-400 mt-1">Supports searchable PDF files (up to 10MB)</p>
                  </div>
                  <span className="text-xs px-3 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Browse Computer
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">
                  PDF
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Alex Rivera - Full Stack Engineer (Sample)</h4>
                  <p className="text-xs text-emerald-400">2.5 Years Experience • Python, FastAPI, React, PostgreSQL</p>
                </div>
              </div>
              <button 
                type="button" 
                onClick={() => setUseSample(false)}
                className="text-xs text-slate-400 hover:text-white underline"
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Step 2: Search Preferences */}
        <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-400" />
            2. Match & Search Preferences
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Job Types */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
                Job Types
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'fte', label: 'Full Time (FTE)' },
                  { id: 'intern', label: 'Internship' },
                  { id: 'contract', label: 'Contract' },
                  { id: 'part_time', label: 'Part Time' },
                ].map((type) => {
                  const active = jobTypes.includes(type.id);
                  return (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => handleToggleJobType(type.id)}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium border text-left transition-all ${
                        active
                          ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-300'
                          : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:bg-slate-800/60'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{type.label}</span>
                        {active && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Sort Priority */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
                Sort Priority
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'match', label: 'Best Match' },
                  { id: 'salary', label: 'Highest Pay' },
                  { id: 'recency', label: 'Most Recent' },
                ].map((sort) => {
                  const active = sortBy === sort.id;
                  return (
                    <button
                      key={sort.id}
                      type="button"
                      onClick={() => setSortBy(sort.id)}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium border text-center transition-all ${
                        active
                          ? 'bg-teal-500/20 border-teal-500/60 text-teal-300'
                          : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:bg-slate-800/60'
                      }`}
                    >
                      {sort.label}
                    </button>
                  );
                })}
              </div>

              {/* Max Age */}
              <div className="mt-4">
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Max Posting Age
                </label>
                <div className="flex gap-2">
                  {[7, 14, 30, 60].map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() => setMaxAgeDays(days)}
                      className={`flex-1 py-1.5 text-xs rounded-lg border ${
                        maxAgeDays === days
                          ? 'bg-blue-500/20 border-blue-500/50 text-blue-300'
                          : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      {days}d
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Salary Filter Slider */}
          <div className="pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="enableSalary"
                  checked={enableMinSalary}
                  onChange={(e) => setEnableMinSalary(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/30 bg-slate-900"
                />
                <label htmlFor="enableSalary" className="text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer">
                  Filter by Minimum Annual Salary
                </label>
              </div>
              <span className={`text-sm font-bold ${enableMinSalary ? 'text-emerald-400' : 'text-slate-500'}`}>
                {enableMinSalary ? `₹${minSalaryLPA} LPA (${(minSalaryLPA * 100000).toLocaleString('en-IN')})` : 'Any Salary (Unfiltered)'}
              </span>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-xs text-slate-500">₹0</span>
              <input
                type="range"
                min="0"
                max="40"
                step="1"
                value={minSalaryLPA}
                disabled={!enableMinSalary}
                onChange={(e) => setMinSalaryLPA(Number(e.target.value))}
                className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${
                  enableMinSalary ? 'bg-slate-700 accent-emerald-500' : 'bg-slate-800 opacity-40 cursor-not-allowed'
                }`}
              />
              <span className="text-xs text-slate-500">₹40 LPA+</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Note: Postings that do not list salary are kept and ranked appropriately.
            </p>
          </div>

          {/* Locations */}
          <div className="pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2.5">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Target Locations
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="remoteOnly"
                  checked={remoteOnly}
                  onChange={(e) => setRemoteOnly(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/30 bg-slate-900"
                />
                <label htmlFor="remoteOnly" className="text-xs text-slate-400 cursor-pointer flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-blue-400" />
                  Remote Only
                </label>
              </div>
            </div>

            {!remoteOnly && (
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2 mb-2">
                  {locations.map((loc) => (
                    <span 
                      key={loc}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs bg-slate-800 text-slate-200 border border-slate-700"
                    >
                      <MapPin className="w-3 h-3 text-emerald-400" />
                      {loc}
                      <button
                        type="button"
                        onClick={() => handleRemoveLocation(loc)}
                        className="hover:text-red-400"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Type city or region and press Enter (e.g. Bangalore, Hyderabad, Remote)..."
                    value={locationInput}
                    onChange={(e) => setLocationInput(e.target.value)}
                    onKeyDown={handleAddLocation}
                    className="flex-1 bg-slate-900/60 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (locationInput.trim()) {
                        if (!locations.includes(locationInput.trim())) {
                          setLocations([...locations, locationInput.trim()]);
                        }
                        setLocationInput('');
                      }
                    }}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs font-semibold"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Submit CTA */}
        <div className="flex justify-center pt-2">
          <button
            type="submit"
            disabled={isSubmitting || (!file && !useSample)}
            className={`w-full sm:w-auto min-w-[320px] px-8 py-4 rounded-xl font-bold text-white text-base shadow-xl flex items-center justify-center gap-3 transition-all duration-300 ${
              isSubmitting || (!file && !useSample)
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-600 hover:from-emerald-400 hover:to-blue-500 shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:scale-[1.01]'
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Launching LangGraph Pipeline...</span>
              </>
            ) : (
              <>
                <span>Analyze Resume & Match Jobs</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </form>
    </motion.div>
  );
}
