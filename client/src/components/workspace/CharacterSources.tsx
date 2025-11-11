import {
  Stack,
  Text,
  Button,
  Group,
  Loader,
  Paper,
  ActionIcon,
  Box,
  Title,
  Tooltip,
  Checkbox,
} from '@mantine/core';
import { useDisclosure, useClipboard } from '@mantine/hooks';
import { useState } from 'react';
import { useModals } from '@mantine/modals';
import type { Project, ProjectSource, ContentType } from '../../types';
import { useProjectSources, useDeleteProjectSource } from '../../hooks/useProjectSources';
import { ProjectSourceModal } from './ProjectSourceModal';
import { useFetchContentJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { IconDownload, IconEye, IconPlus, IconTrash, IconEdit, IconCopy } from '@tabler/icons-react';
import { ViewSourceContentModal } from './ViewSourceContentModal';
import { EditSourceContentModal } from './EditSourceContentModal';
import { CharacterCardFormatSelectorModal } from './CharacterCardFormatSelectorModal';

interface SourceItemProps {
  source: ProjectSource;
  project: Project;
  selectedSourceIds: string[];
  setSelectedSourceIds: React.Dispatch<React.SetStateAction<string[]>>;
  isFetchJobActive: boolean;
  handleOpenViewModal: (sourceId: string) => void;
  handleOpenEditModal: (sourceId: string) => void;
  handleFetchContent: (source: ProjectSource) => void;
  openDeleteModal: (source: ProjectSource) => void;
  deleteSourceMutation: ReturnType<typeof useDeleteProjectSource>;
}

function SourceItem({
  source,
  selectedSourceIds,
  setSelectedSourceIds,
  isFetchJobActive,
  handleOpenViewModal,
  handleOpenEditModal,
  handleFetchContent,
  openDeleteModal,
  deleteSourceMutation,
}: SourceItemProps) {
  const clipboard = useClipboard({ timeout: 500 });

  const statusColor = source.last_crawled_at ? 'green' : 'red';

  return (
    <Paper
      p="xs"
      key={source.id}
      radius="sm"
      style={{
        border: `1px solid var(--mantine-color-default-border)`,
        borderLeft: `4px solid var(--mantine-color-${statusColor}-filled)`,
      }}
    >
      <Stack gap={4}>
        {/* Top Row: Checkbox, Copy Button, Source URL (expands) */}
        <Group wrap="nowrap" align="flex-start" gap={0}>
          <Box mr="xs">
            <Checkbox
              checked={selectedSourceIds.includes(source.id)}
              onChange={(event) => {
                const { checked } = event.currentTarget;
                setSelectedSourceIds((current) =>
                  checked ? [...current, source.id] : current.filter((id) => id !== source.id)
                );
              }}
              disabled={!source.raw_content && !source.last_crawled_at}
            />
          </Box>
          {/* Attached Copy Button Container */}
          <Box
            style={{
              borderTop: '1px solid var(--mantine-color-dark-4)',
              borderBottom: '1px solid var(--mantine-color-dark-4)',
              borderLeft: '1px solid var(--mantine-color-dark-4)',
              borderRight: 'none', // Ensure no right border on copy container
              borderRadius: 'var(--mantine-radius-sm) 0 0 var(--mantine-radius-sm)',
              alignSelf: 'stretch',
              display: 'flex',
              alignItems: 'center',
              padding: '0 var(--mantine-spacing-xs)',
              backgroundColor: 'var(--mantine-color-dark-6)',
            }}
          >
            <Tooltip label={clipboard.copied ? 'Copied!' : 'Copy URL'} withArrow position="top">
              <ActionIcon
                variant="subtle"
                color={clipboard.copied ? 'teal' : 'gray'}
                onClick={() => clipboard.copy(source.url)}
                size="sm"
              >
                <IconCopy size={16} />
              </ActionIcon>
            </Tooltip>
          </Box>

          {/* Bridge Container */}
          <Box
            style={{
              borderTop: '1px solid var(--mantine-color-dark-4)',
              borderBottom: '1px solid var(--mantine-color-dark-4)',
              borderLeft: '1px solid var(--mantine-color-dark-4)', // Add left border to bridge
              borderRight: '1px solid var(--mantine-color-dark-4)', // Add right border to bridge
              backgroundColor: 'var(--mantine-color-dark-7)',
              alignSelf: 'stretch',
              width: 'var(--mantine-spacing-xs)',
            }}
          />

          {/* URL Container (attached and expanding) */}
          <Box
            style={{
              flex: 1,
              minWidth: 0,
              borderTop: '1px solid var(--mantine-color-dark-4)',
              borderBottom: '1px solid var(--mantine-color-dark-4)',
              borderRight: '1px solid var(--mantine-color-dark-4)',
              borderLeft: 'none', // Ensure no left border on URL container
              borderRadius: '0 var(--mantine-radius-sm) var(--mantine-radius-sm) 0',
              backgroundColor: 'var(--mantine-color-dark-6)',
              padding: 'var(--mantine-spacing-xs)',
              alignSelf: 'stretch',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Tooltip label={source.url} withArrow position="top">
              <Text truncate fw={500}>
                {source.url}
              </Text>
            </Tooltip>
          </Box>
        </Group>

        {/* Bottom Row: Status/Tokens (left) and Action Icons (right) */}
        <Group justify="space-between" wrap="nowrap" mt="sm">
          <Group gap="xs" align="center" style={{ flex: 1 }} justify="center">
            {source.content_char_count && (
              <Text size="xs" c="dimmed">
                {Math.ceil(source.content_char_count / 4)} tokens
              </Text>
            )}
          </Group>
          <Group gap="xs" wrap="nowrap">
            <Tooltip label="View Content">
              <ActionIcon
                onClick={() => handleOpenViewModal(source.id)}
                variant="default"
                disabled={source.source_type === 'web_url' && !source.last_crawled_at}
              >
                <IconEye size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Edit Content">
              <ActionIcon
                onClick={() => handleOpenEditModal(source.id)}
                variant="default"
                disabled={source.source_type === 'web_url' && !source.last_crawled_at} // Only disable web_url sources if content hasn't been fetched
              >
                <IconEdit size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Fetch/Re-fetch Content">
              <ActionIcon
                onClick={() => handleFetchContent(source)}
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
      </Stack>
    </Paper>
  );
}

interface CharacterSourcesProps {
  project: Project;
  selectedSourceIds: string[];
  setSelectedSourceIds: React.Dispatch<React.SetStateAction<string[]>>;
}

export function CharacterSources({ project, selectedSourceIds, setSelectedSourceIds }: CharacterSourcesProps) {
  const { data: sources, isLoading: isLoadingSources } = useProjectSources(project.id);
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [viewModalOpened, { open: openViewModal, close: closeViewModal }] = useDisclosure(false);
  const [editModalOpened, { open: openEditModal, close: closeEditModal }] = useDisclosure(false);
  const [formatModalOpened, { open: openFormatModal, close: closeFormatModal }] = useDisclosure(false);
  const [selectedSource, setSelectedSource] = useState<ProjectSource | null>(null);
  const [sourceToViewId, setSourceToViewId] = useState<string | null>(null);
  const [sourceToEditId, setSourceToEditId] = useState<string | null>(null);
  const [sourceToRefetch, setSourceToRefetch] = useState<ProjectSource | null>(null);
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

  const handleOpenEditModal = (sourceId: string) => {
    setSourceToEditId(sourceId);
    openEditModal();
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

  const handleFetchContent = (source: ProjectSource) => {
    if (source.source_type === 'character_card') {
      // If it's a character card, prompt for format selection
      setSourceToRefetch(source);
      openFormatModal();
    } else {
      // For web_url or user_text_file, use the existing content_type or default
      fetchContentMutation.mutate({ project_id: project.id, source_ids: [source.id] });
    }
  };

  const handleFormatSelect = (format: ContentType) => {
    if (sourceToRefetch) {
      fetchContentMutation.mutate({
        project_id: project.id,
        source_ids: [sourceToRefetch.id],
        output_format: format,
      });
      setSourceToRefetch(null);
    }
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
      <EditSourceContentModal
        opened={editModalOpened}
        onClose={closeEditModal}
        projectId={project.id}
        sourceId={sourceToEditId}
      />
      <CharacterCardFormatSelectorModal
        opened={formatModalOpened}
        onClose={closeFormatModal}
        onSelect={handleFormatSelect}
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
                  <SourceItem
                    key={source.id}
                    source={source}
                    project={project}
                    selectedSourceIds={selectedSourceIds}
                    setSelectedSourceIds={setSelectedSourceIds}
                    isFetchJobActive={isFetchJobActive}
                    handleOpenViewModal={handleOpenViewModal}
                    handleOpenEditModal={handleOpenEditModal}
                    handleFetchContent={handleFetchContent}
                    openDeleteModal={openDeleteModal}
                    deleteSourceMutation={deleteSourceMutation}
                  />
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
