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
import { IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';
import { useProjectAnalytics } from '../../hooks/useProjectAnalytics';
import type { JobStatus, LinkStatus } from '../../types';

interface ProjectAnalyticsModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
}

function StatCard({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text c="dimmed" size="xs" tt="uppercase" fw={700}>
        {title}
      </Text>
      <Box mt={4}>{value}</Box>
    </Paper>
  );
}

const linkStatusColors: Record<LinkStatus, string> = {
  pending: 'gray',
  processing: 'yellow',
  completed: 'green',
  failed: 'red',
  skipped: 'yellow',
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
            <StatCard
              title="Total Requests"
              value={
                <Text fw={700} size="xl">
                  {analytics.total_requests}
                </Text>
              }
            />
            <StatCard
              title="Total Cost"
              value={
                <Group gap="xs" align="center">
                  <Text fw={700} size="xl">
                    ${analytics.total_cost.toFixed(6)}
                  </Text>
                  {analytics.has_unknown_costs && (
                    <Tooltip
                      label="Total is partial as some requests used models with unknown pricing."
                      withArrow
                      multiline
                      w={220}
                    >
                      <IconInfoCircle size={18} style={{ color: 'var(--mantine-color-yellow-5)' }} />
                    </Tooltip>
                  )}
                </Group>
              }
            />
            <StatCard
              title="Avg. Latency"
              value={
                <Text fw={700} size="xl">
                  {`${analytics.average_latency_ms.toFixed(0)} ms`}
                </Text>
              }
            />
            <StatCard
              title="Input Tokens"
              value={
                <Text fw={700} size="xl">
                  {analytics.total_input_tokens}
                </Text>
              }
            />
            <StatCard
              title="Output Tokens"
              value={
                <Text fw={700} size="xl">
                  {analytics.total_output_tokens}
                </Text>
              }
            />
          </SimpleGrid>

          <Title order={4} mt="xl" mb="md">
            Project Status
          </Title>
          <StatCard
            title="Lorebook Entries"
            value={
              <Text fw={700} size="xl">
                {analytics.total_lorebook_entries}
              </Text>
            }
          />

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
