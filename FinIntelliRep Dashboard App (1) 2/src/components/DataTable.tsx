import { SurveyResponse } from '../types/survey';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';

interface DataTableProps {
  data: SurveyResponse[];
  title?: string;
  maxHeight?: string;
}

export function DataTable({ data, title = "Survey Responses", maxHeight = "400px" }: DataTableProps) {
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'Positive':
        return 'bg-green-100 text-green-800 hover:bg-green-200';
      case 'Negative':
        return 'bg-red-100 text-red-800 hover:bg-red-200';
      case 'Neutral':
        return 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 hover:bg-gray-200';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'UX/UI':
        return 'bg-blue-100 text-blue-800 hover:bg-blue-200';
      case 'Performance':
        return 'bg-purple-100 text-purple-800 hover:bg-purple-200';
      case 'Features':
        return 'bg-indigo-100 text-indigo-800 hover:bg-indigo-200';
      case 'Support':
        return 'bg-orange-100 text-orange-800 hover:bg-orange-200';
      case 'Data Quality & Reliability':
        return 'bg-cyan-100 text-cyan-800 hover:bg-cyan-200';
      default:
        return 'bg-gray-100 text-gray-800 hover:bg-gray-200';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Showing {data.length} response{data.length !== 1 ? 's' : ''}
        </p>
      </CardHeader>
      <CardContent>
        <ScrollArea style={{ height: maxHeight }}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">User</TableHead>
                <TableHead className="min-w-[300px]">Response</TableHead>
                <TableHead className="w-[150px]">Category</TableHead>
                <TableHead className="w-[100px]">Sentiment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((response, index) => (
                <TableRow key={`${response.user_name}-${index}`} className="hover:bg-muted/50">
                  <TableCell className="font-medium">
                    {response.user_name}
                  </TableCell>
                  <TableCell className="text-sm leading-relaxed">
                    {response.answer}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={getCategoryColor(response.category)}>
                      {response.category}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={getSentimentColor(response.sentiment)}>
                      {response.sentiment}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}