import { Modal, TextInput, Button, Group, Stack, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect } from 'react';
import { useUpdateLorebookEntry } from '../../hooks/useLorebookEntryMutations';
import type { LorebookEntry } from '../../types';
import { CodeMirrorInput } from '../common/CodeMirrorInput';

interface LorebookEntryModalProps {
  opened: boolean;
  onClose: () => void;
  entry: LorebookEntry | null;
}

interface EntryFormValues {
  title: string;
  content: string;
  keywords: string; // Use a string for the form, convert to array on submit
}

export function LorebookEntryModal({ opened, onClose, entry }: LorebookEntryModalProps) {
  const updateEntryMutation = useUpdateLorebookEntry(entry?.project_id || '');

  const form = useForm<EntryFormValues>({
    initialValues: {
      title: '',
      content: '',
      keywords: '',
    },
    validate: {
      title: (value) => (value.trim().length > 0 ? null : 'Title is required'),
      content: (value) => (value.trim().length > 0 ? null : 'Content cannot be empty'),
    },
  });

  useEffect(() => {
    if (entry) {
      form.setValues({
        title: entry.title,
        content: entry.content,
        keywords: entry.keywords.join(', '),
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry, opened]);

  const handleSubmit = (values: EntryFormValues) => {
    if (entry) {
      const keywordsArray = values.keywords.split(',').map((k) => k.trim());
      updateEntryMutation.mutate(
        { entryId: entry.id, data: { ...values, keywords: keywordsArray } },
        { onSuccess: onClose }
      );
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={<Text fw={700}>Edit Lorebook Entry</Text>} size="xl" centered>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput withAsterisk label="Title" placeholder="Entry title" {...form.getInputProps('title')} />
          <TextInput
            label="Keywords"
            description="Comma-separated list of keywords"
            placeholder="keyword1, keyword2"
            {...form.getInputProps('keywords')}
          />
          <CodeMirrorInput
            label="Content"
            language="markdown"
            height="400px"
            {...form.getInputProps('content')}
            error={form.errors.content}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={updateEntryMutation.isPending}>
              Save Changes
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
