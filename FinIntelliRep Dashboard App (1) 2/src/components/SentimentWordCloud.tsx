import { useMemo } from "react";
import { SurveyResponse } from "../types/survey";
import ReactWordcloud from "react-wordcloud";
import "tippy.js/dist/tippy.css";
import "tippy.js/animations/scale.css";

interface SentimentWordCloudProps {
  data: SurveyResponse[];
  sentiment: "Positive" | "Negative";
}

const STOPWORDS = new Set([
  "the",
  "is",
  "at",
  "which",
  "on",
  "a",
  "an",
  "and",
  "or",
  "but",
  "in",
  "with",
  "to",
  "for",
  "of",
  "as",
  "by",
  "that",
  "this",
  "it",
  "from",
  "be",
  "are",
  "was",
  "were",
  "been",
  "have",
  "has",
  "had",
  "do",
  "does",
  "did",
  "will",
  "would",
  "could",
  "should",
  "may",
  "might",
  "can",
  "i",
  "me",
  "my",
  "we",
  "our",
  "you",
  "your",
  "ve",
  "t",
  "s",
  "m",
  "re",
  "ll",
  "d",
  "very",
  "just",
  "so",
  "than",
  "too",
  "when",
  "where",
  "who",
  "what",
  "how",
  "why",
  "if",
  "because",
  "while",
  "after",
  "before",
  "during",
  "without",
  "within",
  "through",
  "over",
  "under",
  "again",
  "further",
  "then",
  "once",
  "here",
  "there",
  "all",
  "both",
  "each",
  "few",
  "more",
  "most",
  "other",
  "some",
  "such",
  "only",
  "own",
  "same",
  "than",
  "into",
  "up",
  "down",
  "out",
  "about",
  "its",
  "dono",
  "don",
]);

export function SentimentWordCloud({
  data,
  sentiment,
}: SentimentWordCloudProps) {
  const words = useMemo(() => {
    // Filter by sentiment
    const filteredData = data.filter(
      (item) => item.sentiment === sentiment,
    );

    // Combine all text
    const allText = filteredData
      .map((item) => item.answer)
      .join(" ");

    // Clean and tokenize
    const cleanText = allText
      .toLowerCase()
      .replace(/[^\w\s]/g, " ") // Remove punctuation
      .split(/\s+/)
      .filter(
        (word) => word.length > 2 && !STOPWORDS.has(word),
      );

    // Count word frequencies
    const wordFreq: Record<string, number> = {};
    cleanText.forEach((word) => {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    });

    // Convert to format expected by react-wordcloud
    return Object.entries(wordFreq)
      .map(([text, value]) => ({ text, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 50); // Top 50 words
  }, [data, sentiment]);

  const options = {
    rotations: 2,
    rotationAngles: [0, 0] as [number, number],
    fontSizes: [16, 60] as [number, number],
    padding: 2,
    enableTooltip: true,
    deterministic: true,
    fontFamily: "system-ui, -apple-system, sans-serif",
    scale: "sqrt" as const,
    spiral: "archimedean" as const,
  };

  const callbacks = {
    getWordColor: () => {
      return sentiment === "Positive"
        ? `hsl(${Math.random() * 30 + 120}, 60%, ${Math.random() * 20 + 35}%)` // Green shades
        : `hsl(${Math.random() * 30}, 70%, ${Math.random() * 20 + 40}%)`; // Red shades
    },
  };

  if (words.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-muted-foreground">
        No {sentiment.toLowerCase()} feedback available
      </div>
    );
  }

  return (
    <div className="h-[400px] w-full">
      <ReactWordcloud
        words={words}
        options={options}
        callbacks={callbacks}
      />
    </div>
  );
}