import {
  Modal,
  TextInput,
  Button,
  Group,
  Stack,
  Textarea,
  NumberInput,
  Select,
  Text,
  Accordion,
  Loader,
  ActionIcon,
  Tooltip,
  Slider,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useCreateProject, useUpdateProject } from '../../hooks/useProjectMutations';
import type { CreateProjectPayload, Project, Credential } from '../../types';
import { useProviders } from '../../hooks/useProviders';
import { useEffect, useMemo, useState } from 'react';
import { useGlobalTemplates } from '../../hooks/useGlobalTemplates';
import { LazyMonacoEditorInput } from '../common/LazyMonacoEditorInput';
import { useCredentials } from '../../hooks/useCredentials';
import { useDisclosure } from '@mantine/hooks';
import { IconPlus } from '@tabler/icons-react';
import { CredentialModal } from '../credentials/CredentialModal';

interface ProjectModalProps {
  opened: boolean;
  onClose: () => void;
  project: Project | null;
}

const slugify = (text: string) =>
  text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^\w-]+/g, '')
    .replace(/--+/g, '-');

export function ProjectModal({ opened, onClose, project }: ProjectModalProps) {
  const isEditMode = !!project;
  const createProjectMutation = useCreateProject();
  const updateProjectMutation = useUpdateProject();

  const { data: credentials, isLoading: isLoadingCredentials } = useCredentials();
  const { data: providers, isLoading: isLoadingProviders } = useProviders();
  const { data: globalTemplates, isLoading: isLoadingTemplates } = useGlobalTemplates({ page: 1, pageSize: 9999 });

  const [credentialModalOpened, { open: openCredentialModal, close: closeCredentialModal }] = useDisclosure(false);
  const [selectedCredentialId, setSelectedCredentialId] = useState<string | null>(null);

  const form = useForm<CreateProjectPayload>({
    initialValues: {
      id: '',
      name: '',
      prompt: '',
      requests_per_minute: 15,
      credential_id: undefined,
      model_name: undefined,
      model_parameters: { temperature: 0.7 },
      templates: { search_params_generation: '', selector_generation: '', entry_creation: '' },
    },
    validate: {
      name: (value) => (value.trim().length < 3 ? 'Name must be at least 3 characters long' : null),
      id: (value) => (/^[a-z0-9-]+$/.test(value) ? null : 'ID must be lowercase, numbers, and dashes only'),
      credential_id: (value) => (value ? null : 'Credential is required'),
      model_name: (value) => (value ? null : 'Model is required'),
    },
  });

  useEffect(() => {
    if (isEditMode && project) {
      form.setValues({
        ...project,
        prompt: project.prompt || '',
        model_parameters: project.model_parameters || { temperature: 0.7 },
      });
      setSelectedCredentialId(project.credential_id || null);
    } else if (!isEditMode && globalTemplates?.data) {
      const templates = globalTemplates.data;
      const getTemplate = (id: string) => templates.find((t) => t.id === id)?.content || '';
      form.reset();
      form.setFieldValue('templates.search_params_generation', getTemplate('search-params-prompt'));
      form.setFieldValue('templates.selector_generation', getTemplate('selector-prompt'));
      form.setFieldValue('templates.entry_creation', getTemplate('entry-creation-prompt'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, opened, globalTemplates?.data]);

  const credentialOptions = useMemo(
    () =>
      credentials?.map((c) => ({
        value: c.id,
        label: c.name,
      })) || [],
    [credentials]
  );

  const selectedCredential = useMemo(
    () => credentials?.find((c) => c.id === selectedCredentialId),
    [credentials, selectedCredentialId]
  );

  const selectedProvider = useMemo(
    () => providers?.find((p) => p.id === selectedCredential?.provider_type),
    [providers, selectedCredential]
  );

  const modelOptions = useMemo(
    () => selectedProvider?.models.map((m) => ({ value: m.id, label: m.name })) || [],
    [selectedProvider]
  );

  const isOaiCompatible = selectedCredential?.provider_type === 'openai_compatible';
  const isModelSelectDisabled = !selectedCredentialId || (modelOptions.length === 0 && !isOaiCompatible);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newName = event.currentTarget.value;
    form.setFieldValue('name', newName);
    if (!isEditMode) {
      form.setFieldValue('id', slugify(newName));
    }
  };

  const handleCredentialChange = (value: string | null) => {
    setSelectedCredentialId(value);
    form.setFieldValue('credential_id', value || undefined);
    form.setFieldValue('model_name', ''); // Reset model on credential change
  };

  const handleCredentialCreated = (newCredential: Credential) => {
    // This function is called by the CredentialModal on success
    // It updates the form with the newly created credential
    form.setFieldValue('credential_id', newCredential.id);
    setSelectedCredentialId(newCredential.id);
  };

  const handleSubmit = (values: CreateProjectPayload) => {
    if (isEditMode && project) {
      updateProjectMutation.mutate({ projectId: project.id, data: values }, { onSuccess: onClose });
    } else {
      createProjectMutation.mutate(values, { onSuccess: onClose });
    }
  };

  const isLoadingMutation = createProjectMutation.isPending || updateProjectMutation.isPending;

  const credentialLabel = (
    <Group justify="space-between" w="100%">
      <Text component="span">Credential</Text>
      <Tooltip label="Add new credential" withArrow position="top-end">
        <ActionIcon
          onClick={openCredentialModal}
          variant="subtle"
          size="xs"
          disabled={isLoadingCredentials}
          aria-label="Add new credential"
        >
          <IconPlus size={16} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );

  return (
    <>
      <CredentialModal
        opened={credentialModalOpened}
        onClose={closeCredentialModal}
        credential={null}
        onSuccess={handleCredentialCreated}
      />
      <Modal
        opened={opened}
        onClose={onClose}
        title={<Text fw={700}>{isEditMode ? 'Edit Project' : 'Create New Project'}</Text>}
        size="xl"
        centered
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="md">
            <TextInput
              withAsterisk
              label="Project Name"
              placeholder="e.g., Skyrim Locations Lorebook"
              {...form.getInputProps('name')}
              onChange={handleNameChange}
            />
            <TextInput
              withAsterisk
              label="Project ID"
              placeholder="auto-generated-from-name"
              {...form.getInputProps('id')}
              disabled={isEditMode}
            />
            <Textarea
              label="High-level Prompt"
              description="A general prompt describing the overall goal of the lorebook."
              placeholder="e.g., 'All major and minor locations in Skyrim'"
              {...form.getInputProps('prompt')}
              autosize
              minRows={2}
            />

            <Group grow>
              <Select
                withAsterisk
                label={credentialLabel}
                placeholder="Select a credential"
                data={credentialOptions}
                disabled={isLoadingCredentials}
                rightSection={isLoadingCredentials ? <Loader size="xs" /> : null}
                {...form.getInputProps('credential_id')}
                onChange={handleCredentialChange}
              />
              {isOaiCompatible ? (
                <TextInput
                  withAsterisk
                  label="Model"
                  placeholder="Enter a custom model name..."
                  disabled={isModelSelectDisabled}
                  {...form.getInputProps('model_name')}
                />
              ) : (
                <Select
                  withAsterisk
                  label="Model"
                  placeholder="Select a model"
                  data={modelOptions}
                  disabled={isModelSelectDisabled || isLoadingProviders}
                  rightSection={isLoadingProviders ? <Loader size="xs" /> : null}
                  searchable
                  nothingFoundMessage="No models found"
                  {...form.getInputProps('model_name')}
                />
              )}
            </Group>

            <div>
              <Text size="sm" fw={500}>
                Temperature
              </Text>
              <Slider
                min={0}
                max={2}
                step={0.05}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' },
                ]}
                label={(value) => value.toFixed(2)}
                {...form.getInputProps('model_parameters.temperature')}
              />
            </div>

            <NumberInput
              label="Requests Per Minute"
              description="Rate limit for AI API calls across the entire project."
              defaultValue={15}
              min={1}
              max={300}
              {...form.getInputProps('requests_per_minute')}
            />

            <Accordion variant="separated" defaultValue="templates">
              <Accordion.Item value="templates">
                <Accordion.Control>
                  <Text fw={500}>Advanced: Prompt Templates</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  {isLoadingTemplates ? (
                    <Loader />
                  ) : (
                    <Stack>
                      <LazyMonacoEditorInput
                        label="Search Params Generation"
                        language="handlebars"
                        height={200}
                        {...form.getInputProps('templates.search_params_generation')}
                      />
                      <LazyMonacoEditorInput
                        label="Selector Generation"
                        language="handlebars"
                        height={200}
                        {...form.getInputProps('templates.selector_generation')}
                      />
                      <LazyMonacoEditorInput
                        label="Entry Creation"
                        language="handlebars"
                        height={200}
                        {...form.getInputProps('templates.entry_creation')}
                      />
                    </Stack>
                  )}
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={isLoadingMutation}>
                {isEditMode ? 'Save Changes' : 'Create Project'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </>
  );
}
