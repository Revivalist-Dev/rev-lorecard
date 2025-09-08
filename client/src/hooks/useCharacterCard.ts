import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { CharacterCard, SingleResponse, UpdateCharacterCardPayload } from '../types';
import { notifications } from '@mantine/notifications';

// --- Fetch ---
const fetchCharacterCard = async (projectId: string): Promise<SingleResponse<CharacterCard>> => {
  const response = await apiClient.get(`/projects/${projectId}/character`);
  return response.data;
};

export const useCharacterCard = (projectId: string) => {
  return useQuery({
    queryKey: ['characterCard', projectId],
    queryFn: () => fetchCharacterCard(projectId),
    enabled: !!projectId,
  });
};

// --- Update ---
const updateCharacterCard = async ({
  projectId,
  data,
}: {
  projectId: string;
  data: UpdateCharacterCardPayload;
}): Promise<SingleResponse<CharacterCard>> => {
  const response = await apiClient.patch(`/projects/${projectId}/character`, data);
  return response.data;
};

export const useUpdateCharacterCard = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateCharacterCard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characterCard', projectId] });
      notifications.show({
        title: 'Character Saved',
        message: 'Your changes have been saved successfully.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to save character: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
