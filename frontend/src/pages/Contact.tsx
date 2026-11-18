import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { Header } from '../components/Header';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { Footer } from '../components/Footer';
import { Mail, MessageSquare, Send, CheckCircle2, AlertTriangle, Bug } from 'lucide-react';

export const Contact: React.FC = () => {
  const [form, setForm] = useState({
    name: '',
    email: '',
    category: 'tracking-bug',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.message) {
      toast.warning('Please provide your email address and message.');
      return;
    }

    setSubmitted(true);
    toast.success('Your feedback has been received. Our team will review the tracking pipeline.');
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden text-white bg-black">
      <BackgroundVideo dimmed />
      <Header />

      <main className="relative z-20 flex-1 px-6 sm:px-10 lg:px-16 py-12 max-w-3xl mx-auto w-full">
        <div className="text-left space-y-3 mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/20 bg-white/5 font-mono text-xs text-white/90">
            <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
            <span>Support & Model Feedback</span>
          </div>

          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-white">
            Report an Issue or Contact Team
          </h1>

          <p className="text-sm sm:text-base text-white/70">
            Have questions about tracking accuracy, occlusions, or camera smoothing? Submit your note below.
          </p>
        </div>

        {submitted ? (
          <div className="vantage-glass rounded-2xl p-8 text-center space-y-4 border border-emerald-400/40">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="font-display text-xl text-white">Thank You for Your Feedback</h3>
            <p className="text-sm text-white/70 max-w-md mx-auto">
              We constantly re-train our Re-ID models with challenging edge cases to guarantee seamless target following.
            </p>
            <button
              onClick={() => {
                setSubmitted(false);
                setForm({ name: '', email: '', category: 'tracking-bug', message: '' });
              }}
              className="px-5 py-2.5 rounded-lg bg-white text-black text-xs font-semibold hover:bg-neutral-200"
            >
              Send Another Note
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="vantage-glass rounded-2xl p-6 sm:p-8 space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5 text-left">
                <label className="text-xs font-mono text-white/80 uppercase">Name (Optional)</label>
                <input
                  type="text"
                  placeholder="Your Name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-white/5 border border-white/15 text-white placeholder-white/30 text-sm focus:border-white focus:outline-none"
                />
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-xs font-mono text-white/80 uppercase">Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="creator@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-white/5 border border-white/15 text-white placeholder-white/30 text-sm focus:border-white focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <label className="text-xs font-mono text-white/80 uppercase">Inquiry Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-lg bg-neutral-900 border border-white/15 text-white text-sm focus:border-white focus:outline-none"
              >
                <option value="tracking-bug">Tracking Lost Subject / Occlusion Issue</option>
                <option value="file-size">Video Upload / 100 MB Limit Question</option>
                <option value="feature-request">Feature Request (e.g. Multi-Track Highlight)</option>
                <option value="general">General Support</option>
              </select>
            </div>

            <div className="space-y-1.5 text-left">
              <label className="text-xs font-mono text-white/80 uppercase">Message & Video Context *</label>
              <textarea
                required
                rows={5}
                placeholder="Describe your video format, crowd density, or any tracking jumpiness you experienced..."
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-lg bg-white/5 border border-white/15 text-white placeholder-white/30 text-sm focus:border-white focus:outline-none"
              />
            </div>

            <button
              type="submit"
              className="w-full py-3 rounded-lg bg-white text-black font-semibold text-sm hover:bg-neutral-200 transition-all flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span>Submit Report</span>
            </button>
          </form>
        )}
      </main>

      <Footer />
    </div>
  );
};

export default Contact;