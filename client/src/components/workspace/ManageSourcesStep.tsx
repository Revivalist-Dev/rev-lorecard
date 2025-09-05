import { Stack, Text, Button, Group, Loader, Checkbox, Paper, ActionIcon, Badge, Box } from '@mantine/core';
import { IconChevronRight, IconPencil, IconPlayerPlay, IconRefresh, IconTrash } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import { useState, useMemo, memo } from 'react';
import { useModals } from '@mantine/modals';
import type { Project, ProjectSource } from '../../types';
import {
  useProjectSources,
  useDeleteProjectSource,
  useProjectSourceHierarchy,
  useDeleteProjectSourcesBulk,
} from '../../hooks/useProjectSources';
import { ProjectSourceModal } from './ProjectSourceModal';
import { useDiscoverAndCrawlJob, useRescanLinksJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';

interface StepProps {
  project: Project;
}

// --- Tree Building Logic ---
interface SourceNode extends ProjectSource {
  children: SourceNode[];
}

const buildSourceTree = (
  sources: ProjectSource[],
  hierarchy: { parent_source_id: string; child_source_id: string }[]
) => {
  const sourceMap = new Map<string, SourceNode>(sources.map((s) => [s.id, { ...s, children: [] }]));
  const rootSources: SourceNode[] = [];
  const childrenIds = new Set<string>();

  hierarchy.forEach((rel) => {
    const parent = sourceMap.get(rel.parent_source_id);
    const child = sourceMap.get(rel.child_source_id);
    if (parent && child) {
      parent.children.push(child);
      childrenIds.add(child.id);
    }
  });

  sourceMap.forEach((source) => {
    if (!childrenIds.has(source.id)) {
      rootSources.push(source);
    }
  });

  return rootSources;
};

// --- Recursive Tree Rendering Component ---
const SourceTreeItem = memo(
  ({
    node,
    level,
    onEdit,
    onDelete,
    onToggleSelect,
    isSelected,
    selectedSourceIds, // Pass the full array for child checking
  }: {
    node: SourceNode;
    level: number;
    onEdit: (source: ProjectSource) => void;
    onDelete: (source: ProjectSource) => void;
    onToggleSelect: (id: string, checked: boolean) => void;
    isSelected: boolean;
    selectedSourceIds: string[];
  }) => {
    const [isOpen, { toggle }] = useDisclosure(true);

    return (
      <Box>
        <Group justify="space-between" wrap="nowrap" py={4}>
          <Group gap="xs" wrap="nowrap">
            <Checkbox checked={isSelected} onChange={(e) => onToggleSelect(node.id, e.currentTarget.checked)} />
            {node.children.length > 0 && (
              <ActionIcon variant="subtle" size="sm" onClick={toggle}>
                <IconChevronRight
                  size={16}
                  style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 200ms ease' }}
                />
              </ActionIcon>
            )}
            <Text fw={500} truncate style={{ paddingLeft: level * 20 }}>
              {node.url}
            </Text>
          </Group>
          <Group gap="xs" wrap="nowrap">
            {node.last_crawled_at && <Badge variant="light">Crawled</Badge>}
            <ActionIcon variant="subtle" onClick={() => onEdit(node)}>
              <IconPencil size={16} />
            </ActionIcon>
            <ActionIcon variant="subtle" color="red" onClick={() => onDelete(node)}>
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        </Group>

        {isOpen && node.children.length > 0 && (
          <Box pl="md">
            {node.children.map((child) => (
              <SourceTreeItem
                key={child.id}
                node={child}
                level={level + 1}
                onEdit={onEdit}
                onDelete={onDelete}
                onToggleSelect={onToggleSelect}
                isSelected={selectedSourceIds.includes(child.id)}
                selectedSourceIds={selectedSourceIds}
              />
            ))}
          </Box>
        )}
      </Box>
    );
  }
);

export function ManageSourcesStep({ project }: StepProps) {
  const { data: sources, isLoading: isLoadingSources } = useProjectSources(project.id);
  const { data: hierarchy, isLoading: isLoadingHierarchy } = useProjectSourceHierarchy(project.id);

  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [selectedSource, setSelectedSource] = useState<ProjectSource | null>(null);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const modals = useModals();

  const deleteSourceMutation = useDeleteProjectSource(project.id);
  const deleteSourcesBulkMutation = useDeleteProjectSourcesBulk(project.id);
  const discoverAndCrawlMutation = useDiscoverAndCrawlJob();
  const rescanMutation = useRescanLinksJob();

  const { job: latestDiscoverJob } = useLatestJob(project.id, 'discover_and_crawl_sources');
  const { job: latestRescanJob } = useLatestJob(project.id, 'rescan_links');

  const isDiscoverJobActive = latestDiscoverJob?.status === 'pending' || latestDiscoverJob?.status === 'in_progress';
  const isRescanJobActive = latestRescanJob?.status === 'pending' || latestRescanJob?.status === 'in_progress';
  const isAnyCrawlJobActive = isDiscoverJobActive || isRescanJobActive;

  const sourceTree = useMemo(() => buildSourceTree(sources || [], hierarchy || []), [sources, hierarchy]);
  const allSourceIds = useMemo(() => (sources || []).map((s) => s.id), [sources]);

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

  const openBulkDeleteModal = () =>
    modals.openConfirmModal({
      title: 'Delete Selected Sources',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete the <strong>{selectedSourceIds.length}</strong> selected sources? This action
          is irreversible.
        </Text>
      ),
      labels: { confirm: 'Delete Sources', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => {
        deleteSourcesBulkMutation.mutate(
          { projectId: project.id, source_ids: selectedSourceIds },
          {
            onSuccess: () => {
              setSelectedSourceIds([]);
            },
          }
        );
      },
    });

  const handleToggleSelect = (id: string, checked: boolean) => {
    setSelectedSourceIds((prev) => (checked ? [...prev, id] : prev.filter((sid) => sid !== id)));
  };

  const handleDiscoverAndCrawlClick = () => {
    const selectedIdsSet = new Set(selectedSourceIds);
    const childToParentMap = new Map<string, string>();
    (hierarchy || []).forEach((rel) => {
      childToParentMap.set(rel.child_source_id, rel.parent_source_id);
    });

    const topLevelSelectedIds = selectedSourceIds.filter((id) => {
      let currentId = id;
      while (childToParentMap.has(currentId)) {
        const parentId = childToParentMap.get(currentId)!;
        if (selectedIdsSet.has(parentId)) {
          // An ancestor is selected, so this node should be excluded.
          return false;
        }
        currentId = parentId;
      }
      // No selected ancestor was found up the chain.
      return true;
    });

    const selectedSources = sources?.filter((s) => topLevelSelectedIds.includes(s.id)) || [];
    const hasDeepCrawl = selectedSources.some((s) => s.max_crawl_depth > 1);

    const mutationPayload = { project_id: project.id, source_ids: topLevelSelectedIds };
    const executeMutation = () => discoverAndCrawlMutation.mutate(mutationPayload);

    if (hasDeepCrawl) {
      const maxDepthSource = selectedSources.reduce(
        (max, s) => (s.max_crawl_depth > max.max_crawl_depth ? s : max),
        selectedSources[0]
      );

      modals.openConfirmModal({
        title: 'Confirm Deep Crawl',
        centered: true,
        children: (
          <Stack>
            <Text size="sm">
              One or more selected sources has a crawl depth greater than 1 (max is{' '}
              <strong>{maxDepthSource.max_crawl_depth}</strong>).
            </Text>
            <Text size="sm">
              This will recursively discover and process sub-categories, which may result in multiple API calls during
              this discovery step and could find a very large number of links for the next step.
            </Text>
            <Text size="sm" fw={700}>
              Are you sure you want to proceed?
            </Text>
          </Stack>
        ),
        labels: { confirm: 'Start Discovery', cancel: 'Cancel' },
        confirmProps: { color: 'blue' },
        onConfirm: executeMutation,
      });
    } else {
      executeMutation();
    }
  };

  if (!project.search_params) {
    return <Text c="dimmed">Complete the previous step to add and manage sources.</Text>;
  }

  if (isLoadingSources || isLoadingHierarchy) return <Loader />;

  return (
    <>
      <ProjectSourceModal opened={modalOpened} onClose={closeModal} projectId={project.id} source={selectedSource} />
      <Stack>
        <Group justify="space-between">
          <Text>Add sources, then select them to discover sub-categories and crawl for links.</Text>
          <Button onClick={handleOpenCreateModal}>Add New Source</Button>
        </Group>

        <Group>
          <Button
            leftSection={<IconPlayerPlay size={14} />}
            disabled={selectedSourceIds.length === 0 || isAnyCrawlJobActive}
            onClick={handleDiscoverAndCrawlClick}
            loading={discoverAndCrawlMutation.isPending || isDiscoverJobActive}
          >
            Discover & Scan ({selectedSourceIds.length})
          </Button>
          <Button
            variant="outline"
            leftSection={<IconRefresh size={14} />}
            disabled={selectedSourceIds.length === 0 || isAnyCrawlJobActive}
            onClick={() => rescanMutation.mutate({ project_id: project.id, source_ids: selectedSourceIds })}
            loading={rescanMutation.isPending || isRescanJobActive}
          >
            Rescan Selected ({selectedSourceIds.length})
          </Button>
          <Button
            variant="outline"
            color="red"
            leftSection={<IconTrash size={14} />}
            disabled={selectedSourceIds.length === 0 || deleteSourcesBulkMutation.isPending || isAnyCrawlJobActive}
            onClick={openBulkDeleteModal}
            loading={deleteSourcesBulkMutation.isPending}
          >
            Delete Selected ({selectedSourceIds.length})
          </Button>
        </Group>

        <JobStatusIndicator job={latestDiscoverJob} title="Discover & Scan Job Status" />
        <JobStatusIndicator job={latestRescanJob} title="Rescan Job Status" />

        <Paper withBorder p="md" mt="md">
          {sourceTree.length > 0 && (
            <Group mb="sm">
              <Checkbox
                label="Select / Deselect All"
                checked={allSourceIds.length > 0 && selectedSourceIds.length === allSourceIds.length}
                indeterminate={selectedSourceIds.length > 0 && selectedSourceIds.length < allSourceIds.length}
                onChange={(e) => setSelectedSourceIds(e.currentTarget.checked ? allSourceIds : [])}
              />
            </Group>
          )}
          {sourceTree.length > 0 ? (
            sourceTree.map((node) => (
              <SourceTreeItem
                key={node.id}
                node={node}
                level={0}
                onEdit={handleOpenEditModal}
                onDelete={openDeleteModal}
                onToggleSelect={handleToggleSelect}
                isSelected={selectedSourceIds.includes(node.id)}
                selectedSourceIds={selectedSourceIds}
              />
            ))
          ) : (
            <Text c="dimmed" ta="center" p="md">
              No sources have been added yet.
            </Text>
          )}
        </Paper>
      </Stack>
    </>
  );
}
