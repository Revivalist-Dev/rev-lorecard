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
  Pagination,
  TextInput,
  Grid,
  Divider,
  Flex,
  Badge,
} from '@mantine/core';
import { useConfirmLinksJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useSearchParams } from 'react-router-dom';
import { IconSearch } from '@tabler/icons-react';

interface StepProps {
  project: Project;
}

const PAGE_SIZE = 50;
const URL_PARAM_KEY = 'links_page';

export function StepConfirmLinks({ project }: StepProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get(URL_PARAM_KEY) || '1', 10);

  const confirmLinks = useConfirmLinksJob();
  const { job: latestConfirmLinksJob } = useLatestJob(project.id, 'confirm_links');
  const { job: latestCrawlJob } = useLatestJob(project.id, 'discover_and_crawl_sources');
  const { job: latestRescanJob } = useLatestJob(project.id, 'rescan_links');

  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);
  const [filterText, setFilterText] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showExisting, setShowExisting] = useState(false);

  // Determine the most recent crawl/rescan job to check for new links
  const relevantCrawlJob = useMemo(() => {
    if (!latestCrawlJob && !latestRescanJob) return null;
    if (latestCrawlJob && !latestRescanJob) return latestCrawlJob;
    if (!latestCrawlJob && latestRescanJob) return latestRescanJob;
    return new Date(latestCrawlJob!.created_at) > new Date(latestRescanJob!.created_at)
      ? latestCrawlJob
      : latestRescanJob;
  }, [latestCrawlJob, latestRescanJob]);

  const { newlyFoundUrls, existingUrlsFoundAgain } = useMemo(() => {
    const lastConfirmDate = latestConfirmLinksJob?.created_at
      ? new Date(latestConfirmLinksJob.created_at)
      : new Date(0);

    // Only consider the crawl job if it's completed and more recent than the last confirmation
    if (
      !relevantCrawlJob ||
      relevantCrawlJob.status !== 'completed' ||
      new Date(relevantCrawlJob.created_at) < lastConfirmDate
    ) {
      return { newlyFoundUrls: [], existingUrlsFoundAgain: [] };
    }

    const result = relevantCrawlJob.result as { new_links?: string[]; existing_links?: string[] };

    return {
      newlyFoundUrls: result?.new_links ?? [],
      existingUrlsFoundAgain: result?.existing_links ?? [],
    };
  }, [relevantCrawlJob, latestConfirmLinksJob]);

  useEffect(() => {
    setSelectedUrls(newlyFoundUrls);
  }, [newlyFoundUrls]);

  const filteredNewUrls = useMemo(
    () => newlyFoundUrls.filter((url) => url.toLowerCase().includes(filterText.toLowerCase())),
    [newlyFoundUrls, filterText]
  );
  const filteredExistingUrls = useMemo(
    () => existingUrlsFoundAgain.filter((url) => url.toLowerCase().includes(filterText.toLowerCase())),
    [existingUrlsFoundAgain, filterText]
  );

  const visibleUrls = showExisting ? [...filteredNewUrls, ...filteredExistingUrls] : filteredNewUrls;
  const showSelectionUI = newlyFoundUrls.length > 0 || existingUrlsFoundAgain.length > 0;

  if (project.status === 'draft' || project.status === 'search_params_generated') {
    return <Text c="dimmed">Complete the previous steps to review links.</Text>;
  }

  const handleSaveLinks = () => {
    confirmLinks.mutate({ project_id: project.id, urls: selectedUrls });
  };
  const isJobActive = latestConfirmLinksJob?.status === 'pending' || latestConfirmLinksJob?.status === 'in_progress';

  // VIEW 1: Show selection UI if there are unconfirmed links from a crawl
  if (showSelectionUI) {
    const totalPages = Math.ceil(visibleUrls.length / PAGE_SIZE);
    const paginatedUrls = visibleUrls.slice((pageFromUrl - 1) * PAGE_SIZE, pageFromUrl * PAGE_SIZE);

    const handlePageChange = (newPage: number) => {
      setSearchParams(
        (prev) => {
          prev.set(URL_PARAM_KEY, newPage.toString());
          return prev;
        },
        { replace: true }
      );
    };

    return (
      <>
        <Stack>
          <Text>
            {newlyFoundUrls.length > 0
              ? `Found ${newlyFoundUrls.length} new links. Review the list and uncheck any you wish to exclude, then save them.`
              : 'No new links found. All discovered links are already saved to the project.'}
          </Text>
          <Grid gutter="xl">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Paper withBorder p="md">
                <Group justify="space-between" mb="sm">
                  <Title order={5}>
                    New Links Found ({selectedUrls.length} / {newlyFoundUrls.length} selected)
                  </Title>
                  <Checkbox
                    label="Select / Deselect All New"
                    checked={selectedUrls.length === newlyFoundUrls.length && newlyFoundUrls.length > 0}
                    indeterminate={selectedUrls.length > 0 && selectedUrls.length < newlyFoundUrls.length}
                    onChange={(event) => setSelectedUrls(event.currentTarget.checked ? newlyFoundUrls : [])}
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
                      {paginatedUrls.map((url) => {
                        const isExisting = !newlyFoundUrls.includes(url);
                        return (
                          <Checkbox
                            key={url}
                            value={url}
                            onMouseEnter={() => setPreviewUrl(url)}
                            disabled={isExisting}
                            label={
                              <Flex justify="space-between" w="100%" gap="md">
                                <Text truncate>{url}</Text>
                                {isExisting && (
                                  <Badge variant="light" color="gray" size="sm">
                                    Saved
                                  </Badge>
                                )}
                              </Flex>
                            }
                          />
                        );
                      })}
                    </Stack>
                  </Checkbox.Group>
                </ScrollArea>
                {totalPages > 1 && (
                  <Group justify="center" mt="md">
                    <Pagination value={pageFromUrl} onChange={handlePageChange} total={totalPages} />
                  </Group>
                )}
                <Divider my="md" />
                <Checkbox
                  label={`Show ${existingUrlsFoundAgain.length} already saved links`}
                  checked={showExisting}
                  onChange={(e) => setShowExisting(e.currentTarget.checked)}
                />
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
              loading={confirmLinks.isPending || isJobActive}
              disabled={selectedUrls.length === 0 || confirmLinks.isPending || isJobActive}
            >
              {isJobActive ? 'Saving...' : `Confirm and Save ${selectedUrls.length} New Links`}
            </Button>
          </Group>

          <JobStatusIndicator job={latestConfirmLinksJob} title="Link Confirmation Job Status" />
        </Stack>
      </>
    );
  }

  // VIEW 2: If no new links are pending, show a simple message.
  return (
    <Text c="dimmed">No new links to confirm. Proceed to the next step to manage and process your saved links.</Text>
  );
}
