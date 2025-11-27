import { useMemo } from 'react';
import { SurveyResponse } from '../types/survey';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { MessageSquare, Hash } from 'lucide-react';

interface UserEngagementMetricsProps {
  data: SurveyResponse[];
}

export function UserEngagementMetrics({ data }: UserEngagementMetricsProps) {
  const metrics = useMemo(() => {
    if (data.length === 0) {
      return {
        avgFeedbackLength: 0,
        avgWordsPerResponse: 0,
      };
    }

    // Calculate average feedback length
    const totalChars = data.reduce((sum, item) => sum + item.answer.length, 0);
    const avgFeedbackLength = Math.round(totalChars / data.length);

    // Calculate average words per response
    const totalWords = data.reduce((sum, item) => {
      return sum + item.answer.split(/\s+/).filter(word => word.length > 0).length;
    }, 0);
    const avgWordsPerResponse = Math.round(totalWords / data.length);

    return {
      avgFeedbackLength,
      avgWordsPerResponse,
    };
  }, [data]);

  const MetricCard = ({ 
    icon: Icon, 
    label, 
    value, 
    subtitle, 
    color 
  }: { 
    icon: any; 
    label: string; 
    value: string | number; 
    subtitle: string; 
    color: string;
  }) => (
    <div className="flex items-start gap-3 p-4 bg-gradient-to-br from-white to-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-medium mt-1">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>User Engagement Metrics</CardTitle>
        <p className="text-sm text-muted-foreground">
          How engaged are users when providing feedback?
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MetricCard
            icon={MessageSquare}
            label="Avg. Feedback Length"
            value={metrics.avgFeedbackLength}
            subtitle="characters per response"
            color="bg-violet-100 text-violet-600"
          />
          <MetricCard
            icon={Hash}
            label="Avg. Words per Response"
            value={metrics.avgWordsPerResponse}
            subtitle="words per feedback"
            color="bg-cyan-100 text-cyan-600"
          />
        </div>
      </CardContent>
    </Card>
  );
}