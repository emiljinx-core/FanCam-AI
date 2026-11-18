import React from 'react';
import { Link } from 'react-router-dom';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';

export const NotFound: React.FC = () => {
  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 flex flex-col items-center justify-center px-6 text-center py-20">
        <span className="font-mono text-xs text-white/60 uppercase tracking-widest px-3 py-1 rounded border border-white/20 mb-4">
          Error 404
        </span>
        <h1 className="font-display text-4xl sm:text-6xl font-bold text-white mb-3">
          Frame Not Found
        </h1>
        <p className="text-white/70 max-w-md text-sm mb-8">
          The requested path could not be located in our tracking pipeline. Return to the home dashboard to continue reframing.
        </p>
        <Link
          to="/"
          className="px-6 py-2.5 rounded-lg bg-white text-black font-medium text-sm hover:bg-neutral-200 transition-colors"
        >
          Return to Home
        </Link>
      </main>

      <Footer />
    </div>
  );
};

export default NotFound;