import React from 'react';
import { Link } from 'react-router-dom';
import { Camera, Shield, Cpu, Sparkles } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="relative z-30 border-t border-white/10 bg-black/90 backdrop-blur-md text-white/80 py-12 px-6 sm:px-10 lg:px-16 mt-auto">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
        {/* Brand Col */}
        <div className="space-y-3 md:col-span-1">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center">
              <Camera className="w-3.5 h-3.5 text-black" />
            </div>
            <span className="font-display font-semibold text-white tracking-tight text-lg">FanCam</span>
          </div>
          <p className="text-xs text-white/60 leading-relaxed">
            Turn crowded group footage into professional solo highlight reels optimized for TikTok, Reels, and Shorts.
          </p>
        </div>

        {/* Pipeline Specs */}
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider text-white font-mono font-medium">Architecture</h4>
          <ul className="text-xs space-y-1.5 text-white/60">
            <li className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-white/80" /> YOLO-v8x Person Detection
            </li>
            <li className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-white/80" /> ByteTrack / DeepSORT Persistent Re-ID
            </li>
            <li className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-white/80" /> Kalman Filter Framing & FFmpeg
            </li>
          </ul>
        </div>

        {/* Quick Nav */}
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider text-white font-mono font-medium">Platform</h4>
          <div className="flex flex-col space-y-1.5 text-xs text-white/60">
            <Link to="/" className="hover:text-white transition-colors">Home Landing</Link>
            <Link to="/upload" className="hover:text-white transition-colors">Upload Workspace</Link>
            <Link to="/about" className="hover:text-white transition-colors">Technology & FAQ</Link>
            <Link to="/contact" className="hover:text-white transition-colors">Report Tracking Issue</Link>
          </div>
        </div>

        {/* Formats & Compliance */}
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider text-white font-mono font-medium">Supported Formats</h4>
          <div className="flex flex-wrap gap-1.5 text-[11px] font-mono text-white/70">
            <span className="px-2 py-0.5 rounded border border-white/10 bg-white/5">MP4</span>
            <span className="px-2 py-0.5 rounded border border-white/10 bg-white/5">MOV</span>

          </div>

        </div>
      </div>

      <div className="max-w-7xl mx-auto pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between text-xs text-white/50 gap-4">
        <p>© 2026 FanCam Engine. All rights reserved.</p>
        <div className="flex items-center gap-6">
          <span className="hover:text-white/80 cursor-pointer">Privacy Policy</span>
          <span className="hover:text-white/80 cursor-pointer">Terms of Service</span>

        </div>
      </div>
    </footer>
  );
};