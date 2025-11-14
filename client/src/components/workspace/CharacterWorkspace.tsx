import { Grid, Stack, Box } from '@mantine/core';
import type { Project } from '../../types';
import { CharacterSources } from './CharacterSources';
import { CharacterEditor } from './CharacterEditor';
import { useState } from 'react';

interface CharacterWorkspaceProps {
  project: Project;
}

export function CharacterWorkspace({ project }: CharacterWorkspaceProps) {
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);

  return (
    <Stack>
      <Grid gutter={5}>
        <Grid.Col span={{ base: 12, lg: 4 }}>
          <CharacterSources
            project={project}
            selectedSourceIds={selectedSourceIds}
            setSelectedSourceIds={setSelectedSourceIds}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 0, lg: 1 }} style={{ display: 'flex', justifyContent: 'center' }}>
          <Box
            w={1}
            h="100%"
            style={{
              background: `linear-gradient(to bottom, transparent 0%, var(--mantine-color-default-border) 20%, var(--mantine-color-default-border) 80%, transparent 100%)`,
            }}
            visibleFrom="lg"
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <CharacterEditor project={project} selectedSourceIds={selectedSourceIds} />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
