import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { Credential } from '../types';

const fetchCredentials = async (): Promise<Credential[]> => {
  const response = await apiClient.get('/credentials');
  return response.data;
};

export const useCredentials = () => {
  return useQuery({
    queryKey: ['credentials'],
    queryFn: fetchCredentials,
  });
};
