import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type {
  ProjectSource,
  ProjectSourceHierarchy,
  SingleResponse,
  TestSelectorsPayload,
  TestSelectorsResult,
} from '../types';
import { notifications } from '@mantine/notifications';

// --- Fetch ---
const fetchProjectSources = async (projectId: string): Promise<ProjectSource[]> => {
  const response = await apiClient.get(`/projects/${projectId}/sources`);
  return response.data;
};

const fetchProjectSourceHierarchy = async (projectId: string): Promise<ProjectSourceHierarchy[]> => {
  const response = await apiClient.get(`/projects/${projectId}/sources/hierarchy`);
  return response.data;
};

export const useProjectSources = (projectId: string) => {
  return useQuery({
    queryKey: ['sources', projectId],
    queryFn: () => fetchProjectSources(projectId),
    enabled: !!projectId,
  });
};

export const useProjectSourceHierarchy = (projectId: string) => {
  return useQuery({
    queryKey: ['sourcesHierarchy', projectId],
    queryFn: () => fetchProjectSourceHierarchy(projectId),
    enabled: !!projectId,
  });
};

// --- Create ---
interface CreateSourcePayload {
  url: string;
  max_pages_to_crawl: number;
  max_crawl_depth: number;
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
      queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', projectId] });
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
type UpdateSourcePayload = Partial<CreateSourcePayload> & {
  link_extraction_selector?: string[];
  link_extraction_pagination_selector?: string;
};

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
      queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', projectId] });
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
      queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', projectId] });
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

// --- Bulk Delete ---
interface BulkDeletePayload {
  projectId: string;
  source_ids: string[];
}
const deleteProjectSourcesBulk = async ({ projectId, source_ids }: BulkDeletePayload): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/sources/delete-bulk`, { source_ids });
};

export const useDeleteProjectSourcesBulk = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProjectSourcesBulk,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] });
      queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', projectId] });
      notifications.show({
        title: 'Sources Deleted',
        message: `${variables.source_ids.length} sources have been successfully deleted.`,
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete sources: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Test Selectors ---
const testProjectSourceSelectors = async ({
  projectId,
  data,
}: {
  projectId: string;
  data: TestSelectorsPayload;
}): Promise<TestSelectorsResult> => {
  const response = await apiClient.post(`/projects/${projectId}/sources/test-selectors`, data);
  return response.data;
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const useTestProjectSourceSelectors = (_projectId: string) => {
  return useMutation({
    mutationFn: testProjectSourceSelectors,
  });
};
