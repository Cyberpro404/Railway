import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl -top-10 -right-10"></div>
        <div className="absolute w-96 h-96 bg-purple-500/20 rounded-full blur-3xl -bottom-10 -left-10"></div>
      </div>

      {/* Content */}
      <div className="relative z-10 text-center max-w-2xl mx-auto">
        {/* 404 Icon */}
        <div className="flex justify-center mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full blur-2xl opacity-30"></div>
            <div className="relative bg-gradient-to-br from-slate-800 to-slate-900 p-8 rounded-full border border-cyan-500/30">
              <AlertTriangle className="w-24 h-24 text-cyan-400 animate-pulse" />
            </div>
          </div>
        </div>

        {/* Error Code */}
        <h1 className="text-9xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent mb-4 animate-pulse">
          404
        </h1>

        {/* Error Title */}
        <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
          Page Not Found
        </h2>

        {/* Error Description */}
        <p className="text-xl text-slate-400 mb-8 leading-relaxed">
          Sorry, the page you're looking for doesn't exist. It might have been moved, deleted, or the URL might be incorrect.
        </p>

        {/* Error Details Card */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 mb-8 backdrop-blur-xl">
          <p className="text-slate-300 font-mono text-sm">
            Error: The requested resource could not be found on this server
          </p>
          <p className="text-slate-400 text-xs mt-2 font-mono">
            Path: {typeof window !== 'undefined' ? window.location.pathname : '/unknown'}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 flex-col sm:flex-row justify-center">
          {/* Go Back Button */}
          <button
            onClick={() => navigate(-1)}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-slate-500 text-white rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/20"
          >
            <ArrowLeft className="w-5 h-5" />
            Go Back
          </button>

          {/* Home Button */}
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/30 font-medium"
          >
            <Home className="w-5 h-5" />
            Back to Dashboard
          </button>
        </div>

        {/* Disclaimer Box */}
        <div className="mt-12 p-6 bg-orange-500/10 border border-orange-500/30 rounded-xl backdrop-blur-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-orange-400 flex-shrink-0 mt-0.5" />
            <div className="text-left">
              <h3 className="text-orange-400 font-semibold mb-2">Disclaimer</h3>
              <p className="text-orange-200/80 text-sm leading-relaxed">
                If you believe this is an error or you need help navigating the application, please check the URL or return to the main dashboard. If the problem persists, please contact support or restart the application.
              </p>
            </div>
          </div>
        </div>

        {/* Status Info */}
        <div className="mt-8 text-slate-500 text-sm">
          <p>Status Code: 404 | Not Found</p>
          <p className="mt-1">Request ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}</p>
        </div>
      </div>
    </div>
  );
}
