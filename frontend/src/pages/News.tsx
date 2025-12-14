import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { newsApi } from '../services/api';
import LoadingLogo from '../components/common/LoadingLogo';
import { ExternalLink } from 'lucide-react';

const News: React.FC = () => {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const data = await newsApi.getArticles();
        setArticles(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchNews();
  }, []);

  if (loading) {
    const newsPhases = [
      { message: "Connecting to news API...", duration: 1000 },
      { message: "Fetching articles...", duration: 2000 },
      { message: "Processing content...", duration: 1500 },
      { message: "Loading images...", duration: 1000 },
    ];
    return <LoadingLogo phases={newsPhases} />;
  }

  return (
    <div className="p-4 md:p-8 pb-24 h-screen overflow-hidden flex flex-col">
      <DesktopWindow title="FPL Wire Service" className="h-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((article, idx) => (
                <div key={idx} className="border-2 border-retro-primary bg-white shadow-[4px_4px_0_rgba(0,0,0,0.1)] flex flex-col">
                    {article.urlToImage && (
                        <div className="h-40 overflow-hidden border-b-2 border-retro-primary relative grayscale hover:grayscale-0 transition-all">
                            <img src={article.urlToImage} alt={article.title} className="w-full h-full object-cover" />
                             <div className="absolute inset-0 bg-retro-pattern opacity-30"></div>
                        </div>
                    )}
                    <div className="p-4 flex-1 flex flex-col">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-retro-textSec mb-1">
                            {article.source.name} • {new Date(article.publishedAt).toLocaleDateString()}
                        </div>
                        <h3 className="text-sm font-bold mb-2 line-clamp-2">{article.title}</h3>
                        <p className="text-xs mb-4 line-clamp-3 opacity-80 flex-1">{article.description}</p>
                        
                        <a 
                            href={article.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="mt-auto flex items-center justify-center space-x-2 bg-retro-primary text-white py-2 text-xs font-bold uppercase hover:bg-black transition-colors"
                        >
                            <span>Read Source</span>
                            <ExternalLink size={12} />
                        </a>
                    </div>
                </div>
            ))}
        </div>
      </DesktopWindow>
    </div>
  );
};

export default News;
