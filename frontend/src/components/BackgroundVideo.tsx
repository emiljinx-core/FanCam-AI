import React from 'react';

interface BackgroundVideoProps {
  dimmed?: boolean;
}

const videoUrl =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4';

export const BackgroundVideo: React.FC<BackgroundVideoProps> = ({ dimmed = false }) => {
  return (
    <div
      className={`fixed inset-0 z-0 overflow-hidden pointer-events-none select-none bg-black ${
        dimmed ? 'other-page-background' : ''
      }`}
      aria-hidden="true"
    >
      <video
        className="background-video h-full w-full object-cover object-center"
        autoPlay
        muted
        loop
        playsInline
        disablePictureInPicture
        aria-hidden="true"
      >
        <source src={videoUrl} type="video/mp4" />
      </video>
      <div className="screen-vignette absolute inset-0" />
    </div>
  );
};