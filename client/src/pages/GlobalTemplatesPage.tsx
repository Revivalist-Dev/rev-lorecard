import { Title, Table, Group, Text, ActionIcon, Stack, Skeleton, Button, Pagination } from '@mantine/core';
import { useGlobalTemplates } from '../hooks/useGlobalTemplates';
import { IconPencil, IconTrash } from '@tabler/icons-react';
import { formatDate } from '../utils/formatDate';
import { useDisclosure } from '@mantine/hooks';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { GlobalTemplate } from '../types';
import { useModals } from '@mantine/modals';
import { GlobalTemplateModal } from '../components/templates/GlobalTemplateModal';
import { useDeleteGlobalTemplate } from '../hooks/useGlobalTemplatesMutations';

const PAGE_SIZE = 25;

export function GlobalTemplatesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageFromUrl = parseInt(searchParams.get('page') || '1', 10);
  const [activePage, setPage] = useState(isNaN(pageFromUrl) ? 1 : pageFromUrl);

  const { data: templatesResponse, isLoading, error } = useGlobalTemplates({ page: activePage, pageSize: PAGE_SIZE });

  useEffect(() => {
    const newPageFromUrl = parseInt(searchParams.get('page') || '1', 10);
    const validPage = isNaN(newPageFromUrl) ? 1 : newPageFromUrl;
    if (validPage !== activePage) {
      setPage(validPage);
    }
  }, [searchParams, activePage]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSearchParams({ page: newPage.toString() });
  };

  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [selectedTemplate, setSelectedTemplate] = useState<GlobalTemplate | null>(null);
  const modals = useModals();
  const deleteTemplateMutation = useDeleteGlobalTemplate();

  const templates = templatesResponse?.data || [];
  const totalItems = templatesResponse?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  const openDeleteModal = (template: GlobalTemplate) =>
    modals.openConfirmModal({
      title: 'Delete Global Template',
      centered: true,
      children: (
        <Text size="sm">
          Are you sure you want to delete the template "<strong>{template.name}</strong>"? This action is irreversible.
        </Text>
      ),
      labels: { confirm: 'Delete Template', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => deleteTemplateMutation.mutate(template.id),
    });

  const handleOpenCreateModal = () => {
    setSelectedTemplate(null);
    openModal();
  };

  const handleOpenEditModal = (template: GlobalTemplate) => {
    setSelectedTemplate(template);
    openModal();
  };

  const rows = templates.map((template) => (
    <Table.Tr key={template.id}>
      <Table.Td>
        <Text fw={500}>{template.name}</Text>
        <Text size="xs" c="dimmed">
          {template.id}
        </Text>
      </Table.Td>
      <Table.Td>{formatDate(template.updated_at)}</Table.Td>
      <Table.Td>
        <Group gap="xs">
          <ActionIcon
            variant="subtle"
            onClick={() => handleOpenEditModal(template)}
            aria-label={`Edit ${template.name}`}
          >
            <IconPencil size={16} />
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            color="red"
            onClick={() => openDeleteModal(template)}
            aria-label={`Delete ${template.name}`}
            disabled={[
              'selector-prompt',
              'search-params-prompt',
              'entry-creation-prompt',
              'lorebook-definition',
            ].includes(template.id)}
          >
            <IconTrash size={16} />
          </ActionIcon>
        </Group>
      </Table.Td>
    </Table.Tr>
  ));

  const loadingRows = Array.from({ length: 5 }).map((_, index) => (
    <Table.Tr key={index}>
      <Table.Td>
        <Skeleton height={8} mt={6} width="70%" radius="xl" />
        <Skeleton height={8} mt={6} width="40%" radius="xl" />
      </Table.Td>
      <Table.Td>
        <Skeleton height={8} mt={6} width="60%" radius="xl" />
      </Table.Td>
      <Table.Td>
        <Skeleton height={16} width={16} radius="sm" />
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <>
      <GlobalTemplateModal opened={modalOpened} onClose={closeModal} template={selectedTemplate} />
      <Stack>
        <Group justify="space-between">
          <Title order={1}>Global Templates</Title>
          <Button onClick={handleOpenCreateModal}>Create New Template</Button>
        </Group>

        {error && <Text color="red">Failed to load templates: {error.message}</Text>}

        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name / ID</Table.Th>
              <Table.Th>Last Updated</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              loadingRows
            ) : rows?.length ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={3}>
                  <Text c="dimmed" ta="center">
                    No global templates found. Create one to get started!
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
        {totalPages > 1 && (
          <Group justify="center" mt="md">
            <Pagination value={activePage} onChange={handlePageChange} total={totalPages} />
          </Group>
        )}
      </Stack>
    </>
  );
}
