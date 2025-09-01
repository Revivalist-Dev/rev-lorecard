import { useState, useEffect } from 'react';
import { Stack, Text, Button, Group, Progress, Table, Badge, Title, Pagination } from '@mantine/core';
import { useProcessProjectEntriesJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useSearchParams } from 'react-router-dom';

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

  const handleStart = () => {
    startGeneration.mutate({ project_id: project.id });
  };

  const links = linksResponse?.data || [];
  const totalItems = linksResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);
  const isProcessing = project.status === 'processing';
  const isDone = project.status === 'completed' || project.status === 'failed';

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
        <Button onClick={handleStart} loading={startGeneration.isPending || isProcessing} disabled={isDone}>
          {isDone ? 'Generation Complete' : 'Start Generation'}
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
          <Progress value={processingJob.progress || 0} striped animated={isProcessing} />
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
