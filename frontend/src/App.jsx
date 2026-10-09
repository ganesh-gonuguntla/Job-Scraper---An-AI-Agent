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
        onResult: ({ final_jobs, status_note }) => {
          setFinalJobs(final_jobs || []);
          if (status_note) {
            setStatusNote(status_note);
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
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-white">
      <Navbar 
        onReset={handleReset} 
        isProcessing={screen === 'progress' || screen === 'review'} 
      />

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="max-w-4xl mx-auto px-4 w-full mt-4">
          <div className="p-4 rounded-xl bg-red-950/80 border border-red-500/40 text-red-200 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button 
              onClick={() => setErrorMessage(null)} 
              className="hover:text-white ml-2"
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
            onRerank={handleRerank}
            isReranking={isReranking}
            onReset={handleReset}
            currentPreferences={preferences}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-center text-xs text-slate-500">
        <p>
          JobPulse • Powered by LangGraph, Google Gemini, Groq, and Exa • Free-Tier Optimized
        </p>
      </footer>
    </div>
  );
}
