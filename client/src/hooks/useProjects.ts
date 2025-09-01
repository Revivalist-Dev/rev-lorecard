import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { PaginatedResponse, Project, SingleResponse } from '../types';

// Fetch all projects
const fetchProjects = async (): Promise<PaginatedResponse<Project>> => {
  const response = await apiClient.get('/projects');
  return response.data;
};

export const useProjects = () => {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });
};

const fetchProject = async (projectId: string): Promise<SingleResponse<Project>> => {
  const response = await apiClient.get(`/projects/${projectId}`);
  return response.data;
};

export const useProject = (projectId: string) => {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => fetchProject(projectId),
    enabled: !!projectId, // Only run the query if projectId is available
  });
};
