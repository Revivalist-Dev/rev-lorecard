import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { ApiRequestLog, PaginatedResponse } from '../types';

interface LogsQuery {
  page: number;
  pageSize: number;
}

const fetchProjectApiLogs = async (
  projectId: string,
  { page, pageSize }: LogsQuery
): Promise<PaginatedResponse<ApiRequestLog>> => {
  const offset = (page - 1) * pageSize;
  const response = await apiClient.get(`/projects/${projectId}/logs`, {
    params: { limit: pageSize, offset },
  });
  return response.data;
};

export const useProjectApiRequestLogs = (projectId: string, { page, pageSize }: LogsQuery) => {
  return useQuery({
    queryKey: ['apiRequestLogs', projectId, { page, pageSize }],
    queryFn: () => fetchProjectApiLogs(projectId, { page, pageSize }),
    enabled: !!projectId,
  });
};
