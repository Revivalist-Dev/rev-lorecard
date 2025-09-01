import { create } from 'zustand';

export type SseStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

export interface SseState {
  status: SseStatus;
  setStatus: (status: SseStatus) => void;
}

export const useSseStore = create<SseState>((set) => ({
  status: 'disconnected',
  setStatus: (status) => set({ status }),
}));
