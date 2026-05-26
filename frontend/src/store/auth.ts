import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserRole } from '../api/types';

interface AuthState {
  token: string | null;
  username: string | null;
  fullName: string | null;
  role: UserRole | null;
  setSession: (s: { token: string; username: string; fullName: string; role: UserRole }) => void;
  logout: () => void;
  hasRole: (...roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      username: null,
      fullName: null,
      role: null,
      setSession: ({ token, username, fullName, role }) =>
        set({ token, username, fullName, role }),
      logout: () => set({ token: null, username: null, fullName: null, role: null }),
      hasRole: (...roles) => {
        const r = get().role;
        return r != null && roles.includes(r);
      },
    }),
    { name: 'gtp-auth' },
  ),
);
