import React from 'react';
import { X } from 'lucide-react';

interface YouTubeDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Full/long YouTube watch URL, e.g. https://www.youtube.com/watch?v=VIDEO_ID */
  videoUrl: string;
}

/**
 * Converts a FULL/LONG YouTube watch URL into an embed URL.
 * Accepts only https://www.youtube.com/watch?v=VIDEO_ID (or youtube.com without www).
 * Raw IDs, youtu.be short links, /shorts/, /embed/ links, and other hosts are rejected.
 */
function toYouTubeEmbedUrl(videoUrl: string): string | null {
  try {
    const parsed = new URL(videoUrl.trim());
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return null;
    if (parsed.hostname !== 'www.youtube.com' && parsed.hostname !== 'youtube.com') return null;
    if (parsed.pathname !== '/watch') return null;

    const videoId = parsed.searchParams.get('v');
    if (!videoId || !/^[A-Za-z0-9_-]{11}$/.test(videoId)) return null;

    return `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`;
  } catch {
    return null;
  }
}

export const YouTubeDemoModal: React.FC<YouTubeDemoModalProps> = ({
  isOpen,
  onClose,
  videoUrl,
}) => {
  if (!isOpen) return null;

  const embedUrl = toYouTubeEmbedUrl(videoUrl);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label="FanCam video demo"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl vantage-glass rounded-2xl p-4 sm:p-6 shadow-2xl border border-white/20"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
          <div>
            <h3 className="text-lg sm:text-xl font-display font-medium text-white">FanCam Demo</h3>
            <p className="text-xs text-white/70 mt-0.5">See FanCam turn crowded footage into a focused highlight reel.</p>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            aria-label="Close demo"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black border border-white/15 flex items-center justify-center">
          {embedUrl ? (
            <iframe
              src={embedUrl}
              title="FanCam demo video"
              className="absolute inset-0 w-full h-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
            />
          ) : (
            <div className="px-4 text-center space-y-1">
              <p className="text-sm font-medium text-white">Demo video coming soon</p>
              <p className="text-xs text-white/60">
                A full YouTube link is required: https://www.youtube.com/watch?v=VIDEO_ID
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default YouTubeDemoModal;
