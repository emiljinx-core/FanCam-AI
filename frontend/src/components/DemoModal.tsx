import React, { useState } from 'react';
import { X, Play, CheckCircle2, Sliders, Smartphone, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DemoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DemoModal: React.FC<DemoModalProps> = ({ isOpen, onClose }) => {
  const [mode, setMode] = useState<'split' | 'reframe' | 'raw'>('split');
  const navigate = useNavigate();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl vantage-glass rounded-2xl p-6 sm:p-8 flex flex-col gap-6 shadow-2xl border border-white/20">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <h3 className="text-xl font-display font-medium text-white">Interactive Transformation Demo</h3>
            </div>
            <p className="text-xs sm:text-sm text-white/70 mt-0.5">
              Crowded Group Input (16:9) → ByteTrack Target Lock → Cinematic 9:16 Vertical Reel
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
            aria-label="Close demo"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Switcher */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="inline-flex rounded-lg p-1 bg-white/5 border border-white/10">
            <button
              onClick={() => setMode('split')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'split' ? 'bg-white text-black shadow' : 'text-white/70 hover:text-white'
              }`}
            >
              Side-by-Side (Crop vs Source)
            </button>
            <button
              onClick={() => setMode('reframe')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'reframe' ? 'bg-white text-black shadow' : 'text-white/70 hover:text-white'
              }`}
            >
              9:16 Social Reframe
            </button>
            <button
              onClick={() => setMode('raw')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'raw' ? 'bg-white text-black shadow' : 'text-white/70 hover:text-white'
              }`}
            >
              Raw Frame + AI Boxes
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-white/60 font-mono">
            <span>Model: YOLO-v8x</span>
            <span>•</span>
            <span>Tracker: ByteTrack-Realtime</span>
          </div>
        </div>

        {/* Demo Video Container */}
        <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-neutral-950 border border-white/15 flex items-center justify-center">
          {mode === 'split' && (
            <div className="relative w-full h-full flex">
              {/* Left: Original with detections */}
              <div className="w-1/2 h-full relative border-r border-white/20 overflow-hidden">
                <video
                  className="w-full h-full object-cover"
                  autoPlay
                  muted
                  loop
                  playsInline
                  src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
                />
                <div className="absolute top-3 left-3 bg-black/60 backdrop-blur px-2 py-1 rounded text-[11px] text-white/80">
                  Group Input (4 Detected)
                </div>
                {/* Simulated Bounding Boxes */}
                <div className="absolute top-[28%] left-[34%] w-[22%] h-[52%] border-2 border-emerald-400 bg-emerald-400/10 rounded pointer-events-none transition-all duration-300">
                  <span className="absolute -top-5 left-0 bg-emerald-500 text-black text-[10px] font-bold px-1 rounded uppercase tracking-wider">
                    TARGET #02 (98.6%)
                  </span>
                </div>
                <div className="absolute top-[32%] left-[12%] w-[18%] h-[48%] border border-white/40 bg-white/5 rounded pointer-events-none">
                  <span className="absolute -top-4 left-0 bg-black/70 text-white/70 text-[9px] px-1 rounded">
                    #01 (92%)
                  </span>
                </div>
                <div className="absolute top-[30%] left-[62%] w-[19%] h-[50%] border border-white/40 bg-white/5 rounded pointer-events-none">
                  <span className="absolute -top-4 left-0 bg-black/70 text-white/70 text-[9px] px-1 rounded">
                    #03 (95%)
                  </span>
                </div>
              </div>

              {/* Right: Reframed 9:16 Vertical Highlight */}
              <div className="w-1/2 h-full relative bg-neutral-900 flex items-center justify-center p-2">
                <div className="relative h-full aspect-[9/16] rounded-lg overflow-hidden border-2 border-white/30 shadow-2xl">
                  <video
                    className="w-full h-full object-cover object-[45%_50%] scale-150"
                    autoPlay
                    muted
                    loop
                    playsInline
                    src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
                  />
                  <div className="absolute top-2 left-2 right-2 flex justify-between items-center text-[10px] text-white font-mono bg-black/50 backdrop-blur px-2 py-0.5 rounded">
                    <span className="flex items-center gap-1 text-emerald-400">
                      <Sparkles className="w-3 h-3" /> Centered Target #02
                    </span>
                    <span>1080×1920 (9:16)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {mode === 'reframe' && (
            <div className="relative w-full h-full flex items-center justify-center py-2">
              <div className="relative h-full aspect-[9/16] rounded-xl overflow-hidden border-2 border-white/40 shadow-2xl">
                <video
                  className="w-full h-full object-cover object-[48%_45%] scale-150"
                  autoPlay
                  muted
                  loop
                  playsInline
                  src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
                />
                <div className="absolute bottom-3 inset-x-3 vantage-glass rounded-lg p-2.5 text-center">
                  <p className="text-xs text-white font-medium">Kinetic Motion Smoothing Active</p>
                  <p className="text-[10px] text-white/60">Target remains strictly centered without jerkiness</p>
                </div>
              </div>
            </div>
          )}

          {mode === 'raw' && (
            <div className="relative w-full h-full">
              <video
                className="w-full h-full object-cover"
                autoPlay
                muted
                loop
                playsInline
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
              />
              <div className="absolute inset-0 bg-black/20 pointer-events-none" />
              <div className="absolute top-[28%] left-[34%] w-[22%] h-[52%] border-2 border-emerald-400 bg-emerald-400/20 rounded">
                <span className="absolute -top-6 left-0 bg-emerald-500 text-black text-xs font-bold px-1.5 py-0.5 rounded">
                  Selected Target #02
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Action Bottom */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-white/10">
          <div className="flex items-center gap-4 text-xs text-white/70">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Multi-Person Re-ID
            </span>
            <span className="flex items-center gap-1.5">
              <Smartphone className="w-4 h-4 text-emerald-400" /> Export 9:16 Reels Ready
            </span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-initial px-4 py-2 rounded-lg border border-white/20 text-white/80 hover:text-white text-xs font-medium"
            >
              Close
            </button>
            <button
              onClick={() => {
                onClose();
                navigate('/upload');
              }}
              className="flex-1 sm:flex-initial px-5 py-2.5 rounded-lg bg-white text-black hover:bg-neutral-200 text-xs font-semibold shadow-lg transition-transform hover:scale-105"
            >
              Try With Your Video
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};