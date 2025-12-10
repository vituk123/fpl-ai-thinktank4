import React, { useState, useEffect } from 'react';
import { dashboardApi } from '../../services/api';

const GameweekCountdown: React.FC = () => {
  const [countdown, setCountdown] = useState<string>('Loading...');
  const [gameweek, setGameweek] = useState<number | null>(null);

  useEffect(() => {
    const fetchDeadline = async () => {
      try {
        const data = await dashboardApi.getCurrentGameweek();
        
        if (!data || !data.deadline_time) {
          throw new Error('No deadline data available');
        }

        setGameweek(data.gameweek);
        const deadlineDate = new Date(data.deadline_time);
        
        // Check if date is valid
        if (isNaN(deadlineDate.getTime())) {
          throw new Error('Invalid deadline date');
        }
        
        // Format date: "Sat, Dec 13th"
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        const dayName = dayNames[deadlineDate.getDay()];
        const month = monthNames[deadlineDate.getMonth()];
        const day = deadlineDate.getDate();
        const daySuffix = day === 1 || day === 21 || day === 31 ? 'st' : 
                         day === 2 || day === 22 ? 'nd' : 
                         day === 3 || day === 23 ? 'rd' : 'th';
        
        // Format time: "15:30"
        const hours = deadlineDate.getHours().toString().padStart(2, '0');
        const minutes = deadlineDate.getMinutes().toString().padStart(2, '0');
        const timeStr = `${hours}:${minutes}`;
        
        // Calculate days remaining
        const now = new Date();
        const diffTime = deadlineDate.getTime() - now.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        let daysText = '';
        if (diffDays < 0) {
          daysText = 'Deadline passed';
        } else if (diffDays === 0) {
          const diffHours = Math.ceil(diffTime / (1000 * 60 * 60));
          if (diffHours <= 0) {
            daysText = 'Deadline passed';
          } else {
            daysText = `in ${diffHours} ${diffHours === 1 ? 'Hour' : 'Hours'}`;
          }
        } else if (diffDays === 1) {
          daysText = 'in 1 Day';
        } else {
          daysText = `in ${diffDays} Day${diffDays > 1 ? 's' : ''}`;
        }
        
        setCountdown(`GW ${data.gameweek} Deadline: ${dayName}, ${month} ${day}${daySuffix} ${timeStr} (${daysText})`);
      } catch (error) {
        console.error('Error fetching deadline:', error);
        setCountdown('Loading deadline...');
      }
    };

    fetchDeadline();
    // Update every minute
    const interval = setInterval(fetchDeadline, 60000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed top-8 left-0 right-0 h-[18px] bg-retro-background border-b-retro border-retro-primary z-40 flex items-center justify-center px-3">
      <p className="text-[8px] font-bold font-mono text-retro-primary">
        {countdown}
      </p>
    </div>
  );
};

export default GameweekCountdown;

