import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase();
  if (method && !["get", "head", "options"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      config.headers.set("X-CSRF-Token", csrf);
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        await api.post("/auth/refresh");
        return api(original);
      } catch {
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  signup: (data: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
    phone?: string;
  }) => api.post("/auth/signup", data),
  login: (data: { email: string; password: string; remember_me?: boolean; otp_code?: string }) =>
    api.post("/auth/login", data),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  resetPassword: (data: { token: string; password: string; confirm_password: string }) =>
    api.post("/auth/reset-password", data),
};

export const dashboardApi = {
  overview: () => api.get("/dashboard/overview"),
  recentTrades: () => api.get("/dashboard/recent-trades"),
};

export const strategyApi = {
  list: () => api.get("/strategies"),
  create: (data: object) => api.post("/strategies", data),
  start: (id: string) => api.post(`/strategies/${id}/start`),
  stop: (id: string) => api.post(`/strategies/${id}/stop`),
  backtest: (data: object) => api.post("/strategies/backtest", data),
  getRun: (runId: string) => api.get(`/strategies/runs/${runId}`),
};

export const portfolioApi = {
  list: () => api.get("/portfolios"),
  create: (data: { name: string; currency?: string; initial_capital?: number }) =>
    api.post("/portfolios", data),
  analytics: (id: string) => api.get(`/portfolios/${id}/analytics`),
  valuation: (id: string, source = "paper") =>
    api.get(`/portfolios/${id}/valuation`, { params: { source } }),
  history: (id: string, days = 30) =>
    api.get(`/portfolios/${id}/history`, { params: { days } }),
  performance: (id: string, days = 30) =>
    api.get(`/portfolios/${id}/performance`, { params: { days } }),
};

export const riskApi = {
  limits: (portfolioId: string) => api.get(`/risk/${portfolioId}`),
  summary: (portfolioId: string) => api.get(`/risk/${portfolioId}/summary`),
  events: (portfolioId: string, limit = 50) =>
    api.get(`/risk/${portfolioId}/events`, { params: { limit } }),
  updateLimits: (portfolioId: string, data: Record<string, unknown>) =>
    api.put(`/risk/${portfolioId}`, data),
};

export const brokerApi = {
  list: () => api.get("/brokers"),
  connect: (data: { broker: string; api_key: string; api_secret: string; access_token?: string }) =>
    api.post("/brokers/connect", data),
  disconnect: (id: string) => api.delete(`/brokers/${id}`),
  quote: (symbol: string, broker?: string) =>
    api.get(`/brokers/quote/${symbol}`, { params: { broker } }),
};

export const notificationApi = {
  list: (unreadOnly?: boolean) =>
    api.get("/notifications", { params: { unread_only: unreadOnly } }),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post("/notifications/read-all"),
};

export const aiApi = {
  marketSummary: () => api.get("/ai/market-summary"),
  riskAnalysis: () => api.get("/ai/risk-analysis"),
  portfolioAnalysis: () => api.get("/ai/portfolio-analysis"),
  tradeJournal: () => api.get("/ai/trade-journal"),
};

export const deploymentApi = {
  list: () => api.get("/deployments"),
  create: (data: { strategy_id: string; name: string; region?: string }) =>
    api.post("/deployments", data),
  start: (id: string) => api.post(`/deployments/${id}/start`),
  stop: (id: string) => api.post(`/deployments/${id}/stop`),
};

export const logsApi = {
  strategy: () => api.get("/logs/strategy"),
  audit: () => api.get("/logs/audit"),
  system: () => api.get("/logs/system"),
};

export const billingApi = {
  plans: () => api.get("/billing/plans"),
  subscription: () => api.get("/billing/subscription"),
  checkout: (plan: "starter" | "pro") => api.post("/billing/checkout", { plan }),
  portal: () => api.post("/billing/portal"),
};
