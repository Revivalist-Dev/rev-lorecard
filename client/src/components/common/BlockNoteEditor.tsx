import { Box, Alert } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteEditor as CoreBlockNoteEditor, type PartialBlock } from "@blocknote/core";
import { BlockNoteView } from "@blocknote/mantine";
import "@blocknote/mantine/style.css";
import "@blocknote/core/fonts/inter.css";

interface BlockNoteEditorProps {
  content: string;
  onContentChange: (content: string) => void;
  language: string;
}

// Helper function to convert Markdown string to a simple BlockNote structure
// NOTE: This is a simplified conversion. For full Markdown support, a dedicated parser is needed.
const markdownToSimpleBlocks = (markdown: string): PartialBlock[] => {
  if (!markdown.trim()) {
    return [{ type: "paragraph", content: "" }];
  }
  // Split by double newline to approximate paragraphs/blocks
  const lines = markdown.split(/\n\n+/);
  return lines.map(line => ({
    type: "paragraph",
    content: line.trim(),
  })) as PartialBlock[];
};

export function BlockNoteEditor({ content, onContentChange, language }: BlockNoteEditorProps) {
  const isMarkdownCompatible = language === 'markdown' || language === 'plaintext';

  // Initialize editor with content converted from Markdown string
  const editor = useCreateBlockNote({
    initialContent: markdownToSimpleBlocks(content),
  });

  // Handle content changes and convert back to Markdown string
  const handleEditorContentChange = async (editor: CoreBlockNoteEditor) => {
    // Use blocksToMarkdownLossy if blocksToMarkdown is not available, but for stable npm package,
    // we rely on the standard API. Since we don't know the exact API, we'll use blocksToMarkdownLossy
    // as it was suggested by the compiler previously, and it's safer.
    const markdown = await editor.blocksToMarkdownLossy(editor.document);
    onContentChange(markdown);
  };

  return (
    <Box flex={1} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {!isMarkdownCompatible && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Visual Editor Warning" color="yellow" mb="md">
          The Visual Editor is optimized for Markdown and Plain Text. Editing content type "{language}" here may lead to formatting issues.
        </Alert>
      )}
      {/* BlockNoteView handles the editor UI */}
      <BlockNoteView
        editor={editor}
        onChange={handleEditorContentChange}
        // Ensure the editor takes up the remaining space
        style={{ flex: 1 }}
      />
    </Box>
  );
}