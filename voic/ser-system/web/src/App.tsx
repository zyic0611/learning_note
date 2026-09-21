import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import AnalysisPage from './pages/AnalysisPage';
import EvaluationPage from './pages/EvaluationPage';
import RealtimePage from './pages/RealtimePage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/realtime" replace />} />
        <Route path="/realtime" element={<RealtimePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/realtime" replace />} />
    </Routes>
  );
}
