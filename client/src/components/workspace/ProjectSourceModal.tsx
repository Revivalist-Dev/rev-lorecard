import { Modal, TextInput, Button, Group, Stack, Text, NumberInput, Textarea, Collapse, Alert, Select } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect, useState } from 'react';
import type { ProjectSource, TestSelectorsResult, ProjectType, SourceType, ContentType } from '../../types';
import {
  useCreateProjectSource,
  useUpdateProjectSource,
  useTestProjectSourceSelectors,
} from '../../hooks/useProjectSources';
import { useDisclosure } from '@mantine/hooks';
import { IconAlertCircle } from '@tabler/icons-react';
import { CharacterCardFormatSelectorModal } from './CharacterCardFormatSelectorModal';

// Since CreateSourcePayload and UpdateSourcePayload are not exported from the hook file,
// I will define them here based on the hook file's content to ensure type safety.
// Based on the previous step, I updated the types in useProjectSources.ts:
interface LocalCreateSourcePayload {
  source_type: SourceType;
  url: string;
  raw_content?: string;
  content_type?: ContentType;
  max_pages_to_crawl?: number;
  max_crawl_depth?: number;
  url_exclusion_patterns?: string[];
}

interface LocalUpdateSourcePayload extends Partial<LocalCreateSourcePayload> {
  link_extraction_selector?: string[];
  link_extraction_pagination_selector?: string;
}

interface ProjectSourceModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
  source: ProjectSource | null;
  projectType: ProjectType; // New prop
}

interface SourceFormValues {
  source_type: SourceType;
  url: string;
  raw_content: string; // For user_text_file
  max_pages_to_crawl: number;
  max_crawl_depth: number;
  link_extraction_selector: string;
  link_extraction_pagination_selector: string;
  url_exclusion_patterns: string;
  content_type: ContentType;
}

