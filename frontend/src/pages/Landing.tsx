import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { entryApi } from '../services/api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Tooltip from '../components/common/Tooltip';

const Landing: React.FC = () => {
  const [inputId, setInputId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setEntryId, setEntryInfo } = useAppContext();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputId) return;

    setLoading(true);
    setError('');

    try {
      const id = parseInt(inputId, 10);
      if (isNaN(id)) throw new Error("Invalid ID");

      const data = await entryApi.getEntry(id);
      setEntryId(id);
      setEntryInfo(data);
      navigate('/dashboard');
    } catch (err: any) {
      const errorMessage = err?.message || 'Could not validate Entry ID. Please try again.';
      setError(errorMessage);
      console.error('Entry validation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-16 pb-24 px-4 flex flex-col items-center justify-center relative overflow-hidden">
        {/* Decorative Background Elements */}
        <div className="absolute top-20 left-10 w-32 h-32 border-retro border-retro-primary opacity-20 transform rotate-12 bg-white"></div>
        <div className="absolute bottom-20 right-10 w-48 h-48 border-retro border-retro-primary opacity-20 transform -rotate-6 bg-retro-secondary"></div>

      <DesktopWindow title="System Access" className="w-full max-w-md z-10">
        <div className="p-6 flex flex-col items-center">
            <div className="mb-6 border-retro border-retro-primary p-4 bg-retro-background w-full text-center">
                <img src="/logo2.png" alt="FPL OPTIMIZER" className="mx-auto mb-3 h-16 object-contain" />
                <h1 className="text-2xl font-black uppercase mb-2">FPL OPTIMIZER</h1>
                <p className="text-sm font-medium">Production Build v1.0</p>
            </div>
          
          <p className="mb-6 text-center text-sm">
            Enter your Fantasy Premier League Entry ID to access analytics and AI recommendations.
          </p>

          <form onSubmit={handleSubmit} className="w-full space-y-4">
            <div>
              <label htmlFor="entryId" className="block text-xs font-bold uppercase mb-1">
                <Tooltip text="Your FPL Entry ID is found in your team URL: https://fantasy.premierleague.com/entry/YOUR_ENTRY_ID/event/X. You can also find it in your browser's address bar when viewing your team page. It's a 6-7 digit number unique to your FPL team.">
                  Entry ID
                </Tooltip>
              </label>
              <input
                id="entryId"
                type="text"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                className="w-full p-3 border-retro border-retro-primary bg-white focus:outline-none focus:ring-2 focus:ring-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] font-mono text-lg"
                placeholder="e.g. 123456"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-retro-error text-white p-2 text-xs font-bold border-2 border-black">
                ERROR: {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-retro-primary text-white font-bold py-3 border-retro border-black shadow-retro hover:shadow-retro-hover active:shadow-retro-active active:translate-x-1 active:translate-y-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider"
            >
              {loading ? 'Authenticating...' : 'Connect'}
            </button>
          </form>
          
          <div className="mt-8 text-xs text-center opacity-60">
             <p>Supports FPL 2024/25 Season</p>
             <p className="mt-1 font-mono">RENDER_API: ONLINE</p>
          </div>
        </div>
      </DesktopWindow>
      
       {/* Fake Loading Overlay if loading */}
       {loading && (
           <div className="absolute inset-0 bg-[#DADAD3] z-50 flex items-center justify-center">
               <LoadingSpinner text="Connecting to Mainframe..." />
           </div>
       )}
    </div>
  );
};

export default Landing;