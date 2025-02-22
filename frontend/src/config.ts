const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const config = {
  apiUrl: API_URL,
  wsUrl: API_URL.replace(/^http/, 'ws'),
  endpoints: {
    deals: `${API_URL}/api/deals`,
    findDeals: `${API_URL}/api/find-deals`,
    websocket: (sessionId: string) => `${API_URL.replace(/^http/, 'ws')}/ws/${sessionId}`,
  }
};

export default config; 