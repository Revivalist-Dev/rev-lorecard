import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { Credential, CreateCredentialPayload, SingleResponse, UpdateCredentialPayload } from '../types';
import { notifications } from '@mantine/notifications';

// --- Create ---
const createCredential = async (data: CreateCredentialPayload): Promise<SingleResponse<Credential>> => {
  const response = await apiClient.post('/credentials', data);
  return response.data;
};

export const useCreateCredential = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCredential,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      notifications.show({
        title: 'Credential Created',
        message: 'The new credential has been created successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to create credential: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Update ---
const updateCredential = async ({
  credentialId,
  data,
}: {
  credentialId: string;
  data: UpdateCredentialPayload;
}): Promise<SingleResponse<Credential>> => {
  const response = await apiClient.patch(`/credentials/${credentialId}`, data);
  return response.data;
};

export const useUpdateCredential = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateCredential,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      notifications.show({
        title: 'Credential Updated',
        message: 'The credential has been updated successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to update credential: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

// --- Delete ---
const deleteCredential = async (credentialId: string): Promise<void> => {
  await apiClient.delete(`/credentials/${credentialId}`);
};

export const useDeleteCredential = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCredential,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      notifications.show({
        title: 'Credential Deleted',
        message: 'The credential has been successfully deleted.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete credential: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
