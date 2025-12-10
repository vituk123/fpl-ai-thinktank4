// Format player name
export const formatPlayerName = (firstName, lastName) => {
  if (!firstName && !lastName) return 'Unknown Player';
  return `${firstName || ''} ${lastName || ''}`.trim();
};

// Format price
export const formatPrice = (price) => {
  if (typeof price === 'number') {
    return `£${(price / 10).toFixed(1)}m`;
  }
  return price;
};

// Format points
export const formatPoints = (points) => {
  if (typeof points === 'number') {
    return points.toFixed(1);
  }
  return points;
};

// Format date
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateString;
  }
};

// Format datetime
export const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
};

// Format time
export const formatTime = (date) => {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  return d.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
  });
};

// Format gameweek
export const formatGameweek = (gw) => {
  return `GW${gw}`;
};

// Format percentage
export const formatPercentage = (value, decimals = 1) => {
  if (typeof value !== 'number') return 'N/A';
  return `${value.toFixed(decimals)}%`;
};

// Format large numbers
export const formatNumber = (num) => {
  if (typeof num !== 'number') return num;
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

// Truncate text
export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
};

// Format team name
export const formatTeamName = (teamName) => {
  if (!teamName) return 'Unknown';
  return teamName;
};

// Format position
export const formatPosition = (position) => {
  const positions = {
    1: 'GK',
    2: 'DEF',
    3: 'MID',
    4: 'FWD',
  };
  return positions[position] || 'UNK';
};

export default {
  formatPlayerName,
  formatPrice,
  formatPoints,
  formatDate,
  formatDateTime,
  formatTime,
  formatGameweek,
  formatPercentage,
  formatNumber,
  truncateText,
  formatTeamName,
  formatPosition,
};

