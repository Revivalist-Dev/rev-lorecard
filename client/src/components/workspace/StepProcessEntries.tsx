import { useState, useEffect, useMemo } from 'react';
import {
  Stack,
  Text,
  Button,
  Group,
  Table,
  Badge,
  Pagination,
  Tooltip,
  Loader,
  Checkbox,
  Modal,
  Textarea,
} from '@mantine/core';
import { useProcessProjectEntriesJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useSearchParams } from 'react-router-dom';
import { useModals } from '@mantine/modals';
import apiClient from '../../services/api';
import { notifications } from '@mantine/notifications';
import { IconPlayerPlay, IconTrash, IconPlus } from '@tabler/icons-react';
import { useDeleteLinksBulk } from '../../hooks/useLinkMutations';
import { useDisclosure } from '@mantine/hooks';
import { useConfirmLinksJob } from '../../hooks/useJobMutations';

interface StepProps {
  project: Project;
}

const PAGE_SIZE = 50;
const URL_PARAM_KEY = 'processing_page';

const statusColors: Record<string, string> = {
  pending: 'gray',
  processing: 'yellow',
  completed: 'green',
  failed: 'red',
  skipped: 'yellow',
};

function AddLinksModal({
  opened,
  onClose,
  onAdd,
}: {
  opened: boolean;
  onClose: () => void;
  onAdd: (urls: string[]) => void;
}) {
  const [urlsToAdd, setUrlsToAdd] = useState('');
  const urls = useMemo(
    () =>
      urlsToAdd
        .split('\n')
        .map((url) => url.trim())
        .filter(Boolean),
    [urlsToAdd]
  );

  const handleAdd = () => {
    if (urls.length > 0) {
      onAdd(urls);
    }
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Add Manual Links" centered>
      <Stack>
        <Textarea
          label="Links"
          description="Enter one URL per line."
          placeholder="https://example.com/page1&#10;https://example.com/page2"
          autosize
          minRows={4}
          value={urlsToAdd}
          onChange={(e) => setUrlsToAdd(e.currentTarget.value)}
        />
        <Button onClick={handleAdd} disabled={urls.length === 0}>
          Add {urls.length} Links
        </Button>
      </Stack>
    </Modal>
  );
}

