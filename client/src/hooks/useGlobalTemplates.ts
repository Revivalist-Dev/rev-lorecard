import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { GlobalTemplate, PaginatedResponse } from '../types';

interface TemplatesQuery {
  page: number;
  pageSize: number;
}

const fetchGlobalTemplates = async ({ page, pageSize }: TemplatesQuery): Promise<PaginatedResponse<GlobalTemplate>> => {
  const offset = (page - 1) * pageSize;
  const response = await apiClient.get('/global-templates', {
    params: { limit: pageSize, offset },
  });
  return response.data;
};

export const useGlobalTemplates = ({ page, pageSize }: TemplatesQuery) => {
  return useQuery({
    queryKey: ['globalTemplates', { page, pageSize }],
    queryFn: () => fetchGlobalTemplates({ page, pageSize }),
  });
};
