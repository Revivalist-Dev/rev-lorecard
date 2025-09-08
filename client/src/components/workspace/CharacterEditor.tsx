import { Stack, Text, Button, Group, Loader, Paper, Title, Textarea, ActionIcon, Tooltip } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import type { Project, ProjectSource } from '../../types';
import { useGenerateCharacterJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';
import { IconDeviceFloppy, IconDownload, IconPlayerPlay, IconSparkles } from '@tabler/icons-react';
import { useCharacterCard, useUpdateCharacterCard } from '../../hooks/useCharacterCard';
import { useForm } from '@mantine/form';
import { useEffect, useState } from 'react';
import { RegenerateFieldModal } from './RegenerateFieldModal';
import { useProjectSources } from '../../hooks/useProjectSources';
import { notifications } from '@mantine/notifications';
import apiClient from '../../services/api';

interface CharacterEditorProps {
  project: Project;
  selectedSourceIds: string[];
}

export function CharacterEditor({ project, selectedSourceIds }: CharacterEditorProps) {
  const { data: characterCardResponse, isLoading: isLoadingCard } = useCharacterCard(project.id);
  const { data: sources } = useProjectSources(project.id);
  const updateCardMutation = useUpdateCharacterCard(project.id);
  const generateCharacterMutation = useGenerateCharacterJob();
  const { job: generateCharacterJob } = useLatestJob(project.id, 'generate_character_card');

  const [regenerateModalOpened, { open: openRegenerateModal, close: closeRegenerateModal }] = useDisclosure(false);
  const [fieldToRegen, setFieldToRegen] = useState<keyof typeof form.values | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const form = useForm({
    initialValues: {
      name: '',
      description: '',
      persona: '',
      scenario: '',
      first_message: '',
      example_messages: '',
    },
  });

  useEffect(() => {
    if (characterCardResponse?.data) {
      const { name, description, persona, scenario, first_message, example_messages } = characterCardResponse.data;
      const values = {
        name: name || '',
        description: description || '',
        persona: persona || '',
        scenario: scenario || '',
        first_message: first_message || '',
        example_messages: example_messages || '',
      };
      form.setValues(values);
      form.resetDirty(values);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [characterCardResponse]);

  const handleRegenerateClick = (fieldName: keyof typeof form.values) => {
    setFieldToRegen(fieldName);
    openRegenerateModal();
  };

  const fetchedSources = sources?.filter((s) => s.content_char_count && s.content_char_count > 0) || [];
  const canGenerate = selectedSourceIds.length > 0;
  const isGenerationJobActive =
    generateCharacterJob?.status === 'pending' || generateCharacterJob?.status === 'in_progress';

  const handleExport = async () => {
    if (!characterCardResponse?.data?.name) {
      notifications.show({
        color: 'yellow',
        title: 'Cannot Export',
        message: 'Please generate or enter a name for the character before exporting.',
      });
      return;
    }
    setIsDownloading(true);
    try {
      const response = await apiClient.get(`/projects/${project.id}/character/export`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = `${characterCardResponse.data.name}.png`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();

      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      notifications.show({
        title: 'Export Failed',
        message: 'Could not export the character card.',
        color: 'red',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  if (isLoadingCard) {
    return <Loader />;
  }

  const renderTextareaWithRegen = (field: keyof typeof form.values, label: string, rows: number) => (
    <Textarea
      label={
        <Group justify="space-between">
          <Text component="span">{label}</Text>
          <Tooltip label={`Regenerate ${label}`} withArrow>
            <ActionIcon
              variant="subtle"
              size="xs"
              onClick={() => handleRegenerateClick(field)}
              disabled={!characterCardResponse?.data.id}
            >
              <IconSparkles size={14} />
            </ActionIcon>
          </Tooltip>
        </Group>
      }
      autosize
      minRows={rows}
      maxRows={12}
      resize="vertical"
      {...form.getInputProps(field)}
    />
  );

  return (
    <>
      <RegenerateFieldModal
        opened={regenerateModalOpened}
        onClose={closeRegenerateModal}
        project={project}
        fieldName={fieldToRegen}
        fetchedSources={fetchedSources as ProjectSource[]}
        characterCard={characterCardResponse?.data}
      />
      <form onSubmit={form.onSubmit((values) => updateCardMutation.mutate({ projectId: project.id, data: values }))}>
        <Stack>
          <Group justify="space-between">
            <Title order={4}>Character Card</Title>
            <Group>
              <Button
                leftSection={<IconPlayerPlay size={16} />}
                onClick={() =>
                  generateCharacterMutation.mutate({ project_id: project.id, source_ids: selectedSourceIds })
                }
                disabled={!canGenerate || isGenerationJobActive}
                loading={isGenerationJobActive}
                title={!canGenerate ? 'Select at least one fetched source to enable generation.' : ''}
              >
                Generate
              </Button>
              <Button
                leftSection={<IconDeviceFloppy size={16} />}
                type="submit"
                variant="default"
                disabled={!form.isDirty()}
                loading={updateCardMutation.isPending}
              >
                Save Changes
              </Button>
              <Button
                leftSection={<IconDownload size={16} />}
                variant="outline"
                onClick={handleExport}
                loading={isDownloading}
                disabled={!characterCardResponse?.data.name}
              >
                Export Card
              </Button>
            </Group>
          </Group>
          <Text size="sm" c="dimmed">
            Generate the character card from your selected sources, or fill out the fields manually.
          </Text>

          <JobStatusIndicator job={generateCharacterJob} title="Character Generation" />

          <Paper withBorder p="md" mt="xs">
            <Stack>
              {renderTextareaWithRegen('name', 'Name', 1)}
              {renderTextareaWithRegen('description', 'Description', 4)}
              {renderTextareaWithRegen('persona', 'Persona', 4)}
              {renderTextareaWithRegen('scenario', 'Scenario', 2)}
              {renderTextareaWithRegen('first_message', 'First Message', 4)}
              {renderTextareaWithRegen('example_messages', 'Example Messages', 4)}
            </Stack>
          </Paper>
        </Stack>
      </form>
    </>
  );
}
