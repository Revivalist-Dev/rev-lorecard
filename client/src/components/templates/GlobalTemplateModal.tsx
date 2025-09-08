import { Modal, TextInput, Button, Group, Stack, Text, Tooltip, ActionIcon } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect } from 'react';
import type { GlobalTemplate } from '../../types';
import { useCreateGlobalTemplate, useUpdateGlobalTemplate } from '../../hooks/useGlobalTemplatesMutations';
import { useDefaultGlobalTemplates } from '../../hooks/useGlobalTemplates';
import { LazyMonacoEditorInput } from '../common/LazyMonacoEditorInput';
import { IconRefresh } from '@tabler/icons-react';

interface GlobalTemplateModalProps {
  opened: boolean;
  onClose: () => void;
  template: GlobalTemplate | null;
}

interface TemplateFormValues {
  id: string;
  name: string;
  content: string;
}

export function GlobalTemplateModal({ opened, onClose, template }: GlobalTemplateModalProps) {
  const isEditMode = !!template;
  const createTemplateMutation = useCreateGlobalTemplate();
  const updateTemplateMutation = useUpdateGlobalTemplate();
  const { data: defaultTemplates } = useDefaultGlobalTemplates();

  const form = useForm<TemplateFormValues>({
    initialValues: {
      id: '',
      name: '',
      content: '',
    },
    validate: {
      id: (value) => (/^[a-z0-9-]+$/.test(value) ? null : 'ID must be lowercase, numbers, and dashes only'),
      name: (value) => (value.trim().length > 0 ? null : 'Name is required'),
      content: (value) => (value.trim().length > 0 ? null : 'Content cannot be empty'),
    },
  });

  useEffect(() => {
    if (isEditMode && template) {
      form.setValues(template);
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template, opened]);

  const handleSubmit = (values: TemplateFormValues) => {
    if (isEditMode && template) {
      const { name, content } = values;
      updateTemplateMutation.mutate({ templateId: template.id, data: { name, content } }, { onSuccess: onClose });
    } else {
      createTemplateMutation.mutate(values, { onSuccess: onClose });
    }
  };

  const isLoading = createTemplateMutation.isPending || updateTemplateMutation.isPending;

  const handleResetContent = () => {
    if (template && defaultTemplates && defaultTemplates[template.id]) {
      form.setFieldValue('content', defaultTemplates[template.id]);
    }
  };

  const hasDefaultTemplate = isEditMode && template && defaultTemplates && !!defaultTemplates[template.id];

  const renderTemplateLabel = (label: string) => (
    <Group justify="space-between" w="100%">
      <Text component="span" size="sm" fw={500}>
        {label}
      </Text>
      <Tooltip label="Reset to default template" withArrow position="top-end">
        <ActionIcon onClick={handleResetContent} variant="subtle" size="xs" aria-label={`Reset ${label} to default`}>
          <IconRefresh size={16} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={700}>{isEditMode ? 'Edit Global Template' : 'Create New Template'}</Text>}
      size="xl"
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            withAsterisk
            label="Template ID"
            placeholder="e.g., my-custom-entry-prompt"
            {...form.getInputProps('id')}
            disabled={isEditMode}
          />
          <TextInput
            withAsterisk
            label="Template Name"
            placeholder="e.g., My Custom Entry Prompt"
            {...form.getInputProps('name')}
          />
          <LazyMonacoEditorInput
            label={hasDefaultTemplate ? renderTemplateLabel('Template Content') : 'Template Content'}
            language="handlebars"
            height={400}
            {...form.getInputProps('content')}
            error={form.errors.content}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isLoading}>
              {isEditMode ? 'Save Changes' : 'Create Template'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
