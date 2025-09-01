import {
  Modal,
  Loader,
  Alert,
  SimpleGrid,
  Paper,
  Text,
  Title,
  Group,
  Progress,
  Tooltip,
  Stack,
  Box,
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useProjectAnalytics } from '../../hooks/useProjectAnalytics';
import type { JobStatus, LinkStatus } from '../../types';

interface ProjectAnalyticsModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text c="dimmed" size="xs" tt="uppercase" fw={700}>
        {title}
      </Text>
      <Text fw={700} size="xl">
        {value}
      </Text>
    </Paper>
  );
}

const linkStatusColors: Record<LinkStatus, string> = {
  pending: 'gray',
  processing: 'yellow',
  completed: 'green',
  failed: 'red',
};

const jobStatusColors: Record<JobStatus, string> = {
  pending: 'gray',
  in_progress: 'blue',
  completed: 'green',
  failed: 'red',
  cancelling: 'yellow',
  canceled: 'orange',
};

export function ProjectAnalyticsModal({ opened, onClose, projectId }: ProjectAnalyticsModalProps) {
  const { data, isLoading, isError, error } = useProjectAnalytics(projectId);
  const analytics = data?.data;

  return (
    <Modal opened={opened} onClose={onClose} title="Project Analytics" size="xl">
      {isLoading && <Loader />}
      {isError && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error!" color="red">
          Failed to load analytics: {error.message}
        </Alert>
      )}
      {analytics && (
        <>
          <Title order={4} mb="md">
            Usage & Cost
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <StatCard title="Total Requests" value={analytics.total_requests} />
            <StatCard title="Total Cost" value={`$${analytics.total_cost.toFixed(6)}`} />
            <StatCard title="Avg. Latency" value={`${analytics.average_latency_ms.toFixed(0)} ms`} />
            <StatCard title="Input Tokens" value={analytics.total_input_tokens} />
            <StatCard title="Output Tokens" value={analytics.total_output_tokens} />
          </SimpleGrid>

          <Title order={4} mt="xl" mb="md">
            Project Status
          </Title>
          <StatCard title="Lorebook Entries" value={analytics.total_lorebook_entries} />

          <Title order={5} mt="lg">
            Link Statuses
          </Title>
          <Stack gap="xs" mt="xs">
            <Progress.Root size="xl">
              {Object.entries(analytics.link_status_counts)
                .filter(([, count]) => count > 0)
                .map(([status, count]) => (
                  <Tooltip
                    key={status}
                    label={`${status.charAt(0).toUpperCase() + status.slice(1)}: ${count}`}
                    withArrow
                  >
                    <Progress.Section
                      value={(count / analytics.total_links) * 100}
                      color={linkStatusColors[status as LinkStatus]}
                    />
                  </Tooltip>
                ))}
            </Progress.Root>
            <Group gap="sm">
              {Object.entries(linkStatusColors).map(([status, color]) => (
                <Group key={status} gap={4}>
                  <Box w={12} h={12} bg={color} style={{ borderRadius: '50%' }} />
                  <Text size="xs" c="dimmed">
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </Text>
                </Group>
              ))}
            </Group>
          </Stack>

          <Title order={5} mt="lg">
            Job Statuses
          </Title>
          <Stack gap="xs" mt="xs">
            <Progress.Root size="xl">
              {Object.entries(analytics.job_status_counts)
                .filter(([, count]) => count > 0)
                .map(([status, count]) => (
                  <Tooltip
                    key={status}
                    label={`${status.charAt(0).toUpperCase() + status.slice(1)}: ${count}`}
                    withArrow
                  >
                    <Progress.Section
                      value={(count / analytics.total_jobs) * 100}
                      color={jobStatusColors[status as JobStatus]}
                    />
                  </Tooltip>
                ))}
            </Progress.Root>
            <Group gap="sm">
              {Object.entries(jobStatusColors).map(([status, color]) => (
                <Group key={status} gap={4}>
                  <Box w={12} h={12} bg={color} style={{ borderRadius: '50%' }} />
                  <Text size="xs" c="dimmed">
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </Text>
                </Group>
              ))}
            </Group>
          </Stack>
        </>
      )}
    </Modal>
  );
}
