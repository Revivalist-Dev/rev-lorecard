import { Modal, Stack, Text, Textarea, Checkbox, Group, Button, Paper, ScrollArea, Title, Badge } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { CharacterCard, Project, ProjectSource } from '../../types';
import { useRegenerateFieldJob } from '../../hooks/useJobMutations';
import { useLatestJob } from '../../hooks/useProjectJobs';
import { JobStatusIndicator } from '../common/JobStatusIndicator';

interface RegenerateFieldModalProps {
  opened: boolean;
  onClose: () => void;
  project: Project;
  fieldName: keyof CharacterCard | null;
  fetchedSources: ProjectSource[];
  characterCard?: CharacterCard;
}

interface RegenForm {
  custom_prompt: string;
  include_existing_fields: boolean;
  source_ids_to_include: string[];
}

export function RegenerateFieldModal({
  opened,
  onClose,
  project,
  fieldName,
  fetchedSources,
  // @ts-expect-error aaaaa
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  characterCard,
}: RegenerateFieldModalProps) {
  const regenerateFieldMutation = useRegenerateFieldJob();
  const { job: regenerateFieldJob } = useLatestJob(project.id, 'regenerate_character_field');

  const form = useForm<RegenForm>({
    initialValues: {
      custom_prompt: '',
      include_existing_fields: true,
      source_ids_to_include: [],
    },
  });

  if (!fieldName) return null;

  const handleSubmit = (values: RegenForm) => {
    regenerateFieldMutation.mutate(
      {
        project_id: project.id,
        field_to_regenerate: fieldName,
        custom_prompt: values.custom_prompt,
        context_options: {
          include_existing_fields: values.include_existing_fields,
          source_ids_to_include: values.source_ids_to_include,
        },
      },
      {
        onSuccess: () => {
          onClose();
          form.reset();
        },
      }
    );
  };

  const selectedSources = fetchedSources.filter((s) => form.values.source_ids_to_include.includes(s.id));
  const totalEstimatedTokens = selectedSources.reduce((acc, s) => acc + Math.ceil((s.content_char_count || 0) / 4), 0);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Title order={4}>Regenerate '{fieldName.replace('_', ' ')}'</Title>}
      size="xl"
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <Textarea
            label="Custom Prompt (Optional)"
            description="Provide a specific instruction for the regeneration."
            placeholder="e.g., Make it more sarcastic and world-weary."
            {...form.getInputProps('custom_prompt')}
          />

          <Title order={5} mt="md">
            Context Sources
          </Title>
          <Text size="sm" c="dimmed">
            Select which sources of information to provide to the AI as context.
          </Text>

          <Checkbox
            label="Include existing character fields"
            description="Uses the other generated fields as context. (Recommended, low token cost)"
            {...form.getInputProps('include_existing_fields', { type: 'checkbox' })}
          />

          <Paper withBorder p="md" mt="xs">
            <Text fw={500}>Include content from fetched sources</Text>
            <Text size="xs" c="dimmed" mb="xs">
              Select which sources to use as context. Be mindful of the token count.
            </Text>
            <ScrollArea h={200}>
              <Checkbox.Group {...form.getInputProps('source_ids_to_include')}>
                <Stack>
                  {fetchedSources.map((source) => (
                    <Checkbox
                      key={source.id}
                      value={source.id}
                      label={
                        <Group justify="space-between" w="100%">
                          <Text truncate>{source.url}</Text>
                          <Badge variant="light" color="gray">
                            ~{Math.ceil((source.content_char_count || 0) / 4)} tokens
                          </Badge>
                        </Group>
                      }
                    />
                  ))}
                </Stack>
              </Checkbox.Group>
            </ScrollArea>
          </Paper>

          <JobStatusIndicator job={regenerateFieldJob} title="Regeneration Job" />

          <Group justify="flex-end" mt="md">
            <Text size="sm" c="dimmed">
              Total Estimated Context Tokens: ~{totalEstimatedTokens.toLocaleString()}
            </Text>
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={regenerateFieldMutation.isPending}>
              Regenerate
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
