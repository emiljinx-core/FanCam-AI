import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import { UploadCloud, FileVideo, AlertCircle, CheckCircle2, Film, Sparkles, ArrowRight } from 'lucide-react';
import { uploadVideoFile } from '../services/api';

const MAX_BYTES = 100 * 1024 * 1024; // 100 MB strict constraint

export const Upload: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<{
    name: string;
    size: number;
    url: string;
    rawFile?: File;
    videoId?: string;
  } | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null);

  // Sample clips hosted in the project's public GitHub repository
  const SAMPLE_BASE_URL = 'https://raw.githubusercontent.com/emiljinx-core/FanCam-AI/main/assets';
  const sampleClips = [
    {
      id: 'sample-dance',
      title: 'Dance Demo',
      fileName: 'danceDemo.mp4',
      githubRawUrl: `${SAMPLE_BASE_URL}/danceDemo.mp4`,
      size: '22.7 MB',
      duration: '0:24',
      thumbnail: `${SAMPLE_BASE_URL}/danceDemo.jpg`,
      peopleCount: 7
    },
    {
      id: 'sample-sports',
      title: 'Street Demo',
      fileName: 'streetDemo.mp4',
      githubRawUrl: `${SAMPLE_BASE_URL}/streetDemo.mp4`,
      size: '6.2 MB',
      duration: '0:07',
      thumbnail: `${SAMPLE_BASE_URL}/streetDemo.jpg`,
      peopleCount: 16
    },
    {
      id: 'sample-party',
      title: 'Movie Demo',
      fileName: 'movieDemo.mp4',
      githubRawUrl: `${SAMPLE_BASE_URL}/movieDemo.mp4`,
      size: '22.2 MB',
      duration: '0:28',
      thumbnail: `${SAMPLE_BASE_URL}/movieDemo.jpg`,
      peopleCount: 1
    }
  ];

  const handleValidateAndSetFile = (file: File, displayName: string = file.name) => {
    // 100 MB check
    if (file.size > MAX_BYTES) {
      toast.error('Please upload a file with less than 100 MB.', {
        icon: <AlertCircle className="w-5 h-5 text-rose-500" />
      });
      return;
    }

    // Format check (.mp4, .mov)
    const validExtensions = ['video/mp4', 'video/quicktime'];
    const hasValidExt = file.name.toLowerCase().endsWith('.mp4') || file.name.toLowerCase().endsWith('.mov');

    if (!validExtensions.includes(file.type) && !hasValidExt) {
      toast.error('Unsupported container. Please provide a valid .mp4 or .mov file.');
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setSelectedFile({
      name: displayName,
      size: file.size,
      url: objectUrl,
      rawFile: file,
    });

    toast.success(`Video verified: ${(file.size / (1024 * 1024)).toFixed(1)} MB (${displayName})`);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleValidateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleValidateAndSetFile(e.target.files[0]);
    }
  };

  const handleUseSample = async (sample: typeof sampleClips[0]) => {
    if (loadingSampleId) return;
    setLoadingSampleId(sample.id);
    try {
      const response = await fetch(sample.githubRawUrl);
      if (!response.ok) {
        throw new Error(`Sample download failed (${response.status})`);
      }
      const blob = await response.blob();
      const file = new File([blob], sample.fileName, { type: 'video/mp4' });

      // Same validation/preview path used by drag-and-drop uploads
      handleValidateAndSetFile(file, sample.title);
      toast.info(`Loaded demo video: ${sample.title}`);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load the sample clip from GitHub.');
    } finally {
      setLoadingSampleId(null);
    }
  };

  const proceedToTargetSelection = async () => {
    if (!selectedFile) {
      toast.warning('Please select or upload a video file first.');
      return;
    }
    setIsAnalyzing(true);
    try {
      let videoId = selectedFile.videoId;

      // If user uploaded a physical File and hasn't uploaded to backend yet
      if (!videoId && selectedFile.rawFile) {
        toast.info('Uploading video to backend...');
        const uploadRes = await uploadVideoFile(selectedFile.rawFile);
        videoId = uploadRes.video_id;
        setSelectedFile((prev) => (prev ? { ...prev, videoId } : null));
      }

      navigate('/select-target', {
        state: {
          videoId: videoId,
          videoName: selectedFile.name,
        },
      });
    } catch (err: any) {
      toast.error(err.message || 'Failed to upload video to backend.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-8 max-w-5xl mx-auto w-full">
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          <span className="px-2.5 py-1 rounded bg-white text-black font-mono text-xs font-bold">STEP 01</span>
          <span className="text-white/60 text-xs font-mono">/ VIDEO UPLOAD & CONSTRAINT CHECK</span>
        </div>

        {/* Title */}
        <div className="mb-8">
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-white">
            Upload Group Footage
          </h1>
          <p className="text-sm sm:text-base text-white/70 mt-1.5 max-w-2xl">
            Drop your party, sports or event clips below.<br className="hidden sm:inline" /> 
            
          </p>
        </div>

        {/* Upload Drop Zone Card */}
        <div
          onDragEnter={() => setDragActive(true)}
          onDragLeave={() => setDragActive(false)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`vantage-glass rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all border-2 border-dashed ${
            dragActive
              ? 'border-emerald-400 bg-emerald-500/10 scale-[1.01]'
              : 'border-white/20 hover:border-white/40 hover:bg-white/[0.03]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,.mp4,.mov"
            className="hidden"
            onChange={handleFileChange}
          />

          <div className="flex flex-col items-center justify-center max-w-md mx-auto space-y-4">
            <div className="w-16 h-16 rounded-full vantage-glass-button flex items-center justify-center text-white/90 shadow-xl group-hover:scale-110 transition-transform">
              <UploadCloud className="w-8 h-8 text-white" />
            </div>

            <div>
              <p className="text-base sm:text-lg font-medium text-white">
                Drag and drop your group video here, or <span className="underline decoration-white/50 text-white">browse</span>
              </p>
              <p className="text-xs sm:text-sm text-white/50 mt-1 font-mono">
                Supports MP4, MOV • No signup required
              </p>
            </div>

            {/* Constraint Pill */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-white/80">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Strict 100 MB Limit</span>
            </div>
          </div>
        </div>

        {/* Selected File Banner */}
        {selectedFile && (
          <div className="mt-6 vantage-glass rounded-xl p-4 flex items-center justify-between border border-emerald-500/30 bg-emerald-950/20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <FileVideo className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="text-left">
                <p className="text-sm font-semibold text-white truncate max-w-xs sm:max-w-md">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-white/60 font-mono">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Verified Safe
                </p>
              </div>
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                proceedToTargetSelection();
              }}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white text-black font-semibold text-xs sm:text-sm hover:bg-neutral-200 transition-all shadow-md"
            >
              {isAnalyzing ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-black border-t-transparent animate-spin" />
                  <span>Scanning Frame 0...</span>
                </>
              ) : (
                <>
                  <span>Select Target</span>
                  <ArrowRight className="w-4 h-4 text-black" />
                </>
              )}
            </button>
          </div>
        )}

        {/* Sample Clips Section */}
        <div className="mt-12">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Film className="w-4 h-4 text-white/70" />
              <h3 className="text-sm font-semibold uppercase tracking-wider text-white/80 font-mono">
                Or Test Instant Sample Clips
              </h3>
            </div>
            <span className="text-xs text-white/50">1-click automated load</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {sampleClips.map((sample) => (
              <div
                key={sample.id}
                onClick={() => handleUseSample(sample)}
                className={`vantage-glass rounded-xl p-3 text-left transition-all ${
                  loadingSampleId === sample.id
                    ? 'opacity-70 cursor-wait'
                    : 'cursor-pointer group hover:border-white/40'
                }`}
              >
                <div className="relative aspect-video rounded-lg overflow-hidden mb-3 bg-neutral-900">
                  <img
                    src={sample.thumbnail}
                    alt={sample.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-[10px] font-mono text-white">
                    {loadingSampleId === sample.id ? 'Loading…' : sample.duration}
                  </span>
                  <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/60 text-[10px] font-mono text-emerald-400">
                    {sample.peopleCount} people detected
                  </span>
                </div>
                <h4 className="text-sm font-medium text-white group-hover:text-emerald-400 transition-colors">
                  {sample.title}
                </h4>
                <p className="text-xs text-white/50 font-mono mt-0.5">
                  {loadingSampleId === sample.id ? 'Downloading from GitHub…' : sample.size}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Upload;