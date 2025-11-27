import { SurveyResponse, CategoryInsights } from '../types/survey';
import { analyzeCategoryData, getSentimentColor, formatPercentage } from '../utils/dataAnalysis';
import { KPICard } from './KPICard';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { MessageSquare, TrendingUp, AlertTriangle } from 'lucide-react';
import { ComparativeSentimentChart } from './ComparativeSentimentChart';
import { DataTable } from './DataTable';
import { CategoryCriteria } from './CategoryCriteria';

interface FeaturesDashboardProps {
  data: SurveyResponse[];
  insights: CategoryInsights;
}

export function FeaturesDashboard({ data, insights }: FeaturesDashboardProps) {
  const category = 'Features';
  const categoryData = data.filter(item => item.category === category);
  const stats = analyzeCategoryData(data, category);
  
  const sentimentData = Object.entries(stats.sentimentDistribution).map(([sentiment, count]) => ({
    name: sentiment,
    value: count,
    color: getSentimentColor(sentiment as any)
  }));

  const sentimentScore = stats.averageSentimentScore;
  const sentimentTrend = sentimentScore > 0.2 ? 'up' : sentimentScore < -0.2 ? 'down' : 'neutral';

  // Extract features from answers and count sentiment distribution
  const extractFeatureSentimentData = () => {
    const featureKeywords = {
      'Scheduling': ['scheduling', 'schedule', 'recurring'],
      'Customization': ['customization', 'customize', 'custom'],
      'Filters': ['filter', 'filtering', 'filters'],
      'Integrations': ['integration', 'integrations', 'integrate'],
      'Export': ['export', 'exporting', 'excel'],
      'Alerts': ['alert', 'alerts', 'notification'],
      'Report Builder': ['report builder', 'builder', 'build']
    };

    const featureCounts: Record<string, { Positive: number; Neutral: number; Negative: number }> = {};

    // Initialize all features
    Object.keys(featureKeywords).forEach(feature => {
      featureCounts[feature] = { Positive: 0, Neutral: 0, Negative: 0 };
    });

    // Count sentiment for each feature mentioned
    categoryData.forEach(response => {
      const answer = response.answer.toLowerCase();
      Object.entries(featureKeywords).forEach(([feature, keywords]) => {
        if (keywords.some(keyword => answer.includes(keyword))) {
          featureCounts[feature][response.sentiment]++;
        }
      });
    });

    // Convert to chart format and filter out features with no mentions
    return Object.entries(featureCounts)
      .filter(([_, counts]) => counts.Positive + counts.Neutral + counts.Negative > 0)
      .map(([feature, counts]) => ({
        feature,
        ...counts
      }));
  };

  const featureSentimentData = extractFeatureSentimentData();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-medium">Features Analysis</h1>
        <p className="text-muted-foreground mt-2">
          Detailed insights and feedback analysis for product features
        </p>
      </div>

      {/* Category Criteria */}
      <CategoryCriteria criteria="Comments about functionality, automation, integrations, customization options." />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Total Responses"
          value={stats.totalResponses}
          description="Category responses"
          icon={MessageSquare}
        />
        <KPICard
          title="Sentiment Score"
          value={sentimentScore.toFixed(2)}
          description={`Range: -1.0 to 1.0`}
          icon={TrendingUp}
          trend={sentimentTrend}
        />
        <KPICard
          title="Negative Feedback"
          value={stats.criticalIssuesCount}
          description="Negative feedback items"
          icon={AlertTriangle}
          trend={stats.criticalIssuesCount > 2 ? 'down' : stats.criticalIssuesCount > 0 ? 'neutral' : 'up'}
        />
      </div>

      {/* Charts Row 1: Sentiment Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Distribution</CardTitle>
            <p className="text-sm text-muted-foreground">
              Breakdown of feedback sentiment for this category
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <ComparativeSentimentChart data={data} currentCategory={category} />
      </div>

      {/* Feature Sentiment Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Sentiment Distribution within Features</CardTitle>
          <p className="text-sm text-muted-foreground">
            Breakdown of sentiment by specific feature mentioned in feedback
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={featureSentimentData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="feature" 
                angle={-45}
                textAnchor="end"
                height={100}
                interval={0}
              />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Positive" stackId="a" fill="#4CAF50" />
              <Bar dataKey="Neutral" stackId="a" fill="#9E9E9E" />
              <Bar dataKey="Negative" stackId="a" fill="#F44336" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Observations */}
        <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
          <CardHeader>
            <CardTitle className="text-blue-800 flex items-center">
              👁️ Key Observations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.observations.map((observation, index) => (
                <div key={index} className="flex items-start p-3 bg-white/60 rounded-lg border border-blue-100 hover:border-blue-200 transition-colors">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                    <span className="text-blue-600 font-medium text-sm">{index + 1}</span>
                  </div>
                  <span className="text-sm text-blue-900 leading-relaxed">{observation}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Actionable Insights */}
        <Card className="border-green-200 bg-gradient-to-br from-green-50 to-emerald-50">
          <CardHeader>
            <CardTitle className="text-green-800 flex items-center">
              ✨ Actionable Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.actionableInsights.map((insight, index) => (
                <div key={index} className="flex items-start p-3 bg-white/60 rounded-lg border border-green-100 hover:border-green-200 transition-colors">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                    <span className="text-green-600 font-medium text-sm">{index + 1}</span>
                  </div>
                  <span className="text-sm text-green-900 leading-relaxed">{insight}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Table */}
      <DataTable 
        data={categoryData} 
        title={`Features Responses`} 
        maxHeight="400px"
      />
    </div>
  );
}