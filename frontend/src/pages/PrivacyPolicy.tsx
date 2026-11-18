import React from 'react';
import { LegalPage, type LegalSection } from '../components/LegalPage';

const sections: LegalSection[] = [
  {
    heading: 'Information we collect',
    paragraphs: [
      'When you use FanCam, we receive the video files you upload (MP4 or MOV, up to 100 MB) and basic metadata such as width, height, frame rate, frame count, and duration.',
      'During processing we generate derived data including extracted frames, person bounding boxes, appearance embeddings used for identity matching, preview images, and the finished reframed video.',
      'If you use the contact form, we receive the name, email address, subject, and message you choose to submit. You are not required to provide a name.',
    ],
  },
  {
    heading: 'How we use your information',
    paragraphs: [
      'Uploaded videos and derived data are used only to detect, track, reframe, render, and deliver your video. Contact form details are used only to respond to your message.',
      'We do not sell your data, show ads, or use your uploads to train models. We do not require accounts and we do not process payments.',
    ],
  },
  {
    heading: 'Third-party services',
    paragraphs: [
      'Contact form messages are delivered through Resend, our email provider. The sample clips and thumbnails on the upload page are loaded from this project’s public GitHub repository.',
      'Video analysis and rendering run on our own backend using OpenCV, YOLOv8, OSNet, and FFmpeg. We do not send your videos to a third-party vision API.',
      'Our hosting provider serves the application and stores the backend files. Basic server logs may contain IP addresses and request metadata.',
    ],
  },
  {
    heading: 'Storage and retention',
    paragraphs: [
      'Uploaded videos, preview frames, embeddings, and rendered outputs are stored on the server so we can complete your request and let you download the result. These files are not automatically deleted after processing.',
      'Contact form submissions are delivered by email and are not written to a database by the application. If you would like uploaded files removed, please use the contact page to request deletion.',
    ],
  },
  {
    heading: 'Cookies and analytics',
    paragraphs: [
      'FanCam does not use accounts, advertising cookies, or third-party analytics trackers. Your browser only stores what is needed for the site to function.',
    ],
  },
  {
    heading: 'Your choices',
    paragraphs: [
      'Only upload footage you are comfortable sharing with our processing server, and avoid uploading sensitive personal material. You can request access to or deletion of your stored files through the contact page.',
    ],
  },
  {
    heading: 'Changes to this policy',
    paragraphs: [
      'We may update this policy as the service evolves. The current version is always available at this page with its last-updated date.',
    ],
  },
];

export const PrivacyPolicy: React.FC = () => (
  <LegalPage
    eyebrow="Legal"
    title="Privacy Policy"
    intro="A plain-language explanation of what FanCam collects, why it collects it, and what you can do about it."
    sections={sections}
    lastUpdated="18 November 2026"
  />
);

export default PrivacyPolicy;
