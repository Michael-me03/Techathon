export type SentimentType = 'Positive' | 'Neutral' | 'Negative';

export type CategoryType = 'UX/UI' | 'Performance' | 'Features' | 'Support' | 'Data Quality & Reliability';

export interface SurveyResponse {
  user_name: string;
  answer: string;
  category: CategoryType;
  sentiment: SentimentType;
}

export interface CategoryInsights {
  observations: string[];
  actionableInsights: string[];
}

export interface CategoryStats {
  totalResponses: number;
  sentimentDistribution: Record<SentimentType, number>;
  averageSentimentScore: number;
  topIssues: string[];
  criticalIssuesCount: number;
}