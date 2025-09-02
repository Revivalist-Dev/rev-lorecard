import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import { notifications } from '@mantine/notifications';

const deleteLorebookEntry = async (entryId: string): Promise<void> => {
  await apiClient.delete(`/entries/${entryId}`);
};

export const useDeleteLorebookEntry = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteLorebookEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entries', projectId] });
      notifications.show({
        title: 'Entry Deleted',
        message: 'The lorebook entry has been successfully deleted.',
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete entry: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
