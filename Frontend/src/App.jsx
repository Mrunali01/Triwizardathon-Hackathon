import React, { useState, useRef } from 'react';
import Header from './components/Header';
import ScanSection from './components/ScanSection';
import Dashboard from './components/Dashboard';
import AnimatedBackground from './components/AnimatedBackground';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function App() {
  const scanSequence = useRef(0);
  const baselines = useRef({});
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState({
    accessibilityReport: null,
    altTextSuggestions: null
  });
  const [altTextLoading, setAltTextLoading] = useState(false);
  const [url, setUrl] = useState('');

  const handleScan = async (inputUrl) => {
    const sequence = ++scanSequence.current;
    setIsScanning(true);
    setAltTextLoading(true);
    setUrl(inputUrl);

    try {
      const normalizedUrl = new URL(inputUrl);
      normalizedUrl.hash = '';
      const baselineKey = `accessibility-baseline:${normalizedUrl.href}`;
      let previousScanId = baselines.current[baselineKey] || null;
      try { previousScanId = localStorage.getItem(baselineKey) || previousScanId; } catch { /* Storage can be disabled. */ }
      // ✅ Step 1: Fetch LLM results first
      const response_llm = await fetch(`${API_BASE}/check-accessibility`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: inputUrl, previous_scan_id: previousScanId }),
      });

      const data_llm = await response_llm.json();
      if (!response_llm.ok || data_llm.error || !Array.isArray(data_llm.issues)) {
        throw new Error(typeof data_llm.detail === 'string' ? data_llm.detail : 'The scan failed. Check the URL and backend setup.');
      }
      baselines.current[baselineKey] = data_llm.scanId;
      try { localStorage.setItem(baselineKey, data_llm.scanId); } catch { /* Current results remain available. */ }
      setIsScanning(false);

      // ⏩ Immediately show LLM output
      setScanResults({
        accessibilityReport: data_llm,
        altTextSuggestions: null
      });

      // ✅ Step 2: Begin BLIP caption fetch in background
      fetch(`${API_BASE}/generate-alt-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: inputUrl }),
      })
        .then(async (res) => { if (!res.ok) throw new Error('Caption request failed'); return res.json(); })
        .then((data_blip) => {
          setScanResults(prev => prev.accessibilityReport?.scanId === data_llm.scanId ? ({ ...prev, altTextSuggestions: data_blip }) : prev);
        })
        .catch((err) => {
          console.error("❌ Alt text error:", err);
          setScanResults(prev => prev.accessibilityReport?.scanId === data_llm.scanId ? ({ ...prev, altTextSuggestions: { message: 'Failed to load image captions.' } }) : prev);
        })
        .finally(() => {
          if (sequence === scanSequence.current) setAltTextLoading(false);

        });

    } catch (err) {
      console.error("❌ LLM fetch error:", err);
      setScanResults({
        accessibilityReport: null,
        altTextSuggestions: null,
        error: err.message || 'Something went wrong while scanning. Please try again.',
      });
      setIsScanning(false);
      setAltTextLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative isolate">
      <AnimatedBackground />
      <div className="relative z-10">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <ScanSection
            onScan={handleScan}
            isScanning={isScanning}
          />
          {scanResults.error && <p role="alert" className="text-red-300 p-4">{scanResults.error}</p>}
          {(scanResults.accessibilityReport || isScanning) && (
            <Dashboard
              results={scanResults}
              isScanning={isScanning}
              altTextLoading={altTextLoading}
              url={url}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
