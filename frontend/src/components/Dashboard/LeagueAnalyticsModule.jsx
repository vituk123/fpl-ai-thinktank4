import React from 'react';
import { CardContent, Box, Typography, Alert } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import MacSpinner from '../MacSpinner';
import { dashboardApi } from '../../services/api';
import useApi from '../../hooks/useApi';
import HeatmapChart from '../charts/HeatmapChart';
import LineChart from '../charts/LineChart';
import BarChart from '../charts/BarChart';
import PieChart from '../charts/PieChart';
import '../../styles/retro.css';

const LeagueAnalyticsModule = ({ module, currentGameweek }) => {
  const { data, loading, error } = useApi(
    () => {
      if (!module.endpoint) return Promise.resolve(null);
      
      // Map module endpoint names to API methods
      const endpointMap = {
        'ownership-correlation': dashboardApi.getOwnershipCorrelation,
        'template-team': dashboardApi.getTemplateTeam,
        'price-predictors': dashboardApi.getPricePredictors,
        'position-distribution': dashboardApi.getPositionDistribution,
        'fixture-swing': dashboardApi.getFixtureSwing,
        'dgw-probability': dashboardApi.getDgwProbability,
        'price-brackets': dashboardApi.getPriceBrackets,
      };
      
      const apiMethod = endpointMap[module.endpoint];
      
      if (!apiMethod) {
        console.warn(`API method not found: ${module.endpoint}`);
        return Promise.resolve(null);
      }
      
      try {
        // League endpoints don't require entryId, but may need gameweek
        if (module.id === 'fixture-swing' || module.id === 'dgw-probability') {
          return apiMethod(null, currentGameweek);
        } else {
          return apiMethod(null, currentGameweek);
        }
      } catch (err) {
        console.error(`Error calling ${module.endpoint}:`, err);
        return Promise.reject(err);
      }
    },
    [currentGameweek, module.endpoint],
    true
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

    switch (module.id) {
      case 'ownership-correlation':
        if (apiData.correlation_data || apiData.data) {
          const correlationData = apiData.correlation_data || apiData.data || [];
          if (Array.isArray(correlationData) && correlationData.length > 0) {
            const chartData = correlationData.map(item => ({
              x: item.ownership || item.x || 0,
              y: item.points || item.y || 0,
            }));
            return <HeatmapChart data={chartData} title="Ownership vs Points" />;
          }
        }
        return <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>No data</Typography>;
      
      case 'template-team':
        if (apiData.template_team || apiData.players) {
          const players = apiData.template_team || apiData.players || [];
          if (Array.isArray(players) && players.length > 0) {
            const chartData = players.slice(0, 15).map((player, idx) => ({
              x: player.name || player.player_name || `Player ${idx + 1}`,
              y: player.ownership || player.ownership_percent || 0,
            }));
            return <BarChart data={chartData} title="Template Team Ownership" color="#50C1EC" />;
          }
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'price-predictors':
        if (apiData.predictions || apiData.data) {
          const predictions = apiData.predictions || apiData.data || [];
          if (Array.isArray(predictions) && predictions.length > 0) {
            const chartData = predictions.slice(0, 20).map(item => ({
              x: item.player_name || item.name || 'Player',
              y: item.predicted_change || item.change || 0,
            }));
            return <BarChart data={chartData} title="Price Predictions" color="#FEE242" />;
          }
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'position-distribution':
        if (apiData.distribution || apiData.positions) {
          const distribution = apiData.distribution || apiData.positions || [];
          if (Array.isArray(distribution) && distribution.length > 0) {
            const pieData = distribution.map(pos => ({
              name: pos.position || pos.name || 'Unknown',
              value: pos.points || pos.count || pos.value || 0,
            }));
            return <PieChart data={pieData} title="Position Distribution" innerRadius={60} />;
          }
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'fixture-swing':
        if (apiData.swings || apiData.data) {
          const swings = apiData.swings || apiData.data || [];
          if (Array.isArray(swings) && swings.length > 0) {
            const chartData = swings.map(item => ({
              x: item.team || item.team_name || 'Team',
              y: item.swing || item.difficulty_change || 0,
            }));
            return <BarChart data={chartData} title="Fixture Difficulty Swings" color="#1CB59F" />;
          }
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'dgw-probability':
        if (apiData.probabilities || apiData.data) {
          const probabilities = apiData.probabilities || apiData.data || [];
          if (Array.isArray(probabilities) && probabilities.length > 0) {
            const chartData = probabilities.map(item => ({
              x: item.team || item.team_name || 'Team',
              y: item.probability || item.dgw_probability || 0,
            }));
            return <BarChart data={chartData} title="DGW Probability" color="#EB3E49" />;
          }
        }
        return <Typography color="text.secondary">No data</Typography>;
      
      case 'price-brackets':
        if (apiData.brackets || apiData.data) {
          const brackets = apiData.brackets || apiData.data || [];
          if (Array.isArray(brackets) && brackets.length > 0) {
            const chartData = brackets.map(item => ({
              x: item.bracket || item.price_range || 'Range',
              y: item.points || item.avg_points || 0,
            }));
            return <BarChart data={chartData} title="Points by Price Bracket" color="#50C1EC" />;
          }
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

export default LeagueAnalyticsModule;

