export interface User {
  id: number;
  email: string;
  full_name: string | null;
  level: string | null;
  subscription_plan: string;
  created_at: string;
}

export interface ResumeOut {
  id: number;
  filename: string;
  ai_summary: string | null;
  detected_level: string | null;
  skills: string[] | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
  recommendations: string[] | null;
  created_at: string;
}

export interface GeneratedQuestion {
  question_text: string;
  category: string;
  difficulty: string;
  expected_answer: string | null;
}

export interface QuestionGenResponse {
  category: string;
  level: string;
  source: string;
  questions: GeneratedQuestion[];
}

export interface QuestionOut {
  id: number;
  order_index: number;
  question_text: string;
  category: string;
  difficulty: string;
  answered: boolean;
}

export interface InterviewOut {
  id: number;
  type: string;
  level: string;
  category: string;
  status: string;
  total_score: number | null;
  created_at: string;
  questions: QuestionOut[];
}

export interface AnswerFeedback {
  score: number;
  strengths: string[];
  weaknesses: string[];
  missing_topics: string[];
  ideal_answer: string;
}

export interface AnswerResponse {
  question_id: number;
  feedback: AnswerFeedback;
  next_question: QuestionOut | null;
  interview_completed: boolean;
  interview_total_score: number | null;
}

export interface InterviewListItem {
  id: number;
  type: string;
  level: string;
  category: string;
  status: string;
  total_score: number | null;
  created_at: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface PlanOut {
  id: string;
  label: string;
  price_usd: number;
  interviews_per_month: number | null;
}

export interface UsageOut {
  plan: string; // plan in force right now
  purchased_plan: string; // what was bought (differs while past_due)
  interviews_used: number;
  interviews_limit: number | null;
  status: string | null; // Stripe subscription status
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  manageable: boolean; // Stripe portal available
  stripe_enabled: boolean;
}

export interface CheckoutResponse {
  mock: boolean;
  plan?: string | null;
  checkout_url?: string | null;
}

export interface PortalResponse {
  portal_url: string;
}

export interface RagSource {
  title: string;
  source: string;
  snippet: string;
  score: number;
}

export interface RagResponse {
  question: string;
  answer: string;
  source: string;
  sources: RagSource[];
}

export interface VacancyOut {
  id: number;
  title: string | null;
  company: string | null;
  required_skills: string[] | null;
  ai_summary: string | null;
  created_at: string;
}

export interface GapAnalysis {
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  topics_to_study: string[];
  summary: string;
}

export interface RoadmapWeek {
  week: number;
  focus: string;
  topics: string[];
  resources: string[];
}

export interface Roadmap {
  level: string;
  summary: string;
  weeks: RoadmapWeek[];
}
