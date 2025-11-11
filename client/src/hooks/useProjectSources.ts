import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type {
  ProjectSource,
  ProjectSourceHierarchy,
  SingleResponse,
  TestSelectorsPayload,
  TestSelectorsResult,
  SourceType,
  BackgroundJob,
  SourceContentVersion,
  ContentType,
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

// --- Fetch Single Source Details ---
const fetchProjectSourceDetails = async (
  projectId: string,
  sourceId: string
): Promise<SingleResponse<ProjectSource>> => {
  const response = await apiClient.get(`/projects/${projectId}/sources/${sourceId}`);
  return response.data;
};

export const useProjectSourceDetails = (projectId: string, sourceId: string | null) => {
  return useQuery({
    queryKey: ['sourceDetails', projectId, sourceId],
    queryFn: () => fetchProjectSourceDetails(projectId, sourceId!),
    enabled: !!projectId && !!sourceId, // Only run when a sourceId is provided
    // Disable automatic refetching to prevent state reset while editing
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
};

// --- Fetch Source Versions ---
const fetchSourceVersions = async (projectId: string, sourceId: string): Promise<SourceContentVersion[]> => {
  const response = await apiClient.get(`/projects/${projectId}/sources/${sourceId}/versions`);
  return response.data;
};

export const useSourceVersions = (projectId: string, sourceId: string | null) => {
  return useQuery({
    queryKey: ['sourceVersions', projectId, sourceId],
    queryFn: () => fetchSourceVersions(projectId, sourceId!),
    enabled: !!projectId && !!sourceId,
  });
};

// --- Restore Source Version ---
const restoreSourceVersion = async ({
  projectId,
  sourceId,
  versionId,
}: {
  projectId: string;
  sourceId: string;
  versionId: string;
}): Promise<SingleResponse<ProjectSource>> => {
  const response = await apiClient.post(
    `/projects/${projectId}/sources/${sourceId}/versions/${versionId}/restore`
  );
  return response.data;
};

export const useRestoreSourceVersion = (projectId: string, sourceId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: restoreSourceVersion,
    onSuccess: () => {
      // Invalidate source details to refetch the newly restored content
      queryClient.invalidateQueries({ queryKey: ['sourceDetails', projectId, sourceId] });
      queryClient.invalidateQueries({ queryKey: ['sourceVersions', projectId, sourceId] });
      notifications.show({
        title: 'Version Restored',
        message: 'The source content has been successfully restored.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to restore version: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Delete Source Version ---
const deleteSourceVersion = async ({
  projectId,
  sourceId,
  versionId,
}: {
  projectId: string;
  sourceId: string;
  versionId: string;
}): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}/sources/${sourceId}/versions/${versionId}`);
};

export const useDeleteSourceVersion = (projectId: string, sourceId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSourceVersion,
    onSuccess: () => {
      // Invalidate source versions list
      queryClient.invalidateQueries({ queryKey: ['sourceVersions', projectId, sourceId] });
      notifications.show({
        title: 'Version Deleted',
        message: 'The source content version has been successfully deleted.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete version: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Clear Source History ---
const clearSourceHistory = async ({
  projectId,
  sourceId,
}: {
  projectId: string;
  sourceId: string;
}): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/sources/${sourceId}/versions/clear-history`);
};

export const useClearSourceHistory = (projectId: string, sourceId: string | null) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: clearSourceHistory,
    onSuccess: () => {
      // Invalidate source versions list
      queryClient.invalidateQueries({ queryKey: ['sourceVersions', projectId, sourceId] });
      notifications.show({
        title: 'History Cleared',
        message: 'Source history has been cleared (keeping only the latest version).',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to clear history: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Create ---
interface CreateSourcePayload {
  source_type: SourceType;
  url: string;
  raw_content?: string;
  content_type?: ContentType;
  max_pages_to_crawl?: number;
  max_crawl_depth?: number;
  url_exclusion_patterns?: string[];
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

// --- AI Edit Source Content ---
interface AiEditSourceContentVariables {
  projectId: string;
  data: {
    source_id: string;
    original_content: string;
    edit_instruction: string;
    full_content_context?: string;
  };
}

const aiEditSourceContent = async ({
  projectId,
  data,
}: AiEditSourceContentVariables): Promise<SingleResponse<BackgroundJob>> => {
  const response = await apiClient.post(`/projects/${projectId}/sources/ai-edit`, data);
  return response.data;
};

export const useAiEditSourceContent = () => {
  return useMutation({
    mutationFn: aiEditSourceContent,
    // No onSuccess notification needed here, as the modal handles the result directly
  });
};
