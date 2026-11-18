import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { UploadCloud, Menu, X, HardDrive } from 'lucide-react';

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="header relative z-50 w-full px-6 sm:px-10 lg:px-16 pt-5 pb-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between h-12">
        <Link
          to="/"
          className="brand flex items-center gap-3.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white rounded-lg p-1"
          aria-label="FanCam Home"
        >
          <div className="w-[28px] h-[28px] rounded-full bg-[#ededed] relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.5)] flex items-center justify-center transition-transform duration-300 group-hover:scale-105">
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" aria-hidden="true">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#050606" />
              <path d="M2 17L12 22L22 17" stroke="#737778" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M2 12L12 17L22 12" stroke="#0a0b0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-display font-semibold text-lg tracking-tight text-white flex items-center gap-1.5">
              FanCam
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border border-white/20 bg-white/5 text-white/80">
                AI 2.4
              </span>
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8 lg:gap-10" aria-label="Main navigation">
          <Link
            to="/"
            className={`text-[15px] font-[430] tracking-[-0.36px] transition-colors relative py-1 ${
              isActive('/') ? 'text-white' : 'text-[#e5e5e6]/75 hover:text-white'
            }`}
          >
            Home
            {isActive('/') && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/85 rounded-full" />}
          </Link>
          <Link
            to="/about"
            className={`text-[15px] font-[430] tracking-[-0.36px] transition-colors relative py-1 ${
              isActive('/about') ? 'text-white' : 'text-[#e5e5e6]/75 hover:text-white'
            }`}
          >
            About
            {isActive('/about') && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/85 rounded-full" />}
          </Link>
          <Link
            to="/contact"
            className={`text-[15px] font-[430] tracking-[-0.36px] transition-colors relative py-1 ${
              isActive('/contact') ? 'text-white' : 'text-[#e5e5e6]/75 hover:text-white'
            }`}
          >
            Contact
            {isActive('/contact') && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/85 rounded-full" />}
          </Link>
        </nav>

        <div className="hidden sm:flex items-center gap-5">
          <div className="flex items-center gap-2 pl-3 py-1.5 border-l-2 border-white/25">
            <HardDrive className="w-4 h-4 text-white/60" aria-hidden="true" />
            <div className="flex flex-col text-left leading-tight">
              <span className="text-[11px] font-[420] text-white/60 uppercase tracking-wider">Constraint</span>
              <span className="text-[13px] font-[460] text-white/95">Max File Size: 100 MB</span>
            </div>
          </div>

          <button
            onClick={() => navigate('/upload')}
            className="sign-up flex items-center gap-2 px-4 py-2 h-[40px] rounded-[7px] bg-white text-[#101010] text-[14px] font-[480] tracking-[-0.3px] shadow-pill hover:bg-white/95 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <UploadCloud className="w-4 h-4 text-black" aria-hidden="true" />
            <span>Upload Video</span>
          </button>
        </div>

        <div className="flex sm:hidden items-center gap-2">
          <button
            onClick={() => navigate('/upload')}
            className="px-3 py-1.5 rounded-[7px] bg-white text-black text-xs font-semibold"
          >
            Upload
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="menu-toggle w-10 h-10 rounded-[10px] vantage-glass flex items-center justify-center text-white"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="sm:hidden mt-3 vantage-glass rounded-2xl p-5 flex flex-col gap-4 animate-in fade-in slide-in-from-top-3 duration-200">
          <div className="flex items-center justify-between py-2 border-b border-white/10">
            <span className="text-xs text-white/60 uppercase tracking-wider">File Limit</span>
            <span className="text-xs font-mono font-medium text-emerald-400">Strict &lt; 100 MB</span>
          </div>
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className={`text-base font-medium ${isActive('/') ? 'text-white' : 'text-white/70'}`}
          >
            Home
          </Link>
          <Link
            to="/about"
            onClick={() => setMobileMenuOpen(false)}
            className={`text-base font-medium ${isActive('/about') ? 'text-white' : 'text-white/70'}`}
          >
            About
          </Link>
          <Link
            to="/contact"
            onClick={() => setMobileMenuOpen(false)}
            className={`text-base font-medium ${isActive('/contact') ? 'text-white' : 'text-white/70'}`}
          >
            Contact
          </Link>
          <button
            onClick={() => {
              setMobileMenuOpen(false);
              navigate('/upload');
            }}
            className="w-full py-2.5 rounded-lg bg-white text-black font-semibold text-sm flex items-center justify-center gap-2 mt-2"
          >
            <UploadCloud className="w-4 h-4" aria-hidden="true" />
            Upload Video
          </button>
        </div>
      )}
    </header>
  );
};