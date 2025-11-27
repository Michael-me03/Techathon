import { useMemo } from 'react';
import { SurveyResponse, CategoryType } from '../types/survey';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine, Legend } from 'recharts';

interface ComparativeSentimentChartProps {
  data: SurveyResponse[];
  currentCategory: CategoryType;
}

const getCategoryColor = (category: CategoryType) => {
  switch (category) {
    case 'UX/UI':
      return '#8b5cf6'; // violet
    case 'Performance':
      return '#06b6d4'; // cyan
    case 'Features':
      return '#f59e0b'; // amber
    case 'Support':
      return '#ec4899'; // pink
    case 'Data Quality & Reliability':
      return '#10b981'; // emerald
    default:
      return '#6b7280';
  }
};

export function ComparativeSentimentChart({ data, currentCategory }: ComparativeSentimentChartProps) {
  const chartData = useMemo(() => {
    const categories: CategoryType[] = [
      'UX/UI',
      'Performance',
      'Features',
      'Support',
      'Data Quality & Reliability'
    ];

    return categories.map(category => {
      const categoryData = data.filter(item => item.category === category);
      const totalResponses = categoryData.length;
      
      if (totalResponses === 0) {
        return {
          category,
          sentimentScore: 0,
          positiveCount: 0,
          negativeCount: 0,
          neutralCount: 0,
          color: getCategoryColor(category),
          isCurrent: category === currentCategory,
        };
      }

      const positiveCount = categoryData.filter(item => item.sentiment === 'Positive').length;
      const negativeCount = categoryData.filter(item => item.sentiment === 'Negative').length;
      const neutralCount = categoryData.filter(item => item.sentiment === 'Neutral').length;
      
      // Calculate sentiment score excluding neutral: (positive - negative) / (positive + negative) * 100
      // Cap minimum at 0 for better visualization
      const nonNeutralTotal = positiveCount + negativeCount;
      const sentimentScore = nonNeutralTotal === 0 ? 0 : Math.max(0, ((positiveCount - negativeCount) / nonNeutralTotal) * 100);

      return {
        category: category === 'Data Quality & Reliability' ? 'Data Quality' : category,
        fullCategory: category,
        sentimentScore: Math.round(sentimentScore * 10) / 10,
        positiveCount,
        negativeCount,
        neutralCount,
        totalResponses,
        color: getCategoryColor(category),
        isCurrent: category === currentCategory,
      };
    });
  }, [data, currentCategory]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium mb-2">{data.fullCategory}</p>
          <div className="text-sm space-y-1">
            <p className="font-medium">Sentiment Score: {data.sentimentScore}%</p>
            <p className="text-green-600">✓ Positive: {data.positiveCount}</p>
            <p className="text-gray-600">○ Neutral: {data.neutralCount}</p>
            <p className="text-red-600">✗ Negative: {data.negativeCount}</p>
            <p className="text-muted-foreground border-t pt-1 mt-1">Total: {data.totalResponses} responses</p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparative Sentiment Analysis</CardTitle>
        <p className="text-sm text-muted-foreground">
          How does this category compare to others? Higher scores indicate better sentiment.
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              type="number" 
              domain={[0, 100]}
              label={{ value: 'Sentiment Score (%)', position: 'bottom' }}
            />
            <YAxis 
              type="category" 
              dataKey="category" 
              width={120}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={0} stroke="#666" strokeWidth={2} />
            <Bar dataKey="sentimentScore" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color} 
                  opacity={entry.isCurrent ? 1 : 0.6}
                  stroke={entry.isCurrent ? entry.color : 'none'}
                  strokeWidth={entry.isCurrent ? 3 : 0}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}