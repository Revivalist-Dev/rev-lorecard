import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { BackgroundJob, PaginatedResponse, TaskName, SingleResponse } from '../types';

const fetchProjectJobs = async (projectId: string): Promise<PaginatedResponse<BackgroundJob>> => {
  const response = await apiClient.get(`/jobs?project_id=${projectId}&limit=200`);
  return response.data;
};

const fetchLatestProjectJob = async (projectId: string, taskName: TaskName): Promise<SingleResponse<BackgroundJob>> => {
  const response = await apiClient.get(`/jobs/latest`, {
    params: { project_id: projectId, task_name: taskName },
  });
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
  const { data, ...queryInfo } = useQuery({
    queryKey: ['latestJob', projectId, taskName],
    queryFn: () => fetchLatestProjectJob(projectId, taskName),
    enabled: !!projectId,
    // Job status must be fresh. We rely on invalidation, but remove restrictive caching
    // to ensure status updates are picked up if invalidation is missed or delayed.
    // Setting staleTime to 0 ensures it refetches on every mount/focus.
    staleTime: 0,
    // It's common for no job to exist yet, so a 404 is not a true "error" state
    // that should cause retries. We'll handle it gracefully.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // If there's a 404 error, we treat it as "no job found" and return undefined.
  // The query will be in an `error` state, but the component using the hook
  // will see `job: undefined` and render correctly.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const job = queryInfo.isError && (queryInfo.error as any)?.response?.status === 404 ? undefined : data?.data;

  return { job, ...queryInfo };
};