export function ProjectSourceModal({ opened, onClose, projectId, source, projectType }: ProjectSourceModalProps) {
  const isEditMode = !!source;
  const createSourceMutation = useCreateProjectSource(projectId);
  const updateSourceMutation = useUpdateProjectSource(projectId);
  const testSelectorsMutation = useTestProjectSourceSelectors(projectId);
  const [selectorsVisible, { toggle: toggleSelectors }] = useDisclosure(false);
  const [testResult, setTestResult] = useState<TestSelectorsResult | null>(null);
  const [formatModalOpened, { open: openFormatModal, close: closeFormatModal }] = useDisclosure(false);
  const [pendingSubmitValues, setPendingSubmitValues] = useState<SourceFormValues | null>(null);

  const form = useForm<SourceFormValues>({
    initialValues: {
      source_type: 'web_url' as SourceType,
      url: '',
      raw_content: '',
      max_pages_to_crawl: 20,
      max_crawl_depth: 1,
      link_extraction_selector: '',
      link_extraction_pagination_selector: '',
      url_exclusion_patterns: '',
      content_type: 'markdown' as ContentType, // Default for character cards
    },
    validate: {
      url: (value, values) => {
        if (values.source_type === 'user_text_file') return null;
        if (!value) return 'URL is required for this source type';
        try {
          new URL(value);
          return null;
        } catch {
          return 'Please enter a valid URL';
        }
      },
      raw_content: (value, values) => {
        if (values.source_type === 'user_text_file' && !value) {
          return 'Content is required for User Text File source type';
        }
        return null;
      },
    },
  });

  useEffect(() => {
    setTestResult(null); // Clear test results when modal opens/changes
    if (isEditMode && source) {
      form.setValues({
        source_type: source.source_type,
        url: source.url,
        raw_content: source.raw_content || '',
        max_pages_to_crawl: source.max_pages_to_crawl,
        max_crawl_depth: source.max_crawl_depth,
        link_extraction_selector: (source.link_extraction_selector || []).join('\n'),
        link_extraction_pagination_selector: source.link_extraction_pagination_selector || '',
        url_exclusion_patterns: (source.url_exclusion_patterns || []).join('\n'),
        content_type: source.content_type || 'markdown',
      });
    } else {
      form.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, opened]);

  const handleFinalSubmit = (values: SourceFormValues) => {
    const { source_type, link_extraction_selector, url_exclusion_patterns, raw_content, content_type, ...rest } = values;

    const parsedLinkSelectors = link_extraction_selector.split('\n').filter(Boolean);
    const parsedUrlExclusionPatterns = url_exclusion_patterns.split('\n').filter(Boolean);

    let payload: LocalCreateSourcePayload | LocalUpdateSourcePayload;

    if (source_type === 'user_text_file') {
      // For user_text_file, we only send source_type, raw_content, and a URL (required by backend, can be placeholder)
      payload = {
        source_type,
        url: values.url || `user-text-file-${Date.now()}`,
        raw_content,
        content_type: 'plaintext', // User text files are always plaintext
        // Explicitly set crawling fields to undefined/defaults if not provided, although they are optional in the type
        max_pages_to_crawl: 1,
        max_crawl_depth: 1,
      } as LocalCreateSourcePayload;
    } else if (source_type === 'character_card') {
      // For character_card, we send source_type, url, and content_type
      payload = {
        source_type,
        url: values.url,
        content_type,
        max_pages_to_crawl: 1,
        max_crawl_depth: 1,
      } as LocalCreateSourcePayload;
    } else {
      // web_url (lorebook only)
      payload = {
        ...rest,
        source_type,
        link_extraction_selector: parsedLinkSelectors,
        url_exclusion_patterns: parsedUrlExclusionPatterns,
      } as LocalCreateSourcePayload;
    }

    if (isEditMode && source) {
      // When updating, we only send fields that are relevant/changed.
      // We cast the payload to UpdateSourcePayload for the mutation.
      updateSourceMutation.mutate({ projectId, sourceId: source.id, data: payload as LocalUpdateSourcePayload }, { onSuccess: onClose });
    } else {
      // When creating, we ensure the payload matches CreateSourcePayload structure.
      createSourceMutation.mutate({ projectId, data: payload as LocalCreateSourcePayload }, { onSuccess: onClose });
    }
  };

  const handlePreSubmit = (values: SourceFormValues) => {
    if (!isEditMode && values.source_type === 'character_card') {
      // If creating a new character card source, open the format selector modal
      setPendingSubmitValues(values);
      openFormatModal();
    } else {
      // Otherwise, proceed directly to submission
      handleFinalSubmit(values);
    }
  };

  const handleFormatSelect = (format: ContentType) => {
    if (pendingSubmitValues) {
      const finalValues = { ...pendingSubmitValues, content_type: format };
      handleFinalSubmit(finalValues);
      setPendingSubmitValues(null);
    }
  };

  const handleTestSelectors = async () => {
    setTestResult(null);
    const { source_type, url, link_extraction_selector, link_extraction_pagination_selector } = form.values;

    if (source_type !== 'web_url') {
      setTestResult({ error: 'Selector testing is only available for Web URL sources.', link_count: 0, content_links: [] });
      return;
    }

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
  const isLorebookProject = projectType === 'lorebook';

  return (
    <>
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={700}>{isEditMode ? 'Edit Source' : 'Add New Source'}</Text>}
      size="lg"
      centered
    >
      <form onSubmit={form.onSubmit(handlePreSubmit)}>
        <Stack gap="md">
            <Select
              withAsterisk
              label="Source Type"
              placeholder="Select source type"
              data={[
                { value: 'web_url', label: 'Web URL (Crawling)' },
                { value: 'user_text_file', label: 'User Text File' },
                { value: 'character_card', label: 'Other Character Card' },
              ]}
              disabled={isEditMode}
              {...form.getInputProps('source_type')}
            />
  
            {form.values.source_type === 'user_text_file' && (
              <Textarea
                withAsterisk
                label="Source Content"
                description="Paste the raw text content here. This content will be used directly for character generation."
                autosize
                minRows={10}
                {...form.getInputProps('raw_content')}
              />
            )}
  
            {(form.values.source_type === 'web_url' || form.values.source_type === 'character_card') && (
              <TextInput
                withAsterisk
                label={form.values.source_type === 'character_card' ? 'Character Card URL/Path' : 'Source URL'}
                placeholder={
                  form.values.source_type === 'character_card'
                    ? 'e.g., file:///path/to/card.json or https://example.com/card.png'
                    : isLorebookProject
                      ? 'e.g., https://elderscrolls.fandom.com/wiki/Category:Skyrim:_Locations'
                      : 'e.g., https://elderscrolls.fandom.com/wiki/Lydia_(Skyrim)'
                }
                {...form.getInputProps('url')}
              />
            )}
  
            {/* Web URL specific fields, only visible for lorebook projects and web_url type */}
            {isLorebookProject && form.values.source_type === 'web_url' && (
              <>
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
                <Group grow>
                  <Textarea
                    w={'100%'}
                    label="URL Exclusion Patterns"
                    description="URLs containing any of these patterns (one per line) will be ignored during crawling."
                    autosize
                    minRows={3}
                    {...form.getInputProps('url_exclusion_patterns')}
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
      <CharacterCardFormatSelectorModal
        opened={formatModalOpened}
        onClose={closeFormatModal}
        onSelect={handleFormatSelect}
      />
    </>
  );
}
