import React from 'react';
import { CardContent, Box, Typography, Alert } from '@mui/material';
import { dashboardApi } from '../../services/api';
import useApi from '../../hooks/useApi';
import AnimatedCard from '../AnimatedCard';
import MacSpinner from '../MacSpinner';
import HeatmapChart from '../charts/HeatmapChart';
import LineChart from '../charts/LineChart';
import BarChart from '../charts/BarChart';
import PieChart from '../charts/PieChart';
import RankProgressionGraph from './RankProgressionGraph';
import ChipActivationPanel from './ChipActivationPanel';
import CaptaincyRiskMeter from './CaptaincyRiskMeter';
import '../../styles/retro.css';

const AnalyticsModule = ({ module, entryId, currentGameweek }) => {
  const { data, loading, error } = useApi(
    () => {
      if (!entryId || !module.endpoint) return Promise.resolve(null);
      
      const apiMethod = dashboardApi[module.endpoint];
      
      if (!apiMethod) {
        console.warn(`API method not found: ${module.endpoint}`);
        return Promise.resolve(null);
      }
      
      try {
        // Call appropriate API method
        if (module.id === 'position-balance') {
          return apiMethod(entryId, currentGameweek);
        } else {
          return apiMethod(entryId);
        }
      } catch (err) {
        console.error(`Error calling ${module.endpoint}:`, err);
        return Promise.reject(err);
      }
    },
    [entryId, currentGameweek, module.endpoint],
    !!entryId
  );

  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
          <MacSpinner size={40} />
        </Box>
      );
    }

    if (error) {
      let errorMessage = 'An error occurred';
      if (typeof error === 'string') {
        errorMessage = error;
      } else if (error instanceof Error) {
        errorMessage = error.message || error.toString();
      } else if (error?.message) {
        errorMessage = error.message;
      } else {
        errorMessage = String(error);
      }
      
      return (
        <Alert severity="error" sx={{ m: 2 }}>
          {errorMessage}
        </Alert>
      );
    }

    if (!data) {
      return (
        <Typography variant="body2" sx={{ p: 2, color: 'rgba(29, 29, 27, 0.7)' }}>
          No data
        </Typography>
      );
    }

    // Handle both StandardResponse format (data.data) and direct format (data)
    const apiData = data?.data || data;
    
    console.log(`AnalyticsModule [${module.id}]:`, {
      rawData: data,
      extractedData: apiData,
      hasData: !!apiData,
      dataKeys: apiData ? Object.keys(apiData) : null
    });

    switch (module.id) {
      case 'heatmap':
        return <HeatmapChart data={apiData} />;
      
      case 'value-tracker':
        if (apiData.history) {
          const chartData = apiData.history.map(item => ({
            x: `GW${item.gameweek || item.gw}`,
            y: item.value || item.team_value || 0,
          }));
          return <LineChart data={chartData} title="Team Value Over Time" color="#50C1EC" />;
        }
        return <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>No data</Typography>;
      
      case 'transfers':
        if (apiData.transfers) {
          const chartData = apiData.transfers.map((transfer, idx) => ({
            x: `GW${transfer.gameweek || idx + 1}`,
            y: transfer.count || 1,
          }));
          return <BarChart data={chartData} title="Transfers by Gameweek" color="#FEE242" />;
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'position-balance':
        if (apiData.positions) {
          const pieData = apiData.positions.map(pos => ({
            name: pos.position || pos.name,
            value: pos.value || pos.count || 0,
          }));
          return <PieChart data={pieData} title="Position Distribution" innerRadius={60} />;
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'chips':
        return <ChipActivationPanel chipData={apiData} />;
      
      case 'captain':
        if (apiData.risk_level !== undefined) {
          return (
            <CaptaincyRiskMeter
              riskLevel={apiData.risk_level}
              playerName={apiData.current_captain}
              expectedPoints={apiData.expected_points}
            />
          );
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'rank-progression':
        return <RankProgressionGraph data={apiData} />;
      
      case 'value-efficiency':
        if (apiData.efficiency) {
          const chartData = apiData.efficiency.map(item => ({
            x: item.player || item.name,
            y: item.efficiency || item.points_per_million || 0,
          }));
          return <BarChart data={chartData} title="Value Efficiency" color="#1CB59F" />;
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      default:
        return (
          <Box className="data-terminal" sx={{ p: 2 }}>
            <pre style={{ margin: 0, fontSize: '0.75rem', fontFamily: "'JetBrains Mono', monospace" }}>
              {JSON.stringify(apiData, null, 2)}
            </pre>
          </Box>
        );
    }
  };

  return (
    <AnimatedCard 
      className="content-update"
      sx={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#DADAD3' }}
    >
      <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#DADAD3' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, color: '#1D1D1B' }}>
          {module.icon}
          <Typography
            variant="h4"
            component="h3"
            sx={{
              ml: 1,
              fontFamily: "'Roboto', sans-serif",
              fontSize: '1.1rem',
              color: '#1D1D1B',
              fontWeight: 500,
            }}
          >
            {module.title}
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1, minHeight: 300 }}>
          {renderContent()}
        </Box>
      </CardContent>
    </AnimatedCard>
  );
};

export default AnalyticsModule;

