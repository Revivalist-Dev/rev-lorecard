import { Modal, ScrollArea, Code, Loader, Alert, Title, Box, useMantineTheme } from '@mantine/core';
import { useProjectSourceDetails } from '../../hooks/useProjectSources';
import { IconAlertCircle } from '@tabler/icons-react';
import showdown from 'showdown';
import { useMemo } from 'react';

interface ViewSourceContentModalProps {
  opened: boolean;
  onClose: () => void;
  projectId: string;
  sourceId: string | null;
}

const converter = new showdown.Converter({ tables: true, openLinksInNewWindow: true });

export function ViewSourceContentModal({ opened, onClose, projectId, sourceId }: ViewSourceContentModalProps) {
  const { data, isLoading, isError, error } = useProjectSourceDetails(projectId, sourceId);
  const source = data?.data;
  const theme = useMantineTheme();

  const renderedContent = useMemo(() => {
    if (!source?.raw_content) {
      return 'No content fetched or content is empty.';
    }
    if (source.content_type === 'markdown') {
      return converter.makeHtml(source.raw_content);
    }
    return source.raw_content;
  }, [source]);

  return (
    <Modal opened={opened} onClose={onClose} size="80%" title={<Title order={4}>View Source Content</Title>}>
      {isLoading && <Loader />}
      {isError && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
          {error.message}
        </Alert>
      )}
      {source && (
        <ScrollArea h="80vh">
          {source.content_type === 'markdown' ? (
            <Box
              p="md"
              dangerouslySetInnerHTML={{ __html: renderedContent }}
              style={{
                color: theme.colors.gray[3],
                lineHeight: 1.6,
                a: { color: theme.colors.blue[4] },
              }}
            />
          ) : (
            <Code block style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {renderedContent}
            </Code>
          )}
        </ScrollArea>
      )}
    </Modal>
  );
}
