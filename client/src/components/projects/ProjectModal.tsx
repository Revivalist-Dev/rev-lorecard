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
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useCreateProject, useUpdateProject } from '../../hooks/useProjectMutations';
import type { CreateProjectPayload, Project } from '../../types';
import { useProviders } from '../../hooks/useProviders';
import { useEffect, useState } from 'react';
import { useGlobalTemplates } from '../../hooks/useGlobalTemplates';
import { LazyMonacoEditorInput } from '../common/LazyMonacoEditorInput';

interface ProjectModalProps {
  opened: boolean;
  onClose: () => void;
  project: Project | null; // Null for create, Project object for edit
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
  const { data: providers, isLoading: isLoadingProviders } = useProviders();
  const { data: globalTemplates, isLoading: isLoadingTemplates } = useGlobalTemplates({ page: 1, pageSize: 9999 });
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);

  const form = useForm<CreateProjectPayload>({
    initialValues: {
      id: '',
      name: '',
      prompt: '',
      requests_per_minute: 15,
      ai_provider_config: { api_provider: '', model_name: '', model_parameters: { temperature: 0.7 } },
      templates: { search_params_generation: '', selector_generation: '', entry_creation: '' },
    },
    validate: {
      name: (value) => (value.trim().length < 3 ? 'Name must be at least 3 characters long' : null),
      id: (value) => (/^[a-z0-9-]+$/.test(value) ? null : 'ID must be lowercase, numbers, and dashes only'),
      ai_provider_config: {
        api_provider: (value) => (value ? null : 'Provider is required'),
        model_name: (value) => (value ? null : 'Model is required'),
      },
    },
  });

  // Effect to populate form when in edit mode or reset when in create mode
  useEffect(() => {
    if (isEditMode && project) {
      form.setValues({
        ...project,
        prompt: project.prompt || '',
      });
      setSelectedProviderId(project.ai_provider_config.api_provider);
    } else if (!isEditMode && globalTemplates?.data) {
      // Set initial values for create mode
      const templates = globalTemplates.data;
      const getTemplate = (id: string) => templates.find((t) => t.id === id)?.content || '';
      form.reset();
      form.setFieldValue('templates.search_params_generation', getTemplate('search-params-prompt'));
      form.setFieldValue('templates.selector_generation', getTemplate('selector-prompt'));
      form.setFieldValue('templates.entry_creation', getTemplate('entry-creation-prompt'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, opened, globalTemplates?.data]);

  const providerOptions = providers?.map((p) => ({ value: p.id, label: p.name })) || [];
  const modelOptions =
    providers?.find((p) => p.id === selectedProviderId)?.models.map((m) => ({ value: m.id, label: m.name })) || [];

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newName = event.currentTarget.value;
    form.setFieldValue('name', newName);
    if (!isEditMode) {
      form.setFieldValue('id', slugify(newName));
    }
  };

  const handleProviderChange = (value: string | null) => {
    setSelectedProviderId(value);
    form.setFieldValue('ai_provider_config.api_provider', value || '');
    form.setFieldValue('ai_provider_config.model_name', '');
  };

  const handleSubmit = (values: CreateProjectPayload) => {
    if (isEditMode && project) {
      updateProjectMutation.mutate({ projectId: project.id, data: values }, { onSuccess: onClose });
    } else {
      createProjectMutation.mutate(values, { onSuccess: onClose });
    }
  };

  const isLoading = createProjectMutation.isPending || updateProjectMutation.isPending;

  return (
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
              label="AI Provider"
              placeholder="Select a provider"
              data={providerOptions}
              disabled={isLoadingProviders}
              rightSection={isLoadingProviders ? <Loader size="xs" /> : null}
              {...form.getInputProps('ai_provider_config.api_provider')}
              onChange={handleProviderChange}
            />
            <Select
              withAsterisk
              label="Model"
              placeholder="Select a model"
              data={modelOptions}
              disabled={!selectedProviderId || modelOptions.length === 0}
              searchable
              nothingFoundMessage="No models found"
              {...form.getInputProps('ai_provider_config.model_name')}
            />
          </Group>

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
            <Button type="submit" loading={isLoading}>
              {isEditMode ? 'Save Changes' : 'Create Project'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
