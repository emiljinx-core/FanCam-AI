import React, { useState } from 'react';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import { Cpu, Target, Camera, Layers, CheckCircle, ChevronDown, ShieldCheck, Zap } from 'lucide-react';

export const About: React.FC = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const faqs = [
    {
      q: 'What is the maximum supported video file size?',
      a: 'FanCam strictly enforces a maximum file size of 100 MB per video. This allows rapid client-side frame scrubbing and real-time backend inference without requiring user accounts or subscriptions.'
    },
    {
      q: 'Do I need to create an account or sign in to process videos?',
      a: 'No. FanCam is entirely frictionless. You can upload group footage, isolate your target subject, adjust smoothing, and download the finished 9:16 reel immediately without registration.'
    },
    {
      q: 'How does FanCam handle occlusions when people cross paths?',
      a: 'FanCam leverages persistent multi-object tracking (ByteTrack combined with visual Re-ID embeddings). Even if another person temporarily walks in front of your subject, the tracker preserves identity continuity without jumping targets.'
    },
    {
      q: 'Can I choose different output aspect ratios?',
      a: 'Yes. You can switch between 9:16 (vertical for TikTok, IG Reels, YouTube Shorts), 1:1 (square for Instagram feeds), and 16:9 (horizontal widescreen).'
    },
    {
      q: 'What video containers are supported?',
      a: 'We support all standard .mp4 and .mov files encoded with standard H.264, H.265, or ProRes video streams and AAC audio.'
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
              Scans video frames using high-accuracy YOLO models to identify, segment, and tag all visible individuals with confidence ratings.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Target className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Persistent Multi-Object Tracking</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              Maintains unbroken identity continuity for the selected person throughout the sequence, even during occlusions, turns, or background crossings.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Camera className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Cinematic Automated Framing</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              Applies continuous cubic smoothing filters to the dynamic crop window, replicating the fluid motion of a professional camera operator without mechanical jitter.
            </p>
          </div>

          <div className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center text-white">
              <Layers className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="font-display text-xl font-medium text-white">Flexible Aspect Ratios</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              Instantly formats the final output to match TikTok (9:16), Instagram (1:1), or YouTube Shorts without letterboxing or audio degradation.
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