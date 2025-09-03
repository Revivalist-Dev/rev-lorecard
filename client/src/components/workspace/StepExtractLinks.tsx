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
  Grid,
  TextInput,
  Alert,
} from '@mantine/core';
import { useExtractLinksJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import type { BackgroundJob, Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useProjectLinks } from '../../hooks/useProjectLinks';
import { useSearchParams } from 'react-router-dom';
import { IconInfoCircle, IconSearch } from '@tabler/icons-react';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);

  const extractLinks = useExtractLinksJob();
  const { job: latestSelectorJob } = useLatestJob(project.id, 'generate_selector');
  const { job: latestRescanJob } = useLatestJob(project.id, 'rescan_links');
  const { job: latestExtractLinksJob } = useLatestJob(project.id, 'extract_links');

  // Determine which job (selector generation or rescan) is the most recent source of URLs.
  const mostRecentCrawlJob = useMemo(() => {
    const jobs = [latestSelectorJob, latestRescanJob].filter((j): j is BackgroundJob => !!j);
    if (jobs.length === 0) return null;
    return jobs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  }, [latestSelectorJob, latestRescanJob]);

  const allUrls = useMemo(
    () => (mostRecentCrawlJob?.result as { found_urls: string[] } | undefined)?.found_urls || [],
    [mostRecentCrawlJob]
  );
  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const [filterText, setFilterText] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const { data: savedLinksResponse, isLoading: isLoadingSavedLinks } = useProjectLinks(project.id, {
    page: activePage,
    pageSize: PAGE_SIZE,
  });

  const hasNewLinksToProcess = useMemo(() => {
    if (!mostRecentCrawlJob) return false;
    // If an extract links job has never run, or if the latest crawl job is newer,
    // then we have new links to process.
    if (!latestExtractLinksJob) return true;
    return new Date(mostRecentCrawlJob.created_at) > new Date(latestExtractLinksJob.created_at);
  }, [mostRecentCrawlJob, latestExtractLinksJob]);

  const showSelectionUI = project.status === 'selector_generated' || (hasNewLinksToProcess && allUrls.length > 0);

  const filteredUrls = useMemo(
    () => allUrls.filter((url) => url.toLowerCase().includes(filterText.toLowerCase())),
    [allUrls, filterText]
  );

  useEffect(() => {
    // Automatically select all found URLs when the selection UI is shown
    if (showSelectionUI) {
      setSelectedUrls(allUrls);
    }
  }, [showSelectionUI, allUrls]);

  const handleSaveLinks = () => {
    extractLinks.mutate({ project_id: project.id, urls: selectedUrls });
  };

  const isJobActive = latestExtractLinksJob?.status === 'pending' || latestExtractLinksJob?.status === 'in_progress';

  if (project.status === 'draft' || project.status === 'search_params_generated') {
    return <Text c="dimmed">Complete the previous step to extract links.</Text>;
  }

  // VIEW 1: Show the selection UI if it's the first time or if new links are available.
  if (showSelectionUI) {
    const totalPages = Math.ceil(filteredUrls.length / PAGE_SIZE);
    const paginatedUrls = filteredUrls.slice((activePage - 1) * PAGE_SIZE, activePage * PAGE_SIZE);

    return (
      <Stack>
        {hasNewLinksToProcess && project.status !== 'selector_generated' && (
          <Alert icon={<IconInfoCircle size="1rem" />} title="New Links Found" color="blue">
            You have re-run the selector generation or link rescan. Review and save the new set of links below to
            continue. This will add to the existing links for this project.
          </Alert>
        )}
        <Text>
          Review the links found by the crawler. Uncheck any links you wish to exclude. Hover over a link to see a live
          preview.
        </Text>
        <Grid gutter="xl">
          <Grid.Col span={{ base: 12, md: 6 }}>
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
            {isJobActive ? 'Saving...' : `Save ${selectedUrls.length} Links`}
          </Button>
        </Group>

        <JobStatusIndicator job={latestExtractLinksJob} title="Link Saving Job Status" />
      </Stack>
    );
  }

  // VIEW 2: If no new links are pending, show the results table of saved links.
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
                <Tooltip label={link.skip_reason} disabled={!link.skip_reason} multiline w={220}>
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
          <Pagination
            value={pageFromUrl}
            onChange={(p) => setSearchParams({ [URL_PARAM_KEY]: p.toString() })}
            total={totalPages}
          />
        </Group>
      )}
      <JobStatusIndicator job={latestExtractLinksJob} title="Link Saving Job Status" />
    </Stack>
  );
}
