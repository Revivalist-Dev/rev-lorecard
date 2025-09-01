import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { ProviderInfo } from '../types';

const fetchProviders = async (): Promise<ProviderInfo[]> => {
  const response = await apiClient.get('/providers');
  // The backend endpoint returns the data directly, not nested in a `data` property.
  return response.data;
};

export const useProviders = () => {
  return useQuery({
    queryKey: ['providers'],
    queryFn: fetchProviders,
  });
};
