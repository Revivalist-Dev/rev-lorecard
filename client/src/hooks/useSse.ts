import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSseStore } from '../stores/sseStore';
import { notifications } from '@mantine/notifications';
import type { BackgroundJob, PaginatedResponse, Link, LorebookEntry } from '../types';

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

    // --- JOB STATUS UPDATES ---
    eventSource.addEventListener('job_status_update', (event) => {
      const updatedJob: BackgroundJob = JSON.parse(event.data);
      const queryKey = ['jobs', updatedJob.project_id];

      queryClient.setQueryData<PaginatedResponse<BackgroundJob>>(queryKey, (oldData) => {
        if (!oldData) return undefined;
        const jobIndex = oldData.data.findIndex((job) => job.id === updatedJob.id);
        if (jobIndex === -1) return oldData;

        const newData = [...oldData.data];
        newData[jobIndex] = updatedJob;
        return { ...oldData, data: newData };
      });

      queryClient.invalidateQueries({ queryKey: ['project', updatedJob.project_id] });

      if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
        notifications.show({
          title: `Job ${updatedJob.status}: ${updatedJob.task_name.replace(/_/g, ' ')}`,
          message: `The job has finished with status: ${updatedJob.status}.`,
          color: updatedJob.status === 'completed' ? 'green' : 'red',
        });

        if (updatedJob.task_name === 'generate_selector' || updatedJob.task_name === 'rescan_links') {
          queryClient.invalidateQueries({ queryKey: ['sources', updatedJob.project_id] });
        }

        queryClient.invalidateQueries({ queryKey: ['apiRequestLogs', updatedJob.project_id] });
        queryClient.invalidateQueries({ queryKey: ['projectAnalytics', updatedJob.project_id] });
      }
    });

    eventSource.addEventListener('link_updated', (event) => {
      const updatedLink: Link = JSON.parse(event.data);
      queryClient.invalidateQueries({ queryKey: ['links', updatedLink.project_id] });
    });

    eventSource.addEventListener('links_created', (event) => {
      const data = JSON.parse(event.data);
      const firstLink = data?.links?.[0];
      if (firstLink?.project_id) {
        queryClient.invalidateQueries({ queryKey: ['links', firstLink.project_id] });
      }
    });

    eventSource.addEventListener('entry_created', (event) => {
      const newEntry: LorebookEntry = JSON.parse(event.data);
      queryClient.invalidateQueries({ queryKey: ['entries', newEntry.project_id] });
    });

    return () => {
      console.log('Closing SSE connection.');
      eventSource.close();
      setStatus('disconnected');
    };
  }, [projectId, queryClient, setStatus]);
}
