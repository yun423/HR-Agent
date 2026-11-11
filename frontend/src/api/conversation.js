import { request } from './index'

// 获取用户的对话列表
export function getConversations(params = {}) {
  return request.get('/conversations/', {
    params: {
      skip: params.skip || 0,
      limit: params.limit || 100,
      ...params
    }
  })
}

// 创建新对话
export function createConversation(data) {
  return request.post('/conversations/', data)
}

// 获取单个对话详情
export function getConversation(conversationId) {
  return request.get(`/conversations/${conversationId}`)
}

// 更新对话
export function updateConversation(conversationId, data) {
  return request.put(`/conversations/${conversationId}`, data)
}

// 删除对话
export function deleteConversation(conversationId) {
  return request.delete(`/conversations/${conversationId}`)
}

// 获取对话的消息列表
export function getConversationMessages(conversationId, params = {}) {
  return request.get(`/conversations/${conversationId}/messages`, {
    params: {
      skip: params.skip || 0,
      limit: params.limit || 100,
      ...params
    }
  })
}

// 追加单条消息
export function addConversationMessage(conversationId, message) {
  return request.post(`/conversations/${conversationId}/messages`, {
    conversation_id: conversationId,
    ...message
  })
}

// 更新单条对话消息
export function updateConversationMessage(conversationId, messageId, message) {
  return request.put(`/conversations/${conversationId}/messages/${messageId}`, message)
}

// 删除单条对话消息
export function deleteConversationMessage(conversationId, messageId) {
  return request.delete(`/conversations/${conversationId}/messages/${messageId}`)
}

// 保存对话消息（批量保存）
export function saveConversationMessages(conversationId, messages) {
  return request.post(`/conversations/${conversationId}/messages/batch`, {
    messages: messages
  })
}
