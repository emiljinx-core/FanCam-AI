import React, { useState } from 'react';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import { Cpu, ShieldCheck, Camera, Layers, ChevronDown, Zap } from 'lucide-react';

export const About: React.FC = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const faqs = [
    {
      q: 'How does FanCam stay locked onto the right person in a crowd?',
      a: 'Your selected subject gets an immutable OSNet appearance signature. Detected people are compared against it by cosine similarity, with a drift guard and ByteTrack/DeepSORT identity continuity, so crossings, occlusions, and late entry do not cause a target switch.'
    },
    {
      q: 'Which tracker should I choose — ByteTrack or DeepSORT?',
      a: 'ByteTrack is the faster option for crowded scenes and motion blur, associating both high- and low-confidence detections. DeepSORT is better when people overlap heavily: it combines appearance cascade matching with Kalman motion gating to keep IDs stable through occlusion.'
    },
    {
      q: 'Why is the camera motion smooth instead of jittery?',
      a: 'A 2D Kalman filter predicts where the subject is heading next, so the crop window moves ahead of them rather than reacting late. Dynamic zoom and strict boundary clamping keep the subject framed without stretching the video or clipping the edges.'
    },
    {
      q: "Will my video's audio stay in sync?",
      a: 'Yes. FFmpeg muxes the original audio track with stream copy when possible, falling back to high-bitrate AAC when needed. Source FPS, frame count, and duration are preserved, so lipsync stays intact.'
    },
    {
      q: 'How do I know when processing is finished?',
      a: 'Processing runs as a background task. The app submits POST /api/process and polls GET /api/status, moving from queued to processing to completed, with the download link appearing automatically.'
    }
  ];

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-12 max-w-5xl mx-auto w-full">
        {/* Intro */}
        <div className="space-y-4 mb-16 text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/20 bg-white/5 font-mono text-xs text-white/90">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>AI Architecture & Pipeline</span>
          </div>

          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tight text-white">
            Transforming Group Chaos into Solo FanCams
          </h1>

          <p className="text-base sm:text-lg text-white/70 max-w-3xl leading-relaxed">
            Content creators spend hours manually setting keyframes to follow a single dancer, player, or friend in crowded footage. FanCam automates this entire pipeline using computer vision.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-20">
          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Cpu className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Smart Person Detection</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              YOLOv8 scans Frame 0 and any scrubbed frame, tagging every detected person with normalized bounding boxes and confidence scores for one-click target selection.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">OSNet Identity Lock</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              An immutable 512-dimensional appearance signature locks onto your subject. Cosine-similarity matching re-identifies them after occlusions or late entry, preventing identity swaps.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Camera className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Predictive Cinematic Framing</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              A 2D Kalman filter predicts position and velocity so the camera leads the subject instead of chasing it. Dynamic zoom and strict boundary clamping keep every pan smooth.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Layers className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Dual Tracking Engines</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              ByteTrack rapidly associates high- and low-confidence detections to hold tracks through motion blur in crowded scenes. DeepSORT adds appearance cascade matching and Kalman motion gating for heavy occlusion.
            </p>
          </div>
        </div>

        {/* FAQs */}
        <div className="mb-16">
          <h2 className="font-display text-2xl sm:text-3xl font-semibold text-white mb-6">
            Frequently Asked Questions
          </h2>

          <div className="space-y-3">
            {faqs.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div
                  key={idx}
                  className="vantage-glass rounded-xl overflow-hidden transition-colors"
                >
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    className="w-full p-5 text-left flex items-center justify-between gap-4 text-sm sm:text-base font-medium text-white focus:outline-none"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      className={`w-5 h-5 text-white/60 transition-transform duration-200 shrink-0 ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                  {isOpen && (
                    <div className="px-5 pb-5 pt-1 text-sm text-white/70 border-t border-white/10 leading-relaxed">
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default About;