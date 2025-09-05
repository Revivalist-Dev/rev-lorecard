import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { LorebookEntry, PaginatedResponse } from '../types';

interface EntriesQuery {
  page: number;
  pageSize: number;
  searchQuery?: string;
}

const fetchProjectEntries = async (
  projectId: string,
  { page, pageSize, searchQuery }: EntriesQuery
): Promise<PaginatedResponse<LorebookEntry>> => {
  const offset = (page - 1) * pageSize;
  const response = await apiClient.get(`/projects/${projectId}/entries`, {
    params: { limit: pageSize, offset, q: searchQuery },
  });
  return response.data;
};

export const useProjectEntries = (projectId: string, { page, pageSize, searchQuery }: EntriesQuery) => {
  return useQuery({
    queryKey: ['entries', projectId, { page, pageSize, searchQuery }],
    queryFn: () => fetchProjectEntries(projectId, { page, pageSize, searchQuery }),
    enabled: !!projectId,
  });
};
