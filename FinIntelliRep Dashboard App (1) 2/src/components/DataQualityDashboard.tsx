import { SurveyResponse, CategoryInsights } from '../types/survey';
import { analyzeCategoryData, getSentimentColor, formatPercentage } from '../utils/dataAnalysis';
import { KPICard } from './KPICard';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MessageSquare, TrendingUp, AlertTriangle } from 'lucide-react';
import { FeedbackLengthChart } from './FeedbackLengthChart';
import { SentimentWordCloud } from './SentimentWordCloud';
import { ComparativeSentimentChart } from './ComparativeSentimentChart';
import { UserEngagementMetrics } from './UserEngagementMetrics';
import { DataTable } from './DataTable';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { CategoryCriteria } from './CategoryCriteria';

interface DataQualityDashboardProps {
  data: SurveyResponse[];
  insights: CategoryInsights;
}

export function DataQualityDashboard({ data, insights }: DataQualityDashboardProps) {
  const category = 'Data Quality & Reliability';
  const categoryData = data.filter(item => item.category === category);
  const stats = analyzeCategoryData(data, category);
  
  const sentimentData = Object.entries(stats.sentimentDistribution).map(([sentiment, count]) => ({
    name: sentiment,
    value: count,
    color: getSentimentColor(sentiment as any)
  }));

  const sentimentScore = stats.averageSentimentScore;
  const sentimentTrend = sentimentScore > 0.2 ? 'up' : sentimentScore < -0.2 ? 'down' : 'neutral';

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-medium">Data Quality & Reliability Analysis</h1>
        <p className="text-muted-foreground mt-2">
          Detailed insights and feedback analysis for data quality and system reliability
        </p>
      </div>

      {/* Category Criteria */}
      <CategoryCriteria criteria="Comments about data accuracy, sync issues, permissions, authentication." />

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

      {/* User Engagement Metrics */}
      <UserEngagementMetrics data={categoryData} />

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

      {/* Charts Row 2: Feedback Analysis */}
      <FeedbackLengthChart data={categoryData} />

      {/* Word Clouds */}
      <Card>
        <CardHeader>
          <CardTitle>Feedback Word Analysis</CardTitle>
          <p className="text-sm text-muted-foreground">
            Most common words used in positive and negative feedback
          </p>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="positive" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="positive">Positive Feedback</TabsTrigger>
              <TabsTrigger value="negative">Negative Feedback</TabsTrigger>
            </TabsList>
            <TabsContent value="positive" className="mt-4">
              <SentimentWordCloud data={categoryData} sentiment="Positive" />
            </TabsContent>
            <TabsContent value="negative" className="mt-4">
              <SentimentWordCloud data={categoryData} sentiment="Negative" />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>



      {/* Data Table */}
      <DataTable 
        data={categoryData} 
        title={`Data Quality & Reliability Responses`} 
        maxHeight="400px"
      />
    </div>
  );
}