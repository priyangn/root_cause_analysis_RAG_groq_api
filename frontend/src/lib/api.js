import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
};

export const uploadAPI = {
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listUploads: () => api.get('/upload'),
  deleteUpload: (fileId) => api.delete(`/upload/${fileId}`),
};

export const analysisAPI = {
  startAnalysis: (fileIds, projectName) => api.post('/analysis/start', { 
    file_ids: fileIds,
    project_name: projectName 
  }),
  getAnalysis: (analysisId) => api.get(`/analysis/${analysisId}`),
  listAnalyses: () => api.get('/analysis'),
};

export const chatAPI = {
  sendMessage: (message, analysisId) => 
    api.post('/chat', { message, analysis_id: analysisId }),
};

export const reportAPI = {
  downloadReport: (analysisId) => 
    api.get(`/reports/${analysisId}/download`, { responseType: 'blob' }),
};

export default api;