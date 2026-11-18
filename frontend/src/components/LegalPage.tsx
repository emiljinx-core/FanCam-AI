import React from 'react';
import { FileText } from 'lucide-react';
import { Header } from './Header';
import { BackgroundVideo } from './BackgroundVideo';
import { Footer } from './Footer';

export interface LegalSection {
  heading: string;
  paragraphs: string[];
}

interface LegalPageProps {
  eyebrow: string;
  title: string;
  intro: string;
  sections: LegalSection[];
  lastUpdated: string;
}

export const LegalPage: React.FC<LegalPageProps> = ({
  eyebrow,
  title,
  intro,
  sections,
  lastUpdated,
}) => {
  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-12 max-w-3xl mx-auto w-full">
        <div className="space-y-4 mb-10 text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/20 bg-white/5 font-mono text-xs text-white/90">
            <FileText className="w-3.5 h-3.5 text-emerald-400" />
            <span>{eyebrow}</span>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tight text-white">
            {title}
          </h1>
          <p className="text-sm sm:text-base text-white/70 leading-relaxed">{intro}</p>
        </div>

        <div className="space-y-4">
          {sections.map((section, index) => (
            <section key={index} className="vantage-glass rounded-2xl p-6 sm:p-7 space-y-3">
              <h2 className="font-display text-lg font-medium text-white">{section.heading}</h2>
              {section.paragraphs.map((paragraph, paragraphIndex) => (
                <p key={paragraphIndex} className="text-sm text-white/70 leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </section>
          ))}
        </div>

        <p className="mt-8 text-xs text-white/50 font-mono">Last updated: {lastUpdated}</p>
      </main>

      <Footer />
    </div>
  );
};

export default LegalPage;
