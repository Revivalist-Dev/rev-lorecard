import {
  Modal,
  Loader,
  Alert,
  Title,
  Box,
  Group,
  Button,
  Textarea,
  Stack,
  Text,
  Select,
  SegmentedControl,
  Tabs,
  Checkbox,
} from '@mantine/core';
import {
  useProjectSourceDetails,
  useAiEditSourceContent,
  useUpdateProjectSource,
  useConvertCharacterCardContent,
} from '../../hooks/useProjectSources';
import { IconAlertCircle, IconRobot, IconHourglass, IconHistory, IconLock, IconLockOpen, IconExchange } from '@tabler/icons-react';
import { useState, useEffect, useCallback } from 'react';
import { CodeMirrorDiffEditor } from '../common/CodeMirrorDiffEditor';
import { BlockNoteEditor } from '../common/BlockNoteEditor';
import { useSse } from '../../hooks/useSse';
import { useProjectJobs } from '../../hooks/useProjectJobs';
import type { BackgroundJob, ContentType } from '../../types';
import { notifications } from '@mantine/notifications';
import { SourceVersionHistoryModal } from './SourceVersionHistoryModal';

const FILE_TYPE_OPTIONS = [
  { value: 'cc_json_v2', label: 'Character Card JSON (V2)' },
  { value: 'cc_json_v3', label: 'Character Card JSON (V3)' },
  { value: 'cc_markdown_v2', label: 'Character Card Markdown (V2)' },
  { value: 'cc_markdown_v3', label: 'Character Card Markdown (V3)' },
  { value: 'yaml', label: 'YAML (.yaml)' },
  { value: 'plaintext', label: 'Plain Text (.txt)' },
  { value: 'html', label: 'HTML (.html)' },
  { value: 'cc_json_v1', label: 'Character Card JSON (V1)' },
  { value: 'cc_markdown_v1', label: 'Character Card Markdown (V1)' },
  { value: 'cc_json_misc', label: 'Miscellaneous JSON' },
  { value: 'json', label: 'Legacy JSON' },
  { value: 'markdown', label: 'Legacy Markdown' },
];

const CONVERSION_TARGET_OPTIONS = FILE_TYPE_OPTIONS.filter(
  (opt) =>
    opt.value.startsWith('cc_json') || opt.value.startsWith('cc_markdown')
);

interface EditSourceContentModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
  sourceId: string | null;
}


