import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import {
  Check,
  Sparkles,
  Smartphone,
  Square,
  Monitor,
  AlertCircle,
  RefreshCw,
  UserCheck,
  Loader2,
  Film,
  Scan,
} from 'lucide-react';
import {
  detectFramePeople,
  selectTarget,
  startProcessingVideo,
  getVideoMetadata,
  extractFramePreview,
  API_BASE_URL,
  type VideoMetaResponse,
  type DetectedPerson,
} from '../services/api';

export const SelectTarget: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const locationState = (location.state as {
    videoId?: string;
    videoName?: string;
  }) || {};

  const videoId = locationState.videoId;

  // Video metadata & timeline state
  const [videoMeta, setVideoMeta] = useState<VideoMetaResponse | null>(null);
  const [selectedFrame, setSelectedFrame] = useState<number>(0);
  const [selectedTimestamp, setSelectedTimestamp] = useState<number>(0);
  const [framePreviewUrl, setFramePreviewUrl] = useState<string | null>(null);
  const [isLoadingFrame, setIsLoadingFrame] = useState<boolean>(true);
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Real backend detections and target selection
  const [detectedPeople, setDetectedPeople] = useState<DetectedPerson[]>([]);
  const [hasRunDetection, setHasRunDetection] = useState<boolean>(false);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);

  // Target and algorithm configuration
  const [trackingAlgorithm, setTrackingAlgorithm] = useState<'bytetrack' | 'deepsort'>('bytetrack');
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '1:1' | '16:9'>('9:16');
  const [smoothingLevel, setSmoothingLevel] = useState<number>(85);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressStep, setProgressStep] = useState<string>('');

  // 1. Initial Load: Fetch video metadata and extract Frame 0 preview (NO auto YOLO detection)
  useEffect(() => {
    if (!videoId) {
      setFetchError('No active video found. Please upload a video first.');
      setIsLoadingFrame(false);
      return;
    }

    let isMounted = true;
    const initVideo = async () => {
      setIsLoadingFrame(true);
      setFetchError(null);
      try {
        const meta = await getVideoMetadata(videoId);
        if (!isMounted) return;
        setVideoMeta(meta);

        // Extract frame 0 preview initially
        const frame0 = await extractFramePreview(videoId, 0);
        if (!isMounted) return;
        const pUrl = frame0.preview_url.startsWith('http')
          ? frame0.preview_url
          : `${API_BASE_URL}${frame0.preview_url}`;
        setFramePreviewUrl(pUrl);
        setSelectedFrame(0);
        setSelectedTimestamp(0);
      } catch (err: any) {
        if (!isMounted) return;
        const errorMsg = err.message || 'Failed to initialize video metadata.';
        setFetchError(errorMsg);
        toast.error(errorMsg);
      } finally {
        if (isMounted) setIsLoadingFrame(false);
      }
    };

    initVideo();
    return () => {
      isMounted = false;
    };
  }, [videoId]);

  // Handle timeline scrubber change
  const handleSeekFrame = async (newFrame: number) => {
    if (!videoId || !videoMeta) return;

    setSelectedFrame(newFrame);
    const estTimestamp = videoMeta.fps > 0 ? newFrame / videoMeta.fps : 0;
    setSelectedTimestamp(estTimestamp);

    // Requirement: Clear previous detections & selected target whenever frame changes
    setDetectedPeople([]);
    setSelectedTargetId(null);
    setHasRunDetection(false);

    try {
      setIsLoadingFrame(true);
      const res = await extractFramePreview(videoId, newFrame);
      const pUrl = res.preview_url.startsWith('http')
        ? res.preview_url
        : `${API_BASE_URL}${res.preview_url}`;
      setFramePreviewUrl(pUrl);
      setSelectedTimestamp(res.timestamp_sec);
    } catch (err: any) {
      toast.error('Failed to extract selected frame preview.');
    } finally {
      setIsLoadingFrame(false);
    }
  };

  // Requirement: Detect People on currently selected frame
  const handleDetectPeople = async () => {
    if (!videoId) return;

    setIsDetecting(true);
    setFetchError(null);

    try {
      const data = await detectFramePeople(videoId, selectedFrame, 0.35);

      if (data.frame_preview_url) {
        const previewUrl = data.frame_preview_url.startsWith('http')
          ? data.frame_preview_url
          : `${API_BASE_URL}${data.frame_preview_url}`;
        setFramePreviewUrl(previewUrl);
      }

      const people = data.detected_people || [];
      setDetectedPeople(people);
      setHasRunDetection(true);

      if (people.length > 0) {
        toast.success(`Detected ${people.length} person(s) in Frame ${selectedFrame}! Click to select target.`);
      } else {
        toast.info(`No people detected in Frame ${selectedFrame}. Try choosing a different frame.`);
      }
    } catch (err: any) {
      const msg = err.message || 'Failed to detect people in selected frame.';
      toast.error(msg);
    } finally {
      setIsDetecting(false);
    }
  };

  const selectedPerson = detectedPeople.find((p) => p.id === selectedTargetId);

  // Requirement: Once target is selected, Generate FanCam Highlight
  const handleStartGeneration = async () => {
    if (!selectedTargetId) {
      toast.warning('Please click on one of the detected individuals to select your target.');
      return;
    }

    if (!videoId) {
      toast.error('Video ID missing. Please return to upload and re-select your video.');
      return;
    }

    const algoName = trackingAlgorithm === 'deepsort' ? 'DeepSORT' : 'ByteTrack';
    setIsProcessing(true);
    setProgressStep(`Initializing ${algoName} multi-object tracking...`);

    try {
      // 1. Register selected target and compute OSNet embedding
      setProgressStep('Extracting OSNet appearance embedding for target...');
      await selectTarget(videoId, selectedTargetId, selectedPerson?.crop_url);

      // 2. Queue video processing task with chosen algorithm
      setProgressStep(`Dispatching ${algoName} background tracking...`);
      const procRes = await startProcessingVideo({
        video_id: videoId,
        target_id: selectedTargetId,
        tracking_algorithm: trackingAlgorithm,
        aspect_ratio: aspectRatio,
        smoothing_level: smoothingLevel,
      });

      // Navigate to results with taskId and parameters
      navigate('/result', {
        state: {
          taskId: procRes.task_id,
          videoId: videoId,
          targetId: selectedTargetId,
          targetName: selectedPerson?.name || selectedTargetId,
          trackingAlgorithm,
          ratio: aspectRatio,
          smoothing: smoothingLevel,
        },
      });
    } catch (err: any) {
      toast.error(err.message || 'Failed to start video processing.');
      setIsProcessing(false);
    }
  };

  const totalFrames = videoMeta?.frame_count || 1;
  const durationSec = videoMeta?.duration_seconds || 0;

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-8 max-w-6xl mx-auto w-full">
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          <span className="px-2.5 py-1 rounded bg-white text-black font-mono text-xs font-bold">STEP 02</span>
          <span className="text-white/60 text-xs font-mono">/ TIMELINE SCRUBBING & TARGET LOCK</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-white">
              {selectedPerson ? 'Confirm Target & Aspect Ratio' : 'Select Frame & Detect Subject'}
            </h1>
            <p className="text-sm text-white/70 mt-1">
              Scrub the timeline slider to pick the best frame, detect people, and click your target to lock.
            </p>
          </div>

          {hasRunDetection && (
            <div className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg flex items-center gap-2 self-start sm:self-auto">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>
                {detectedPeople.length} {detectedPeople.length === 1 ? 'Person' : 'People'} Detected
              </span>
            </div>
          )}
        </div>

        {/* Interactive Workspace Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Main Frame Canvas (8 Cols) */}
          <div className="lg:col-span-8 vantage-glass rounded-2xl p-4 sm:p-5 flex flex-col gap-4">
            <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-neutral-950 border border-white/20 select-none flex items-center justify-center">
              {isLoadingFrame && !framePreviewUrl ? (
                <div className="flex flex-col items-center justify-center gap-3 p-8 text-white/80">
                  <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
                  <span className="text-xs font-mono tracking-wide">
                    Loading video frame preview...
                  </span>
                </div>
              ) : fetchError ? (
                <div className="flex flex-col items-center justify-center gap-3 p-8 text-center max-w-md">
                  <AlertCircle className="w-8 h-8 text-rose-400" />
                  <p className="text-sm text-white/90">{fetchError}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <button
                      onClick={() => navigate('/upload')}
                      className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-mono transition-colors"
                    >
                      Go to Upload
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Actual Video Frame Preview */}
                  {framePreviewUrl ? (
                    <img
                      src={framePreviewUrl}
                      alt={`Frame ${selectedFrame} Preview`}
                      className={`w-full h-full object-fill pointer-events-none transition-opacity ${
                        isLoadingFrame ? 'opacity-50' : 'opacity-100'
                      }`}
                    />
                  ) : (
                    <div className="text-white/40 text-xs font-mono">No preview frame available</div>
                  )}

                  {/* Frame Loading Spinner Indicator */}
                  {isLoadingFrame && (
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center">
                      <Loader2 className="w-7 h-7 text-white animate-spin" />
                    </div>
                  )}

                  {/* Empty Detection Overlay Message */}
                  {hasRunDetection && detectedPeople.length === 0 && !isDetecting && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center">
                      <AlertCircle className="w-8 h-8 text-amber-400 mb-2" />
                      <p className="text-sm font-semibold text-white">No Persons Detected in Frame {selectedFrame}</p>
                      <p className="text-xs text-white/60 mt-1 max-w-sm">
                        YOLO did not find clear human subjects in this frame. Scrub the timeline to a frame where your subject is clearly visible.
                      </p>
                    </div>
                  )}

                  {/* Interactive Bounding Boxes Overlaid using exact normalized % coordinates */}
                  {detectedPeople.map((person) => {
                    const isSelected = selectedTargetId === person.id;
                    return (
                      <button
                        key={person.id}
                        type="button"
                        onClick={() => {
                          setSelectedTargetId(person.id);
                          toast.info(`Target locked to ${person.name} (${person.confidence.toFixed(1)}%)`);
                        }}
                        style={{
                          position: 'absolute',
                          top: `${person.box.top}%`,
                          left: `${person.box.left}%`,
                          width: `${person.box.width}%`,
                          height: `${person.box.height}%`,
                        }}
                        className={`group border-2 transition-all cursor-pointer rounded pointer-events-auto ${
                          isSelected
                            ? 'border-emerald-400 bg-emerald-400/25 shadow-[0_0_20px_rgba(52,211,153,0.7)] z-30'
                            : 'border-white/50 bg-black/20 hover:border-white hover:bg-white/10 z-20'
                        }`}
                        title={`Click to select ${person.name}`}
                      >
                        {/* Person Label Tag with confidence and ID */}
                        <span
                          className={`absolute -top-7 left-0 px-2 py-0.5 rounded text-[10px] font-mono font-semibold whitespace-nowrap flex items-center gap-1.5 shadow ${
                            isSelected
                              ? 'bg-emerald-400 text-black font-bold'
                              : 'bg-black/80 text-white border border-white/20 group-hover:bg-white group-hover:text-black'
                          }`}
                        >
                          {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                          <span>{person.name}</span>
                          <span className="opacity-90">({person.confidence.toFixed(1)}%)</span>
                        </span>
                      </button>
                    );
                  })}

                  <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur px-2.5 py-1 rounded text-xs text-white/80 font-mono pointer-events-none z-10">
                    Frame {selectedFrame} • {selectedTimestamp.toFixed(2)}s / {durationSec.toFixed(2)}s
                  </div>
                </>
              )}
            </div>

            {/* Timeline Seekable Slider Bar */}
            <div className="vantage-glass rounded-xl p-3 sm:p-4 flex flex-col gap-2 border border-white/10 bg-white/5">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-white/80 flex items-center gap-1.5">
                  <Film className="w-3.5 h-3.5 text-white/60" />
                  <span>Timeline Scrubber</span>
                </span>
                <span className="text-emerald-400">
                  Frame {selectedFrame} of {Math.max(0, totalFrames - 1)} ({selectedTimestamp.toFixed(2)}s)
                </span>
              </div>
              <input
                type="range"
                min="0"
                max={Math.max(0, totalFrames - 1)}
                value={selectedFrame}
                disabled={isLoadingFrame || isDetecting || isProcessing || !videoMeta}
                onChange={(e) => handleSeekFrame(Number(e.target.value))}
                className="w-full accent-emerald-400 cursor-pointer h-2 bg-white/20 rounded-lg"
              />
              <div className="flex items-center justify-between text-[10px] font-mono text-white/40">
                <span>0:00 (Start)</span>
                <span>Move slider to pick any frame before detection</span>
                <span>{durationSec.toFixed(1)}s (End)</span>
              </div>
            </div>

            {/* Target Details Strip */}
            <div className="flex items-center justify-between text-xs text-white/70 px-1">
              <span>
                Target:{' '}
                <strong className="text-white">
                  {selectedPerson ? `${selectedPerson.name} (${selectedPerson.role})` : hasRunDetection ? 'None selected (click a box)' : 'Detect people first'}
                </strong>
              </span>
              <span>
                YOLO Confidence Score:{' '}
                <strong className="text-emerald-400">
                  {selectedPerson ? `${selectedPerson.confidence.toFixed(1)}%` : '—'}
                </strong>
              </span>
            </div>
          </div>

          {/* Configuration Sidebar (4 Cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            {/* Tracking Algorithm Selector */}
            {selectedTargetId && (
              <div className="vantage-glass rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold uppercase tracking-wider text-white font-mono block">
                    Tracking Algorithm
                  </label>
                  <span className="text-[10px] font-mono text-emerald-400">
                    {trackingAlgorithm === 'bytetrack' ? 'Fast IoU Association' : 'Appearance Cascade + Motion'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setTrackingAlgorithm('bytetrack')}
                    className={`p-3 rounded-lg border flex flex-col items-center justify-center gap-1 transition-all ${
                      trackingAlgorithm === 'bytetrack'
                        ? 'border-emerald-400 bg-emerald-500/20 text-white font-semibold shadow-[0_0_15px_rgba(52,211,153,0.3)]'
                        : 'border-white/15 bg-white/5 text-white/70 hover:border-white/30'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono font-bold">ByteTrack</span>
                      {trackingAlgorithm === 'bytetrack' && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                    </div>
                    <span className="text-[9px] opacity-75">Default • Real-time</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setTrackingAlgorithm('deepsort')}
                    className={`p-3 rounded-lg border flex flex-col items-center justify-center gap-1 transition-all ${
                      trackingAlgorithm === 'deepsort'
                        ? 'border-emerald-400 bg-emerald-500/20 text-white font-semibold shadow-[0_0_15px_rgba(52,211,153,0.3)]'
                        : 'border-white/15 bg-white/5 text-white/70 hover:border-white/30'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono font-bold">DeepSORT</span>
                      {trackingAlgorithm === 'deepsort' && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                    </div>
                    <span className="text-[9px] opacity-75">Alternative • OSNet Re-ID</span>
                  </button>
                </div>
              </div>
            )}

            {/* Aspect Ratio Selector */}
            <div className="vantage-glass rounded-xl p-5 space-y-3">
              <label className="text-xs font-semibold uppercase tracking-wider text-white font-mono block">
                Target Aspect Ratio
              </label>

              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setAspectRatio('9:16')}
                  className={`p-3 rounded-lg border flex flex-col items-center justify-center gap-1.5 transition-all ${
                    aspectRatio === '9:16'
                      ? 'border-white bg-white text-black font-semibold shadow'
                      : 'border-white/15 bg-white/5 text-white/70 hover:border-white/30'
                  }`}
                >
                  <Smartphone className="w-4 h-4" />
                  <span className="text-xs font-mono">9:16</span>
                  <span className="text-[9px] opacity-75">Reels/Shorts</span>
                </button>

                <button
                  type="button"
                  onClick={() => setAspectRatio('1:1')}
                  className={`p-3 rounded-lg border flex flex-col items-center justify-center gap-1.5 transition-all ${
                    aspectRatio === '1:1'
                      ? 'border-white bg-white text-black font-semibold shadow'
                      : 'border-white/15 bg-white/5 text-white/70 hover:border-white/30'
                  }`}
                >
                  <Square className="w-4 h-4" />
                  <span className="text-xs font-mono">1:1</span>
                  <span className="text-[9px] opacity-75">Square Feed</span>
                </button>

                <button
                  type="button"
                  onClick={() => setAspectRatio('16:9')}
                  className={`p-3 rounded-lg border flex flex-col items-center justify-center gap-1.5 transition-all ${
                    aspectRatio === '16:9'
                      ? 'border-white bg-white text-black font-semibold shadow'
                      : 'border-white/15 bg-white/5 text-white/70 hover:border-white/30'
                  }`}
                >
                  <Monitor className="w-4 h-4" />
                  <span className="text-xs font-mono">16:9</span>
                  <span className="text-[9px] opacity-75">Standard</span>
                </button>
              </div>
            </div>

            {/* Camera Motion Smoothing */}
            <div className="vantage-glass rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-white font-mono">
                  Kinetic Smoothing Filter
                </label>
                <span className="text-xs font-mono text-emerald-400">{smoothingLevel}%</span>
              </div>
              <input
                type="range"
                min="30"
                max="100"
                value={smoothingLevel}
                onChange={(e) => setSmoothingLevel(Number(e.target.value))}
                className="w-full accent-white cursor-pointer"
              />
              <p className="text-[11px] text-white/50 leading-relaxed">
                Applies cinematic pan dampening to eliminate jittery camera motion when the subject crosses paths.
              </p>
            </div>

            {/* Dynamic Action Button: Detect People VS Generate FanCam Highlight */}
            {selectedPerson ? (
              <button
                onClick={handleStartGeneration}
                disabled={isProcessing}
                className={`w-full py-4 rounded-xl font-semibold text-sm transition-all shadow-xl flex items-center justify-center gap-2 ${
                  isProcessing
                    ? 'bg-white/20 text-white/40 cursor-not-allowed'
                    : 'bg-white text-black hover:bg-neutral-200 active:scale-98'
                }`}
              >
                {isProcessing ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-black border-t-transparent animate-spin" />
                    <span className="text-xs font-mono">{progressStep}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Generate FanCam Highlight</span>
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={handleDetectPeople}
                disabled={isDetecting || isLoadingFrame || !videoId}
                className={`w-full py-4 rounded-xl font-semibold text-sm transition-all shadow-xl flex items-center justify-center gap-2 ${
                  isDetecting || isLoadingFrame || !videoId
                    ? 'bg-white/20 text-white/40 cursor-not-allowed'
                    : 'bg-emerald-400 text-black hover:bg-emerald-300 active:scale-98'
                }`}
              >
                {isDetecting ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-black border-t-transparent animate-spin" />
                    <span className="text-xs font-mono">Running YOLO Detection on Frame {selectedFrame}...</span>
                  </>
                ) : (
                  <>
                    <Scan className="w-4 h-4" />
                    <span>Detect People (Frame {selectedFrame})</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SelectTarget;