export function StepProcessEntries({ project }: StepProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);
  const [isFetchingCount, setIsFetchingCount] = useState(false);
  const modals = useModals();
  const [addLinksModalOpened, { open: openAddLinksModal, close: closeAddLinksModal }] = useDisclosure(false);
  const confirmLinks = useConfirmLinksJob();

  const startGeneration = useProcessProjectEntriesJob();
  const { job: processingJob } = useLatestJob(project.id, 'process_project_entries');
  const { data: linksResponse, isLoading: isLoadingLinks } = useProjectLinks(project.id, {
    page: activePage,
    pageSize: PAGE_SIZE,
  });

  const [selectedLinkIds, setSelectedLinkIds] = useState<string[]>([]);
  const deleteLinksMutation = useDeleteLinksBulk(project.id);
  const processEntriesMutation = useProcessProjectEntriesJob();

  useEffect(() => {
    const newPageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
    const validPage = isNaN(newPageFromUrl) ? 1 : newPageFromUrl;
    if (validPage !== activePage) {
      setPage(validPage);
    }
  }, [searchParams, activePage]);

  // Reset selection when page changes
  useEffect(() => {
    setSelectedLinkIds([]);
  }, [activePage, linksResponse]);

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

  const links = useMemo(() => linksResponse?.data || [], [linksResponse]);
  const totalItems = linksResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);
  const isJobActive = processingJob?.status === 'pending' || processingJob?.status === 'in_progress';

  const processableSelectedLinks = useMemo(
    () =>
      links.filter(
        (link) => selectedLinkIds.includes(link.id) && (link.status === 'pending' || link.status === 'failed')
      ),
    [links, selectedLinkIds]
  );

  const handleStartAll = async () => {
    setIsFetchingCount(true);
    try {
      const response = await apiClient.get<{ data: { count: number } }>(
        `/projects/${project.id}/links/processable-count`
      );
      const processableCount = response.data.data.count;

      if (processableCount === 0) {
        notifications.show({
          title: 'No Links to Process',
          message: 'All links for this project have already been processed.',
          color: 'blue',
        });
        return;
      }

      modals.openConfirmModal({
        title: 'Confirm Generation',
        centered: true,
        children: (
          <Stack>
            <Text size="sm">
              You are about to process <strong>{processableCount}</strong> pending or failed links.
            </Text>
            <Text size="sm">
              This will make up to {processableCount} API calls to the{' '}
              <strong>{project.model_name}</strong> model.
            </Text>
            <Text size="sm" fw={700}>
              Are you sure you want to proceed?
            </Text>
          </Stack>
        ),
        labels: { confirm: 'Start Generation', cancel: 'Cancel' },
        confirmProps: { color: 'blue' },
        onConfirm: () => startGeneration.mutate({ project_id: project.id }),
      });
    } finally {
      setIsFetchingCount(false);
    }
  };

  const openDeleteModal = () =>
    modals.openConfirmModal({
      title: 'Delete Selected Links',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete the <strong>{selectedLinkIds.length}</strong> selected links?
        </Text>
      ),
      labels: { confirm: 'Delete Links', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () =>
        deleteLinksMutation.mutate(
          { projectId: project.id, link_ids: selectedLinkIds },
          { onSuccess: () => setSelectedLinkIds([]) }
        ),
    });

  const openReprocessModal = () =>
    modals.openConfirmModal({
      title: 'Reprocess Selected Links',
      centered: true,
      children: (
        <Text size="sm">
          You are about to reprocess <strong>{processableSelectedLinks.length}</strong> selected links.
        </Text>
      ),
      labels: { confirm: 'Reprocess', cancel: 'Cancel' },
      confirmProps: { color: 'blue' },
      onConfirm: () =>
        processEntriesMutation.mutate(
          { project_id: project.id, link_ids: processableSelectedLinks.map((l) => l.id) },
          { onSuccess: () => setSelectedLinkIds([]) }
        ),
    });

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedLinkIds(event.currentTarget.checked ? links.map((link) => link.id) : []);
  };

  const handleAddManualLinks = (urls: string[]) => {
    confirmLinks.mutate({ project_id: project.id, urls });
  };

  if (
    project.status === 'draft' ||
    project.status === 'search_params_generated' ||
    project.status === 'selector_generated'
  ) {
    return <Text c="dimmed">Complete the previous steps to generate entries.</Text>;
  }

  return (
    <>
      <AddLinksModal opened={addLinksModalOpened} onClose={closeAddLinksModal} onAdd={handleAddManualLinks} />
      <Stack>
        <Text>
          Manage your project's links below. You can start a job to process all pending/failed links, or select specific
          links to reprocess or delete.
        </Text>

        <Group>
          <Button
            onClick={handleStartAll}
            loading={startGeneration.isPending || isJobActive || isFetchingCount}
            disabled={isJobActive || isFetchingCount}
          >
            Start Generation for All
          </Button>
          <Button
            leftSection={<IconPlayerPlay size={14} />}
            disabled={processableSelectedLinks.length === 0 || isJobActive}
            onClick={openReprocessModal}
            loading={processEntriesMutation.isPending}
            variant="outline"
          >
            Reprocess Selected ({processableSelectedLinks.length})
          </Button>
          <Button
            leftSection={<IconTrash size={14} />}
            color="red"
            variant="outline"
            disabled={selectedLinkIds.length === 0 || isJobActive}
            onClick={openDeleteModal}
            loading={deleteLinksMutation.isPending}
          >
            Delete Selected ({selectedLinkIds.length})
          </Button>
          <Button leftSection={<IconPlus size={14} />} onClick={openAddLinksModal} variant="outline">
            Add Manual Links
          </Button>
        </Group>

        <JobStatusIndicator job={processingJob} title="Main Generation Job Status" />

        {isLoadingLinks && <Loader />}

        {totalItems > 0 && (
          <>
            <Table mt="md" striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: 40 }}>
                    <Checkbox
                      checked={selectedLinkIds.length === links.length && links.length > 0}
                      indeterminate={selectedLinkIds.length > 0 && selectedLinkIds.length < links.length}
                      onChange={handleSelectAll}
                    />
                  </Table.Th>
                  <Table.Th>Link URL</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {links.map((link) => (
                  <Table.Tr key={link.id}>
                    <Table.Td>
                      <Checkbox
                        checked={selectedLinkIds.includes(link.id)}
                        onChange={(event) =>
                          setSelectedLinkIds(
                            event.currentTarget.checked
                              ? [...selectedLinkIds, link.id]
                              : selectedLinkIds.filter((id) => id !== link.id)
                          )
                        }
                      />
                    </Table.Td>
                    <Table.Td>
                      <Text truncate>{link.url}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Tooltip
                        label={link.skip_reason || link.error_message}
                        disabled={!link.skip_reason && !link.error_message}
                        multiline
                        w={220}
                      >
                        <Badge color={statusColors[link.status]} variant="light">
                          {link.status}
                        </Badge>
                      </Tooltip>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {totalPages > 1 && (
              <Group justify="center" mt="md">
                <Pagination value={activePage} onChange={handlePageChange} total={totalPages} />
              </Group>
            )}
          </>
        )}
      </Stack>
    </>
  );
}
