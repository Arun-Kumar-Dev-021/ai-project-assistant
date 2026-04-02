import axios from 'axios';

const API = axios.create({ baseURL: '/api' });

// Projects
export const getProjects = () => API.get('/projects/').then(r => r.data);
export const createProject = (data) => API.post('/projects/', data).then(r => r.data);
export const getProject = (id) => API.get(`/projects/${id}`).then(r => r.data);
export const updateProject = (id, data) => API.patch(`/projects/${id}`, data).then(r => r.data);
export const deleteProject = (id) => API.delete(`/projects/${id}`).then(r => r.data);
export const getProjectSummary = (id) => API.get(`/projects/${id}/summary`).then(r => r.data);

// Chat
export const sendMessage = (data) => API.post('/chat/', data).then(r => r.data);
export const getConversations = (projectId) => API.get(`/chat/conversations/${projectId}`).then(r => r.data);
export const getChatHistory = (convId) => API.get(`/chat/history/${convId}`).then(r => r.data);
export const deleteConversation = (convId) => API.delete(`/chat/conversations/${convId}`).then(r => r.data);

// Images
export const generateImage = (data) => API.post('/images/generate', data).then(r => r.data);
export const analyzeImage = (data) => API.post('/images/analyze', data).then(r => r.data);
export const getProjectImages = (projectId) => API.get(`/images/${projectId}`).then(r => r.data);

// Memory
export const getMemory = (projectId) => API.get(`/memory/${projectId}`).then(r => r.data);
export const saveMemory = (data) => API.post('/memory/', data).then(r => r.data);
export const deleteMemory = (id) => API.delete(`/memory/${id}`).then(r => r.data);

// Agent
export const triggerAgent = (projectId) => API.post('/agent/trigger', { project_id: projectId }).then(r => r.data);
export const getAgentStatus = (jobId) => API.get(`/agent/status/${jobId}`).then(r => r.data);
export const getAgentJobs = (projectId) => API.get(`/agent/jobs/${projectId}`).then(r => r.data);
