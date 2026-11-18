import React, { Suspense } from 'react';
import '@radix-ui/themes/styles.css';
import { Theme } from '@radix-ui/themes';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

const Home = React.lazy(() => import('./src/pages/Home'));
const Upload = React.lazy(() => import('./src/pages/Upload'));
const SelectTarget = React.lazy(() => import('./src/pages/SelectTarget'));
const Result = React.lazy(() => import('./src/pages/Result'));
const About = React.lazy(() => import('./src/pages/About'));
const Contact = React.lazy(() => import('./src/pages/Contact'));
const PrivacyPolicy = React.lazy(() => import('./src/pages/PrivacyPolicy'));
const TermsOfService = React.lazy(() => import('./src/pages/TermsOfService'));
const NotFound = React.lazy(() => import('./src/pages/NotFound'));

const App: React.FC = () => {
  return (
    <Theme appearance="dark" radius="medium">
      <Router>
        <div className="min-h-screen bg-black font-sans text-white">
          <Suspense
            fallback={
              <div className="min-h-screen bg-black flex items-center justify-center text-white font-mono text-xs">
                <span className="animate-pulse">Loading FanCam Engine...</span>
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/select-target" element={<SelectTarget />} />
              <Route path="/result" element={<Result />} />
              <Route path="/about" element={<About />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/terms" element={<TermsOfService />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>

          <ToastContainer
            position="top-right"
            autoClose={3200}
            theme="dark"
            newestOnTop
            closeOnClick
            pauseOnHover
          />
        </div>
      </Router>
    </Theme>
  );
};

export default App;