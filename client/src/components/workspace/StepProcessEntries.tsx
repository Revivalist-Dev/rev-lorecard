import { useState, useEffect } from 'react';
import { Stack, Text, Button, Group, Progress, Table, Badge, Title, Pagination } from '@mantine/core';
import { useProcessProjectEntriesJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useSearchParams } from 'react-router-dom';
import { useModals } from '@mantine/modals';
import apiClient from '../../services/api';
import { notifications } from '@mantine/notifications';

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
};

export function StepProcessEntries({ project }: StepProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);
  const [isFetchingCount, setIsFetchingCount] = useState(false);
  const modals = useModals();

  const startGeneration = useProcessProjectEntriesJob();
  const { job: processingJob } = useLatestJob(project.id, 'process_project_entries');
  const { data: linksResponse } = useProjectLinks(project.id, { page: activePage, pageSize: PAGE_SIZE });

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

  const links = linksResponse?.data || [];
  const totalItems = linksResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);
  const isJobActive = processingJob?.status === 'pending' || processingJob?.status === 'in_progress';
  const isDone = project.status === 'completed' || project.status === 'failed';
  const hasIncompleteLinks = totalItems > 0 && links.some((link) => link.status !== 'completed');

  const handleStart = async () => {
    setIsFetchingCount(true);
    try {
      const response = await apiClient.get<{ data: {count: number} }>(`/projects/${project.id}/links/processable-count`);
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
              <strong>{project.ai_provider_config.model_name}</strong> model. This can be a costly operation.
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
    } catch (error) {
      console.error('Failed to fetch processable links count', error);
      notifications.show({
        title: 'Error',
        message: 'Could not retrieve the number of links to process. Please try again.',
        color: 'red',
      });
    } finally {
      setIsFetchingCount(false);
    }
  };

  let buttonText = 'Start Generation';
  if (isJobActive) {
    buttonText = 'Processing...';
  } else if (project.status === 'links_extracted') {
    buttonText = 'Start Generation';
  } else if (isDone && hasIncompleteLinks) {
    buttonText = 'Reprocess Failed/Pending Links';
  } else if (isDone) {
    buttonText = 'Generation Complete';
  }

  if (
    project.status === 'draft' ||
    project.status === 'search_params_generated' ||
    project.status === 'selector_generated'
  ) {
    return <Text c="dimmed">Complete the previous steps to generate entries.</Text>;
  }

  return (
    <Stack>
      <Text>
        You are ready to start the main generation process. This will go through each of your saved links, scrape the
        content, and use the AI to create a lorebook entry.
      </Text>

      <Group justify="flex-end">
        <Button
          onClick={handleStart}
          loading={startGeneration.isPending || isJobActive || isFetchingCount}
          disabled={startGeneration.isPending || isJobActive || (isDone && !hasIncompleteLinks) || isFetchingCount}
        >
          {buttonText}
        </Button>
      </Group>

      <JobStatusIndicator job={processingJob} title="Main Generation Job Status" />

      {processingJob && (
        <Stack mt="md">
          <Title order={4}>Generation Progress</Title>
          <Group>
            <Text fw={500}>Status:</Text>
            <Badge color={statusColors[processingJob.status]}>{processingJob.status}</Badge>
          </Group>
          <Progress value={processingJob.progress || 0} striped animated={isJobActive} />
          <Text c="dimmed" size="sm">
            {processingJob.processed_items || 0} / {processingJob.total_items || links.length} links processed
          </Text>
        </Stack>
      )}

      {totalItems > 0 && (
        <>
          <Table mt="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Link URL</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {links.map((link) => (
                <Table.Tr key={link.id}>
                  <Table.Td>
                    <Text truncate>{link.url}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={statusColors[link.status]} variant="light">
                      {link.status}
                    </Badge>
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
  );
}
