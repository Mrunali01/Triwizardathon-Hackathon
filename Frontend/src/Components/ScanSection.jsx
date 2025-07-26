import { useState } from 'react';

const ScanSection = ({ onScan, isScanning }) => {
  const [url, setUrl] = useState('');
  const [isValid, setIsValid] = useState(true);

  const validateUrl = (inputUrl) => {
    try {
      new URL(inputUrl);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateUrl(url)) {
      setIsValid(true);
      onScan(url);  // ✅ directly call the prop
    } else {
      setIsValid(false);
    }
  };

  const handleUrlChange = (e) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    if (!isValid && newUrl) {
      setIsValid(validateUrl(newUrl));
    }
  };

  return (
    <section className="text-center py-12 sm:py-16">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-blue-400 bg-clip-text text-transparent">
            AI-Powered Accessibility Analysis
          </h2>
          <p className="text-lg sm:text-xl text-gray-300 max-w-3xl mx-auto leading-relaxed">
            Get instant insights into your website's accessibility compliance with WCAG guidelines
          </p>
        </div>

        {/* Scan Form */}
        <form onSubmit={handleSubmit} className="mb-16">
          <div className="max-w-4xl mx-auto mb-8">
            <div className="relative group">
              <input
                type="text"
                className={`w-full px-6 py-4 sm:px-8 sm:py-6 text-lg sm:text-xl bg-gray-900/50 backdrop-blur-xl border-2 rounded-2xl text-white placeholder-gray-400 outline-none transition-all duration-300 ${isValid
                  ? 'border-blue-500/30 focus:border-blue-400 focus:shadow-2xl focus:shadow-blue-500/20'
                  : 'border-red-500/50 focus:border-red-400'
                  }`}
                placeholder="Enter website URL (e.g., https://example.com)"
                value={url}
                onChange={handleUrlChange}
                disabled={isScanning}
              />
              {/* Glow effect */}
              <div className={`absolute inset-0 rounded-2xl transition-opacity duration-300 pointer-events-none ${isValid ? 'bg-gradient-to-r from-blue-500/10 via-transparent to-blue-500/10' : 'bg-gradient-to-r from-red-500/10 via-transparent to-red-500/10'
                } opacity-0 group-focus-within:opacity-100`}></div>
            </div>
            {!isValid && (
              <p className="text-red-400 text-sm mt-2 text-left max-w-4xl mx-auto px-2">
                Please enter a valid URL
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isScanning || !url}
            className="group relative px-8 py-4 sm:px-12 sm:py-6 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-lg sm:text-xl font-semibold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:from-blue-600 hover:to-blue-700 hover:shadow-2xl hover:shadow-blue-500/30 hover:-translate-y-1 active:translate-y-0"
          >
            <span className="flex items-center justify-center space-x-3">
              {isScanning ? (
                <>
                  <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <span className="text-2xl">🔍</span>
                  <span>Start AI Scan</span>
                </>
              )}
            </span>
            {/* Button glow */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-400/20 to-blue-600/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </button>
        </form>


        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {[
            { icon: '⚡', title: 'Lightning Fast', desc: 'Complete analysis in seconds' },
            { icon: '🎯', title: 'WCAG Compliant', desc: 'Follows latest accessibility standards' },
            { icon: '🤖', title: 'AI-Powered', desc: 'Smart suggestions and fixes' }
          ].map((feature, index) => (
            <div
              key={index}
              className="group p-6 sm:p-8 bg-gray-900/30 backdrop-blur-xl border border-blue-500/20 rounded-2xl hover:border-blue-400/50 hover:shadow-xl hover:shadow-blue-500/10 hover:-translate-y-2 transition-all duration-300"
            >
              <div className="text-4xl sm:text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">
                {feature.icon}
              </div>
              <h3 className="text-xl sm:text-2xl font-semibold text-blue-400 mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-300 text-sm sm:text-base">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ScanSection;