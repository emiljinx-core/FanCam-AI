import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Play } from 'lucide-react';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { DemoModal } from '../components/DemoModal';
import { YouTubeDemoModal } from '../components/YouTubeDemoModal';

const DEMO_YOUTUBE_URL = 'https://youtu.be/UB3KRTeprBU';

const demoVideoUrl =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [demoOpen, setDemoOpen] = useState(false);
  const [youtubeDemoOpen, setYoutubeDemoOpen] = useState(false);
  const motionTimer = useRef<number | null>(null);

  const finishMotion = (event?: React.AnimationEvent<HTMLElement>) => {
    if (event && event.target !== event.currentTarget) return;
    if (motionTimer.current !== null) {
      window.clearTimeout(motionTimer.current);
      motionTimer.current = null;
    }
    document.querySelector('.home-shell')?.classList.remove('motion-pending');
  };

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      finishMotion();
      return;
    }

    motionTimer.current = window.setTimeout(() => finishMotion(), 3500);
    return () => {
      if (motionTimer.current !== null) {
        window.clearTimeout(motionTimer.current);
        motionTimer.current = null;
      }
    };
  }, []);

  return (
    <div className="home-shell motion-pending relative h-screen min-h-screen overflow-hidden text-white bg-black">
      <BackgroundVideo />

      <Header />

      <main className="relative z-20 flex h-[calc(100vh-4rem)] flex-col justify-end px-6 sm:px-10 lg:px-16 pt-8 pb-12 sm:pb-16 max-w-[1600px] mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-end w-full">
          <div className="lg:col-span-8 flex flex-col items-start space-y-6 sm:space-y-8">
            <h1 className="hero-title font-display font-[500] text-4xl sm:text-6xl md:text-7xl lg:text-[82px] leading-[0.98] tracking-[-2.1px] text-left select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]">
              <span className="line line-one block text-white origin-left transform sm:scale-x-[0.92]">
                <span className="line-reveal">My FanCam</span>
              </span>
              <span className="line line-two block text-[#d3cfcf]/90 origin-left transform sm:scale-x-[0.94] mt-1 sm:mt-2">
                <span className="line-reveal">Favorites in Focus</span>
              </span>
            </h1>

            <p className="hero-copy text-[#e2e5e4]/90 text-sm sm:text-base md:text-lg font-[350] tracking-[0.13px] leading-relaxed max-w-xl text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.7)]">
              Choose people for personalized edits.<br className="hidden sm:inline" />
              AI automatically tracks selected subjects across frames.<br className="hidden sm:inline" />
              Inspired by fan cam trends, bringing favorite people into focus.
            </p>

            <div className="home-cta-wrap pt-2">
              <button
                onClick={() => navigate('/upload')}
                className="primary-cta group relative flex items-center justify-between w-[168px] sm:w-[180px] h-[44px] sm:h-[48px] rounded-[7px] bg-white text-[#111111] px-4 font-[460] tracking-[-0.3px] text-[15px] sm:text-[16px] shadow-[0_1px_5px_rgba(0,0,0,0.38)] hover:bg-[#fafafa] hover:scale-105 active:scale-95 transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
              >
                <span className="font-medium">Get Started</span>
                <span className="w-8 h-8 rounded-[6px] bg-[#070909] text-white flex items-center justify-center transition-transform group-hover:translate-x-0.5">
                  <ArrowRight className="w-4 h-4 text-white" aria-hidden="true" />
                </span>
              </button>
            </div>
          </div>

          <div className="lg:col-span-4 flex justify-start lg:justify-end w-full">
            <article
              className="home-demo-card vantage-glass rounded-[16px] p-3.5 sm:p-4 w-full max-w-[240px] sm:max-w-[260px] aspect-[201/265] flex flex-col justify-between hover:-translate-y-1 transition-all duration-300"
              onAnimationEnd={finishMotion}
            >
              <div className="relative w-full aspect-square rounded-[10px] overflow-hidden bg-[#101a1e] flex items-center justify-center border border-white/10 group">
                <video
                  src={demoVideoUrl}
                  className="w-full h-full object-cover brightness-[0.88] saturate-[0.95] contrast-[1.04] transition-transform duration-500 group-hover:scale-105"
                  autoPlay
                  muted
                  loop
                  playsInline
                  disablePictureInPicture
                  aria-label="Crowd footage with a tracked target"
                />

                <div className="absolute top-[20%] left-[30%] w-[40%] h-[60%] border-2 border-white rounded bg-white/10 pointer-events-none">
                  <span className="absolute -top-6 left-0 whitespace-nowrap rounded bg-white px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-black shadow-md">
                    Person #01 · Target
                  </span>
                </div>

                <div className="absolute bottom-2 left-2 rounded bg-black/70 px-2 py-1 font-mono text-[9px] text-white/90 backdrop-blur">
                  Frame 0:00 · Click subject to lock
                </div>

                <button
                  onClick={() => setDemoOpen(true)}
                  className="absolute w-12 h-12 rounded-full border border-white/40 bg-[#030507]/60 backdrop-blur-md flex items-center justify-center text-white hover:scale-110 active:scale-95 transition-transform shadow-lg cursor-pointer z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
                  aria-label="Play demo"
                >
                  <Play className="w-5 h-5 fill-white text-white ml-0.5" aria-hidden="true" />
                </button>
              </div>

              <button
                onClick={() => setYoutubeDemoOpen(true)}
                className="w-full py-2.5 rounded-[9px] vantage-glass-button text-white text-[13px] sm:text-[14px] font-[440] hover:brightness-110 transition-all flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-4"
              >
                <Play className="w-3.5 h-3.5 fill-white text-white" aria-hidden="true" />
                <span>Watch Demo</span>
              </button>
            </article>
          </div>
        </div>
      </main>

      <DemoModal isOpen={demoOpen} onClose={() => setDemoOpen(false)} />
      <YouTubeDemoModal
        isOpen={youtubeDemoOpen}
        onClose={() => setYoutubeDemoOpen(false)}
        videoUrl={DEMO_YOUTUBE_URL}
      />
    </div>
  );
};

export default Home;