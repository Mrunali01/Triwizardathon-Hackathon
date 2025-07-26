import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ScanSection from './components/ScanSection';
import Dashboard from './components/Dashboard';
import AnimatedBackground from './components/AnimatedBackground';

function App() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState({
    accessibilityReport: null,
    altTextSuggestions: null
  });
  const [altTextLoading, setAltTextLoading] = useState(false);
  const [url, setUrl] = useState('');

  const handleScan = async (inputUrl) => {
    setIsScanning(true);
    setAltTextLoading(true);
    setUrl(inputUrl);

    try {
      // ✅ Step 1: Fetch LLM results first
      const response_llm = await fetch('http://localhost:8000/check-accessibility', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: inputUrl }),
      });

      const data_llm = await response_llm.json();

      // ⏩ Immediately show LLM output
      setScanResults({
        accessibilityReport: data_llm,
        altTextSuggestions: null
      });

      // ✅ Step 2: Begin BLIP caption fetch in background
      fetch('http://127.0.0.1:8000/generate-alt-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: inputUrl }),
      })
        .then((res) => res.json())
        .then((data_blip) => {
          setScanResults(prev => ({
            ...prev,
            altTextSuggestions: data_blip
          }));
        })
        .catch((err) => {
          console.error("❌ Alt text error:", err);
          setScanResults(prev => ({
            ...prev,
            altTextSuggestions: { message: "⚠️ Failed to load image captions." }
          }));
        })
        .finally(() => {
          setAltTextLoading(false);
          setIsScanning(false);
        });

    } catch (err) {
      console.error("❌ LLM fetch error:", err);
      setScanResults({
        accessibilityReport: null,
        altTextSuggestions: null,
        error: "Something went wrong while scanning. Please try again.",
      });
      setIsScanning(false);
      setAltTextLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <div className="relative z-10">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <ScanSection
            onScan={handleScan}
            isScanning={isScanning}
          />
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