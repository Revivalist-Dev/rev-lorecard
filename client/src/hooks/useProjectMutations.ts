import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { Project, SingleResponse, CreateProjectPayload } from '../types';
import { notifications } from '@mantine/notifications';
import { useNavigate } from 'react-router-dom';

// Types for mutation
type UpdateProjectPayload = Partial<CreateProjectPayload>;

// Create a new project
const createProject = async (projectData: CreateProjectPayload): Promise<SingleResponse<Project>> => {
  const response = await apiClient.post('/projects', projectData);
  return response.data;
};

export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      notifications.show({
        title: 'Project Created',
        message: 'The new project has been created successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to create project: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// Update an existing project
const updateProject = async ({
  projectId,
  data,
}: {
  projectId: string;
  data: UpdateProjectPayload;
}): Promise<SingleResponse<Project>> => {
  const response = await apiClient.patch(`/projects/${projectId}`, data);
  return response.data;
};

export const useUpdateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateProject,
    onSuccess: (data) => {
      const projectId = data.data.id;
      // Invalidate both the list of projects and the specific project query
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      notifications.show({
        title: 'Project Updated',
        message: 'The project has been updated successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to update project: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

const deleteProject = async (projectId: string): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}`);
};

export const useDeleteProject = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: deleteProject,
    onSuccess: (_, deletedProjectId) => {
      // Remove the specific project query if it exists
      queryClient.removeQueries({ queryKey: ['project', deletedProjectId] });
      // Invalidate the list of all projects to refetch it
      queryClient.invalidateQueries({ queryKey: ['projects'] });

      notifications.show({
        title: 'Project Deleted',
        message: 'The project has been successfully deleted.',
        color: 'green',
      });

      // Navigate to the home page if the user was on the deleted project's page
      if (window.location.pathname.includes(`/projects/${deletedProjectId}`)) {
        navigate('/');
      }
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete project: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
