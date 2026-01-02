import { useState, useEffect } from 'react';
import VideoUpload from './components/VideoUpload';
import SOPViewer from './components/SOPViewer';
import HistorySidebar from './components/HistorySidebar';
import Login from './components/Login';
import { History, FileText, BrainCircuit, LayoutGrid, CheckCircle2, AlertCircle } from 'lucide-react';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // State matching child components
  const [sopContent, setSopContent] = useState<string>('');
  const [processingTime, setProcessingTime] = useState<number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  useEffect(() => {
    const auth = localStorage.getItem('isAuthenticated');
    if (auth === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  // Handlers matching VideoUploadProps
  const handleSopGenerated = (sop: string, time?: number) => {
    setSopContent(sop);
    setProcessingTime(time);
    setIsLoading(false);
    setRefreshTrigger(prev => prev + 1); // Refresh sidebar
  };

  // Handlers matching HistorySidebarProps
  const handleHistorySelect = (content: string, time?: number) => {
    setSopContent(content);
    setProcessingTime(time);
  };

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    setIsAuthenticated(false);
  }

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="flex h-screen bg-gray-900 text-white overflow-hidden font-sans">
      {/* Sidebar with Glassmorphism */}
      <HistorySidebar onSelectDoc={handleHistorySelect} refreshTrigger={refreshTrigger} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Abstract Background Elements */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
          <div className="absolute -top-[20%] -right-[10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[100px] opacity-50"></div>
          <div className="absolute top-[40%] -left-[10%] w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[100px] opacity-40"></div>
        </div>

        {/* Header */}
        <header className="h-20 border-b border-gray-800 bg-gray-900/80 backdrop-blur-md flex items-center justify-between px-8 z-10 shrink-0">
          <div className="flex items-center gap-4 cursor-pointer hover:opacity-80 transition-opacity" onClick={() => {
            setSopContent('');
            setIsLoading(false);
          }}>
            <div className="p-2.5 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl shadow-lg shadow-blue-500/20">
              <BrainCircuit className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">
                Pace <span className="text-blue-400 font-light">Process Miner</span>
              </h1>
              <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">AI-Powered Orchestrator</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Status Badge */}
            {isLoading && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-blue-400">Processing Evidence</span>
              </div>
            )}
            {!isLoading && sopContent && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                <span className="text-xs font-medium text-green-400">Ready</span>
              </div>
            )}
            <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign Out
            </button>
          </div>
        </header>

        {/* Scrollable Workspace */}
        <main className="flex-1 overflow-y-auto p-8 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent z-10 pb-20">
          <div className="max-w-6xl mx-auto space-y-8">

            {/* Hero / Upload Section */}
            {!sopContent && !isLoading && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] animate-in fade-in zoom-in duration-500">
                <div className="text-center mb-10 max-w-2xl">
                  <h2 className="text-4xl font-bold text-white mb-4 leading-tight">
                    Transform Videos into <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Intelligent SOPs</span>
                  </h2>
                  <p className="text-gray-400 text-lg">
                    Upload your process recordings. Our AI Orchestrator will analyze, extract, and document the entire workflow in seconds.
                  </p>
                </div>
                {/* Main VideoUpload Component */}
                <VideoUpload
                  onSopGenerated={handleSopGenerated}
                  isLoading={isLoading}
                  setIsLoading={setIsLoading}
                />
              </div>
            )}

            {/* Processing State */}
            {isLoading && (
              <div className="flex flex-col items-center justify-center min-h-[50vh] animate-in fade-in duration-500">
                <div className="relative w-24 h-24 mb-8">
                  <div className="absolute inset-0 border-4 border-gray-700 rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
                  <BrainCircuit className="absolute inset-0 m-auto w-10 h-10 text-blue-500 animate-pulse" />
                </div>
                <h3 className="text-2xl font-semibold text-white mb-2">Analyzing Workflow Evidence</h3>
                <p className="text-gray-400 max-w-md text-center">
                  Deconstructing video, identifying actions, and synthesizing documentation...
                </p>
              </div>
            )}

            {/* Results Section */}
            {sopContent && (
              <div className="animate-in slide-in-from-bottom-8 duration-700">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-2xl font-bold flex items-center gap-3">
                    <FileText className="w-6 h-6 text-blue-400" />
                    Generated Documentation
                  </h3>
                  {processingTime && (
                    <span className="text-sm text-gray-400 bg-gray-800 px-3 py-1 rounded-full border border-gray-700">
                      Generated in {processingTime}s
                    </span>
                  )}
                </div>

                <SOPViewer content={sopContent} processingTime={processingTime} />

                <div className="mt-8 flex justify-center">
                  <button
                    onClick={() => {
                      setSopContent('');
                      setIsLoading(false);
                    }}
                    className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
                  >
                    <LayoutGrid className="w-4 h-4" />
                    Process Another Video
                  </button>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
