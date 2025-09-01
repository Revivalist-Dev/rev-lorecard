import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { BackgroundJob, PaginatedResponse, TaskName } from '../types';

const fetchProjectJobs = async (projectId: string): Promise<PaginatedResponse<BackgroundJob>> => {
  const response = await apiClient.get(`/jobs?project_id=${projectId}&limit=200`);
  return response.data;
};

export const useProjectJobs = (projectId: string) => {
  return useQuery({
    queryKey: ['jobs', projectId],
    queryFn: () => fetchProjectJobs(projectId),
    enabled: !!projectId,
  });
};

// A derived hook to easily find the latest job of a specific type
export const useLatestJob = (projectId: string, taskName: TaskName) => {
  const { data: jobsResponse, ...queryInfo } = useProjectJobs(projectId);

  const latestJob = jobsResponse?.data
    .filter((job) => job.task_name === taskName)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

  return { job: latestJob, ...queryInfo };
};
