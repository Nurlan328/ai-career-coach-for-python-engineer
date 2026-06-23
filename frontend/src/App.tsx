import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import BillingPage from "./pages/BillingPage";
import DashboardPage from "./pages/DashboardPage";
import InterviewPage from "./pages/InterviewPage";
import LoginPage from "./pages/LoginPage";
import QuestionsPage from "./pages/QuestionsPage";
import RegisterPage from "./pages/RegisterPage";
import ResumePage from "./pages/ResumePage";
import TutorPage from "./pages/TutorPage";
import VacancyPage from "./pages/VacancyPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="resume" element={<ResumePage />} />
        <Route path="vacancy" element={<VacancyPage />} />
        <Route path="questions" element={<QuestionsPage />} />
        <Route path="interview" element={<InterviewPage />} />
        <Route path="tutor" element={<TutorPage />} />
        <Route path="billing" element={<BillingPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
