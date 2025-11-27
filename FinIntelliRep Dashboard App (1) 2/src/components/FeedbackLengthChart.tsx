import { useMemo } from 'react';
import { SurveyResponse } from '../types/survey';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';

interface FeedbackLengthChartProps {
  data: SurveyResponse[];
}

interface BoxPlotData {
  sentiment: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  mean: number;
  color: string;
}

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case 'Positive':
      return '#22c55e'; // green
    case 'Negative':
      return '#ef4444'; // red
    case 'Neutral':
      return '#6b7280'; // gray
    default:
      return '#6b7280';
  }
};

const calculateBoxPlotStats = (values: number[]): Omit<BoxPlotData, 'sentiment' | 'color'> => {
  const sorted = [...values].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const median = sorted[Math.floor(sorted.length / 2)];
  const q1 = sorted[Math.floor(sorted.length / 4)];
  const q3 = sorted[Math.floor((sorted.length * 3) / 4)];
  const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
  
  return { min, q1, median, q3, max, mean };
};

export function FeedbackLengthChart({ data }: FeedbackLengthChartProps) {
  const chartData = useMemo(() => {
    const sentiments = ['Positive', 'Negative', 'Neutral'];
    
    return sentiments.map(sentiment => {
      const sentimentData = data.filter(item => item.sentiment === sentiment);
      const lengths = sentimentData.map(item => item.answer.length);
      
      if (lengths.length === 0) {
        return {
          sentiment,
          min: 0,
          q1: 0,
          median: 0,
          q3: 0,
          max: 0,
          mean: 0,
          color: getSentimentColor(sentiment),
        };
      }
      
      return {
        sentiment,
        ...calculateBoxPlotStats(lengths),
        color: getSentimentColor(sentiment),
      };
    });
  }, [data]);

  const CustomBoxPlot = (props: any) => {
    const { x, y, width, height, payload } = props;
    const boxWidth = width * 0.6;
    const centerX = x + width / 2;
    const chartHeight = 300;
    
    // Scale values to fit the chart
    const scale = (value: number) => {
      const maxValue = Math.max(...chartData.map(d => d.max));
      return chartHeight - (value / maxValue) * chartHeight;
    };
    
    const minY = scale(payload.min);
    const q1Y = scale(payload.q1);
    const medianY = scale(payload.median);
    const q3Y = scale(payload.q3);
    const maxY = scale(payload.max);
    const meanY = scale(payload.mean);
    
    return (
      <g>
        {/* Whisker line (min to max) */}
        <line
          x1={centerX}
          y1={minY}
          x2={centerX}
          y2={maxY}
          stroke={payload.color}
          strokeWidth={2}
          opacity={0.6}
        />
        
        {/* Box (Q1 to Q3) */}
        <rect
          x={centerX - boxWidth / 2}
          y={q3Y}
          width={boxWidth}
          height={q1Y - q3Y}
          fill={payload.color}
          fillOpacity={0.3}
          stroke={payload.color}
          strokeWidth={2}
        />
        
        {/* Median line */}
        <line
          x1={centerX - boxWidth / 2}
          y1={medianY}
          x2={centerX + boxWidth / 2}
          y2={medianY}
          stroke={payload.color}
          strokeWidth={3}
        />
        
        {/* Mean marker (diamond) */}
        <circle
          cx={centerX}
          cy={meanY}
          r={4}
          fill="white"
          stroke={payload.color}
          strokeWidth={2}
        />
        
        {/* Min and Max caps */}
        <line
          x1={centerX - boxWidth / 4}
          y1={minY}
          x2={centerX + boxWidth / 4}
          y2={minY}
          stroke={payload.color}
          strokeWidth={2}
        />
        <line
          x1={centerX - boxWidth / 4}
          y1={maxY}
          x2={centerX + boxWidth / 4}
          y2={maxY}
          stroke={payload.color}
          strokeWidth={2}
        />
      </g>
    );
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium mb-1">{data.sentiment}</p>
          <div className="text-sm space-y-0.5">
            <p>Max: {data.max} characters</p>
            <p>Q3: {data.q3} characters</p>
            <p>Median: {data.median} characters</p>
            <p>Mean: {Math.round(data.mean)} characters</p>
            <p>Q1: {data.q1} characters</p>
            <p>Min: {data.min} characters</p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feedback Length by Sentiment</CardTitle>
        <p className="text-sm text-muted-foreground">
          Distribution of response lengths (in characters) grouped by sentiment
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="sentiment" />
            <YAxis label={{ value: 'Number of Characters', angle: -90, position: 'insideLeft' }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="median" shape={<CustomBoxPlot />}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 flex items-center justify-center gap-6 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-current"></div>
            <span>Median</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full border-2 border-current bg-white"></div>
            <span>Mean</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-6 border-2 border-current opacity-30"></div>
            <span>Q1-Q3 Range</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
