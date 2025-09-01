import { Input, Box } from '@mantine/core';
import Editor, { type EditorProps } from '@monaco-editor/react';

interface MonacoEditorInputProps extends Omit<EditorProps, 'value' | 'onChange'> {
  value?: string;
  onChange?: (value: string | undefined) => void;
  label?: React.ReactNode;
  description?: React.ReactNode;
  error?: React.ReactNode;
}

export function MonacoEditorInput({ value, onChange, label, description, error, ...props }: MonacoEditorInputProps) {
  return (
    <Input.Wrapper label={label} description={description} error={error} size="md">
      <Box
        mt="xs"
        style={{
          border: `1px solid ${error ? 'var(--mantine-color-error)' : 'var(--mantine-color-dark-4)'}`,
          borderRadius: 'var(--mantine-radius-sm)',
          overflow: 'hidden',
        }}
      >
        <Editor
          theme="vs-dark"
          value={value}
          onChange={onChange}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
          {...props}
        />
      </Box>
    </Input.Wrapper>
  );
}
