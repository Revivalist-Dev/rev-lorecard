import { Notifications } from '@mantine/notifications';
import { Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { GlobalTemplatesPage } from './pages/GlobalTemplatesPage';

export default function App() {
  return (
    <>
      <Notifications />
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/templates" element={<GlobalTemplatesPage />} />
        </Route>
      </Routes>
    </>
  );
}
