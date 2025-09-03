import { Stack, Text, Button, Group, Accordion, Loader, Alert, ActionIcon, Badge, Code, Checkbox } from '@mantine/core';
import { IconAlertCircle, IconPencil, IconPlayerPlay, IconRefresh, IconTrash } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import { useModals } from '@mantine/modals';
import type { Project, ProjectSource } from '../../types';
import { useProjectSources, useDeleteProjectSource } from '../../hooks/useProjectSources';
import { ProjectSourceModal } from './ProjectSourceModal';
import { formatDate } from '../../utils/formatDate';
import { useGenerateSelectorJob, useRescanLinksJob } from '../../hooks/useJobMutations';

interface StepProps {
  project: Project;
}

export function ManageSourcesStep({ project }: StepProps) {
  const { data: sources, isLoading, isError, error } = useProjectSources(project.id);
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [selectedSource, setSelectedSource] = useState<ProjectSource | null>(null);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const modals = useModals();
  const deleteSourceMutation = useDeleteProjectSource(project.id);
  const generateAndScanMutation = useGenerateSelectorJob();
  const rescanMutation = useRescanLinksJob();

  const handleOpenCreateModal = () => {
    setSelectedSource(null);
    openModal();
  };

  const handleOpenEditModal = (source: ProjectSource) => {
    setSelectedSource(source);
    openModal();
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

  const isUnlocked = !!project.search_params;

  if (!isUnlocked) {
    return <Text c="dimmed">Complete the previous step to add and manage sources.</Text>;
  }

  if (isLoading) return <Loader />;
  if (isError) {
    return (
      <Alert icon={<IconAlertCircle size="1rem" />} title="Error!" color="red">
        Failed to load project sources: {error.message}
      </Alert>
    );
  }

  return (
    <>
      <ProjectSourceModal opened={modalOpened} onClose={closeModal} projectId={project.id} source={selectedSource} />
      <Stack>
        <Group justify="space-between">
          <Text>Add sources, then select them to generate selectors and crawl for links.</Text>
          <Button onClick={handleOpenCreateModal}>Add New Source</Button>
        </Group>

        <Group>
          <Button
            leftSection={<IconPlayerPlay size={14} />}
            disabled={selectedSourceIds.length === 0}
            onClick={() => generateAndScanMutation.mutate({ project_id: project.id, source_ids: selectedSourceIds })}
            loading={generateAndScanMutation.isPending}
          >
            Generate & Scan Selected ({selectedSourceIds.length})
          </Button>
          <Button
            variant="outline"
            leftSection={<IconRefresh size={14} />}
            disabled={selectedSourceIds.length === 0}
            onClick={() => rescanMutation.mutate({ project_id: project.id, source_ids: selectedSourceIds })}
            loading={rescanMutation.isPending}
          >
            Rescan Selected ({selectedSourceIds.length})
          </Button>
        </Group>

        <Checkbox.Group value={selectedSourceIds} onChange={setSelectedSourceIds}>
          <Accordion variant="separated">
            {sources?.map((source) => {
              const hasSelectors = source.link_extraction_selector && source.link_extraction_selector.length > 0;
              return (
                <Accordion.Item key={source.id} value={source.id}>
                  <Accordion.Control>
                    <Group justify="space-between">
                      <Group>
                        <Checkbox value={source.id} onClick={(e) => e.stopPropagation()} />
                        <Text fw={500} truncate maw="50%">
                          {source.url}
                        </Text>
                      </Group>
                      <Group gap="xs">
                        {source.last_crawled_at && <Badge variant="light">Crawled</Badge>}
                        <ActionIcon
                          variant="subtle"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenEditModal(source);
                          }}
                        >
                          <IconPencil size={16} />
                        </ActionIcon>
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          onClick={(e) => {
                            e.stopPropagation();
                            openDeleteModal(source);
                          }}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Group>
                    </Group>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <Stack>
                      <Text size="sm" c="dimmed">
                        Max Pages: {source.max_pages_to_crawl} | Last Crawled:{' '}
                        {source.last_crawled_at ? formatDate(source.last_crawled_at) : 'Never'}
                      </Text>
                      {hasSelectors && (
                        <Stack gap={4} mt="xs">
                          <Text size="xs" fw={500}>
                            Generated Selectors:
                          </Text>
                          {source.link_extraction_selector?.map((s) => (
                            <Code key={s}>{s}</Code>
                          ))}
                          {source.link_extraction_pagination_selector && (
                            <>
                              <Text size="xs" fw={500} mt={4}>
                                Pagination Selector:
                              </Text>
                              <Code>{source.link_extraction_pagination_selector}</Code>
                            </>
                          )}
                        </Stack>
                      )}
                    </Stack>
                  </Accordion.Panel>
                </Accordion.Item>
              );
            })}
          </Accordion>
        </Checkbox.Group>
        {sources?.length === 0 && (
          <Text c="dimmed" ta="center" p="md">
            No sources have been added yet.
          </Text>
        )}
      </Stack>
    </>
  );
}
