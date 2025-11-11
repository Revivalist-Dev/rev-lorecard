import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSseStore } from '../stores/sseStore';
import { notifications } from '@mantine/notifications';
import type { BackgroundJob, PaginatedResponse, Link, LorebookEntry, CharacterCard, ProjectSource } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export function useSse(projectId: string | undefined) {
  const queryClient = useQueryClient();
  const { setStatus } = useSseStore();
  const isClosingRef = useRef(false); // Flag to track intentional closure
  
  useEffect(() => {
    if (!projectId) return;

    const eventSource = new EventSource(`${API_BASE_URL}/api/sse/subscribe/${projectId}`);

    eventSource.onopen = () => {
      console.log('SSE connection established.');
      setStatus('connected');
    };

    eventSource.onerror = () => {
      if (isClosingRef.current) {
        // Expected error during unmount/refresh, suppress verbose logging
        console.log('SSE connection interrupted during closure.');
        return;
      }
      console.warn('SSE Error: Connection interrupted.');
      setStatus('error');
      eventSource.close();
    };

    // --- JOB STATUS UPDATES ---
    eventSource.addEventListener('job_status_update', (event) => {
      const updatedJob: BackgroundJob = JSON.parse(event.data);
      const queryKey = ['jobs', updatedJob.project_id];

      queryClient.invalidateQueries({ queryKey: ['latestJob', updatedJob.project_id, updatedJob.task_name] });

      queryClient.setQueryData<PaginatedResponse<BackgroundJob>>(queryKey, (oldData) => {
        if (!oldData) return undefined;
        const jobIndex = oldData.data.findIndex((job) => job.id === updatedJob.id);
        if (jobIndex === -1) return oldData;

        const newData = [...oldData.data];
        newData[jobIndex] = updatedJob;
        return { ...oldData, data: newData };
      });

      if (
        (updatedJob.task_name === 'discover_and_crawl_sources' || updatedJob.task_name === 'rescan_links') &&
        updatedJob.status === 'in_progress'
      ) {
        queryClient.invalidateQueries({ queryKey: ['sources', updatedJob.project_id] });
        queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', updatedJob.project_id] });
        queryClient.invalidateQueries({ queryKey: ['apiRequestLogs', updatedJob.project_id] });
      }

      queryClient.invalidateQueries({ queryKey: ['project', updatedJob.project_id] });

      if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
        notifications.show({
          title: `Job ${updatedJob.status}: ${updatedJob.task_name.replace(/_/g, ' ')}`,
          message: `The job has finished with status: ${updatedJob.status}.`,
          color: updatedJob.status === 'completed' ? 'green' : 'red',
        });

        if (updatedJob.task_name === 'discover_and_crawl_sources' || updatedJob.task_name === 'rescan_links') {
          queryClient.invalidateQueries({ queryKey: ['sources', updatedJob.project_id] });
          queryClient.invalidateQueries({ queryKey: ['sourcesHierarchy', updatedJob.project_id] });
        }

        // Invalidate analytics and logs for any completed/failed job
        queryClient.invalidateQueries({ queryKey: ['apiRequestLogs', updatedJob.project_id] });
        queryClient.invalidateQueries({ queryKey: ['projectAnalytics', updatedJob.project_id] });
      }
    });

    // --- LOREBOOK EVENTS ---
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

    // --- CHARACTER CREATOR EVENTS ---
    eventSource.addEventListener('character_card_update', (event) => {
      const updatedCard: CharacterCard = JSON.parse(event.data);
      const queryKey = ['characterCard', updatedCard.project_id];
      queryClient.setQueryData(queryKey, { data: updatedCard });
    });

    eventSource.addEventListener('source_updated', (event) => {
      const updatedSource: ProjectSource = JSON.parse(event.data);
      const listQueryKey = ['sources', updatedSource.project_id];
      const detailQueryKey = ['sourceDetails', updatedSource.project_id, updatedSource.id];

      // 1. Update the list of sources cache
      queryClient.setQueryData<ProjectSource[]>(listQueryKey, (oldData) => {
        if (!oldData) return [];
        return oldData.map((source) => (source.id === updatedSource.id ? updatedSource : source));
      });

      // 2. Invalidate the single source detail cache (used by View/Edit modals)
      // This forces a refetch when the modal is opened or focused.
      queryClient.invalidateQueries({ queryKey: detailQueryKey });
    });

    return () => {
      isClosingRef.current = true; // Set flag before closing
      console.log('Closing SSE connection.');
      eventSource.close();
      setStatus('disconnected');
    };
  }, [projectId, queryClient, setStatus]);
}
