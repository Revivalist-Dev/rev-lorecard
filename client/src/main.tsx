import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MantineProvider, createTheme } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import './index.css';

const queryClient = new QueryClient();

const theme = createTheme({
  colors: {
    'terra-cotta': [
      '#FBF5F3',
      '#F3D8D2',
      '#EABCB1',
      '#E2A190',
      '#DA8570',
      '#D26A4F',
      '#C84E2E',
      '#A93F22',
      '#8A3016',
      '#6B210A',
    ],
    'app-gray': [
      '#F8F7F6',
      '#E9E7E6',
      '#DAD8D6',
      '#CBC8C6',
      '#BCB8B6',
      '#ADAAAB',
      '#9E9B9A',
      '#8F8D8A',
      '#807E79',
      '#717069',
    ],
    'dark-bg': [
      '#1A1A1A',
      '#262626',
      '#333333',
      '#404040',
      '#4D4D4D',
      '#5A5A5A',
      '#666666',
      '#737373',
      '#808080',
      '#8C8C8C',
    ],
  },

  primaryColor: 'terra-cotta',

  fontFamily: "'Manrope', system-ui, -apple-system, sans-serif",
  fontFamilyMonospace: "'JetBrains Mono', 'Fira Code', monospace",

  fontSizes: {
    xs: '0.6875rem',
    sm: '0.8125rem',
    md: '0.9375rem',
    lg: '1rem',
    xl: '1.125rem',
  },

  headings: {
    fontFamily: "'Manrope', system-ui, sans-serif",
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '2rem', lineHeight: '1.2' },
      h2: { fontSize: '1.75rem', lineHeight: '1.3' },
      h3: { fontSize: '1.5rem', lineHeight: '1.4' },
    },
  },

  spacing: {
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },

  radius: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
  },

  shadows: {
    xs: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
    sm: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.2)',
    md: '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.2)',
    lg: '0 8px 16px rgba(0, 0, 0, 0.15), 0 4px 8px rgba(0, 0, 0, 0.25)',
    xl: '0 12px 24px rgba(0, 0, 0, 0.2), 0 6px 12px rgba(0, 0, 0, 0.3)',
  },

  components: {
    Paper: {
      defaultProps: {
        withBorder: true,
      },
    },
    Title: {
      styles: {
        root: {
          color: 'rgba(255, 255, 255, 0.9)',
        },
      },
    },
    Text: {
      styles: {
        root: {
          '&[data-dimmed]': {
            color: 'rgba(255, 255, 255, 0.6) !important',
          },
        },
      },
    },
    Table: {
      styles: {
        table: { backgroundColor: 'transparent' },
        th: {
          color: 'rgba(255, 255, 255, 0.9)',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          fontWeight: 600,
        },
        td: {
          color: 'rgba(255, 255, 255, 0.7)',
          borderColor: 'rgba(255, 255, 255, 0.1)',
        },
      },
    },
    Code: {
      styles: {
        root: {
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          color: 'var(--terra-cotta-color)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          fontWeight: 500,
        },
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <BrowserRouter>
          <ModalsProvider>
            <App />
          </ModalsProvider>
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
