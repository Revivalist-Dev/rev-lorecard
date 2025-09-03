import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { ProjectSource, SingleResponse } from '../types';
import { notifications } from '@mantine/notifications';

// --- Fetch ---
const fetchProjectSources = async (projectId: string): Promise<ProjectSource[]> => {
  const response = await apiClient.get(`/projects/${projectId}/sources`);
  return response.data;
};

export const useProjectSources = (projectId: string) => {
  return useQuery({
    queryKey: ['sources', projectId],
    queryFn: () => fetchProjectSources(projectId),
    enabled: !!projectId,
  });
};

// --- Create ---
interface CreateSourcePayload {
  url: string;
  max_pages_to_crawl: number;
}

const createProjectSource = async ({
  projectId,
  data,
}: {
  projectId: string;
  data: CreateSourcePayload;
}): Promise<SingleResponse<ProjectSource>> => {
  const response = await apiClient.post(`/projects/${projectId}/sources`, data);
  return response.data;
};

export const useCreateProjectSource = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProjectSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      notifications.show({
        title: 'Source Added',
        message: 'The new source has been added successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to add source: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Update ---
type UpdateSourcePayload = Partial<CreateSourcePayload>;

const updateProjectSource = async ({
  projectId,
  sourceId,
  data,
}: {
  projectId: string;
  sourceId: string;
  data: UpdateSourcePayload;
}): Promise<SingleResponse<ProjectSource>> => {
  const response = await apiClient.patch(`/projects/${projectId}/sources/${sourceId}`, data);
  return response.data;
};

export const useUpdateProjectSource = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProjectSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      notifications.show({
        title: 'Source Updated',
        message: 'The source has been updated successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to update source: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Delete ---
const deleteProjectSource = async ({ projectId, sourceId }: { projectId: string; sourceId: string }): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}/sources/${sourceId}`);
};

export const useDeleteProjectSource = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProjectSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      notifications.show({
        title: 'Source Deleted',
        message: 'The source has been successfully deleted.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete source: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
