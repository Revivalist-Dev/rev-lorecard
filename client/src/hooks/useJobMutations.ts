import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { BackgroundJob, PaginatedResponse, SingleResponse } from '../types';
import { notifications } from '@mantine/notifications';

interface CreateJobPayload {
  project_id: string;
}

const optimisticallyAddNewJob = (queryClient: ReturnType<typeof useQueryClient>, newJob: BackgroundJob) => {
  const projectId = newJob.project_id;
  const queryKey = ['jobs', projectId];

  // Immediately update the 'jobs' query cache
  queryClient.setQueryData<PaginatedResponse<BackgroundJob>>(queryKey, (oldData) => {
    // If there's no old data, create a new structure
    if (!oldData) {
      return {
        data: [newJob],
        meta: { current_page: 1, per_page: 200, total_items: 1 },
      };
    }

    return {
      ...oldData,
      data: [newJob, ...oldData.data],
      meta: {
        ...oldData.meta,
        total_items: oldData.meta.total_items + 1,
      },
    };
  });
};

const createJob =
  (endpoint: string) =>
  async (payload: CreateJobPayload): Promise<SingleResponse<BackgroundJob>> => {
    const response = await apiClient.post(`/jobs/${endpoint}`, payload);
    return response.data;
  };

const useJobMutation = (endpoint: string, notificationTitle: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createJob(endpoint),
    onSuccess: (response) => {
      const newJob = response.data;

      optimisticallyAddNewJob(queryClient, newJob);

      queryClient.invalidateQueries({ queryKey: ['project', newJob.project_id] });

      notifications.show({
        title: notificationTitle,
        message: 'The background job has been started successfully.',
        color: 'blue',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to start job: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

export const useGenerateSearchParamsJob = () =>
  useJobMutation('generate-search-params', 'Search Parameter Generation Started');
export const useGenerateSelectorJob = () => useJobMutation('generate-selector', 'Selector Generation Started');
export const useProcessProjectEntriesJob = () =>
  useJobMutation('process-project-entries', 'Lorebook Generation Started');

// The extract-links job has a different payload but can use the same logic
interface ExtractLinksPayload {
  project_id: string;
  urls: string[];
}
const createExtractLinksJob = async (payload: ExtractLinksPayload): Promise<SingleResponse<BackgroundJob>> => {
  const response = await apiClient.post('/jobs/extract-links', payload);
  return response.data;
};

export const useExtractLinksJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createExtractLinksJob,
    onSuccess: (response) => {
      const newJob = response.data;

      optimisticallyAddNewJob(queryClient, newJob);

      queryClient.invalidateQueries({ queryKey: ['project', newJob.project_id] });

      notifications.show({
        title: 'Link Extraction Started',
        message: 'The links are being saved to the project.',
        color: 'blue',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to extract links: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

const cancelJob = async (jobId: string): Promise<SingleResponse<BackgroundJob>> => {
  const response = await apiClient.post(`/jobs/${jobId}/cancel`);
  return response.data;
};

export const useCancelJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelJob,
    onSuccess: (data) => {
      const projectId = data.data.project_id;
      queryClient.invalidateQueries({ queryKey: ['jobs', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      notifications.show({
        title: 'Cancellation Requested',
        message: 'The job cancellation request has been sent.',
        color: 'yellow',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to cancel job: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
