import { Notifications } from '@mantine/notifications';
import { Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { GlobalTemplatesPage } from './pages/GlobalTemplatesPage';
import { CredentialsPage } from './pages/CredentialsPage';

export default function App() {
  return (
    <>
      <Notifications zIndex={9999} />
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/templates" element={<GlobalTemplatesPage />} />
          <Route path="/credentials" element={<CredentialsPage />} />
        </Route>
      </Routes>
    </>
  );
}
