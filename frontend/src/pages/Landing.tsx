import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { entryApi } from '../services/api';
import { useAppContext } from '../context/AppContext';
import LoadingLogo from '../components/common/LoadingLogo';
import Tooltip from '../components/common/Tooltip';
import LetterGlitch from '../components/common/LetterGlitch';

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
    <div className="min-h-screen pt-16 pb-24 px-4 flex flex-col items-center justify-center relative overflow-visible">
        {/* LetterGlitch Background */}
        <LetterGlitch
          glitchSpeed={50}
          centerVignette={true}
          outerVignette={false}
          smooth={true}
          glitchColors={['#000000', '#808080', '#000000', '#FF0000']}
        />

      <DesktopWindow title="System Access" className="w-full max-w-md md:max-w-md max-w-[90%] z-20 relative scale-90 md:scale-100">
        <div className="p-4 md:p-6 flex flex-col items-center">
            <div className="mb-4 md:mb-6 border-retro border-retro-primary p-3 md:p-4 bg-retro-background w-full text-center">
                <img src="/logo3.png" alt="FPL OPTIMIZER" className="mx-auto mb-2 md:mb-3 h-64 md:h-96 object-contain" />
            </div>
          
          <p className="mb-4 md:mb-6 text-center text-xs md:text-sm px-2">
            Enter your Fantasy Premier League Entry ID to access analytics and AI recommendations.
          </p>

          <form onSubmit={handleSubmit} className="w-full space-y-3 md:space-y-4">
            <div>
              <label htmlFor="entryId" className="block text-[10px] md:text-xs font-bold uppercase mb-1">
                <Tooltip text="Your FPL Entry ID is found in your team URL: https://fantasy.premierleague.com/entry/YOUR_ENTRY_ID/event/X. You can also find it in your browser's address bar when viewing your team page. It's a 6-7 digit number unique to your FPL team.">
                  Entry ID
                </Tooltip>
              </label>
              <input
                id="entryId"
                type="text"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                className="w-full p-2 md:p-3 border-retro border-retro-primary bg-white focus:outline-none focus:ring-2 focus:ring-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] font-mono text-base md:text-lg"
                placeholder="e.g. 123456"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-retro-error text-white p-2 text-[10px] md:text-xs font-bold border-2 border-black">
                ERROR: {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-retro-primary text-white font-bold py-2 md:py-3 border-retro border-black shadow-retro hover:shadow-retro-hover active:shadow-retro-active active:translate-x-1 active:translate-y-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-sm md:text-base"
            >
              {loading ? 'Authenticating...' : 'Connect'}
            </button>
          </form>
          
          <div className="mt-6 md:mt-8 text-[10px] md:text-xs text-center opacity-60">
             <p>Made by Vitu K</p>
          </div>
        </div>
      </DesktopWindow>
      
       {/* Loading Overlay if loading */}
       {loading && (
           <div className="absolute inset-0 bg-white z-50 flex items-center justify-center">
               <LoadingLogo phases={[
                 { message: "Validating Entry ID...", duration: 1000 },
                 { message: "Connecting to Mainframe...", duration: 1500 },
                 { message: "Authenticating...", duration: 1000 },
               ]} />
           </div>
       )}
    </div>
  );
};

export default Landing;