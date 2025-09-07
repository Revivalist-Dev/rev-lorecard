import { Grid, Stack } from '@mantine/core';
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
      <Grid gutter="xl">
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <CharacterSources
            project={project}
            selectedSourceIds={selectedSourceIds}
            setSelectedSourceIds={setSelectedSourceIds}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <CharacterEditor project={project} selectedSourceIds={selectedSourceIds} />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
