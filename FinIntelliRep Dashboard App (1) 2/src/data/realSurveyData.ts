import { SurveyResponse, CategoryType, CategoryInsights } from '../types/survey';

export const realSurveyData: SurveyResponse[] = [
  {"user_name": "alice", "answer": "The reporting tool is intuitive and saves me a lot of time.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "bob", "answer": "I find it confusing and often buggy, especially when generating charts.", "category": "Performance", "sentiment": "Negative"},
  {"user_name": "carla", "answer": "It's okay for basic reports but lacks advanced customization features.", "category": "Features", "sentiment": "Neutral"},
  {"user_name": "daniel", "answer": "Absolutely love the automation features—it's a game changer!", "category": "Features", "sentiment": "Positive"},
  {"user_name": "emma", "answer": "The interface feels outdated and clunky. Needs a redesign.", "category": "UX/UI", "sentiment": "Negative"},
  {"user_name": "farid", "answer": "It works well for my needs, but I wish it had better export options.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "grace", "answer": "I've had frequent issues with data syncing. Support was slow to respond.", "category": "Data Quality & Reliability", "sentiment": "Negative"},
  {"user_name": "hugo", "answer": "Very efficient and easy to use. I recommend it to my team.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "isla", "answer": "Not user-friendly. Took me hours to figure out how to build a report.", "category": "UX/UI", "sentiment": "Negative"},
  {"user_name": "james", "answer": "Reliable and fast. Handles large datasets without crashing.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "karen", "answer": "The dashboard visuals are clean and informative.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "liam", "answer": "I wish it had more integrations with third-party tools.", "category": "Features", "sentiment": "Neutral"},
  {"user_name": "maya", "answer": "It's a solid tool, but the learning curve is steep.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "nina", "answer": "I love the scheduling feature—it keeps my reports timely.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "oliver", "answer": "Sometimes the filters don't work as expected. Frustrating!", "category": "Features", "sentiment": "Negative"},
  {"user_name": "paula", "answer": "The export to Excel feature is a lifesaver.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "quentin", "answer": "I've had trouble with permissions and sharing reports with my team.", "category": "Data Quality & Reliability", "sentiment": "Negative"},
  {"user_name": "rachel", "answer": "The tool is powerful but not very beginner-friendly.", "category": "UX/UI", "sentiment": "Neutral"},
  {"user_name": "sam", "answer": "Great for tracking KPIs. I use it daily.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "tina", "answer": "The mobile version is buggy and crashes often.", "category": "Performance", "sentiment": "Negative"},
  {"user_name": "umar", "answer": "I appreciate the customization options—it fits our workflow well.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "victor", "answer": "The UI is slick and modern. Very pleasant to use.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "wendy", "answer": "I don't like how long it takes to load large reports.", "category": "Performance", "sentiment": "Negative"},
  {"user_name": "xander", "answer": "The support team was helpful when I had issues.", "category": "Support", "sentiment": "Positive"},
  {"user_name": "yasmin", "answer": "It's decent, but I prefer other tools for visualization.", "category": "Features", "sentiment": "Neutral"},
  {"user_name": "zane", "answer": "The templates are useful and save setup time.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "abby", "answer": "I had to watch several tutorials before I could use it effectively.", "category": "UX/UI", "sentiment": "Negative"},
  {"user_name": "bruno", "answer": "The real-time data updates are impressive.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "cindy", "answer": "It's too complex for casual users.", "category": "UX/UI", "sentiment": "Negative"},
  {"user_name": "derek", "answer": "I like the alerts feature—it keeps me informed.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "ella", "answer": "The tool feels unfinished. Lots of small bugs.", "category": "Performance", "sentiment": "Negative"},
  {"user_name": "finn", "answer": "It's fast and responsive. No complaints so far.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "gia", "answer": "I wish it had dark mode.", "category": "UX/UI", "sentiment": "Neutral"},
  {"user_name": "harry", "answer": "The report builder is flexible and powerful.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "irene", "answer": "I don't trust the data accuracy sometimes.", "category": "Data Quality & Reliability", "sentiment": "Negative"},
  {"user_name": "jack", "answer": "The onboarding process was smooth and helpful.", "category": "Support", "sentiment": "Positive"},
  {"user_name": "kylie", "answer": "I use it for client reports—it's professional and clean.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "leo", "answer": "The drag-and-drop interface is intuitive.", "category": "UX/UI", "sentiment": "Positive"},
  {"user_name": "mia", "answer": "I've had issues with login and authentication.", "category": "Data Quality & Reliability", "sentiment": "Negative"},
  {"user_name": "noah", "answer": "The analytics are deep and insightful.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "opal", "answer": "It's good, but the pricing is a bit high.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "peter", "answer": "The tool helped us streamline our reporting process.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "quincy", "answer": "I dislike the font choices and layout.", "category": "UX/UI", "sentiment": "Negative"},
  {"user_name": "rose", "answer": "The documentation is thorough and easy to follow.", "category": "Support", "sentiment": "Positive"},
  {"user_name": "steve", "answer": "I had a great experience with the trial version.", "category": "Support", "sentiment": "Positive"},
  {"user_name": "tara", "answer": "The tool doesn't support my preferred file format.", "category": "Features", "sentiment": "Negative"},
  {"user_name": "ursula", "answer": "I love the ability to schedule recurring reports.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "vince", "answer": "The charts are beautiful and customizable.", "category": "Features", "sentiment": "Positive"},
  {"user_name": "wanda", "answer": "It's okay, but I miss some features from our old tool.", "category": "Features", "sentiment": "Neutral"},
  {"user_name": "xenia", "answer": "The tool is very responsive and rarely lags.", "category": "Performance", "sentiment": "Positive"},
  {"user_name": "yuri", "answer": "I had to contact support multiple times for basic issues.", "category": "Support", "sentiment": "Negative"},
  {"user_name": "zoe", "answer": "It's my go-to tool for monthly reporting.", "category": "Performance", "sentiment": "Positive"}
];

// Updated insights based on the real data patterns
export const realCategoryInsights: Record<CategoryType, CategoryInsights> = {
  "UX/UI": {
    observations: [
      "🎨 Mixed feedback on interface design - users appreciate clean visuals but find complexity challenging",
      "📱 Strong positive sentiment for intuitive features like drag-and-drop interface",
      "👥 Learning curve is a common concern, especially for casual users",
      "🎯 Professional appearance is highly valued for client-facing reports"
    ],
    actionableInsights: [
      "🚀 Develop a simplified 'beginner mode' to reduce complexity for new users",
      "📚 Create interactive onboarding tutorials to address the steep learning curve",
      "🌙 Add dark mode option as specifically requested by users",
      "✨ Maintain the professional, clean aesthetic while improving usability"
    ]
  },
  "Performance": {
    observations: [
      "⚡ Strong performance with large datasets and real-time updates",
      "📱 Mobile version has significant stability issues with frequent crashes",
      "🐌 Report loading times are a concern for users with large reports",
      "🏆 Desktop performance is generally reliable and fast"
    ],
    actionableInsights: [
      "📱 Prioritize mobile app stability fixes and crash prevention",
      "⚡ Implement progressive loading for large reports to improve perceived speed",
      "🔧 Optimize chart generation performance to reduce bugs during creation",
      "📊 Consider caching mechanisms for frequently accessed large datasets"
    ]
  },
  "Features": {
    observations: [
      "❤️ Users love automation, scheduling, and customizable features.",
      "⚠️ Some features are missing or limited, like advanced customization, filters, and integrations."
    ],
    actionableInsights: [
      "🔧 Improve advanced customization and filtering.",
      "🔗 Add more export options.",
    ]
  },
  "Support": {
    observations: [
      "👍 Support quality is good when users can reach the team",
      "📖 Documentation is comprehensive and well-structured",
      "⏰ Response time issues with some users needing multiple contacts",
      "🎯 Onboarding process receives positive feedback"
    ],
    actionableInsights: [
      "⚡ Improve support response times and ticket management system",
      "🤖 Implement chatbot or FAQ system for common issues"
    ]
  },
  "Data Quality & Reliability": {
    observations: [
      "🔄 Data syncing issues cause user frustration and trust concerns",
      "🔐 Authentication and login problems affect user experience",
      "👥 Permission and sharing functionality needs improvement",
      "⚠️ Some users question data accuracy, impacting confidence"
    ],
    actionableInsights: [
      "🔧 Investigate and fix data synchronization issues as top priority",
      "🔐 Improve authentication system reliability and user experience",
      "👥 Simplify permission management and team sharing features",
      "✅ Implement data validation indicators to build user trust"
    ]
  }
};