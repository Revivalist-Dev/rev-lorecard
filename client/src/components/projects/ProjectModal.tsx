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
  SegmentedControl,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useCreateProject, useUpdateProject } from '../../hooks/useProjectMutations';
import type { CreateProjectPayload, Project, Credential, ProjectType } from '../../types';
import { useProviders } from '../../hooks/useProviders';
import { useEffect, useMemo, useState } from 'react';
import { useGlobalTemplates } from '../../hooks/useGlobalTemplates';
import { CodeMirrorInput } from '../common/CodeMirrorInput';
import { useCredentials } from '../../hooks/useCredentials';
import { useDisclosure } from '@mantine/hooks';
import { IconBook, IconPlus, IconRefresh, IconUser } from '@tabler/icons-react';
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
      project_type: 'lorebook',
      prompt: '',
      requests_per_minute: 15,
      credential_id: undefined,
      model_name: undefined,
      model_parameters: { temperature: 0.7 },
      json_enforcement_mode: 'api_native',
      templates: {
        search_params_generation: '',
        selector_generation: '',
        entry_creation: '',
        character_generation: '',
        character_field_regeneration: '',
      },
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
        json_enforcement_mode: project.json_enforcement_mode || 'api_native',
        templates: {
          search_params_generation: project.templates.search_params_generation || '',
          selector_generation: project.templates.selector_generation || '',
          entry_creation: project.templates.entry_creation || '',
          character_generation: project.templates.character_generation || '',
          character_field_regeneration: project.templates.character_field_regeneration || '',
        },
      });
      setSelectedCredentialId(project.credential_id || null);
    } else if (!isEditMode && globalTemplates?.data) {
      const templates = globalTemplates.data;
      const getTemplate = (id: string) => templates.find((t) => t.id === id)?.content || '';
      form.reset();
      // Set defaults for lorebook initially, as it's the default project type
      form.setFieldValue('templates.search_params_generation', getTemplate('search-params-prompt'));
      form.setFieldValue('templates.selector_generation', getTemplate('selector-prompt'));
      form.setFieldValue('templates.entry_creation', getTemplate('entry-creation-prompt'));
      form.setFieldValue('templates.character_generation', '');
      form.setFieldValue('templates.character_field_regeneration', '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, opened, globalTemplates?.data]);

  // Update templates when project type changes
  const handleProjectTypeChange = (value: string) => {
    const projectType = value as ProjectType;
    form.setFieldValue('project_type', projectType);
    if (!isEditMode && globalTemplates?.data) {
      const templates = globalTemplates.data;
      const getTemplate = (id: string) => templates.find((t) => t.id === id)?.content || '';
      if (projectType === 'character') {
        form.setFieldValue('templates.character_generation', getTemplate('character-generation-prompt'));
        form.setFieldValue(
          'templates.character_field_regeneration',
          getTemplate('character-field-regeneration-prompt')
        );
        // Clear lorebook-specific templates
        form.setFieldValue('templates.search_params_generation', '');
        form.setFieldValue('templates.selector_generation', '');
        form.setFieldValue('templates.entry_creation', '');
      } else {
        form.setFieldValue('templates.search_params_generation', getTemplate('search-params-prompt'));
        form.setFieldValue('templates.selector_generation', getTemplate('selector-prompt'));
        form.setFieldValue('templates.entry_creation', getTemplate('entry-creation-prompt'));
        // Clear character-specific templates
        form.setFieldValue('templates.character_generation', '');
        form.setFieldValue('templates.character_field_regeneration', '');
      }
    }
  };

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

  const handleResetTemplate = (templateField: keyof CreateProjectPayload['templates'], templateId: string) => {
    if (globalTemplates?.data) {
      const template = globalTemplates.data.find((t) => t.id === templateId);
      if (template) {
        form.setFieldValue(`templates.${templateField}`, template.content);
      }
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

  const isLorebook = form.values.project_type === 'lorebook';

  const renderTemplateLabel = (label: string, onReset: () => void) => (
    <Group justify="space-between" w="100%">
      <Text component="span" size="sm" fw={500}>
        {label}
      </Text>
      <Tooltip label="Reset to global template" withArrow position="top-end">
        <ActionIcon onClick={onReset} variant="subtle" size="xs" aria-label={`Reset ${label} to global template`}>
          <IconRefresh size={16} />
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
            {!isEditMode && (
              <SegmentedControl
                fullWidth
                data={[
                  {
                    value: 'lorebook',
                    label: (
                      <Group justify="center" gap="xs">
                        <IconBook size={16} />
                        <Text>Lorebook</Text>
                      </Group>
                    ),
                  },
                  {
                    value: 'character',
                    label: (
                      <Group justify="center" gap="xs">
                        <IconUser size={16} />
                        <Text>Character</Text>
                      </Group>
                    ),
                  },
                ]}
                {...form.getInputProps('project_type')}
                onChange={handleProjectTypeChange}
              />
            )}
            <TextInput
              withAsterisk
              label="Project Name"
              placeholder={isLorebook ? 'e.g., Skyrim Locations Lorebook' : 'e.g., Lydia from Skyrim'}
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
              description={
                isLorebook
                  ? 'A general prompt describing the overall goal of the lorebook.'
                  : 'A prompt describing the character to generate. Be specific about their personality and key traits.'
              }
              placeholder={
                isLorebook
                  ? "e.g., 'All major and minor locations in Skyrim'"
                  : "e.g., 'Lydia, the loyal and sarcastic housecarl from Whiterun in Skyrim.'"
              }
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

            <Stack gap={4}>
              <Text size="sm" fw={500}>
                JSON Enforcement Mode
              </Text>
              <Text size="xs" c="dimmed">
                'API Native' uses the model's built-in JSON mode (faster, less reliable). 'Prompt Engineering' uses a
                special prompt to ensure valid JSON (slower, more reliable with models that struggle with JSON modes).
              </Text>
              <SegmentedControl
                fullWidth
                data={[
                  { label: 'API Native', value: 'api_native' },
                  { label: 'Prompt Engineering', value: 'prompt_engineering' },
                ]}
                {...form.getInputProps('json_enforcement_mode')}
              />
            </Stack>

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

            <Accordion variant="separated">
              <Accordion.Item value="templates">
                <Accordion.Control>
                  <Text fw={500}>Advanced: Prompt Templates</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  {isLoadingTemplates ? (
                    <Loader />
                  ) : (
                    <Stack>
                      {isLorebook ? (
                        <>
                          <CodeMirrorInput
                            label={renderTemplateLabel('Search Params Generation', () =>
                              handleResetTemplate('search_params_generation', 'search-params-prompt')
                            )}
                            language="markdown"
                            height="200px"
                            {...form.getInputProps('templates.search_params_generation')}
                          />
                          <CodeMirrorInput
                            label={renderTemplateLabel('Selector Generation', () =>
                              handleResetTemplate('selector_generation', 'selector-prompt')
                            )}
                            language="markdown"
                            height="200px"
                            {...form.getInputProps('templates.selector_generation')}
                          />
                          <CodeMirrorInput
                            label={renderTemplateLabel('Entry Creation', () =>
                              handleResetTemplate('entry_creation', 'entry-creation-prompt')
                            )}
                            language="markdown"
                            height="200px"
                            {...form.getInputProps('templates.entry_creation')}
                          />
                        </>
                      ) : (
                        <>
                          <CodeMirrorInput
                            label={renderTemplateLabel('Character Generation', () =>
                              handleResetTemplate('character_generation', 'character-generation-prompt')
                            )}
                            language="markdown"
                            height="200px"
                            {...form.getInputProps('templates.character_generation')}
                          />
                          <CodeMirrorInput
                            label={renderTemplateLabel('Character Field Regeneration', () =>
                              handleResetTemplate('character_field_regeneration', 'character-field-regeneration-prompt')
                            )}
                            language="markdown"
                            height="200px"
                            {...form.getInputProps('templates.character_field_regeneration')}
                          />
                        </>
                      )}
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
