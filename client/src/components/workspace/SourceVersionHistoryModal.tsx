import {
  Modal,
  ScrollArea,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Loader,
  Alert,
  Box,
} from '@mantine/core';
import { IconAlertCircle, IconHistory, IconRestore, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { useModals } from '@mantine/modals';
import {
  useSourceVersions,
  useRestoreSourceVersion,
  useDeleteSourceVersion,
  useClearSourceHistory,
} from '../../hooks/useProjectSources';
import type { SourceContentVersion, ContentType } from '../../types';
import { CodeMirrorDiffEditor } from '../common/CodeMirrorDiffEditor';
import formatDate from '../../utils/formatDate';

interface SourceVersionHistoryModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
  sourceId: string | null;
  currentContent: string;
  contentType: ContentType;
}

export function SourceVersionHistoryModal({
  opened,
  onClose,
  projectId,
  sourceId,
  currentContent,
  contentType,
}: SourceVersionHistoryModalProps) {
  const {
    data: versions,
    isLoading,
    isError,
    error,
  } = useSourceVersions(projectId, sourceId);
  const restoreMutation = useRestoreSourceVersion(projectId, sourceId);
  const deleteMutation = useDeleteSourceVersion(projectId, sourceId);
  const clearHistoryMutation = useClearSourceHistory(projectId, sourceId);
  const modals = useModals();

  const [selectedVersion, setSelectedVersion] = useState<SourceContentVersion | null>(null);

  const handleRestore = (version: SourceContentVersion) => {
    if (!sourceId) return;
    restoreMutation.mutate(
      { projectId, sourceId, versionId: version.id },
      {
        onSuccess: () => {
          // Close the modal after successful restoration
          onClose();
        },
      }
    );
  };

  const openDeleteModal = (version: SourceContentVersion) =>
    modals.openConfirmModal({
      title: 'Delete Version',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete version "<strong>{version.version_name}</strong>"? This is irreversible.
        </Text>
      ),
      labels: { confirm: 'Delete Version', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => deleteMutation.mutate({ projectId, sourceId: sourceId!, versionId: version.id }),
    });

  const openClearHistoryModal = () =>
    modals.openConfirmModal({
      title: 'Clear History',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to clear all historical versions for this source? Only the latest version will be kept. This is irreversible.
        </Text>
      ),
      labels: { confirm: 'Clear History', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => clearHistoryMutation.mutate({ projectId, sourceId: sourceId! }),
    });

  const handleSelectVersion = (version: SourceContentVersion) => {
    setSelectedVersion(version);
  };

  const versionsList = versions?.map((version, index) => {
    // The latest version is always the first element (index 0)
    const isLatestVersion = index === 0;

    return (
      <Group
        key={version.id}
        justify="space-between"
        p="xs"
        style={{
          border: '1px solid var(--mantine-color-dark-4)',
          borderRadius: 'var(--mantine-radius-sm)',
          cursor: 'pointer',
          backgroundColor:
            selectedVersion?.id === version.id ? 'var(--mantine-color-dark-6)' : 'transparent',
        }}
        onClick={() => handleSelectVersion(version)}
      >
        <Stack gap={0}>
          <Text size="sm" fw={500}>
            {version.version_name}
          </Text>
          <Text size="xs" c="dimmed">
            {formatDate(version.created_at)}
          </Text>
        </Stack>
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            variant="light"
            color="red"
            leftSection={<IconTrash size={14} />}
            onClick={(e) => {
              e.stopPropagation();
              openDeleteModal(version);
            }}
            loading={deleteMutation.isPending}
            disabled={deleteMutation.isPending || isLatestVersion}
          >
            Delete
          </Button>
          <Button
            size="xs"
            variant="light"
            color="red"
            leftSection={<IconRestore size={14} />}
            onClick={(e) => {
              e.stopPropagation();
              handleRestore(version);
            }}
            loading={restoreMutation.isPending}
            disabled={restoreMutation.isPending}
          >
            Restore
          </Button>
        </Group>
      </Group>
    );
  });

  const diffView = selectedVersion ? (
    <CodeMirrorDiffEditor
      originalContent={selectedVersion.raw_content}
      modifiedContent={currentContent}
      language={contentType}
      height="100%"
    />
  ) : (
    <Box p="md">
      <Text c="dimmed">Select a version from the history list to view the difference against the current content.</Text>
    </Box>
  );

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="90%"
      title={
        <Group justify="space-between" w="100%">
          <Group>
            <IconHistory size={20} />
            <Title order={4}>Source Content History</Title>
          </Group>
          <Button
            size="xs"
            variant="outline"
            color="red"
            onClick={openClearHistoryModal}
            disabled={clearHistoryMutation.isPending || (versions?.length ?? 0) <= 1}
            loading={clearHistoryMutation.isPending}
          >
            Clear History
          </Button>
        </Group>
      }
    >
      {isLoading && <Loader />}
      {isError && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
          {error?.message || 'Failed to load version history.'}
        </Alert>
      )}
      {versions && (
        <Group align="flex-start" wrap="nowrap" h="70vh">
          <ScrollArea w={300} h="100%" style={{ borderRight: '1px solid var(--mantine-color-dark-4)' }}>
            <Stack gap="xs" p="xs">
              {versionsList && versionsList.length > 0 ? (
                versionsList
              ) : (
                <Text c="dimmed" size="sm" p="md">
                  No historical versions found. Versions are created when content is manually saved.
                </Text>
              )}
            </Stack>
          </ScrollArea>
          <Box flex={1} h="100%">
            {diffView}
          </Box>
        </Group>
      )}
    </Modal>
  );
}