export function EditSourceContentModal({ opened, onClose, projectId, sourceId }: EditSourceContentModalProps) {
  const { data, isLoading, isError, error, refetch } = useProjectSourceDetails(projectId, sourceId);
  const source = data?.data;

  const [editedContent, setEditedContent] = useState<string>('');
  const [aiInstruction, setAiInstruction] = useState<string>('');
  const [aiEditedContent, setAiEditedContent] = useState<string | null>(null);
  const [selectedText, setSelectedText] = useState<string>('');
  const [lockedSelection, setLockedSelection] = useState<string | null>(null);
  const [activeAiJobId, setActiveAiJobId] = useState<string | null>(null);
  const [historyModalOpened, setHistoryModalOpened] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<ContentType>('plaintext');
  const [conversionTarget, setConversionTarget] = useState<ContentType | null>(null);
  const [stripComments, setStripComments] = useState(false);
  const [editingMode, setEditingMode] = useState<'ManualReview' | 'AIReview'>('ManualReview');
  const [activeTab, setActiveTab] = useState<'Visual' | 'Difference'>('Visual');

  const aiEditMutation = useAiEditSourceContent();
  const updateSourceMutation = useUpdateProjectSource(projectId);
  const convertMutation = useConvertCharacterCardContent();
  // useSse is a side-effect hook and returns void. We use useProjectJobs to read job updates.
  useSse(projectId);
  const { data: jobsResponse } = useProjectJobs(projectId);
  const jobUpdates = jobsResponse?.data;

  // 1. Initialize content and diff view on source change
  useEffect(() => {
    if (source) {
      if (source.raw_content) {
        setEditedContent(source.raw_content);
      } else {
        setEditedContent('');
      }
      // Initialize diff view with current content
      setAiEditedContent(source.raw_content ?? '');

      // Initialize selected language based on source content_type
      const initialLanguage = (source.content_type || 'plaintext') as ContentType;
      setSelectedLanguage(initialLanguage);
      setConversionTarget(null); // Reset conversion target on source change
    }
    // Clear any active job when the modal source changes
    setActiveAiJobId(null);
  }, [source]);

  // 2. Listen for job completion
  useEffect(() => {
    if (!activeAiJobId || !jobUpdates) return;

    // Find the specific job update
    const job = jobUpdates.find((j: BackgroundJob) => j.id === activeAiJobId);

    if (job && job.status === 'completed') {
      setActiveAiJobId(null);
      
      const result = job.result as BackgroundJob['result'];

      // Safely check for edited_content property
      if (result && typeof result === 'object' && 'edited_content' in result) {
        const editedContentResult = result as { edited_content: string };
        setAiEditedContent(editedContentResult.edited_content);
        
        // Automatically switch to AI Review mode to prompt user review
        setEditingMode('AIReview');
      }
      
      // Continue with notifications update logic
      
      // Fix: Use newJobId for notifications.update
      notifications.update({
        id: activeAiJobId,
        title: 'AI Edit Complete',
        message: 'Review the changes in the diff view.',
        color: 'green',
        icon: <IconRobot size={16} />,
        loading: false,
        autoClose: 5000,
      });
      
      // The notification logic needs to be updated to handle success/failure based on content presence
      if (result && typeof result === 'object' && 'edited_content' in result) {
        notifications.update({
          id: activeAiJobId,
          title: 'AI Edit Complete',
          message: 'Review the changes in the diff view.',
          color: 'green',
          icon: <IconRobot size={16} />,
          loading: false,
          autoClose: 5000,
        });
      } else {
        notifications.update({
          id: activeAiJobId,
          title: 'AI Edit Failed',
          message: 'The AI job completed but returned no content.',
          color: 'red',
          icon: <IconAlertCircle size={16} />,
          loading: false,
          autoClose: 5000,
        });
      }
    } else if (job && job.status === 'failed') {
      setActiveAiJobId(null);
      notifications.update({
        id: activeAiJobId,
        title: 'AI Edit Failed',
        message: job.error_message || 'The AI job failed due to a server error.',
        color: 'red',
        icon: <IconAlertCircle size={16} />,
        loading: false,
        autoClose: 5000,
      });
    }
  }, [activeAiJobId, jobUpdates]);

  const handleModifiedChange = useCallback((value: string) => {
    setEditedContent(value);
  }, []);

  const handleAiModifiedChange = useCallback((value: string) => {
    setAiEditedContent(value);
  }, []);

  const handleSelectionChange = useCallback((text: string) => {
    // Only update selectedText if no selection is currently locked
    if (!lockedSelection) {
      setSelectedText(text);
    }
  }, [lockedSelection]);


  const handleLockSelection = () => {
    if (lockedSelection) {
      setLockedSelection(null);
      setSelectedText(''); // Clear selected text state
    } else if (selectedText.trim()) {
      setLockedSelection(selectedText);
    }
  };

  const handleAiEdit = async () => {
    if (!sourceId || !source || !aiInstruction) return;

    // Determine content to send: use locked selection if available, otherwise use full edited content
    const contentToEdit = lockedSelection || editedContent;
    const fullContext = lockedSelection ? editedContent : undefined;

    // Clear previous AI result before starting a new job
    setAiEditedContent(editedContent);

    try {
      const result = await aiEditMutation.mutateAsync({
        projectId,
        data: {
          source_id: sourceId,
          original_content: contentToEdit,
          edit_instruction: aiInstruction,
          full_content_context: fullContext,
        },
      });
      const newJobId = result.data.id;
      // Start tracking the new job
      setActiveAiJobId(newJobId);
      notifications.show({
        title: 'AI Edit Started',
        message: 'The AI is processing your request in the background.',
        color: 'blue',
        icon: <IconHourglass size={16} />,
        loading: true,
        autoClose: false,
        id: newJobId, // Use the new job ID here
      });
    } catch {
      // Fix: Removed 'error' variable from catch block
      setActiveAiJobId(null);
    }
  };
const handleSave = async () => {
  if (!sourceId) return;

  try {
    await updateSourceMutation.mutateAsync(
      {
        projectId,
        sourceId,
        data: {
          raw_content: editedContent,
          content_type: selectedLanguage,
        },
      },
      {
        onSuccess: () => {
          // Refetch source details to update the original content for the diff view
          refetch();
          setAiEditedContent(null); // Clear diff view if active
        },
      }
    );
  } catch (e) {
    // Error handling is primarily done by the useMutation onError,
    // but catching here prevents unhandled promise rejection if needed.
    console.error('Save failed:', e);
  }
};

const handleConvert = async () => {
  if (!sourceId || !conversionTarget) return;

  // Conversion is only allowed between character card formats (Markdown/JSON)
  const isSourceCC =
    selectedLanguage.startsWith('cc_json') ||
    selectedLanguage.startsWith('cc_markdown') ||
    selectedLanguage === 'json' ||
    selectedLanguage === 'markdown';
  const isTargetCC = conversionTarget.startsWith('cc_json') || conversionTarget.startsWith('cc_markdown');

  if (!isSourceCC || !isTargetCC) {
    notifications.show({
      title: 'Conversion Error',
      message: 'Conversion is only supported between Character Card formats (including legacy JSON/Markdown) and versioned Character Card formats.',
      color: 'red',
    });
    return;
  }

  if (selectedLanguage === conversionTarget) {
    notifications.show({
      title: 'Conversion Error',
      message: 'Source and target formats are the same.',
      color: 'red',
    });
    return;
  }

  try {
    const result = await convertMutation.mutateAsync({
      projectId,
      data: {
        content: editedContent,
        source_type: selectedLanguage,
        target_type: conversionTarget,
        regex_patterns_to_strip: stripComments
          ? [
              // SillyTavern comment macro regex: /^{{comment:[\s\S]*?}}\n?|[ ]?{{comment:[\s\S]*?}}/gm
              '^{{comment:[\\s\\S]*?}}\\n?|[ ]?{{comment:[\\s\\S]*?}}',
            ]
          : undefined,
      },
    });

    const convertedContent = result.data.converted_content;
    setEditedContent(convertedContent);
    setSelectedLanguage(conversionTarget);
    setConversionTarget(null); // Clear target after successful conversion

    notifications.show({
      title: 'Conversion Complete',
      message: `Content successfully converted from ${selectedLanguage} to ${conversionTarget}.`,
      color: 'green',
    });
  } catch (e) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const error = e as any;
    notifications.show({
      title: 'Conversion Failed',
      message: `Error: ${error.response?.data?.detail || error.message}`,
      color: 'red',
    });
  }
};

