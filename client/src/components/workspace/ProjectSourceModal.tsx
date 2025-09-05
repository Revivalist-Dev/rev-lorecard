import { Modal, TextInput, Button, Group, Stack, Text, NumberInput, Textarea, Collapse, Alert } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect, useState } from 'react';
import type { ProjectSource, TestSelectorsResult } from '../../types';
import {
  useCreateProjectSource,
  useUpdateProjectSource,
  useTestProjectSourceSelectors,
} from '../../hooks/useProjectSources';
import { useDisclosure } from '@mantine/hooks';
import { IconAlertCircle } from '@tabler/icons-react';

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
  link_extraction_selector: string;
  link_extraction_pagination_selector: string;
}

export function ProjectSourceModal({ opened, onClose, projectId, source }: ProjectSourceModalProps) {
  const isEditMode = !!source;
  const createSourceMutation = useCreateProjectSource(projectId);
  const updateSourceMutation = useUpdateProjectSource(projectId);
  const testSelectorsMutation = useTestProjectSourceSelectors(projectId);
  const [selectorsVisible, { toggle: toggleSelectors }] = useDisclosure(false);
  const [testResult, setTestResult] = useState<TestSelectorsResult | null>(null);

  const form = useForm<SourceFormValues>({
    initialValues: {
      url: '',
      max_pages_to_crawl: 20,
      max_crawl_depth: 1,
      link_extraction_selector: '',
      link_extraction_pagination_selector: '',
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
    setTestResult(null); // Clear test results when modal opens/changes
    if (isEditMode && source) {
      form.setValues({
        url: source.url,
        max_pages_to_crawl: source.max_pages_to_crawl,
        max_crawl_depth: source.max_crawl_depth,
        link_extraction_selector: (source.link_extraction_selector || []).join('\n'),
        link_extraction_pagination_selector: source.link_extraction_pagination_selector || '',
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, opened]);

  const handleSubmit = (values: SourceFormValues) => {
    const payload = {
      ...values,
      link_extraction_selector: values.link_extraction_selector.split('\n').filter(Boolean),
    };

    if (isEditMode && source) {
      updateSourceMutation.mutate({ projectId, sourceId: source.id, data: payload }, { onSuccess: onClose });
    } else {
      createSourceMutation.mutate({ projectId, data: payload }, { onSuccess: onClose });
    }
  };

  const handleTestSelectors = async () => {
    setTestResult(null);
    const { url, link_extraction_selector, link_extraction_pagination_selector } = form.values;
    testSelectorsMutation.mutate(
      {
        projectId,
        data: {
          url,
          content_selectors: link_extraction_selector.split('\n').filter(Boolean),
          pagination_selector: link_extraction_pagination_selector,
        },
      },
      {
        onSuccess: (data) => {
          setTestResult(data);
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onError: (error: any) => {
          setTestResult({
            error: error.response?.data?.detail || 'An unknown error occurred.',
            link_count: 0,
            content_links: [],
          });
        },
      }
    );
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

          {isEditMode && (
            <>
              <Button variant="subtle" size="xs" onClick={toggleSelectors}>
                {selectorsVisible ? 'Hide' : 'Show'} Advanced: CSS Selectors
              </Button>
              <Collapse in={selectorsVisible}>
                <Stack>
                  <Textarea
                    label="Content Link Selectors"
                    description="CSS selectors for links to content pages, one per line."
                    autosize
                    minRows={3}
                    {...form.getInputProps('link_extraction_selector')}
                  />
                  <TextInput
                    label="Pagination Link Selector"
                    description="CSS selector for the 'next page' link."
                    {...form.getInputProps('link_extraction_pagination_selector')}
                  />
                  <Group justify="flex-end">
                    <Button
                      variant="outline"
                      onClick={handleTestSelectors}
                      loading={testSelectorsMutation.isPending}
                      disabled={!form.values.url}
                    >
                      Test Selectors
                    </Button>
                  </Group>
                  {testResult && (
                    <Alert
                      icon={<IconAlertCircle size="1rem" />}
                      title="Selector Test Result"
                      color={testResult.error ? 'red' : 'green'}
                      withCloseButton
                      onClose={() => setTestResult(null)}
                    >
                      {testResult.error ? (
                        <Text>{testResult.error}</Text>
                      ) : (
                        <Stack>
                          <Text>Found {testResult.link_count} content links.</Text>
                          {testResult.pagination_link ? (
                            <Text>Pagination link found: {testResult.pagination_link}</Text>
                          ) : (
                            <Text>No pagination link found.</Text>
                          )}
                          {testResult.content_links.length > 0 && (
                            <Text size="xs" c="dimmed">
                              First link: {testResult.content_links[0]}
                            </Text>
                          )}
                        </Stack>
                      )}
                    </Alert>
                  )}
                </Stack>
              </Collapse>
            </>
          )}

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
