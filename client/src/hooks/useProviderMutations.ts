import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { ModelInfo, TestCredentialPayload, TestCredentialResult } from '../types';
import { notifications } from '@mantine/notifications';

const testCredential = async (data: TestCredentialPayload): Promise<TestCredentialResult> => {
  const response = await apiClient.post('/providers/test', data);
  return response.data;
};

export const useTestCredential = () => {
  return useMutation({
    mutationFn: testCredential,
    onSuccess: (data) => {
      notifications.show({
        title: 'Success',
        message: data.message,
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Test Failed',
        message: `Error: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};

const fetchProviderModels = async (data: TestCredentialPayload): Promise<ModelInfo[]> => {
  const response = await apiClient.post('/providers/models', data);
  return response.data;
};

export const useFetchProviderModels = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fetchProviderModels,
    onSuccess: () => {
      // We still invalidate this so that the global state is updated if the user saves.
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Failed to Fetch Models',
        message: `Error: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
