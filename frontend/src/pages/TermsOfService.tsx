import React from 'react';
import { LegalPage, type LegalSection } from '../components/LegalPage';

const sections: LegalSection[] = [
  {
    heading: 'Acceptance of terms',
    paragraphs: [
      'By using FanCam, you agree to these terms. If you do not agree, please do not use the service.',
    ],
  },
  {
    heading: 'What FanCam provides',
    paragraphs: [
      'FanCam is a video reframing tool that detects and follows a selected person in group footage and produces a cropped highlight video. Results depend on footage quality, crowd density, lighting, and the selected output settings.',
      'The service is provided for convenience and experimentation. We do not guarantee a particular creative result for every video.',
    ],
  },
  {
    heading: 'Your content and rights',
    paragraphs: [
      'You keep ownership of the videos you upload. By uploading a file, you confirm that you have the right to process it and that it does not violate anyone else’s rights.',
      'You grant us a limited, non-exclusive permission to host and process your file only for the purpose of providing the service. Please consider the privacy of people appearing in footage before uploading it.',
    ],
  },
  {
    heading: 'Acceptable use',
    paragraphs: [
      'Do not use FanCam to upload illegal, harmful, or infringing material, to violate anyone’s privacy, or to interfere with the operation of the service.',
      'Do not attempt to bypass upload limits, overload the backend, or scrape or abuse the contact form.',
    ],
  },
  {
    heading: 'Technical limits',
    paragraphs: [
      'Uploads are limited to MP4 or MOV files under 100 MB. Processing time depends on video length, server load, and available hardware.',
      'Sample clips shown on the upload page are loaded from a public GitHub repository and are provided for demonstration purposes.',
    ],
  },
  {
    heading: 'Availability and warranty',
    paragraphs: [
      'FanCam is provided “as is” without warranties of any kind. We may change, suspend, or discontinue parts of the service at any time.',
    ],
  },
  {
    heading: 'Limitation of liability',
    paragraphs: [
      'To the extent permitted by law, FanCam is not liable for indirect damages, lost profits, or loss of content arising from use of the service. You are responsible for keeping copies of any videos you upload.',
    ],
  },
  {
    heading: 'Changes and contact',
    paragraphs: [
      'We may update these terms from time to time and will post the revised version here with a new last-updated date. Questions about these terms can be sent through the contact page.',
    ],
  },
];

export const TermsOfService: React.FC = () => (
  <LegalPage
    eyebrow="Legal"
    title="Terms of Service"
    intro="The basic rules for using FanCam, written to be readable rather than intimidating."
    sections={sections}
    lastUpdated="18 November 2026"
  />
);

export default TermsOfService;
