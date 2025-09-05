import { Modal, TextInput, Button, Group, Stack, Text, NumberInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect } from 'react';
import type { ProjectSource } from '../../types';
import { useCreateProjectSource, useUpdateProjectSource } from '../../hooks/useProjectSources';

interface ProjectSourceModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
  source: ProjectSource | null;
}

interface SourceFormValues {
  url: string;
  max_pages_to_crawl: number;
  max_crawl_depth: number;
}

export function ProjectSourceModal({ opened, onClose, projectId, source }: ProjectSourceModalProps) {
  const isEditMode = !!source;
  const createSourceMutation = useCreateProjectSource(projectId);
  const updateSourceMutation = useUpdateProjectSource(projectId);

  const form = useForm<SourceFormValues>({
    initialValues: {
      url: '',
      max_pages_to_crawl: 20,
      max_crawl_depth: 1,
    },
    validate: {
      url: (value) => {
        try {
          new URL(value);
          return null;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
        } catch (e: any) {
          return 'Please enter a valid URL';
        }
      },
    },
  });

  useEffect(() => {
    if (isEditMode && source) {
      form.setValues({
        url: source.url,
        max_pages_to_crawl: source.max_pages_to_crawl,
        max_crawl_depth: source.max_crawl_depth,
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, opened]);

  const handleSubmit = (values: SourceFormValues) => {
    if (isEditMode && source) {
      updateSourceMutation.mutate({ projectId, sourceId: source.id, data: values }, { onSuccess: onClose });
    } else {
      createSourceMutation.mutate({ projectId, data: values }, { onSuccess: onClose });
    }
  };

  const isLoading = createSourceMutation.isPending || updateSourceMutation.isPending;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={700}>{isEditMode ? 'Edit Source' : 'Add New Source'}</Text>}
      size="lg"
      centered
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput
            withAsterisk
            label="Source URL"
            placeholder="e.g., https://elderscrolls.fandom.com/wiki/Category:Skyrim:_Locations"
            {...form.getInputProps('url')}
          />
          <Group grow>
            <NumberInput
              label="Max Pages to Crawl"
              description="Pagination limit per source. Set to 1 to disable."
              defaultValue={20}
              min={1}
              max={100}
              {...form.getInputProps('max_pages_to_crawl')}
            />
            <NumberInput
              label="Max Crawl Depth"
              description="How many levels of sub-categories to discover."
              defaultValue={1}
              min={1}
              max={5}
              {...form.getInputProps('max_crawl_depth')}
            />
          </Group>
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isLoading}>
              {isEditMode ? 'Save Changes' : 'Add Source'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
