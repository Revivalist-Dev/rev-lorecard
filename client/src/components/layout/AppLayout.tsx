import { AppShell, Burger, Group, Title, NavLink, Box, Text, Anchor, Stack } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { IconGift, IconHome, IconKey, IconTemplate } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';
import { notifications } from '@mantine/notifications';
import { useEffect } from 'react';

interface AppInfo {
  current_version: string;
  latest_version?: string;
  runtime_env: 'docker' | 'source';
  update_available: boolean;
}

const fetchAppInfo = async (): Promise<AppInfo> => {
  const response = await apiClient.get('/info');
  return response.data;
};

const UpdateInstructions = ({ runtimeEnv }: { runtimeEnv: 'docker' | 'source' }) => {
  const instruction =
    runtimeEnv === 'docker'
      ? 'To update, please pull the latest Docker image and run your container.'
      : 'To update, please restart the application using the start.bat script.';

  return (
    <Text size="sm" mt="xs" fw={500}>
      {instruction}
    </Text>
  );
};

export function AppLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { pathname } = useLocation();
  const { data: appInfo } = useQuery({
    queryKey: ['appInfo'],
    queryFn: fetchAppInfo,
    staleTime: 1000 * 60 * 30,
  });

  useEffect(() => {
    if (appInfo?.current_version !== 'development' && appInfo?.update_available) {
      notifications.show({
        id: 'update-notification',
        title: 'Update Available!',
        color: 'teal',
        icon: <IconGift size={18} />,
        autoClose: false,
        message: (
          <Stack gap="xs">
            <Text size="sm">
              A new version (<strong>{appInfo.latest_version}</strong>) is available. You are currently on{' '}
              <strong>{appInfo.current_version}</strong>.
            </Text>
            <UpdateInstructions runtimeEnv={appInfo.runtime_env} />
          </Stack>
        ),
      });
    }
  }, [appInfo]);

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
            to="/credentials"
            label="Credentials"
            leftSection={<IconKey size="1rem" />}
            active={pathname === '/credentials'}
          />
          <NavLink
            component={Link}
            to="/templates"
            label="Templates"
            leftSection={<IconTemplate size="1rem" />}
            active={pathname === '/templates'}
          />
        </Box>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
        <Box component="footer" p="md" mt="xl" style={{ textAlign: 'center' }}>
          <Text c="dimmed" size="xs">
            Lorebook Creator
            {appInfo?.current_version && ` - Version: ${appInfo.current_version}`}
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
