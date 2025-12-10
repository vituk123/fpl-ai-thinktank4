import React from 'react';
import { Box, Typography } from '@mui/material';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = ['#e2deda', '#50C1EC', '#FEE242', '#1CB59F', '#EB3E49', '#398CB0', '#F8D059'];

/**
 * Pie/Donut Chart Component
 */
const PieChart = ({ data, title, innerRadius = 0 }) => {
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
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            outerRadius={120}
            innerRadius={innerRadius}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#292929',
              border: '1px solid rgba(226, 222, 218, 0.2)',
              borderRadius: 4,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          />
          <Legend />
        </RechartsPieChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default PieChart;

