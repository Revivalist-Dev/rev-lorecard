import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { ProjectAnalytics, SingleResponse } from '../types';

const fetchProjectAnalytics = async (projectId: string): Promise<SingleResponse<ProjectAnalytics>> => {
  const response = await apiClient.get(`/analytics/projects/${projectId}`);
  return response.data;
};

export const useProjectAnalytics = (projectId: string) => {
  return useQuery({
    queryKey: ['projectAnalytics', projectId],
    queryFn: () => fetchProjectAnalytics(projectId),
    enabled: !!projectId,
  });
};
