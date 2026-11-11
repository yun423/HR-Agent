import { request } from './index'

// 获取知识库列表
export function getKnowledgeBases(params = {}) {
  return request.get('/knowledge-base/', {
    params: {
      skip: params.skip || 0,
      limit: params.limit || 100,
      ...params
    }
  })
}

// 创建知识库
export function createKnowledgeBase(data) {
  return request.post('/knowledge-base/', data)
}

// 获取知识库详情
export function getKnowledgeBase(id) {
  return request.get(`/knowledge-base/${id}`)
}

// 更新知识库
export function updateKnowledgeBase(id, data) {
  return request.put(`/knowledge-base/${id}`, data)
}

// 删除知识库
export function deleteKnowledgeBase(id) {
  return request.delete(`/knowledge-base/${id}`)
}

// 搜索知识库
export function searchKnowledgeBase(id, query, limit = 10) {
  return request.post(`/knowledge-base/${id}/search`, {
    query,
    limit
  })
}

// 获取知识库文档列表
export function getKnowledgeBaseDocuments(knowledgeBaseId, params = {}) {
  return request.get('/knowledge-assistant/documents', {
    params: {
      knowledge_base_id: knowledgeBaseId,
      skip: params.skip || 0,
      limit: params.limit || 20,
      ...params
    }
  })
}

// 删除文档
export function deleteDocument(documentId) {
  return request.delete(`/documents/${documentId}`)
}

// 获取文档分块内容
export function getDocumentChunks(documentId) {
  return request.get(`/documents/${documentId}/chunks`)
}

// 处理已上传文档（提取文本、分块、向量化）
export function processDocument(documentId) {
  return request.post(`/documents/${documentId}/process`)
}