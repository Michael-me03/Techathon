import { SurveyResponse, CategoryType, SentimentType } from '../types/survey';
import { getOverallStats, getSentimentColor, getCategoryColor } from '../utils/dataAnalysis';
import { KPICard } from './KPICard';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, MessageSquare, TrendingUp, Upload } from 'lucide-react';
import { SentimentWordCloud } from './SentimentWordCloud';
import { FeedbackLengthChart } from './FeedbackLengthChart';
import { DataTable } from './DataTable';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Button } from './ui/button';
import { toast } from 'sonner@2.0.3';
import { useRef } from 'react';

interface OverviewDashboardProps {
  data: SurveyResponse[];
  onDataUpdate?: (data: SurveyResponse[]) => void;
}

export function OverviewDashboard({ data, onDataUpdate }: OverviewDashboardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stats = getOverallStats(data);
  
  const sentimentData = Object.entries(stats.overallSentimentDistribution).map(([sentiment, count]) => ({
    name: sentiment,
    value: count,
    color: getSentimentColor(sentiment as any)
  }));

  const categoryData = Object.entries(stats.categoryDistribution).map(([category, count], index) => ({
    name: category.replace('Data Quality & Reliability', 'Data Quality'),
    value: count,
    color: getCategoryColor(index)
  }));

  // Calculate positive sentiment including neutral comments
  const positiveCount = stats.overallSentimentDistribution.Positive || 0;
  const neutralCount = stats.overallSentimentDistribution.Neutral || 0;
  const positivePercentage = Math.round(((positiveCount + neutralCount) / stats.totalResponses) * 100);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file');
      return;
    }

    try {
      const text = await file.text();
      const parsedData = parseCSV(text);
      
      if (parsedData.length === 0) {
        toast.error('No valid data found in the CSV file');
        return;
      }

      onDataUpdate?.(parsedData);
      toast.success(`Successfully uploaded ${parsedData.length} survey responses`);
      
      // Reset the input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Error parsing CSV:', error);
      toast.error('Failed to parse CSV file. Please check the format.');
    }
  };

  const parseCSV = (text: string): SurveyResponse[] => {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length < 2) return [];

    // Parse header
    const header = lines[0].split(',').map(h => h.trim().toLowerCase());
    const userNameIndex = header.findIndex(h => h === 'user_name' || h === 'username' || h === 'user');
    const answerIndex = header.findIndex(h => h === 'answer' || h === 'feedback' || h === 'comment');
    const categoryIndex = header.findIndex(h => h === 'category');
    const sentimentIndex = header.findIndex(h => h === 'sentiment');

    if (userNameIndex === -1 || answerIndex === -1 || categoryIndex === -1 || sentimentIndex === -1) {
      throw new Error('CSV must contain columns: user_name, answer, category, sentiment');
    }

    // Parse data rows
    const validCategories: CategoryType[] = ['UX/UI', 'Performance', 'Features', 'Support', 'Data Quality & Reliability'];
    const validSentiments: SentimentType[] = ['Positive', 'Neutral', 'Negative'];
    
    const parsedData: SurveyResponse[] = [];
    
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i]);
      
      if (values.length <= Math.max(userNameIndex, answerIndex, categoryIndex, sentimentIndex)) {
        continue;
      }

      const category = values[categoryIndex].trim() as CategoryType;
      const sentiment = values[sentimentIndex].trim() as SentimentType;

      if (!validCategories.includes(category) || !validSentiments.includes(sentiment)) {
        continue;
      }

      parsedData.push({
        user_name: values[userNameIndex].trim(),
        answer: values[answerIndex].trim(),
        category,
        sentiment
      });
    }

    return parsedData;
  };

  const parseCSVLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current);
        current = '';
      } else {
        current += char;
      }
    }
    
    result.push(current);
    return result.map(v => v.replace(/^"|"$/g, '').trim());
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-medium">Survey Results Overview</h1>
          <p className="text-muted-foreground mt-2">
            Comprehensive analysis of survey responses across all categories
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
          />
          <Button onClick={handleUploadClick} className="flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Upload Data
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Total Responses"
          value={stats.totalResponses}
          description="Across all categories"
          icon={MessageSquare}
        />
        <KPICard
          title="Categories Analyzed"
          value={stats.categories.length}
          description="Different feedback areas"
          icon={Users}
        />
        <KPICard
          title="Early Acceptance"
          value={`${positivePercentage}%`}
          description="Includes positive and neutral feedback"
          icon={TrendingUp}
          trend={positivePercentage > 60 ? 'up' : positivePercentage > 40 ? 'neutral' : 'down'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Overall Sentiment Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
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

        {/* Category Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Responses by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name" 
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  fontSize={12}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value">
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Feedback Length Analysis */}
      <FeedbackLengthChart data={data} />

      {/* Feedback Word Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Feedback Word Analysis</CardTitle>
          <p className="text-sm text-muted-foreground">
            Most common words used in positive and negative feedback across all categories
          </p>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="positive" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="positive">Positive Feedback</TabsTrigger>
              <TabsTrigger value="negative">Negative Feedback</TabsTrigger>
            </TabsList>
            <TabsContent value="positive" className="mt-4">
              <SentimentWordCloud data={data} sentiment="Positive" />
            </TabsContent>
            <TabsContent value="negative" className="mt-4">
              <SentimentWordCloud data={data} sentiment="Negative" />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Data Table */}
      <DataTable 
        data={data} 
        title="All Survey Responses" 
        maxHeight="500px"
      />

    </div>
  );
}