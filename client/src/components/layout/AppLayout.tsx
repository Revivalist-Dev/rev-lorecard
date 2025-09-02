import { AppShell, Burger, Group, Title, NavLink, Box, Text, Anchor } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { IconHome } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface AppInfo {
  version: string;
}

const fetchAppInfo = async (): Promise<AppInfo> => {
  const response = await apiClient.get('/info');
  return response.data;
};

export function AppLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { pathname } = useLocation();
  const { data: appInfo } = useQuery({
    queryKey: ['appInfo'],
    queryFn: fetchAppInfo,
    staleTime: Infinity,
  });

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 300, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <Title order={3}>Lorebook Creator</Title>
          </Link>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Box>
          <NavLink
            component={Link}
            to="/"
            label="Projects"
            leftSection={<IconHome size="1rem" />}
            active={pathname === '/' || pathname.startsWith('/projects')}
          />
          <NavLink
            component={Link}
            to="/templates"
            label="Templates"
            leftSection={<IconHome size="1rem" />}
            active={pathname === '/templates'}
          />
        </Box>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
        <Box component="footer" p="md" mt="xl" style={{ textAlign: 'center' }}>
          <Text c="dimmed" size="xs">
            Lorebook Creator
            {appInfo?.version && ` - Version: ${appInfo.version}`}
            {' | '}
            <Anchor href="https://github.com/bmen25124/lorebook-creator" target="_blank" c="dimmed" size="xs">
              GitHub
            </Anchor>
          </Text>
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
