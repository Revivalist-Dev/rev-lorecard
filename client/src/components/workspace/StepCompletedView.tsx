import { useState, useEffect } from 'react';
import { Stack, Text, Button, Group, Table, Loader, Alert, Title, ActionIcon, Pagination } from '@mantine/core';
import { IconAlertCircle, IconDownload, IconTrash } from '@tabler/icons-react';
import { useProjectEntries } from '../../hooks/useProjectEntries';
import type { Project } from '../../types';
import apiClient from '../../services/api';
import { notifications } from '@mantine/notifications';
import { useModals } from '@mantine/modals';
import { useDeleteLorebookEntry } from '../../hooks/useLorebookEntryMutations';
import { useSearchParams } from 'react-router-dom';

interface StepCompletedViewProps {
  project: Project;
}

const PAGE_SIZE = 50;
const URL_PARAM_KEY = 'entries_page';

export function StepCompletedView({ project }: StepCompletedViewProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);

  const {
    data: entriesResponse,
    isLoading,
    isError,
    error,
  } = useProjectEntries(project.id, { page: activePage, pageSize: PAGE_SIZE });

  useEffect(() => {
    const newPageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
    const validPage = isNaN(newPageFromUrl) ? 1 : newPageFromUrl;
    if (validPage !== activePage) {
      setPage(validPage);
    }
  }, [searchParams, activePage]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSearchParams(
      (prev) => {
        prev.set(URL_PARAM_KEY, newPage.toString());
        return prev;
      },
      { replace: true }
    );
  };

  const [isDownloading, setIsDownloading] = useState(false);
  const modals = useModals();
  const deleteEntryMutation = useDeleteLorebookEntry(project.id);

  const openDeleteModal = (entryId: string, entryTitle: string) =>
    modals.openConfirmModal({
      title: 'Delete Lorebook Entry',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete the entry "<strong>{entryTitle}</strong>"? This action is irreversible.
        </Text>
      ),
      labels: { confirm: 'Delete Entry', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => deleteEntryMutation.mutate(entryId),
    });

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const response = await apiClient.get(`/projects/${project.id}/lorebook/download`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${project.id}.json`);
      document.body.appendChild(link);
      link.click();

      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      notifications.show({
        title: 'Download Started',
        message: 'Your lorebook is being downloaded.',
        color: 'green',
      });
    } catch (err) {
      console.error('Download failed:', err);
      notifications.show({
        title: 'Download Failed',
        message: 'Could not download the lorebook file.',
        color: 'red',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  if (isLoading) {
    return <Loader />;
  }

  if (isError) {
    return (
      <Alert icon={<IconAlertCircle size="1rem" />} title="Error!" color="red">
        Failed to load lorebook entries: {error.message}
      </Alert>
    );
  }

  const entries = entriesResponse?.data || [];
  const totalItems = entriesResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  return (
    <Stack mt="md">
      <Group justify="space-between">
        <Title order={3}>Lorebook Generation Complete</Title>
        <Button
          leftSection={<IconDownload size={16} />}
          onClick={handleDownload}
          loading={isDownloading}
          disabled={totalItems === 0}
        >
          Download Lorebook
        </Button>
      </Group>

      <Text c="dimmed">
        {totalItems} entries have been successfully generated for this project. You can review them below or download
        the final JSON file.
      </Text>

      <Table striped highlightOnHover withTableBorder withColumnBorders>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Title</Table.Th>
            <Table.Th>Keywords</Table.Th>
            <Table.Th>Content Snippet</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {entries.map((entry) => (
            <Table.Tr key={entry.id}>
              <Table.Td>{entry.title}</Table.Td>
              <Table.Td>{entry.keywords.join(', ')}</Table.Td>
              <Table.Td>
                <Text lineClamp={2}>{entry.content}</Text>
              </Table.Td>
              <Table.Td>
                <Group gap="xs" justify="center">
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => openDeleteModal(entry.id, entry.title)}
                    loading={deleteEntryMutation.isPending && deleteEntryMutation.variables === entry.id}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {totalItems === 0 && (
        <Text c="dimmed" ta="center" p="md">
          No entries were generated.
        </Text>
      )}

      {totalPages > 1 && (
        <Group justify="center" mt="md">
          <Pagination value={activePage} onChange={handlePageChange} total={totalPages} />
        </Group>
      )}
    </Stack>
  );
}
