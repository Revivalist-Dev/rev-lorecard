// client/src/hooks/useProjectEntries.ts
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { LorebookEntry, PaginatedResponse } from '../types';

interface EntriesQuery {
  page: number;
  pageSize: number;
}

const fetchProjectEntries = async (
  projectId: string,
  { page, pageSize }: EntriesQuery
): Promise<PaginatedResponse<LorebookEntry>> => {
  const offset = (page - 1) * pageSize;
  const response = await apiClient.get(`/projects/${projectId}/entries`, {
    params: { limit: pageSize, offset },
  });
  return response.data;
};

export const useProjectEntries = (projectId: string, { page, pageSize }: EntriesQuery) => {
  return useQuery({
    queryKey: ['entries', projectId, { page, pageSize }],
    queryFn: () => fetchProjectEntries(projectId, { page, pageSize }),
    enabled: !!projectId,
  });
};
