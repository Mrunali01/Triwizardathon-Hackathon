import { useState, useEffect } from 'react';

const LoadingAnimation = ({ url }) => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    'Analyzing page structure...',
    'Checking color contrast...',
    'Validating ARIA attributes...',
    'Testing keyboard navigation...',
    'Generating AI recommendations...'
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + 2;
        const stepIndex = Math.floor(newProgress / 20);
        setCurrentStep(Math.min(stepIndex, steps.length - 1));
        return Math.min(newProgress, 100);
      });
    }, 60);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="text-center py-8">
      {/* Header */}
      <div className="mb-12">
        <h3 className="text-2xl sm:text-3xl font-bold text-blue-400 mb-6">
          Scanning {url}
        </h3>
        
        {/* Progress Bar */}
        <div className="flex items-center space-x-4 max-w-2xl mx-auto">
          <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-300 ease-out shadow-lg shadow-blue-500/50"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <span className="text-blue-400 font-semibold text-lg min-w-[3rem]">
            {progress}%
          </span>
        </div>
      </div>

      {/* Radar Visualization */}
      <div className="flex justify-center mb-12">
        <div className="relative w-48 h-48 sm:w-64 sm:h-64">
          {/* Radar rings */}
          <div className="absolute inset-0">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="absolute border border-blue-400/30 rounded-full"
                style={{
                  width: `${100 - i * 20}%`,
                  height: `${100 - i * 20}%`,
                  top: `${i * 10}%`,
                  left: `${i * 10}%`,
                }}
              ></div>
            ))}
          </div>
          
          {/* Radar sweep */}
          <div className="absolute inset-0 rounded-full animate-spin" style={{animationDuration: '2s'}}>
            <div 
              className="absolute inset-0 rounded-full"
              style={{
                background: 'conic-gradient(from 0deg, transparent 0deg, rgba(59, 130, 246, 0.3) 30deg, transparent 60deg)'
              }}
            ></div>
          </div>
          
          {/* Center dot */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse shadow-lg shadow-blue-400/50"></div>
          </div>
        </div>
      </div>

      {/* Current Step */}
      <div className="bg-gray-800/50 backdrop-blur-sm border border-blue-500/20 rounded-xl p-4 max-w-md mx-auto">
        <p className="text-gray-300 text-lg">
          {steps[currentStep]}
        </p>
      </div>
    </div>
  );
};

export default LoadingAnimation;