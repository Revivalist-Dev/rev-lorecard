import { Suspense } from 'react';
import { Loader, Center } from '@mantine/core';
import React from 'react';

// Dynamically import the MonacoEditorInput component
const MonacoEditorInput = React.lazy(() =>
  import('./MonacoEditorInput').then((module) => ({ default: module.MonacoEditorInput }))
);

export const LazyMonacoEditorInput = (props: React.ComponentProps<typeof MonacoEditorInput>) => (
  <Suspense
    fallback={
      <Center
        style={{
          height: props.height || 200,
          border: '1px solid var(--mantine-color-dark-4)',
          borderRadius: 'var(--mantine-radius-sm)',
        }}
      >
        <Loader />
      </Center>
    }
  >
    <MonacoEditorInput {...props} />
  </Suspense>
);
