import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import { Download, RefreshCw, Share2, CheckCircle2, Film, Sparkles, Smartphone, Eye, AlertCircle, Loader2 } from 'lucide-react';
import { getTaskStatus, getDownloadUrl, type TaskStatusResponse, API_BASE_URL } from '../services/api';

export const Result: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<'reframed' | 'comparison'>('reframed');

  const locationState = (location.state as {
    taskId?: string;
    videoId?: string;
    targetId?: string;
    targetName?: string;
    trackingAlgorithm?: string;
    ratio?: string;
    smoothing?: number;
  }) || {};

  const { taskId, videoId, targetId, targetName } = locationState;
  const ratio = locationState.ratio || '9:16';
  const algorithmDisplay = locationState.trackingAlgorithm === 'deepsort' ? 'DeepSORT (OSNet)' : 'ByteTrack';

  const [taskData, setTaskData] = useState<TaskStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Poll task status if taskId is present
  useEffect(() => {
    if (!taskId) {
      if (!videoId) {
        setError('No active processing task or video ID found.');
        setIsLoading(false);
      } else {
        setIsLoading(false);
      }
      return;
    }

    let isMounted = true;
    let timer: NodeJS.Timeout;

    const poll = async () => {
      try {
        const data = await getTaskStatus(taskId);
        if (!isMounted) return;
        setTaskData(data);

        if (data.status === 'completed') {
          setIsLoading(false);
        } else if (data.status === 'failed') {
          setError(data.error || 'Video reframing failed.');
          setIsLoading(false);
        } else {
          // Continue polling while queued or processing
          timer = setTimeout(poll, 1500);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || 'Failed to poll task status.');
        setIsLoading(false);
      }
    };

    poll();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, videoId]);

  // Resolve video URLs
  const highlightVideoPath = taskData?.output_video_url || (videoId ? `/static/outputs/${videoId}/fancam_${targetId || 'p1'}_${ratio.replace(':', '_')}.mp4` : '');
  const comparisonVideoPath = taskData?.comparison_video_url || (videoId ? `/static/outputs/${videoId}/comparison_${targetId || 'p1'}.mp4` : '');

  const highlightVideoUrl = highlightVideoPath ? `${API_BASE_URL}${highlightVideoPath}` : '';
  const comparisonVideoUrl = comparisonVideoPath ? `${API_BASE_URL}${comparisonVideoPath}` : '';

  const activeVideoSrc = activeTab === 'reframed' ? highlightVideoUrl : comparisonVideoUrl;

  const handleDownload = () => {
    if (!videoId) {
      toast.error('No video ID available for download.');
      return;
    }
    const downloadUrl = getDownloadUrl(videoId);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `fancam_${targetName || targetId || videoId}.mp4`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('FanCam highlight download started!');
  };

  const getAspectRatioClasses = () => {
    if (activeTab === 'comparison') {
      return 'aspect-video max-w-2xl';
    }
    if (ratio === '1:1') {
      return 'aspect-square max-w-md';
    }
    if (ratio === '16:9') {
      return 'aspect-video max-w-2xl';
    }
    // Default 9:16
    return 'aspect-[9/16] max-w-sm';
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-8 max-w-5xl mx-auto w-full">
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          <span className="px-2.5 py-1 rounded bg-emerald-400 text-black font-mono text-xs font-bold">
            {isLoading ? 'PROCESSING' : error ? 'FAILED' : 'COMPLETED'}
          </span>
          <span className="text-white/60 text-xs font-mono">
            {isLoading
              ? `/ ${taskData?.current_step || 'RENDERING HIGHLIGHT'} (${taskData?.progress ?? 0}%)`
              : error
              ? `/ ERROR OCCURRED`
              : '/ EXPORT & DOWNLOAD READY'}
          </span>
        </div>

        {/* Heading */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-white">
              {isLoading ? 'Generating Your FanCam Highlight' : error ? 'Processing Error' : 'Your FanCam Highlight is Ready'}
            </h1>
            <p className="text-sm text-white/70 mt-1">
              {targetName || targetId || 'Subject'} isolated, dynamically tracked, and formatted for {ratio} video feeds.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/upload')}
              className="px-3.5 py-2 rounded-lg border border-white/20 text-white/80 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Process Another</span>
            </button>
            <button
              onClick={handleDownload}
              disabled={isLoading || !!error}
              className={`px-5 py-2.5 rounded-lg text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-lg transition-transform ${
                isLoading || !!error
                  ? 'bg-white/20 text-white/40 cursor-not-allowed'
                  : 'bg-white text-black hover:bg-neutral-200 hover:scale-105 active:scale-95'
              }`}
            >
              <Download className="w-4 h-4" />
              <span>Download Video</span>
            </button>
          </div>
        </div>

        {/* Video Player Display */}
        <div className="vantage-glass rounded-2xl p-6 mb-8 flex flex-col items-center">
          {/* View toggle */}
          <div className="inline-flex rounded-lg p-1 bg-white/5 border border-white/10 mb-6">
            <button
              onClick={() => setActiveTab('reframed')}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'reframed' ? 'bg-white text-black' : 'text-white/70 hover:text-white'
              }`}
            >
              {ratio} Reframed Highlight
            </button>
            <button
              onClick={() => setActiveTab('comparison')}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'comparison' ? 'bg-white text-black' : 'text-white/70 hover:text-white'
              }`}
            >
              Source vs Tracked Crop
            </button>
          </div>

          {/* Player Container */}
          <div className={`relative w-full ${getAspectRatioClasses()} rounded-2xl overflow-hidden border-2 border-white/30 shadow-2xl bg-neutral-950 flex items-center justify-center`}>
            {isLoading ? (
              <div className="flex flex-col items-center gap-3 p-8 text-center">
                <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
                <p className="text-sm font-medium text-white">{taskData?.current_step || 'Rendering frames...'}</p>
                <div className="w-48 bg-white/10 h-1.5 rounded-full overflow-hidden mt-1">
                  <div
                    className="bg-emerald-400 h-full transition-all duration-300"
                    style={{ width: `${taskData?.progress ?? 10}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-white/50">{taskData?.progress ?? 0}% completed</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center gap-3 p-8 text-center text-rose-400">
                <AlertCircle className="w-10 h-10" />
                <p className="text-sm font-medium">{error}</p>
                <button
                  onClick={() => navigate('/upload')}
                  className="mt-2 text-xs text-white/70 underline hover:text-white"
                >
                  Return to Upload
                </button>
              </div>
            ) : activeVideoSrc ? (
              <>
                <video
                  key={activeVideoSrc}
                  className="w-full h-full object-cover"
                  autoPlay
                  loop
                  controls
                  playsInline
                  src={activeVideoSrc}
                />
                {/* Live Indicator overlay */}
                <div className="absolute top-3 left-3 bg-black/70 backdrop-blur px-2.5 py-1 rounded text-[11px] font-mono text-emerald-400 flex items-center gap-1.5 pointer-events-none">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Centered {targetName || targetId || 'Target'} ({ratio})
                </div>
              </>
            ) : (
              <div className="text-white/40 text-xs font-mono">No video stream available</div>
            )}
          </div>

          {/* Quick Metadata Bar */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-4 w-full max-w-2xl text-center text-xs font-mono text-white/70 pt-4 border-t border-white/10">
            <div>
              <span className="block text-white font-semibold">
                {ratio === '9:16' ? '1080 × 1920' : ratio === '1:1' ? '1080 × 1080' : '1920 × 1080'}
              </span>
              <span className="text-[10px] text-white/40">Resolution</span>
            </div>
            <div>
              <span className="block text-white font-semibold">Source FPS</span>
              <span className="text-[10px] text-white/40">Framerate</span>
            </div>
            <div>
              <span className="block text-white font-semibold">H.264 / AAC</span>
              <span className="text-[10px] text-white/40">Codec</span>
            </div>
            <div>
              <span className="block text-emerald-400 font-semibold">{algorithmDisplay}</span>
              <span className="text-[10px] text-white/40">Tracker</span>
            </div>
            <div>
              <span className="block text-white font-semibold">Ready</span>
              <span className="text-[10px] text-white/40">Status</span>
            </div>
          </div>
        </div>

        {/* Social Platforms Export Checklist */}
        <div className="vantage-glass rounded-xl p-6 text-left">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-white font-mono mb-3">
            Ready to Publish
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-white/80">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>TikTok (9:16 Fullscreen)</span>
            </div>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Instagram Reels & Stories</span>
            </div>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>YouTube Shorts (Safe Zone)</span>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Result;
