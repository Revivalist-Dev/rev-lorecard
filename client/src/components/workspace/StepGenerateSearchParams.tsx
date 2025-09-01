import { Stack, Text, Textarea, Button, Paper, Code, Group } from '@mantine/core';
import type { Project } from '../../types';
import { useGenerateSearchParamsJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';

interface StepProps {
  project: Project;
}

export function StepGenerateSearchParams({ project }: StepProps) {
  const generateSearchParams = useGenerateSearchParamsJob();
  const { job } = useLatestJob(project.id, 'generate_search_params');

  const handleGenerate = () => {
    generateSearchParams.mutate({ project_id: project.id });
  };

  const hasBeenProcessed = !!project.search_params;

  return (
    <Stack>
      <Text>
        First, we'll use an AI to analyze your high-level prompt and generate structured search parameters. This helps
        guide the next steps of the process more effectively.
      </Text>
      <Textarea label="Your high-level prompt" value={project.prompt || ''} readOnly autosize minRows={2} />
      <Group justify="flex-end">
        <Button onClick={handleGenerate} loading={generateSearchParams.isPending} disabled={hasBeenProcessed}>
          {hasBeenProcessed ? 'Generated' : 'Generate Search Parameters'}
        </Button>
      </Group>

      <JobStatusIndicator job={job} title="Generation Job Status" />

      {project.search_params && (
        <Paper withBorder p="md" mt="md">
          <Stack>
            <Text fw={500}>Generated Purpose:</Text>
            <Code block>{project.search_params.purpose}</Code>
            <Text fw={500}>Generated Extraction Notes:</Text>
            <Code block>{project.search_params.extraction_notes}</Code>
            <Text fw={500}>Generated Criteria:</Text>
            <Code block>{project.search_params.criteria}</Code>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
