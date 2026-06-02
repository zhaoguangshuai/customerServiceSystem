import request from '../utils/request'

// --- Auth ---
export function login(username, password) {
  return request.post('/admin/login', { username, password })
}

export function getCurrentUser() {
  return request.get('/admin/me')
}

// --- Tenants ---
export function listTenants() {
  return request.get('/admin/tenants')
}

export function createTenant(data) {
  return request.post('/admin/tenants', data)
}

export function updateTenant(tenantId, data) {
  return request.put(`/admin/tenants/${tenantId}`, data)
}

export function deleteTenant(tenantId) {
  return request.delete(`/admin/tenants/${tenantId}`)
}

// --- Prompts ---
export function getPrompt(tenantId) {
  return request.get(`/admin/prompts/${tenantId}`)
}

export function updatePrompt(tenantId, data) {
  return request.put(`/admin/prompts/${tenantId}`, data)
}

// --- Chat Logs ---
export function listChatLogs(params) {
  return request.get('/admin/chat-logs', { params })
}

// --- FAQs ---
export function listFaqs(tenantId) {
  return request.get('/admin/faqs', { params: { tenant_id: tenantId } })
}

export function createFaq(data) {
  return request.post('/admin/faqs', data)
}

export function updateFaq(faqId, data) {
  return request.put(`/admin/faqs/${faqId}`, data)
}

export function deleteFaq(faqId) {
  return request.delete(`/admin/faqs/${faqId}`)
}

// --- Knowledge ---
export function listKnowledge(tenantId, category) {
  return request.get('/jewelry/knowledge/list', {
    params: { tenant_id: tenantId, category },
  })
}

export function deleteKnowledge(docId) {
  return request.delete(`/jewelry/knowledge/${docId}`)
}

// --- Statistics ---
export function getStatistics(tenantId) {
  return request.get('/admin/statistics', { params: { tenant_id: tenantId } })
}

// --- Quality Inspection ---
export function listReviews(params) {
  return request.get('/admin/reviews', { params })
}

export function submitReview(logId, data) {
  return request.put(`/admin/reviews/${logId}`, data)
}

export function flagReview(logId, data) {
  return request.put(`/admin/reviews/${logId}/flag`, data)
}

export function getReviewStats(tenantId) {
  return request.get('/admin/reviews/stats', { params: { tenant_id: tenantId } })
}
