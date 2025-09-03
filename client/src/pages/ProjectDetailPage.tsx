import { Title, Text, Paper, Stack, Stepper, Loader, Alert, Group, Button } from '@mantine/core';
import { useParams, useSearchParams } from 'react-router-dom';
import type { ProjectStatus } from '../types';
import { IconAlertCircle, IconChartBar, IconFileText, IconPencil } from '@tabler/icons-react';
import { StepGenerateSearchParams } from '../components/workspace/StepGenerateSearchParams';
import { ManageSourcesStep } from '../components/workspace/ManageSourcesStep';
import { StepConfirmLinks } from '../components/workspace/StepConfirmLinks';
import { StepProcessEntries } from '../components/workspace/StepProcessEntries';
import { useProject } from '../hooks/useProjects';
import { useSse } from '../hooks/useSse';
import { StepCompletedView } from '../components/workspace/StepCompletedView';
import { useDisclosure } from '@mantine/hooks';
import { ApiRequestLogModal } from '../components/projects/ApiRequestLogModal';
import { ProjectAnalyticsModal } from '../components/projects/ProjectAnalyticsModal';
import { ProjectModal } from '../components/projects/ProjectModal';
import { useEffect } from 'react';

const stepIdentifiers = ['search-params', 'sources', 'links', 'entries', 'completed'] as const;
type StepIdentifier = (typeof stepIdentifiers)[number];

const stepIdentifierToIndex: Record<StepIdentifier, number> = {
  'search-params': 0,
  sources: 1,
  links: 2,
  entries: 3,
  completed: 4,
};

const stepIndexToIdentifier = Object.fromEntries(
  Object.entries(stepIdentifierToIndex).map(([key, value]) => [value, key])
) as Record<number, StepIdentifier>;

const statusToStepIndex: Record<ProjectStatus, number> = {
  draft: 0,
  search_params_generated: 1,
  selector_generated: 2,
  links_extracted: 3,
  processing: 3,
  completed: 4,
  failed: 3,
};

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const [logsModalOpened, { open: openLogsModal, close: closeLogsModal }] = useDisclosure(false);
  const [analyticsModalOpened, { open: openAnalyticsModal, close: closeAnalyticsModal }] = useDisclosure(false);
  const [editModalOpened, { open: openEditModal, close: closeEditModal }] = useDisclosure(false);

  const { data: projectResponse, isLoading, error, isError } = useProject(projectId!);
  useSse(projectId!);

  const project = projectResponse?.data;

  const highestReachableStep = project ? statusToStepIndex[project.status] : 0;

  const stepFromUrl = searchParams.get('step') as StepIdentifier;
  const activeStep =
    stepFromUrl && stepIdentifiers.includes(stepFromUrl)
      ? stepIdentifierToIndex[stepFromUrl]
      : project
        ? statusToStepIndex[project.status]
        : 0;

  useEffect(() => {
    if (project && !searchParams.get('step')) {
      const stepIndexForStatus = statusToStepIndex[project.status];
      setSearchParams({ step: stepIndexToIdentifier[stepIndexForStatus] }, { replace: true });
    }
  }, [project, searchParams, setSearchParams]);

  const handleStepClick = (stepIndex: number) => {
    const newIdentifier = stepIndexToIdentifier[stepIndex];
    setSearchParams({ step: newIdentifier }, { replace: true });
  };

  if (isLoading && !projectResponse) {
    return <Loader />;
  }

  if (isError) {
    return (
      <Alert icon={<IconAlertCircle size="1rem" />} title="Error!" color="red">
        Failed to load project: {error.message}
      </Alert>
    );
  }

  if (!project) {
    return <Text>Project not found.</Text>;
  }

  const futureStepStyle = (stepIndex: number): React.CSSProperties => ({
    opacity: stepIndex > highestReachableStep ? 0.5 : 1,
    transition: 'opacity 300ms ease',
  });

  return (
    <>
      <ApiRequestLogModal opened={logsModalOpened} onClose={closeLogsModal} projectId={project.id} />
      <ProjectAnalyticsModal opened={analyticsModalOpened} onClose={closeAnalyticsModal} projectId={project.id} />
      <ProjectModal opened={editModalOpened} onClose={closeEditModal} project={project} />
      <Stack>
        <Group justify="space-between">
          <div>
            <Title order={1}>{project.name}</Title>
            <Text c="dimmed">ID: {project.id}</Text>
          </div>
          <Group>
            <Button variant="outline" leftSection={<IconFileText size={16} />} onClick={openLogsModal}>
              View API Logs
            </Button>
            <Button variant="outline" leftSection={<IconChartBar size={16} />} onClick={openAnalyticsModal}>
              View Analytics
            </Button>
            <Button variant="default" leftSection={<IconPencil size={16} />} onClick={openEditModal}>
              Edit Project
            </Button>
          </Group>
        </Group>

        <Paper withBorder p="xl" mt="lg" radius="md">
          <Stepper active={activeStep} onStepClick={handleStepClick}>
            <Stepper.Step label="Step 1" description="Search Params" style={futureStepStyle(0)}>
              <StepGenerateSearchParams project={project} />
            </Stepper.Step>
            <Stepper.Step label="Step 2" description="Manage Sources & Crawl" style={futureStepStyle(1)}>
              <ManageSourcesStep project={project} />
            </Stepper.Step>
            <Stepper.Step label="Step 3" description="Confirm Links" style={futureStepStyle(2)}>
              <StepConfirmLinks project={project} />
            </Stepper.Step>
            <Stepper.Step label="Step 4" description="Generate Entries" style={futureStepStyle(3)}>
              <StepProcessEntries project={project} />
            </Stepper.Step>
            <Stepper.Step label="Completed" description="Review & Download" style={futureStepStyle(4)}>
              <StepCompletedView project={project} />
            </Stepper.Step>
          </Stepper>
        </Paper>
      </Stack>
    </>
  );
}
