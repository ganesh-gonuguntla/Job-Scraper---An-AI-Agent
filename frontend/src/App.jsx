import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import UploadPreferencesScreen from './components/UploadPreferencesScreen';
import ProgressStepperScreen from './components/ProgressStepperScreen';
import HumanReviewModal from './components/HumanReviewModal';
import ResultsScreen from './components/ResultsScreen';
import { startRun, subscribeRunStream, resumeRun, rerankJobs } from './api';
import { AlertCircle, X } from 'lucide-react';

export default function App() {
  const [screen, setScreen] = useState('upload'); // 'upload' | 'progress' | 'review' | 'results'
  const [runId, setRunId] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [completedNodes, setCompletedNodes] = useState([]);
  const [currentNode, setCurrentNode] = useState(null);
  const [nodeSummaries, setNodeSummaries] = useState({});
  const [statusNote, setStatusNote] = useState(null);
  const [interruptData, setInterruptData] = useState(null);
  const [finalJobs, setFinalJobs] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [isReranking, setIsReranking] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [sourceCounts, setSourceCounts] = useState(null);
  const [sourceStatuses, setSourceStatuses] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [countriesUsed, setCountriesUsed] = useState([]);
  const [expansionAction, setExpansionAction] = useState(null);

  // Close SSE stream cleanup reference
  const [streamUnsubscribe, setStreamUnsubscribe] = useState(null);

  useEffect(() => {
    return () => {
      if (streamUnsubscribe) {
        streamUnsubscribe();
      }
    };
  }, [streamUnsubscribe]);

  const handleStartRun = async ({ file, preferences: userPrefs }) => {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setPreferences(userPrefs);
      setCompletedNodes([]);
      setCurrentNode('extract_text');
      setNodeSummaries({});
      setStatusNote(null);
      setFinalJobs([]);
      setSourceStatuses(null);

      const data = await startRun(file, userPrefs);
      setRunId(data.run_id);
      setScreen('progress');
      setIsSubmitting(false);

      // Connect SSE stream
      const unsub = subscribeRunStream(data.run_id, {
        onNodeStart: ({ node }) => {
          setCurrentNode(node);
        },
        onNodeEnd: ({ node, summary }) => {
          setCompletedNodes((prev) => [...new Set([...prev, node])]);
          if (summary) {
            setNodeSummaries((prev) => ({ ...prev, [node]: summary }));
            setStatusNote(summary);
          }
        },
        onInterrupt: (interruptPayload) => {
          setInterruptData(interruptPayload);
          setScreen('review');
        },
        onResult: ({ final_jobs, status_note, source_counts, source_statuses, funnel, countries_used, expansion_action }) => {
          setFinalJobs(final_jobs || []);
          if (status_note) {
            setStatusNote(status_note);
          }
          if (source_counts) {
            setSourceCounts(source_counts);
          }
          if (source_statuses) {
            setSourceStatuses(source_statuses);
          }
          if (funnel) {
            setFunnel(funnel);
          }
          if (countries_used) {
            setCountriesUsed(countries_used);
          }
          if (expansion_action) {
            setExpansionAction(expansion_action);
          }
          setScreen('results');
        },
        onError: (msg) => {
          setErrorMessage(msg);
        },
      });

      setStreamUnsubscribe(() => unsub);
    } catch (err) {
      setIsSubmitting(false);
      setErrorMessage(err.message || 'Failed to initialize agent run');
    }
  };

  const handleResume = async (editedData) => {
    if (!runId) return;
    try {
      setIsResuming(true);
      setScreen('progress');
      setCurrentNode('search_dispatcher');
      await resumeRun(runId, editedData);
      setIsResuming(false);
    } catch (err) {
      setIsResuming(false);
      setErrorMessage(err.message || 'Failed to resume search');
      setScreen('review');
    }
  };

  const handleRerank = async (newPreferences) => {
    if (!runId) return;
    try {
      setIsReranking(true);
      setPreferences(newPreferences);
      const res = await rerankJobs(runId, newPreferences);
      if (res.final_jobs) {
        setFinalJobs(res.final_jobs);
      }
      setIsReranking(false);
    } catch (err) {
      setIsReranking(false);
      setErrorMessage('Failed to re-sort jobs');
    }
  };

  const handleReset = () => {
    if (streamUnsubscribe) {
      streamUnsubscribe();
      setStreamUnsubscribe(null);
    }
    setRunId(null);
    setCompletedNodes([]);
    setCurrentNode(null);
    setNodeSummaries({});
    setStatusNote(null);
    setInterruptData(null);
    setFinalJobs([]);
    setErrorMessage(null);
    setScreen('upload');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0A0C10] text-[#E5E7EB] selection:bg-[#D4C4A8] selection:text-[#0A0C10]">
      <Navbar 
        onReset={handleReset} 
        isProcessing={screen === 'progress' || screen === 'review'} 
      />

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="max-w-4xl mx-auto px-4 w-full mt-4">
          <div className="p-4 rounded-xl bg-[#1E1418] border border-red-500/30 text-red-200 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button 
              onClick={() => setErrorMessage(null)} 
              className="hover:text-white ml-2"
              aria-label="Dismiss error"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 pb-16">
        {screen === 'upload' && (
          <UploadPreferencesScreen 
            onSubmit={handleStartRun} 
            isSubmitting={isSubmitting} 
          />
        )}

        {screen === 'progress' && (
          <ProgressStepperScreen
            completedNodes={completedNodes}
            currentNode={currentNode}
            statusNote={statusNote}
            nodeSummaries={nodeSummaries}
          />
        )}

        {screen === 'review' && (
          <HumanReviewModal
            interruptData={interruptData}
            onResume={handleResume}
            isResuming={isResuming}
          />
        )}

        {screen === 'results' && (
          <ResultsScreen
            jobs={finalJobs}
            statusNote={statusNote}
            sourceCounts={sourceCounts}
            sourceStatuses={sourceStatuses}
            funnel={funnel}
            countriesUsed={countriesUsed}
            expansionAction={expansionAction}
            onRerank={handleRerank}
            isReranking={isReranking}
            onReset={handleReset}
            currentPreferences={preferences}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#2A303C] bg-[#07090C] py-6 text-center text-xs text-[#9CA3AF]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[#E5E7EB] font-semibold tracking-tight">
            <span>JobPulse</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#D4C4A8]/10 text-[#D4C4A8] border border-[#D4C4A8]/20">
              Grand Tourer Edition
            </span>
          </div>
          <p className="text-[11px] text-[#6B7280]">
            LangGraph Autonomous Agent • Groq High-Precision Extractions • Verified Live Career Portals
          </p>
        </div>
      </footer>
    </div>
  );
}
