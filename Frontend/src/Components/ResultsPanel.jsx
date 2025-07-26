import { useState } from 'react';

const ResultsPanel = ({ results }) => {
  const { accessibilityReport, altTextSuggestions } = results || {};
  const [selectedIssue, setSelectedIssue] = useState(null);

  if (!accessibilityReport) {
    return (
      <div className="text-white text-center p-4">
        No accessibility report available.
      </div>
    );
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'text-red-400 bg-red-500/20 border-red-500/30';
      case 'medium': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      case 'low': return 'text-blue-400 bg-blue-500/20 border-blue-500/30';
      default: return 'text-blue-400 bg-blue-500/20 border-blue-500/30';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreStroke = (score) => {
    if (score >= 90) return '#10b981';
    if (score >= 70) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="space-y-8">
      {/* Score Header */}
      <div className="bg-gray-800/50 backdrop-blur-sm border border-blue-500/20 rounded-2xl p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row items-center space-y-6 sm:space-y-0 sm:space-x-8">
          {/* Score Circle */}
          <div className="relative w-32 h-32 sm:w-40 sm:h-40">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="8"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke={getScoreStroke(accessibilityReport.score)}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(results.score / 100) * 314} 314`}
                className="transition-all duration-1000 ease-out drop-shadow-lg"
                style={{ filter: `drop-shadow(0 0 10px ${getScoreStroke(accessibilityReport.score)})` }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-3xl sm:text-4xl font-bold ${getScoreColor(accessibilityReport.score)}`}>
                {accessibilityReport.score}
              </span>
              <span className="text-gray-400 text-sm">Score</span>
            </div>
          </div>

          {/* Score Details */}
          <div className="text-center sm:text-left">
            <h3 className="text-2xl sm:text-3xl font-bold text-blue-400 mb-2">
              Accessibility Score
            </h3>
            <p className="text-gray-300 text-lg mb-1">
              {accessibilityReport.totalIssues} issues found
            </p>
            <p className="text-gray-400">
              Scanned in {accessibilityReport.scanTime}
            </p>
          </div>
        </div>
      </div>

      {/* Issues Section */}
      <div>
        <div className="space-y-4">
          <div>
            {Array.isArray(accessibilityReport.issues) ? (
              <div className="space-y-4">
                {accessibilityReport.issues.map((issue) => (
                  <div
                    key={issue.id}
                    className={`bg-gray-800/30 backdrop-blur-sm border rounded-2xl p-6 cursor-pointer transition-all duration-300 hover:border-blue-400/50 hover:shadow-xl hover:shadow-blue-500/10 ${selectedIssue?.id === issue.id
                      ? 'border-blue-400/50 shadow-xl shadow-blue-500/10'
                      : 'border-gray-700/50'
                      }`}
                    onClick={() => setSelectedIssue(selectedIssue?.id === issue.id ? null : issue)}
                  >
                    {/* Issue Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-4">
                        <div className={`w-3 h-3 rounded-full ${getSeverityColor(issue.severity).split(' ')[1]}`}></div>
                        <div>
                          <h4 className="text-lg sm:text-xl font-semibold text-white">
                            {issue.title}
                          </h4>
                          <p className="text-gray-400 text-sm">
                            {issue.count} instances
                          </p>
                        </div>
                      </div>

                      <div className={`px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wide ${getSeverityColor(issue.severity)}`}>
                        {issue.type}
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {selectedIssue?.id === issue.id && (
                      <div className="space-y-6 pt-6 border-t border-gray-700/50">
                        <p className="text-gray-300 leading-relaxed">
                          {issue.description}
                        </p>

                        {/* Code Snippet */}
                        <div>
                          <h5 className="text-blue-400 font-semibold mb-2 flex items-center">
                            Found in:
                          </h5>
                          <div className="bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 overflow-x-auto">
                            <code className="text-gray-300 font-mono text-sm whitespace-pre-wrap">
                              {issue.element}
                            </code>
                          </div>
                        </div>

                        {/* Suggestion */}
                        <div>
                          <h5 className="text-blue-400 font-semibold mb-2 flex items-center">
                            AI Suggestion:
                          </h5>
                          <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 overflow-x-auto">
                            <code className="text-blue-200 font-mono text-sm whitespace-pre-wrap">
                              {issue.suggestion}
                            </code>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-white whitespace-pre-wrap">
                <h3 className="text-2xl sm:text-3xl font-bold text-blue-400 mb-4">🧠 AI Accessibility Report</h3>
                <p>{results?.report || "No structured issues found. Check backend or LLM formatting."}</p>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Alt Text Suggestions */}
      <div className="mt-8 space-y-4">
        <h3 className="text-2xl sm:text-3xl font-bold text-blue-400">🖼️ Alt Text Suggestions</h3>
        {altTextSuggestions?.message ? (
          <p className="text-green-400">{altTextSuggestions.message}</p>
        ) : (
          <ul className="space-y-4">
            {altTextSuggestions?.uncaptioned_images?.map((img, idx) => (
              <li key={idx} className="bg-gray-800/30 border border-blue-500/20 rounded-xl p-4">
                <p className="text-gray-300 text-sm mb-2">
                  <strong>Image URL:</strong> <a href={img.img_url} className="text-blue-400 underline" target="_blank" rel="noopener noreferrer">{img.img_url}</a>
                </p>
                <p className="text-blue-200 font-mono text-sm whitespace-pre-wrap">
                  <strong>Caption:</strong> {img.caption}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ResultsPanel;