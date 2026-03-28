import { create } from 'zustand';

export type ToastTone = 'success' | 'error' | 'info';

export interface ToastItem {
  id: string;
  title: string;
  message?: string;
  tone: ToastTone;
}

interface ToastStore {
  toasts: ToastItem[];
  pushToast: (item: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  pushToast: (item) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    set((state) => ({ toasts: [...state.toasts, { ...item, id }] }));
    setTimeout(() => {
      get().removeToast(id);
    }, 3800);
  },
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
