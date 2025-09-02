import { useEffect } from 'react';
import { Stack, Text, Button, Paper, Code, Group, Accordion, TextInput, NumberInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useGenerateSelectorJob } from '../../hooks/useJobMutations';
import { useUpdateProject } from '../../hooks/useProjectMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import type { Project } from '../../types';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { notifications } from '@mantine/notifications';

interface StepProps {
  project: Project;
}

interface FormValues {
  source_url: string;
  max_pages_to_crawl: number;
}

export function StepGenerateSelector({ project }: StepProps) {
  const generateSelector = useGenerateSelectorJob();
  const updateProjectMutation = useUpdateProject();
  const { job: latestSelectorJob } = useLatestJob(project.id, 'generate_selector');

  const form = useForm<FormValues>({
    initialValues: {
      source_url: project.source_url || '',
      max_pages_to_crawl: project.max_pages_to_crawl || 20,
    },
    validate: {
      source_url: (value) => (value.trim().length > 0 ? null : 'Source URL cannot be empty'),
    },
  });

  useEffect(() => {
    form.setValues({
      source_url: project.source_url || '',
      max_pages_to_crawl: project.max_pages_to_crawl || 20,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const handleGenerate = () => {
    generateSelector.mutate({ project_id: project.id });
  };

  const handleSaveChanges = (values: FormValues) => {
    updateProjectMutation.mutate(
      { projectId: project.id, data: values },
      {
        onSuccess: () => {
          notifications.show({ title: 'Saved', message: 'Project settings updated.', color: 'green' });
          form.resetDirty();
        },
      }
    );
  };

  const isUnlocked = !!project.search_params;
  const selectorResult = latestSelectorJob?.result as
    | { selectors: string[]; found_urls: string[]; pagination_selector?: string }
    | undefined;
  const isJobActive = latestSelectorJob?.status === 'pending' || latestSelectorJob?.status === 'in_progress';
  const hasUnsavedChanges = form.isDirty();

  if (!isUnlocked) {
    return <Text c="dimmed">Complete the previous step to generate selectors.</Text>;
  }

  return (
    <Stack>
      <Text>
        The AI will analyze your source URL to propose CSS selectors. The system will then use these selectors to crawl
        the site and find all links.
      </Text>

      <form onSubmit={form.onSubmit(handleSaveChanges)}>
        <Paper withBorder p="md">
          <Stack>
            <TextInput
              label="Source URL"
              placeholder="https://example.com/category/items"
              {...form.getInputProps('source_url')}
            />
            <NumberInput
              label="Max Pages to Crawl"
              description="The maximum number of pages to follow via pagination links. Set to 1 to disable."
              min={1}
              max={100}
              {...form.getInputProps('max_pages_to_crawl')}
            />
          </Stack>
        </Paper>

        <Group justify="flex-end">
          {hasUnsavedChanges && (
            <Button type="submit" loading={updateProjectMutation.isPending} variant="outline">
              Save Changes
            </Button>
          )}
          <Button
            onClick={handleGenerate}
            loading={generateSelector.isPending || isJobActive}
            disabled={generateSelector.isPending || isJobActive || hasUnsavedChanges}
            title={hasUnsavedChanges ? 'You have unsaved changes' : ''}
          >
            {isJobActive ? 'Crawling...' : 'Generate Selectors & Find Links'}
          </Button>
        </Group>
      </form>

      <JobStatusIndicator job={latestSelectorJob} title="Selector Generation & Crawl Status" />

      {selectorResult && (
        <Paper withBorder p="md" mt="md">
          <Text fw={500} mb="sm">
            Crawl Complete: Found {selectorResult.found_urls.length} unique links.
          </Text>
          <Accordion variant="separated">
            <Accordion.Item value="summary">
              <Accordion.Control>Selectors Used for Crawl</Accordion.Control>
              <Accordion.Panel>
                <Stack gap="xs">
                  <Text size="sm" fw={500}>
                    Content Selectors:
                  </Text>
                  {selectorResult.selectors.map((selector) => (
                    <Code key={selector}>{selector}</Code>
                  ))}
                  {selectorResult.pagination_selector && (
                    <>
                      <Text size="sm" fw={500} mt="xs">
                        Pagination Selector:
                      </Text>
                      <Code>{selectorResult.pagination_selector}</Code>
                    </>
                  )}
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Paper>
      )}
    </Stack>
  );
}
