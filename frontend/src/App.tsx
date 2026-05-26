import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import RequireAuth from './components/RequireAuth';
import LoginPage from './pages/Login';
import DashboardPage from './pages/Dashboard';
import GasTurbinesPage from './pages/GasTurbines';
import CCUnitsPage from './pages/CCUnits';
import PerformancePage from './pages/Performance';
import DegradationPage from './pages/Degradation';
import AlertsPage from './pages/Alerts';
import UsersPage from './pages/Users';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="gas-turbines" element={<GasTurbinesPage />} />
          <Route path="cc-units" element={<CCUnitsPage />} />
          <Route path="performance" element={<PerformancePage />} />
          <Route path="degradation" element={<DegradationPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="users" element={<UsersPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
