import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { BackgroundJob, SingleResponse } from '../types';
import { notifications } from '@mantine/notifications';

interface CreateJobPayload {
  project_id: string;
}

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
    onSuccess: (data) => {
      const projectId = data.data.project_id;
      // Invalidate the project query to refetch its status and related jobs
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
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

// The extract-links job has a different payload
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
    onSuccess: (data) => {
      const projectId = data.data.project_id;
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
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
