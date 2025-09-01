import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSseStore } from '../stores/sseStore';
import { notifications } from '@mantine/notifications';
import type { BackgroundJob } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export function useSse(projectId: string | undefined) {
  const queryClient = useQueryClient();
  const { setStatus } = useSseStore();

  useEffect(() => {
    if (!projectId) return;

    const eventSource = new EventSource(`${API_BASE_URL}/api/sse/subscribe/${projectId}`);

    eventSource.onopen = () => {
      console.log('SSE connection established.');
      setStatus('connected');
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      setStatus('error');
      eventSource.close();
    };

    // Listen for job status updates
    eventSource.addEventListener('job_status_update', (event) => {
      console.log('Received job_status_update:', event.data);
      const job: BackgroundJob = JSON.parse(event.data);

      // Invalidate queries to trigger a refetch of project and job data
      queryClient.invalidateQueries({ queryKey: ['project', job.project_id] });
      queryClient.invalidateQueries({ queryKey: ['jobs', job.project_id] });

      if (job.status === 'completed' || job.status === 'failed') {
        notifications.show({
          title: `Job ${job.status}: ${job.task_name.replace(/_/g, ' ')}`,
          message: `The job has finished with status: ${job.status}.`,
          color: job.status === 'completed' ? 'green' : 'red',
        });
      }
    });

    // Clean up the connection when the component unmounts or projectId changes
    return () => {
      console.log('Closing SSE connection.');
      eventSource.close();
      setStatus('disconnected');
    };
  }, [projectId, queryClient, setStatus]);
}
