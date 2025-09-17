import {
  Stack,
  Text,
  Button,
  Group,
  Loader,
  Paper,
  ActionIcon,
  Badge,
  Box,
  Title,
  Tooltip,
  Checkbox,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import { useModals } from '@mantine/modals';
import type { Project, ProjectSource } from '../../types';
import { useProjectSources, useDeleteProjectSource } from '../../hooks/useProjectSources';
import { ProjectSourceModal } from './ProjectSourceModal';
import { useFetchContentJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { IconDownload, IconEye, IconPlus, IconTrash } from '@tabler/icons-react';
import { formatDate } from '../../utils/formatDate';
import { ViewSourceContentModal } from './ViewSourceContentModal';

interface CharacterSourcesProps {
  project: Project;
  selectedSourceIds: string[];
  setSelectedSourceIds: React.Dispatch<React.SetStateAction<string[]>>;
}

export function CharacterSources({ project, selectedSourceIds, setSelectedSourceIds }: CharacterSourcesProps) {
  const { data: sources, isLoading: isLoadingSources } = useProjectSources(project.id);
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [viewModalOpened, { open: openViewModal, close: closeViewModal }] = useDisclosure(false);
  const [selectedSource, setSelectedSource] = useState<ProjectSource | null>(null);
  const [sourceToViewId, setSourceToViewId] = useState<string | null>(null);
  const modals = useModals();

  const deleteSourceMutation = useDeleteProjectSource(project.id);
  const fetchContentMutation = useFetchContentJob();
  const { job: fetchContentJob } = useLatestJob(project.id, 'fetch_source_content');

  const handleOpenCreateModal = () => {
    setSelectedSource(null);
    openModal();
  };

  const handleOpenViewModal = (sourceId: string) => {
    setSourceToViewId(sourceId);
    openViewModal();
  };

  const openDeleteModal = (source: ProjectSource) =>
    modals.openConfirmModal({
      title: 'Delete Source',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete the source "<strong>{source.url}</strong>"? This is irreversible.
        </Text>
      ),
      labels: { confirm: 'Delete Source', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => deleteSourceMutation.mutate({ projectId: project.id, sourceId: source.id }),
    });

  const handleFetchContent = (sourceId: string) => {
    fetchContentMutation.mutate({ project_id: project.id, source_ids: [sourceId] });
  };

  const isFetchJobActive = fetchContentJob?.status === 'pending' || fetchContentJob?.status === 'in_progress';

  return (
    <>
      <ProjectSourceModal
        opened={modalOpened}
        onClose={closeModal}
        projectId={project.id}
        source={selectedSource}
        projectType="character"
      />
      <ViewSourceContentModal
        opened={viewModalOpened}
        onClose={closeViewModal}
        projectId={project.id}
        sourceId={sourceToViewId}
      />
      <Stack>
        <Group justify="space-between">
          <Title order={4}>Context Sources</Title>
          <Button leftSection={<IconPlus size={16} />} onClick={handleOpenCreateModal} size="xs">
            Add Source
          </Button>
        </Group>
        <Text size="sm" c="dimmed">
          Add source URLs, fetch their content, then select which ones to use for generation.
        </Text>

        <JobStatusIndicator job={fetchContentJob} title="Content Fetching" />

        <Paper withBorder p="md" mt="xs">
          {isLoadingSources ? (
            <Loader />
          ) : (
            <Stack>
              {sources && sources.length > 0 ? (
                sources.map((source) => (
                  <Paper withBorder p="xs" key={source.id} radius="sm">
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                        <Checkbox
                          checked={selectedSourceIds.includes(source.id)}
                          onChange={(event) => {
                            const { checked } = event.currentTarget;
                            setSelectedSourceIds((current) =>
                              checked ? [...current, source.id] : current.filter((id) => id !== source.id)
                            );
                          }}
                          disabled={!source.last_crawled_at}
                        />
                        <Box style={{ minWidth: 0 }}>
                          <Text truncate fw={500}>
                            {source.url}
                          </Text>
                          <Group gap="xs">
                            {source.last_crawled_at ? (
                              <Tooltip label={`Last fetched: ${formatDate(source.last_crawled_at)}`}>
                                <Badge size="sm" variant="light" color="green">
                                  Fetched
                                </Badge>
                              </Tooltip>
                            ) : (
                              <Badge size="sm" variant="light" color="gray">
                                Not Fetched
                              </Badge>
                            )}
                            {source.content_char_count && (
                              <Text size="xs" c="dimmed">
                                ~{Math.ceil(source.content_char_count / 4)} tokens
                              </Text>
                            )}
                          </Group>
                        </Box>
                      </Group>
                      <Group gap="xs" wrap="nowrap">
                        <Tooltip label="View Content">
                          <ActionIcon
                            onClick={() => handleOpenViewModal(source.id)}
                            variant="default"
                            disabled={!source.last_crawled_at}
                          >
                            <IconEye size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Fetch/Re-fetch Content">
                          <ActionIcon
                            onClick={() => handleFetchContent(source.id)}
                            variant="default"
                            loading={isFetchJobActive}
                            disabled={isFetchJobActive}
                          >
                            <IconDownload size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Delete Source">
                          <ActionIcon
                            onClick={() => openDeleteModal(source)}
                            variant="default"
                            color="red"
                            loading={deleteSourceMutation.isPending}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Group>
                  </Paper>
                ))
              ) : (
                <Text ta="center" c="dimmed" p="md">
                  No sources added yet.
                </Text>
              )}
            </Stack>
          )}
        </Paper>
      </Stack>
    </>
  );
}
