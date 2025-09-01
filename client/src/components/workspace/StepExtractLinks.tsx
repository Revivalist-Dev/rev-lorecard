import { useState, useEffect } from 'react';
import {
  Stack,
  Text,
  Button,
  Group,
  Checkbox,
  ScrollArea,
  Paper,
  Title,
  Center,
  Loader,
  Pagination,
  Table,
  Badge,
} from '@mantine/core';
import { useExtractLinksJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import { useSearchParams } from 'react-router-dom';

interface StepProps {
  project: Project;
}

const PAGE_SIZE = 50;
const URL_PARAM_KEY = 'links_page';

const statusColors: Record<string, string> = {
  pending: 'gray',
  processing: 'yellow',
  completed: 'green',
  failed: 'red',
};

export function StepExtractLinks({ project }: StepProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);

  const extractLinks = useExtractLinksJob();
  const { job: latestSelectorJob } = useLatestJob(project.id, 'generate_selector');
  const { job: latestExtractLinksJob } = useLatestJob(project.id, 'extract_links');

  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const selectorResult = latestSelectorJob?.result as { selectors: Record<string, string[]> } | undefined;
  const allUrls = selectorResult ? [...new Set(Object.values(selectorResult.selectors).flat())] : [];

  const { data: savedLinksResponse, isLoading: isLoadingSavedLinks } = useProjectLinks(project.id, {
    page: activePage,
    pageSize: PAGE_SIZE,
  });

  const isProcessed = project.status !== 'selector_generated';

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

  useEffect(() => {
    if (!isProcessed && allUrls.length > 0) {
      setSelectedUrls(allUrls);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isProcessed, latestSelectorJob]);

  const handleSaveLinks = () => {
    extractLinks.mutate({ project_id: project.id, urls: selectedUrls });
  };

  if (project.status === 'draft' || project.status === 'search_params_generated') {
    return <Text c="dimmed">Complete the previous step to extract links.</Text>;
  }

  if (isProcessed) {
    if (isLoadingSavedLinks) {
      return (
        <Center p="xl">
          <Loader />
        </Center>
      );
    }
    const links = savedLinksResponse?.data || [];
    const totalItems = savedLinksResponse?.meta.total_items || 0;
    const totalPages = Math.ceil(totalItems / PAGE_SIZE);

    return (
      <Stack>
        <Text>The links for this project have been saved. You can review them below.</Text>
        <Table mt="md" striped highlightOnHover withTableBorder>
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
        <JobStatusIndicator job={latestExtractLinksJob} title="Link Extraction Job Status" />
      </Stack>
    );
  }

  const totalPages = Math.ceil(allUrls.length / PAGE_SIZE);
  const paginatedUrls = allUrls.slice((activePage - 1) * PAGE_SIZE, activePage * PAGE_SIZE);

  return (
    <Stack>
      <Text>
        Review the links found by the generated selectors. Uncheck any links you wish to exclude from the lorebook.
      </Text>
      <Paper withBorder p="md">
        <Group justify="space-between" mb="sm">
          <Title order={5}>
            Found Links ({selectedUrls.length} / {allUrls.length} selected)
          </Title>
          <Checkbox
            label="Select / Deselect All"
            checked={selectedUrls.length === allUrls.length && allUrls.length > 0}
            indeterminate={selectedUrls.length > 0 && selectedUrls.length < allUrls.length}
            onChange={(event) => setSelectedUrls(event.currentTarget.checked ? allUrls : [])}
          />
        </Group>
        <ScrollArea h={300}>
          <Checkbox.Group value={selectedUrls} onChange={setSelectedUrls}>
            <Stack gap="xs">
              {paginatedUrls.map((url) => (
                <Checkbox key={url} value={url} label={url} />
              ))}
            </Stack>
          </Checkbox.Group>
        </ScrollArea>
        {totalPages > 1 && (
          <Group justify="center" mt="md">
            <Pagination value={activePage} onChange={handlePageChange} total={totalPages} />
          </Group>
        )}
      </Paper>

      <Group justify="flex-end">
        <Button
          onClick={handleSaveLinks}
          loading={extractLinks.isPending}
          disabled={selectedUrls.length === 0}
        >{`Save ${selectedUrls.length} Links`}</Button>
      </Group>

      <JobStatusIndicator job={latestExtractLinksJob} title="Link Extraction Job Status" />
    </Stack>
  );
}
