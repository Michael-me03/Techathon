import { useState } from 'react';
import { CategoryType, SurveyResponse } from './types/survey';
import { realSurveyData, realCategoryInsights } from './data/realSurveyData';
import { Sidebar } from './components/Sidebar';
import { OverviewDashboard } from './components/OverviewDashboard';
import { UXUIDashboard } from './components/UXUIDashboard';
import { PerformanceDashboard } from './components/PerformanceDashboard';
import { FeaturesDashboard } from './components/FeaturesDashboard';
import { SupportDashboard } from './components/SupportDashboard';
import { DataQualityDashboard } from './components/DataQualityDashboard';
import { Toaster } from './components/ui/sonner';

export default function App() {
  const [activeCategory, setActiveCategory] = useState<CategoryType | 'overview'>('overview');
  const [surveyData, setSurveyData] = useState<SurveyResponse[]>(realSurveyData);

  const handleCategoryChange = (category: CategoryType | 'overview') => {
    setActiveCategory(category);
  };

  const handleDataUpdate = (newData: SurveyResponse[]) => {
    setSurveyData(newData);
  };

  return (
    <div className="flex h-screen bg-background">
      <Sidebar 
        activeCategory={activeCategory} 
        onCategoryChange={handleCategoryChange} 
      />
      
      <div className="flex-1 overflow-auto">
        {activeCategory === 'overview' ? (
          <OverviewDashboard data={surveyData} onDataUpdate={handleDataUpdate} />
        ) : activeCategory === 'UX/UI' ? (
          <UXUIDashboard 
            data={surveyData}
            insights={realCategoryInsights['UX/UI']}
          />
        ) : activeCategory === 'Performance' ? (
          <PerformanceDashboard 
            data={surveyData}
            insights={realCategoryInsights['Performance']}
          />
        ) : activeCategory === 'Features' ? (
          <FeaturesDashboard 
            data={surveyData}
            insights={realCategoryInsights['Features']}
          />
        ) : activeCategory === 'Support' ? (
          <SupportDashboard 
            data={surveyData}
            insights={realCategoryInsights['Support']}
          />
        ) : activeCategory === 'Data Quality & Reliability' ? (
          <DataQualityDashboard 
            data={surveyData}
            insights={realCategoryInsights['Data Quality & Reliability']}
          />
        ) : null}
      </div>
      <Toaster />
    </div>
  );
}