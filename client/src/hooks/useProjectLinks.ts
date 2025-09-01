import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { Link, PaginatedResponse } from '../types';

interface LinksQuery {
  page: number;
  pageSize: number;
}

const fetchProjectLinks = async (
  projectId: string,
  { page, pageSize }: LinksQuery
): Promise<PaginatedResponse<Link>> => {
  const offset = (page - 1) * pageSize;
  const response = await apiClient.get(`/projects/${projectId}/links`, {
    params: { limit: pageSize, offset },
  });
  return response.data;
};

export const useProjectLinks = (projectId: string, { page, pageSize }: LinksQuery) => {
  return useQuery({
    queryKey: ['links', projectId, { page, pageSize }],
    queryFn: () => fetchProjectLinks(projectId, { page, pageSize }),
    enabled: !!projectId,
  });
};
