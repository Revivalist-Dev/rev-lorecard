import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { GlobalTemplate, SingleResponse } from '../types';
import { notifications } from '@mantine/notifications';

// Types for mutation payloads
interface CreateTemplatePayload {
  id: string;
  name: string;
  content: string;
}

type UpdateTemplatePayload = Partial<Omit<CreateTemplatePayload, 'id'>>;

// --- Create ---
const createGlobalTemplate = async (templateData: CreateTemplatePayload): Promise<SingleResponse<GlobalTemplate>> => {
  const response = await apiClient.post('/global-templates', templateData);
  return response.data;
};

export const useCreateGlobalTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createGlobalTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalTemplates'] });
      notifications.show({
        title: 'Template Created',
        message: 'The new global template has been created successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to create template: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Update ---
const updateGlobalTemplate = async ({
  templateId,
  data,
}: {
  templateId: string;
  data: UpdateTemplatePayload;
}): Promise<SingleResponse<GlobalTemplate>> => {
  const response = await apiClient.patch(`/global-templates/${templateId}`, data);
  return response.data;
};

export const useUpdateGlobalTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateGlobalTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalTemplates'] });
      notifications.show({
        title: 'Template Updated',
        message: 'The template has been updated successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to update template: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Delete ---
const deleteGlobalTemplate = async (templateId: string): Promise<void> => {
  await apiClient.delete(`/global-templates/${templateId}`);
};

export const useDeleteGlobalTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteGlobalTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalTemplates'] });
      notifications.show({
        title: 'Template Deleted',
        message: 'The template has been successfully deleted.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete template: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
