import { create } from "zustand";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_verified: boolean;
  two_factor_enabled: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, remember?: boolean, otp?: string) => Promise<void>;
  signup: (data: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,

  login: async (email, password, remember = false, otp) => {
    set({ isLoading: true });
    try {
      await authApi.login({ email, password, remember_me: remember, otp_code: otp });
      const { data } = await authApi.me();
      set({ user: data, isAuthenticated: true, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  signup: async (data) => {
    set({ isLoading: true });
    try {
      await authApi.signup(data);
      set({ isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } finally {
      set({ user: null, isAuthenticated: false });
    }
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const { data } = await authApi.me();
      set({ user: data, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
