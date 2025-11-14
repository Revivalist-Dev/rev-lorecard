import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const apiClient = axios.create({
  baseURL: API_BASE_URL ? `${API_BASE_URL}/api` : '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;

// --- Character Card Conversion API ---

import type {
  SingleResponse,
  ContentConversionRequest,
  ContentConversionResponse,
} from '../types';

export const convertCharacterCardContent = (
  projectId: string,
  data: ContentConversionRequest,
) => {
  return apiClient.post<SingleResponse<ContentConversionResponse>>(
    `/projects/${projectId}/character/convert`,
    data,
  );
};
