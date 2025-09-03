import { useState, useEffect, useMemo } from 'react';
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
  Tooltip,
  TextInput,
  Grid,
} from '@mantine/core';
import { useExtractLinksJob } from '../../hooks/useJobMutations';
import { useLatestJob, useProjectJobs } from '../../hooks/useProjectJobs';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import { useSearchParams } from 'react-router-dom';
import { IconSearch } from '@tabler/icons-react';

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
  skipped: 'yellow',
};

export function StepExtractLinks({ project }: StepProps) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [searchParams, _setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);

  const extractLinks = useExtractLinksJob();
  const { job: latestExtractLinksJob } = useLatestJob(project.id, 'extract_links');
  const { data: allJobsResponse } = useProjectJobs(project.id);
  const { data: savedLinksResponse, isLoading: isLoadingSavedLinks } = useProjectLinks(project.id, {
    page: 1,
    pageSize: 1,
  });

  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const [filterText, setFilterText] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const unconfirmedUrls = useMemo(() => {
    if (!allJobsResponse) return [];
    const latestConfirmJobDate = latestExtractLinksJob?.created_at
      ? new Date(latestExtractLinksJob.created_at)
      : new Date(0);

    const recentCrawlJobs = allJobsResponse.data.filter(
      (job) =>
        (job.task_name === 'generate_selector' || job.task_name === 'rescan_links') &&
        job.status === 'completed' &&
        new Date(job.created_at) > latestConfirmJobDate
    );

    const urlSet = new Set<string>();
    for (const job of recentCrawlJobs) {
      const urls = (job.result as { found_urls: string[] })?.found_urls || [];
      for (const url of urls) {
        urlSet.add(url);
      }
    }
    return Array.from(urlSet);
  }, [allJobsResponse, latestExtractLinksJob]);

  useEffect(() => {
    setSelectedUrls(unconfirmedUrls);
  }, [unconfirmedUrls]);

  const filteredUrls = useMemo(
    () => unconfirmedUrls.filter((url) => url.toLowerCase().includes(filterText.toLowerCase())),
    [unconfirmedUrls, filterText]
  );

  const showSelectionUI = unconfirmedUrls.length > 0;

  if (project.status === 'draft' || project.status === 'search_params_generated') {
    return <Text c="dimmed">Complete the previous steps to review links.</Text>;
  }

  const handleSaveLinks = () => {
    extractLinks.mutate({ project_id: project.id, urls: selectedUrls });
  };
  const isJobActive = latestExtractLinksJob?.status === 'pending' || latestExtractLinksJob?.status === 'in_progress';

  // VIEW 1: Show selection UI if there are unconfirmed links from a crawl
  if (showSelectionUI) {
    const totalPages = Math.ceil(filteredUrls.length / PAGE_SIZE);
    const paginatedUrls = filteredUrls.slice((activePage - 1) * PAGE_SIZE, activePage * PAGE_SIZE);

    return (
      <Stack>
        <Text>
          New links have been found. Review the list and uncheck any you wish to exclude, then save them to the project.
        </Text>
        <Grid gutter="xl">
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Paper withBorder p="md">
              <Group justify="space-between" mb="sm">
                <Title order={5}>
                  Found Links ({selectedUrls.length} / {unconfirmedUrls.length} selected)
                </Title>
                <Checkbox
                  label="Select / Deselect All"
                  checked={selectedUrls.length === unconfirmedUrls.length && unconfirmedUrls.length > 0}
                  indeterminate={selectedUrls.length > 0 && selectedUrls.length < unconfirmedUrls.length}
                  onChange={(event) => setSelectedUrls(event.currentTarget.checked ? unconfirmedUrls : [])}
                />
              </Group>
              <TextInput
                placeholder="Filter links..."
                leftSection={<IconSearch size={14} />}
                value={filterText}
                onChange={(event) => setFilterText(event.currentTarget.value)}
                mb="md"
              />
              <ScrollArea h={400}>
                <Checkbox.Group value={selectedUrls} onChange={setSelectedUrls}>
                  <Stack gap="xs">
                    {paginatedUrls.map((url) => (
                      <Checkbox key={url} value={url} label={url} onMouseEnter={() => setPreviewUrl(url)} />
                    ))}
                  </Stack>
                </Checkbox.Group>
              </ScrollArea>
              {totalPages > 1 && (
                <Group justify="center" mt="md">
                  <Pagination value={activePage} onChange={setPage} total={totalPages} />
                </Group>
              )}
            </Paper>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Paper withBorder style={{ height: '100%', minHeight: 400 }}>
              {previewUrl ? (
                <iframe src={previewUrl} title="Link Preview" style={{ width: '100%', height: '100%', border: 0 }} />
              ) : (
                <Center style={{ height: '100%' }}>
                  <Text c="dimmed">Hover over a link to preview it here</Text>
                </Center>
              )}
            </Paper>
          </Grid.Col>
        </Grid>

        <Group justify="flex-end">
          <Button
            onClick={handleSaveLinks}
            loading={extractLinks.isPending || isJobActive}
            disabled={selectedUrls.length === 0 || extractLinks.isPending || isJobActive}
          >
            {isJobActive ? 'Saving...' : `Confirm and Save ${selectedUrls.length} Links`}
          </Button>
        </Group>

        <JobStatusIndicator job={latestExtractLinksJob} title="Link Saving Job Status" />
      </Stack>
    );
  }

  // VIEW 2: If no new links are pending, show the results table of saved links.
  if (isLoadingSavedLinks && !savedLinksResponse) {
    return (
      <Center p="xl">
        <Loader />
      </Center>
    );
  }

  const hasSavedLinks = (savedLinksResponse?.meta.total_items || 0) > 0;

  if (!hasSavedLinks) {
    return (
      <Text c="dimmed">
        No links have been found or saved for this project yet. Go back to the previous step to crawl a source.
      </Text>
    );
  }

  return <SavedLinksView project={project} />;
}

function SavedLinksView({ project }: StepProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const { data: linksResponse, isLoading } = useProjectLinks(project.id, {
    page: pageFromUrl,
    pageSize: PAGE_SIZE,
  });

  if (isLoading) {
    return (
      <Center p="xl">
        <Loader />
      </Center>
    );
  }

  const links = linksResponse?.data || [];
  const totalItems = linksResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  return (
    <Stack>
      <Text>
        All found links have been saved. The next step will process all links with a "pending" or "failed" status.
      </Text>
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
        <Center mt="md">
          <Pagination
            value={pageFromUrl}
            onChange={(p) => setSearchParams({ [URL_PARAM_KEY]: p.toString() })}
            total={totalPages}
          />
        </Center>
      )}
    </Stack>
  );
}
