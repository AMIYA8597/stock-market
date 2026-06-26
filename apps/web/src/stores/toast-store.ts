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
  addToast: (params: {
    id: string;
    title: string;
    description: string;
    variant: 'success' | 'destructive' | 'default' | 'info';
    duration?: number;
  }) => void;
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
  addToast: (params) => {
    const exists = get().toasts.some((t) => t.id === params.id);
    if (exists) return;

    const tone: ToastTone =
      params.variant === 'success'
        ? 'success'
        : params.variant === 'destructive'
          ? 'error'
          : 'info';

    const newItem: ToastItem = {
      id: params.id,
      title: params.title,
      message: params.description,
      tone,
    };

    set((state) => ({ toasts: [...state.toasts, newItem] }));

    const duration = params.duration ?? 3800;
    setTimeout(() => {
      get().removeToast(params.id);
    }, duration);
  },
}));
