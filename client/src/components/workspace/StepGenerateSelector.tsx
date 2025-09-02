import { Stack, Text, Button, Paper, Code, Group, Accordion, ThemeIcon } from '@mantine/core';
import { IconLink } from '@tabler/icons-react';
import { useGenerateSelectorJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';

interface StepProps {
  project: Project;
}

export function StepGenerateSelector({ project }: StepProps) {
  const generateSelector = useGenerateSelectorJob();
  const { job: latestSelectorJob } = useLatestJob(project.id, 'generate_selector');

  const handleGenerate = () => {
    generateSelector.mutate({ project_id: project.id });
  };

  const isUnlocked = !!project.search_params;
  const isProcessed = project.status !== 'draft' && project.status !== 'search_params_generated';
  const selectorResult = latestSelectorJob?.result as { selectors: Record<string, string[]> } | undefined;

  if (!isUnlocked) {
    return <Text c="dimmed">Complete the previous step to generate selectors.</Text>;
  }

  return (
    <Stack>
      <Text>
        Next, the AI will analyze the HTML of your source URL and your search parameters to propose CSS selectors for
        finding content links.
      </Text>

      <Paper withBorder p="md" bg="dark.6">
        <Text size="sm">
          <Text span fw={700}>
            Source URL:
          </Text>{' '}
          {project.source_url}
        </Text>
      </Paper>

      <Group justify="flex-end">
        <Button onClick={handleGenerate} loading={generateSelector.isPending}>
          {isProcessed ? 'Re-generate Selector' : 'Generate Selector'}
        </Button>
      </Group>

      <JobStatusIndicator job={latestSelectorJob} title="Selector Job Status" />

      {selectorResult && (
        <Paper withBorder p="md" mt="md">
          <Text fw={500} mb="sm">
            Generated Selectors & Matched Links:
          </Text>
          <Accordion variant="separated">
            {Object.entries(selectorResult.selectors).map(([selector, urls]) => (
              <Accordion.Item value={selector} key={selector}>
                <Accordion.Control>
                  <Code>{selector}</Code> ({urls.length} links found)
                </Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="xs">
                    {urls.slice(0, 10).map((url, i) => (
                      <Group key={i} gap="xs" wrap="nowrap">
                        <ThemeIcon size={20} variant="light">
                          <IconLink size={14} />
                        </ThemeIcon>
                        <Text size="xs" truncate>
                          {url}
                        </Text>
                      </Group>
                    ))}
                    {urls.length > 10 && (
                      <Text size="xs" c="dimmed">
                        ...and {urls.length - 10} more.
                      </Text>
                    )}
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Paper>
      )}
    </Stack>
  );
}
