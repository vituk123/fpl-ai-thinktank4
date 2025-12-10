import React from 'react';
import { Box, Typography } from '@mui/material';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * Line Chart Component for time series data
 */
const LineChart = ({ data, xKey = 'x', yKey = 'y', title, color = '#e2deda' }) => {
  if (!data || data.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', height: 400, p: 2 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(226, 222, 218, 0.1)" />
          <XAxis 
            dataKey={xKey} 
            stroke="rgba(226, 222, 218, 0.6)"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          />
          <YAxis 
            stroke="rgba(226, 222, 218, 0.6)"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#292929',
              border: '1px solid rgba(226, 222, 218, 0.2)',
              borderRadius: 4,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </RechartsLineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default LineChart;

