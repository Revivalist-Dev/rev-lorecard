import { Stack, Text, Textarea, Button, Paper, Group } from '@mantine/core';
import type { Project, SearchParams } from '../../types';
import { useGenerateSearchParamsJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { useForm } from '@mantine/form';
import { useUpdateProject } from '../../hooks/useProjectMutations';
import { useEffect } from 'react';
import { notifications } from '@mantine/notifications';

interface StepProps {
  project: Project;
}

interface FormValues {
  prompt: string;
  search_params: SearchParams;
}

export function StepGenerateSearchParams({ project }: StepProps) {
  const generateSearchParams = useGenerateSearchParamsJob();
  const updateProjectMutation = useUpdateProject();
  const { job } = useLatestJob(project.id, 'generate_search_params');

  const form = useForm<FormValues>({
    initialValues: {
      prompt: project.prompt || '',
      search_params: project.search_params || { purpose: '', extraction_notes: '', criteria: '' },
    },
  });

  // Re-sync form when project data changes from outside (e.g., after generation)
  useEffect(() => {
    form.setValues({
      prompt: project.prompt || '',
      search_params: project.search_params || { purpose: '', extraction_notes: '', criteria: '' },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const handleGenerate = () => {
    generateSearchParams.mutate({ project_id: project.id });
  };

  const handleSaveChanges = (values: FormValues) => {
    updateProjectMutation.mutate(
      { projectId: project.id, data: values },
      {
        onSuccess: () => {
          notifications.show({
            title: 'Saved',
            message: 'Your changes have been saved successfully.',
            color: 'green',
          });
        },
      }
    );
  };

  const hasBeenGenerated = !!project.search_params;
  const isDirty = form.isDirty();
  const isJobActive = job?.status === 'pending' || job?.status === 'in_progress';

  return (
    <form onSubmit={form.onSubmit(handleSaveChanges)}>
      <Stack>
        <Text>
          First, we'll use an AI to analyze your high-level prompt and generate structured search parameters. You can
          also edit these manually.
        </Text>
        <Textarea
          label="Your high-level prompt"
          placeholder="e.g., 'All major and minor locations in Skyrim'"
          autosize
          minRows={2}
          {...form.getInputProps('prompt')}
        />
        <Group justify="flex-end">
          <Button
            variant="default"
            onClick={handleGenerate}
            loading={generateSearchParams.isPending || isJobActive}
            disabled={!form.values.prompt || generateSearchParams.isPending || isJobActive || isDirty}
            title={isDirty ? 'You have unsaved changes' : ''}
          >
            {isJobActive ? 'Generating...' : hasBeenGenerated ? 'Re-generate Parameters' : 'Generate Search Parameters'}
          </Button>
          {isDirty && (
            <Button type="submit" loading={updateProjectMutation.isPending}>
              Save Changes
            </Button>
          )}
        </Group>

        <JobStatusIndicator job={job} title="Generation Job Status" />

        {hasBeenGenerated && (
          <Paper withBorder p="md" mt="md">
            <Stack>
              <Textarea
                label="Generated Purpose"
                autosize
                minRows={2}
                {...form.getInputProps('search_params.purpose')}
              />
              <Textarea
                label="Generated Extraction Notes"
                autosize
                minRows={3}
                {...form.getInputProps('search_params.extraction_notes')}
              />
              <Textarea
                label="Generated Criteria"
                autosize
                minRows={2}
                {...form.getInputProps('search_params.criteria')}
              />
            </Stack>
          </Paper>
        )}
      </Stack>
    </form>
  );
}
