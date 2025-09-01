import { useState } from 'react';
import { Modal, Table, Loader, Alert, Pagination, Group, Text, Tooltip } from '@mantine/core';
import { IconAlertCircle, IconCircleCheck, IconCircleX } from '@tabler/icons-react';
import { useProjectApiRequestLogs } from '../../hooks/useProjectApiRequestLogs';
import { formatDate } from '../../utils/formatDate';

interface ApiRequestLogModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
}

const PAGE_SIZE = 30;

export function ApiRequestLogModal({ opened, onClose, projectId }: ApiRequestLogModalProps) {
  const [activePage, setPage] = useState(1);
  const { data, isLoading, isError, error } = useProjectApiRequestLogs(projectId, {
    page: activePage,
    pageSize: PAGE_SIZE,
  });

  const logs = data?.data || [];
  const totalItems = data?.meta.total_items || 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);

  return (
    <Modal opened={opened} onClose={onClose} title="API Request Logs" size="90%">
      {isLoading && <Loader />}
      {isError && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error!" color="red">
          Failed to load API logs: {error.message}
        </Alert>
      )}
      {!isLoading && !isError && (
        <>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Status</Table.Th>
                <Table.Th>Timestamp</Table.Th>
                <Table.Th>Model</Table.Th>
                <Table.Th>Input Tokens</Table.Th>
                <Table.Th>Output Tokens</Table.Th>
                <Table.Th>Cost ($)</Table.Th>
                <Table.Th>Latency (ms)</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {logs.map((log) => (
                <Table.Tr key={log.id}>
                  <Table.Td>
                    <Tooltip label={log.error ? 'Failed' : 'Success'}>
                      {log.error ? <IconCircleX color="red" /> : <IconCircleCheck color="green" />}
                    </Tooltip>
                  </Table.Td>
                  <Table.Td>{formatDate(log.timestamp)}</Table.Td>
                  <Table.Td>{log.model_used}</Table.Td>
                  <Table.Td>{log.input_tokens ?? 'N/A'}</Table.Td>
                  <Table.Td>{log.output_tokens ?? 'N/A'}</Table.Td>
                  <Table.Td>{log.calculated_cost?.toFixed(6) ?? 'N/A'}</Table.Td>
                  <Table.Td>{log.latency_ms}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {logs.length === 0 && (
            <Text c="dimmed" ta="center" p="md">
              No API requests have been logged for this project.
            </Text>
          )}
          {totalPages > 1 && (
            <Group justify="center" mt="md">
              <Pagination value={activePage} onChange={setPage} total={totalPages} />
            </Group>
          )}
        </>
      )}
    </Modal>
  );
}
