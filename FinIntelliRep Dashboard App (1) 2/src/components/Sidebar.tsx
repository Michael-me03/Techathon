import { CategoryType } from '../types/survey';
import { Button } from './ui/button';
import { BarChart3, Users, Zap, Star, Database, Shield } from 'lucide-react';

interface SidebarProps {
  activeCategory: CategoryType | 'overview';
  onCategoryChange: (category: CategoryType | 'overview') => void;
}

const categoryIcons = {
  overview: BarChart3,
  'UX/UI': Users,
  'Performance': Zap,
  'Features': Star,
  'Support': Shield,
  'Data Quality & Reliability': Database,
};

export function Sidebar({ activeCategory, onCategoryChange }: SidebarProps) {
  const categories: Array<CategoryType | 'overview'> = [
    'overview',
    'UX/UI',
    'Performance',
    'Features',
    'Support',
    'Data Quality & Reliability'
  ];

  return (
    <div className="w-64 bg-card border-r border-border p-4 h-full">
      <div className="mb-6">
        <h1 className="text-xl font-medium text-foreground mb-2">Hackstreetboys</h1>
        <p className="text-sm text-muted-foreground">Survey Results Dashboard</p>
      </div>
      
      <nav className="space-y-2">
        {categories.map((category) => {
          const Icon = categoryIcons[category];
          const isActive = activeCategory === category;
          
          return (
            <Button
              key={category}
              variant={isActive ? "default" : "ghost"}
              className="w-full justify-start"
              onClick={() => onCategoryChange(category)}
            >
              <Icon className="mr-2 h-4 w-4" />
              {category === 'overview' ? 'Overview' : category}
            </Button>
          );
        })}
      </nav>
    </div>
  );
}