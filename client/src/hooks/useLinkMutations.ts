import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import { notifications } from '@mantine/notifications';

interface BulkDeleteLinksPayload {
  projectId: string;
  link_ids: string[];
}

const deleteLinksBulk = async ({ projectId, link_ids }: BulkDeleteLinksPayload): Promise<void> => {
  await apiClient.post(`/projects/${projectId}/links/delete-bulk`, { link_ids });
};

export const useDeleteLinksBulk = (projectId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteLinksBulk,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['links', projectId] });
      notifications.show({
        title: 'Links Deleted',
        message: `${variables.link_ids.length} links have been successfully deleted.`,
        color: 'green',
      });
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      notifications.show({
        title: 'Error',
        message: `Failed to delete links: ${error.response?.data?.detail || error.message}`,
        color: 'red',
      });
    },
  });
};
