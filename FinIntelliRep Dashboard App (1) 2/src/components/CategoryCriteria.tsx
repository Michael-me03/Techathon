import { Info } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';

interface CategoryCriteriaProps {
  criteria: string;
}

export function CategoryCriteria({ criteria }: CategoryCriteriaProps) {
  return (
    <Alert className="border-purple-200/60 bg-gradient-to-r from-purple-50/40 to-pink-50/40 shadow-sm">
      <Info className="h-4 w-4 text-purple-600" />
      <AlertDescription className="text-sm text-muted-foreground ml-2">
        <span className="text-purple-900/70">
          <span className="font-medium text-purple-800">Category Criteria: </span>
          {criteria}
        </span>
      </AlertDescription>
    </Alert>
  );
}