import { SurveyResponse, CategoryType, SentimentType, CategoryStats } from '../types/survey';

export function analyzeCategoryData(data: SurveyResponse[], category: CategoryType): CategoryStats {
  const categoryData = data.filter(item => item.category === category);
  
  const sentimentDistribution = categoryData.reduce((acc, item) => {
    acc[item.sentiment] = (acc[item.sentiment] || 0) + 1;
    return acc;
  }, {} as Record<SentimentType, number>);

  // Calculate average sentiment score (Positive: 1, Neutral: 0, Negative: -1)
  const sentimentScores = categoryData.map(item => {
    switch (item.sentiment) {
      case 'Positive': return 1;
      case 'Neutral': return 0;
      case 'Negative': return -1;
      default: return 0;
    }
  });
  
  const averageSentimentScore = sentimentScores.length > 0 
    ? sentimentScores.reduce((sum, score) => sum + score, 0) / sentimentScores.length
    : 0;

  // Extract top issues from negative feedback
  const negativeResponses = categoryData.filter(item => item.sentiment === 'Negative');
  const topIssues = negativeResponses.slice(0, 3).map(item => item.answer);
  const criticalIssuesCount = negativeResponses.length;

  return {
    totalResponses: categoryData.length,
    sentimentDistribution,
    averageSentimentScore,
    topIssues,
    criticalIssuesCount
  };
}

export function getOverallStats(data: SurveyResponse[]) {
  const totalResponses = data.length;
  const categories = Array.from(new Set(data.map(item => item.category))) as CategoryType[];
  
  const overallSentimentDistribution = data.reduce((acc, item) => {
    acc[item.sentiment] = (acc[item.sentiment] || 0) + 1;
    return acc;
  }, {} as Record<SentimentType, number>);

  const categoryDistribution = data.reduce((acc, item) => {
    acc[item.category] = (acc[item.category] || 0) + 1;
    return acc;
  }, {} as Record<CategoryType, number>);

  return {
    totalResponses,
    categories,
    overallSentimentDistribution,
    categoryDistribution
  };
}

export function getSentimentColor(sentiment: SentimentType): string {
  switch (sentiment) {
    case 'Positive': return '#10b981'; // Emerald-500
    case 'Neutral': return '#f59e0b'; // Amber-500  
    case 'Negative': return '#f87171'; // Red-400
    default: return '#6b7280';
  }
}

export function getCategoryColor(index: number): string {
  const colors = [
    '#8b5cf6', // Violet-500
    '#06b6d4', // Cyan-500
    '#f59e0b', // Amber-500
    '#ec4899', // Pink-500
    '#10b981', // Emerald-500
  ];
  return colors[index % colors.length];
}

export function formatPercentage(value: number, total: number): string {
  return total > 0 ? `${Math.round((value / total) * 100)}%` : '0%';
}