const handleApplyAiEdit = () => {
  if (aiEditedContent !== null) {
    setEditedContent(aiEditedContent);
    setAiEditedContent(null); // Clear diff view state, but keep the content in editedContent
  }
};

  const handleCancelAiEdit = () => {
    // Revert the modified content in the diff view back to the current edited content
    setAiEditedContent(editedContent);
  };

  // All sources are now editable for manual cleanup
  const isEditable = !!source;

  // isAiReviewMode is now derived from the explicit editingMode state
  const handleClose = () => {
    setAiEditedContent(null);
    setAiInstruction('');
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      size="90%"
      styles={{
        content: {
          height: '90vh',
          maxHeight: '90vh',
        },
        body: {
          height: 'calc(90vh - 60px)', // Estimate header height at 60px
          maxHeight: 'calc(90vh - 60px)',
        },
      }}
      title={
        <Group justify="space-between" w="100%">
          <Title order={4}>Edit Source Content</Title>
          {source && isEditable && (
            <Group gap="xs">
              <SegmentedControl
                value={editingMode}
                onChange={(value) => setEditingMode(value as 'ManualReview' | 'AIReview')}
                data={[
                  { label: 'Manual Review', value: 'ManualReview' },
                  { label: 'AI Review', value: 'AIReview', disabled: aiEditedContent === null },
                ]}
                size="xs"
              />
              <Button
                leftSection={<IconHistory size={16} />}
                onClick={() => setHistoryModalOpened(true)}
                variant="default"
                size="xs"
                disabled={!sourceId}
              >
                View History
              </Button>
              <Button
                variant="filled"
                onClick={handleSave}
                disabled={
                  updateSourceMutation.isPending ||
                  !!activeAiJobId ||
                  editingMode === 'AIReview' || // Disable save in AI Review mode
                  editedContent === (source.raw_content ?? '')
                }
                size="xs"
              >
                Save Changes
              </Button>
              {editingMode === 'AIReview' && (
                <>
                  <Button
                    variant="default"
                    onClick={handleCancelAiEdit}
                    disabled={aiEditMutation.isPending || !!activeAiJobId}
                    size="xs"
                  >
                    Revert Diff
                  </Button>
                  <Button
                    variant="filled"
                    onClick={handleApplyAiEdit}
                    disabled={aiEditMutation.isPending || !!activeAiJobId || aiEditedContent === editedContent}
                    size="xs"
                  >
                    Apply AI Edit
                  </Button>
                </>
              )}
            </Group>
          )}
        </Group>
      }
    >
      <SourceVersionHistoryModal
        opened={historyModalOpened}
        onClose={() => {
          setHistoryModalOpened(false);
          refetch(); // Refetch source details in case a version was restored
        }}
        projectId={projectId}
        sourceId={sourceId}
        currentContent={editedContent}
        contentType={selectedLanguage}
      />
      {isLoading && <Loader />}
      {isError && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
          {error.message}
        </Alert>
      )}
      {source && (
        <Stack gap="md" style={{ height: '100%' }}>
          {/* Selection Lock UI */}
          <Group justify="space-between" align="center" p="xs" style={{ border: '1px solid var(--mantine-color-dark-4)', borderRadius: 'var(--mantine-radius-sm)' }}>
            <Text size="sm" c="dimmed" style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {lockedSelection
                ? `Locked for AI Edit: ${lockedSelection}`
                : selectedText.trim()
                  ? `Selected: ${selectedText}`
                  : 'Highlight text in the editor to lock a selection for AI editing.'}
            </Text>
            <Button
              size="xs"
              variant={lockedSelection ? 'filled' : 'default'}
              color={lockedSelection ? 'red' : 'blue'}
              leftSection={lockedSelection ? <IconLock size={16} /> : <IconLockOpen size={16} />}
              onClick={handleLockSelection}
              disabled={!selectedText.trim() && !lockedSelection}
            >
              {lockedSelection ? 'Unlock Selection' : 'Lock Selection'}
            </Button>
          </Group>

          <Group justify="space-between" align="flex-end">
            <Textarea
              label="AI Editing Instruction"
              placeholder="e.g., Summarize this content into 5 bullet points, focusing only on character traits."
              value={aiInstruction}
              onChange={(event) => setAiInstruction(event.currentTarget.value)}
              autosize
              minRows={2}
              maxRows={4}
              disabled={!!activeAiJobId}
              style={{ flexGrow: 1 }}
            />
            <Select
              label="Source Content Type"
              placeholder="Select file type"
              data={FILE_TYPE_OPTIONS}
              value={selectedLanguage}
              onChange={(value) => setSelectedLanguage((value as ContentType) ?? 'plaintext')}
              disabled={!!activeAiJobId}
              w={200}
            />
          </Group>
          
          {/* Conversion Controls */}
          <Group justify="space-between" align="flex-end">
            <Select
              label="Convert To Format"
              placeholder="Select target format"
              data={CONVERSION_TARGET_OPTIONS}
              value={conversionTarget}
              onChange={(value) => setConversionTarget((value as ContentType) ?? null)}
              disabled={!!activeAiJobId || convertMutation.isPending}
              w={200}
            />
            <Checkbox
              label="Strip SillyTavern Comments"
              checked={stripComments}
              onChange={(event) => setStripComments(event.currentTarget.checked)}
              disabled={!!activeAiJobId || convertMutation.isPending}
              style={{ alignSelf: 'flex-end', marginBottom: 4 }}
            />
            <Button
              leftSection={<IconExchange size={16} />}
              onClick={handleConvert}
              loading={convertMutation.isPending}
              disabled={
                !conversionTarget ||
                conversionTarget === selectedLanguage ||
                !!activeAiJobId ||
                convertMutation.isPending
              }
              size="xs"
            >
              Convert Content
            </Button>
          </Group>

          <Group justify="flex-end">
            <Button
              leftSection={<IconRobot size={16} />}
              onClick={handleAiEdit}
              loading={!!activeAiJobId}
              disabled={!aiInstruction || !!activeAiJobId}
              size="xs"
            >
              {activeAiJobId
                ? 'Processing...'
                : selectedText.trim()
                  ? 'Edit Selected Text'
                  : 'Generate AI Edit'}
            </Button>
          </Group>

          {!!activeAiJobId && (
            <Alert icon={<IconHourglass size="1rem" />} title="AI Job Running" color="blue">
              The AI is currently processing your edit request. This modal will update automatically when finished.
            </Alert>
          )}

          <Box flex={1} style={{ display: 'flex', flexDirection: 'column' }}>
            <Tabs value={activeTab} onChange={(value) => setActiveTab(value as 'Visual' | 'Difference')} keepMounted={false} style={{ flex: 1 }}>
              <Tabs.List>
                <Tabs.Tab value="Visual">Visual</Tabs.Tab>
                <Tabs.Tab value="Difference">Difference</Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="Visual" style={{ height: '100%', flex: 1 }}>
                <Box style={{ overflowY: 'auto', height: '100%', paddingTop: 'var(--mantine-spacing-md)' }}>
                  <BlockNoteEditor
                    content={editedContent}
                    onContentChange={handleModifiedChange}
                    language={selectedLanguage}
                  />
                </Box>
              </Tabs.Panel>

              <Tabs.Panel value="Difference" style={{ height: '100%', flex: 1 }}>
                <Box style={{ overflowY: 'auto', height: '100%', paddingTop: 'var(--mantine-spacing-md)' }}>
                  <CodeMirrorDiffEditor
                    key={`${sourceId}-${editingMode}`}
                    originalContent={editingMode === 'AIReview' ? editedContent : (source.raw_content ?? '')}
                    modifiedContent={editingMode === 'AIReview' ? (aiEditedContent ?? editedContent) : editedContent}
                    language={selectedLanguage}
                    onModifiedChange={editingMode === 'AIReview' ? handleAiModifiedChange : handleModifiedChange}
                    onSelectionChange={handleSelectionChange}
                  />
                </Box>
              </Tabs.Panel>
            </Tabs>
          </Box>
        </Stack>
      )}
    </Modal>
  );
}