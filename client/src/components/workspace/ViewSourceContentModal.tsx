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

export function ViewSourceContentModal({ opened, onClose, projectId, sourceId }: ViewSourceContentModalProps) {
  const { data, isLoading, isError, error } = useProjectSourceDetails(projectId, sourceId);
  const source = data?.data;
  const theme = useMantineTheme();

  // Create a memoized showdown converter with our custom extension
  const converter = useMemo(() => {
    if (!source?.url) {
      // Return a default converter if the source URL isn't available yet
      return new showdown.Converter({ tables: true, openLinksInNewWindow: true });
    }

    const baseUrl = new URL(source.url).origin;

    const absoluteLinksExtension = () => [
      {
        type: 'output', // Run this after markdown has been converted to HTML
        filter: (text: string) => {
          // Use the browser's own parser to safely manipulate the HTML
          const wrapper = document.createElement('div');
          wrapper.innerHTML = text;

          // Process all links (<a> tags)
          wrapper.querySelectorAll('a').forEach((anchor) => {
            const href = anchor.getAttribute('href');
            if (href && !href.startsWith('http') && !href.startsWith('#')) {
              try {
                const absoluteUrl = new URL(href, baseUrl).href;
                anchor.setAttribute('href', absoluteUrl);
              } catch (e) {
                console.error(`Could not create absolute URL for href="${href}" with base "${baseUrl}"`, e);
              }
            }
          });

          // Process all images (<img> tags)
          wrapper.querySelectorAll('img').forEach((img) => {
            const src = img.getAttribute('src');
            if (src && !src.startsWith('http')) {
              try {
                const absoluteUrl = new URL(src, baseUrl).href;
                img.setAttribute('src', absoluteUrl);
              } catch (e) {
                console.error(`Could not create absolute URL for src="${src}" with base "${baseUrl}"`, e);
              }
            }
          });

          return wrapper.innerHTML;
        },
      },
    ];

    return new showdown.Converter({
      tables: true,
      openLinksInNewWindow: true,
      extensions: [absoluteLinksExtension],
    });
  }, [source?.url]);

  const renderedContent = useMemo(() => {
    if (!source?.raw_content) {
      return 'No content fetched or content is empty.';
    }
    if (source.content_type === 'markdown') {
      return converter.makeHtml(source.raw_content);
    }
    return source.raw_content;
  }, [source, converter]);

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
                // Add styles for better preview
                'h1, h2, h3': {
                  marginTop: '24px',
                  marginBottom: '16px',
                  fontWeight: 600,
                  lineHeight: 1.25,
                },
                h1: { fontSize: '2em' },
                h2: { fontSize: '1.5em' },
                h3: { fontSize: '1.25em' },
                a: { color: theme.colors.blue[4], textDecoration: 'none' },
                'a:hover': { textDecoration: 'underline' },
                'p, ul, ol': {
                  marginBottom: '16px',
                },
                'ul, ol': {
                  paddingLeft: '30px',
                },
                li: {
                  marginBottom: '8px',
                },
                code: {
                  padding: '.2em .4em',
                  margin: '0',
                  fontSize: '85%',
                  backgroundColor: 'rgba(135,131,120,.15)',
                  borderRadius: '6px',
                },
                pre: {
                  padding: '16px',
                  overflow: 'auto',
                  fontSize: '85%',
                  lineHeight: 1.45,
                  backgroundColor: 'rgba(135,131,120,.15)',
                  borderRadius: '6px',
                },
                table: {
                  width: '100%',
                  borderCollapse: 'collapse',
                  marginBottom: '16px',
                },
                'th, td': {
                  border: `1px solid ${theme.colors.dark[4]}`,
                  padding: '8px',
                },
                th: {
                  fontWeight: 600,
                },
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
