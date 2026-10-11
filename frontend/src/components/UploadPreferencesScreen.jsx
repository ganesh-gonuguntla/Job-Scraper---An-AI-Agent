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
  X,
  Info
} from 'lucide-react';

export default function UploadPreferencesScreen({ onSubmit, isSubmitting }) {
  const [file, setFile] = useState(null);
  const [jobTypes, setJobTypes] = useState(['fte', 'intern']);
  const [minSalaryLPA, setMinSalaryLPA] = useState(10);
  const [enableMinSalary, setEnableMinSalary] = useState(false);
  const [locations, setLocations] = useState([]);
  const [locationInput, setLocationInput] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [anyLocation, setAnyLocation] = useState(true); // Default to Any Location
  const [sortBy, setSortBy] = useState('match');
  const [maxAgeDays, setMaxAgeDays] = useState(30);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0]);
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
        setAnyLocation(false); // Mutually exclusive: adding specific location unchecks Any
      }
      setLocationInput('');
    }
  };

  const handleRemoveLocation = (locToRemove) => {
    const nextLocations = locations.filter((l) => l !== locToRemove);
    setLocations(nextLocations);
    if (nextLocations.length === 0) {
      setAnyLocation(true);
    }
  };

  const handleToggleAnyLocation = (checked) => {
    setAnyLocation(checked);
    if (checked) {
      setLocations([]);
      setLocationInput('');
    }
  };

  const isReadyToAnalyze = Boolean(file);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isReadyToAnalyze) return;

    let finalLocations = ['any'];
    if (anyLocation) {
      finalLocations = ['any'];
    } else if (remoteOnly && locations.length === 0) {
      finalLocations = ['remote'];
    } else if (locations.length > 0) {
      finalLocations = locations;
    }

    const preferences = {
      job_types: jobTypes,
      min_salary_inr_annual: enableMinSalary ? minSalaryLPA * 100000 : null,
      locations: finalLocations,
      sort_by: sortBy,
      max_age_days: maxAgeDays,
      remote_only: remoteOnly,
    };

    onSubmit({
      file,
      preferences,
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 12 }} 
      animate={{ opacity: 1, y: 0 }} 
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.25 }}
      className="max-w-[1200px] mx-auto py-6 sm:py-8 px-4 sm:px-6"
    >
      {/* Hero Header */}
      <div className="text-center mb-6 sm:mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#D4C4A8]/10 border border-[#D4C4A8]/25 text-[#D4C4A8] text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Autonomous Career Intelligence Pipeline</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#E5E7EB] tracking-tight mb-2.5">
          Find High-Fit Jobs Tailored to <span className="text-[#D4C4A8]">Your Experience</span>
        </h1>
        <p className="text-[#9CA3AF] max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
          Our AI agent reads your resume, pulls real open roles from job boards and company career pages, verifies they are still live, and ranks every match from 20% to 100%.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Two-column layout on desktop; stacked with Upload first on mobile */}
        <div className="flex flex-col md:grid md:grid-cols-2 gap-6 lg:gap-8 items-start">
          
          {/* LEFT HALF (Desktop Column 1, Mobile Order 2): Match & Search Preferences */}
          <div className="order-2 md:order-1 w-full glass-panel p-6 sm:p-7 space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-[#2A303C]">
              <h2 className="text-base sm:text-lg font-bold text-[#E5E7EB] flex items-center gap-2">
                <Sliders className="w-4 h-4 text-[#D4C4A8]" />
                Match & Search Preferences
              </h2>
              <span className="text-xs text-[#9CA3AF]">Custom Criteria</span>
            </div>

            {/* Job Types */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#9CA3AF] mb-2.5">
                Target Employment Types
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'fte', label: 'Full-Time' },
                  { id: 'intern', label: 'Internship' },
                  { id: 'contract', label: 'Contract' },
                  { id: 'part_time', label: 'Part-Time' },
                ].map((item) => {
                  const active = jobTypes.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleToggleJobType(item.id)}
                      className={`px-3 py-2 text-xs font-medium rounded-xl transition-all text-center ${
                        active ? 'chip-selected' : 'chip-unselected'
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Target Locations */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF]">
                  Target Locations
                </label>
                <div className="flex items-center gap-4">
                  {/* Remote Only Toggle */}
                  <label className="flex items-center gap-1.5 text-xs text-[#E5E7EB] cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={remoteOnly}
                      onChange={(e) => setRemoteOnly(e.target.checked)}
                      className="w-3.5 h-3.5 rounded border-[#4B5563] bg-[#14171E] accent-[#D4C4A8] cursor-pointer"
                    />
                    <span>Remote Only</span>
                  </label>

                  {/* Any Location Toggle */}
                  <label className="flex items-center gap-1.5 text-xs text-[#E5E7EB] cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={anyLocation}
                      onChange={(e) => handleToggleAnyLocation(e.target.checked)}
                      className="w-3.5 h-3.5 rounded border-[#4B5563] bg-[#14171E] accent-[#D4C4A8] cursor-pointer"
                    />
                    <span className="font-medium text-[#D4C4A8]">Any Location (Worldwide)</span>
                  </label>
                </div>
              </div>

              {/* Location Input & Chips */}
              <div className="space-y-2">
                <div className="relative">
                  <MapPin className="w-4 h-4 text-[#6B7280] absolute left-3 top-3" />
                  <input
                    type="text"
                    disabled={anyLocation}
                    placeholder={
                      anyLocation 
                        ? 'Any location is active (worldwide & remote roles included)' 
                        : 'Type city or country and press Enter (e.g. San Francisco, India)...'
                    }
                    value={locationInput}
                    onChange={(e) => setLocationInput(e.target.value)}
                    onKeyDown={handleAddLocation}
                    className={`w-full pl-9 pr-3 py-2 text-xs rounded-xl border bg-[#0A0C10] text-[#E5E7EB] transition-all ${
                      anyLocation 
                        ? 'border-[#2A303C] text-[#6B7280] cursor-not-allowed opacity-60' 
                        : 'border-[#374151] focus:border-[#D4C4A8] focus:ring-1 focus:ring-[#D4C4A8]/40'
                    }`}
                  />
                </div>

                {/* Selected Location Chips */}
                {locations.length > 0 && !anyLocation && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {locations.map((loc) => (
                      <span
                        key={loc}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/25"
                      >
                        {loc}
                        <button
                          type="button"
                          onClick={() => handleRemoveLocation(loc)}
                          className="hover:text-white"
                          aria-label={`Remove ${loc}`}
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Salary Preference (Soft Filter / Ranking Boost) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF] flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5 text-[#D4C4A8]" />
                  Target Compensation Preference
                </label>
                <button
                  type="button"
                  onClick={() => setEnableMinSalary(!enableMinSalary)}
                  className={`text-xs px-2.5 py-0.5 rounded-full border transition-all ${
                    enableMinSalary 
                      ? 'bg-[#D4C4A8]/15 text-[#D4C4A8] border-[#D4C4A8]/40 font-semibold' 
                      : 'bg-[#14171E] text-[#9CA3AF] border-[#374151]'
                  }`}
                >
                  {enableMinSalary ? `Active: ₹${minSalaryLPA} LPA+` : 'No Minimum'}
                </button>
              </div>

              {enableMinSalary && (
                <div className="p-3.5 rounded-xl bg-[#0A0C10] border border-[#2A303C] space-y-2 mt-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-[#9CA3AF]">Desired Minimum Salary:</span>
                    <span className="text-[#D4C4A8] font-bold text-sm">₹{minSalaryLPA} LPA</span>
                  </div>
                  <input
                    type="range"
                    min="3"
                    max="60"
                    step="1"
                    value={minSalaryLPA}
                    onChange={(e) => setMinSalaryLPA(Number(e.target.value))}
                    className="w-full accent-[#D4C4A8] cursor-pointer bg-[#222733]"
                  />
                  <div className="flex justify-between text-[10px] text-[#6B7280]">
                    <span>₹3 LPA</span>
                    <span>₹30 LPA</span>
                    <span>₹60 LPA+</span>
                  </div>
                </div>
              )}
              
              <div className="flex items-start gap-1.5 mt-2 text-[11px] text-[#6B7280] leading-relaxed">
                <Info className="w-3.5 h-3.5 text-[#9CA3AF] flex-shrink-0 mt-0.5" />
                <span>
                  Soft preference: prioritizes matching compensation in ranking. Roles without published salary figures are preserved so you never miss high-fit opportunities.
                </span>
              </div>
            </div>

            {/* Sorting & Max Age Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-[#2A303C]">
              {/* Sort Priority */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#9CA3AF] mb-1.5">
                  Sorting Priority
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#374151] bg-[#0A0C10] text-[#E5E7EB] focus:border-[#D4C4A8] focus:ring-1 focus:ring-[#D4C4A8]/40"
                >
                  <option value="match">Match Score (Highest First)</option>
                  <option value="recency">Freshness / Date Posted</option>
                  <option value="salary">Compensation (Highest First)</option>
                </select>
              </div>

              {/* Max Age */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#9CA3AF] mb-1.5">
                  Max Posting Age
                </label>
                <select
                  value={maxAgeDays}
                  onChange={(e) => setMaxAgeDays(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#374151] bg-[#0A0C10] text-[#E5E7EB] focus:border-[#D4C4A8] focus:ring-1 focus:ring-[#D4C4A8]/40"
                >
                  <option value={7}>Last 7 Days (Fresh)</option>
                  <option value={14}>Last 14 Days</option>
                  <option value={30}>Last 30 Days (Standard)</option>
                  <option value={60}>Last 60 Days (Broad)</option>
                </select>
              </div>
            </div>
          </div>

          {/* RIGHT HALF (Desktop Column 2, Mobile Order 1): Upload Card & Analyze Button */}
          <div className="order-1 md:order-2 w-full space-y-4">
               {/* Upload Card */}
            <div className="glass-panel p-6 sm:p-7 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#2A303C]">
                <h2 className="text-base sm:text-lg font-bold text-[#E5E7EB] flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#D4C4A8]" />
                  Upload Your Resume (PDF)
                </h2>
                <span className="text-xs text-[#9CA3AF]">Direct AI Analysis</span>
              </div>

              {/* Dropzone Area */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                  isDragActive
                    ? 'border-[#D4C4A8] bg-[#D4C4A8]/5'
                    : file
                    ? 'border-[#D4C4A8]/50 bg-[#1B1F28]'
                    : 'border-[#374151] hover:border-[#D4C4A8]/40 bg-[#0A0C10]/60 hover:bg-[#14171E]'
                }`}
              >
                <input {...getInputProps()} />
                {file ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-[#D4C4A8]/15 flex items-center justify-center text-[#D4C4A8]">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#E5E7EB]">{file.name}</p>
                      <p className="text-xs text-[#9CA3AF]">{(file.size / 1024).toFixed(1)} KB • PDF Ready for Analysis</p>
                    </div>
                    <span className="text-xs text-[#D4C4A8] hover:underline">
                      Click or drag to replace
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-[#14171E] border border-[#2A303C] flex items-center justify-center text-[#9CA3AF]">
                      <UploadCloud className="w-6 h-6 text-[#D4C4A8]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#E5E7EB]">
                        Drop your resume here, or <span className="text-[#D4C4A8] underline">browse</span>
                      </p>
                      <p className="text-xs text-[#6B7280] mt-1">Supports standard PDF formats up to 10MB</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Privacy Guarantee */}
              <div className="text-[11px] text-[#6B7280] text-center pt-1">
                Your data is processed in-memory and hashed for session search only. No profile data is stored permanently.
              </div>
            </div>

            {/* Primary Action Button (Directly Below Upload Card) */}
            <div className="space-y-2">
              <button
                type="submit"
                disabled={!isReadyToAnalyze || isSubmitting}
                className="btn-champagne w-full py-4 text-sm font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-[#0A0C10] border-t-transparent rounded-full animate-spin" />
                    <span>Initiating Multi-Agent Pipeline...</span>
                  </>
                ) : (
                  <>
                    <span>Analyze Resume & Match Jobs</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Clarifying Hint Under Button */}
              <p className="text-xs text-center text-[#6B7280]">
                {!isReadyToAnalyze 
                  ? "Upload your PDF resume to begin matching real live jobs." 
                  : "Ready. Launching live search across JSearch, Adzuna, Remotive, Arbeitnow & verified portals."}
              </p>
            </div>

          </div>

        </div>
      </form>
    </motion.div>
  );
}
