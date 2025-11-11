import { Modal, Button, Group, Stack, Text, Title, Box } from '@mantine/core';
import { IconCode, IconFileDescription } from '@tabler/icons-react';
import type { ContentType } from '../../types';

interface FormatOption {
  value: ContentType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const FORMAT_OPTIONS: FormatOption[] = [
  {
    value: 'markdown',
    label: 'Structured Text (.md)',
    description: 'Extracts character fields into a human-readable, structured text format (Markdown).',
    icon: <IconFileDescription size={24} />,
  },
  {
    value: 'json',
    label: 'Raw JSON (.json)',
    description: 'Extracts the raw character card data as a JSON object.',
    icon: <IconCode size={24} />,
  },
];

interface CharacterCardFormatSelectorModalProps {
  opened: boolean;
  onClose: () => void;
  onSelect: (format: ContentType) => void;
}

export function CharacterCardFormatSelectorModal({ opened, onClose, onSelect }: CharacterCardFormatSelectorModalProps) {
  const handleSelect = (format: ContentType) => {
    onSelect(format);
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Title order={3}>Select Character Card Output Format</Title>}
      size="lg"
      centered
    >
      <Stack gap="lg">
        <Text size="sm" c="dimmed">
          Please choose the format in which the character card data should be extracted and stored as a source.
        </Text>
        <Group grow>
          {FORMAT_OPTIONS.map((option) => (
            <Button
              key={option.value}
              variant="default"
              onClick={() => handleSelect(option.value)}
              style={{ minHeight: 150, padding: '20px 10px' }}
            >
              <Stack justify="center" align="center" w="100%" h="100%" gap="xs">
                <Box c="blue">{option.icon}</Box>
                <Text fw={700} size="md" ta="center">
                  {option.label}
                </Text>
              </Stack>
            </Button>
          ))}
        </Group>
      </Stack>
    </Modal>
  );
}