import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const DemandChart = ({ baseline, scenario }) => {
  const data = [
    {
      name: 'Electricity Demand',
      Baseline: baseline,
      Scenario: scenario,
    },
  ];

  return (
    <div className="demand-chart">
      <h3>Demand Comparison</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip formatter={(value) => [`${value} MW`, '']} />
          <Legend />
          <Bar dataKey="Baseline" fill="#8884d8" />
          <Bar dataKey="Scenario" fill="#82ca9d" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DemandChart;