import React from 'react';
import { Box, Typography } from '@mui/material';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * Bar Chart Component
 */
const BarChart = ({ data, xKey = 'x', yKey = 'y', title, color = '#e2deda' }) => {
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
        <RechartsBarChart data={data}>
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
          <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default BarChart;

