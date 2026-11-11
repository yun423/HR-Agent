import { request } from '@/api'

export const adminApi = {
  listUsers(params = {}) {
    return request.get('/users/', { params })
  },
  createUser(data) {
    return request.post('/users/admin/users', data)
  },
  listRoles() {
    return request.get('/users/admin/roles')
  },
  createRole(data) {
    return request.post('/users/admin/roles', data)
  },
  deleteRole(roleId) {
    return request.delete(`/users/admin/roles/${roleId}`)
  },
  getUserRoles(userId) {
    return request.get(`/users/admin/users/${userId}/roles`)
  },
  assignUserRoles(userId, roleIds) {
    return request.put(`/users/admin/users/${userId}/roles`, { role_ids: roleIds })
  }
}

export const accountApi = {
  getMyRoles() {
    return request.get('/users/me/roles')
  }
}

// 邮箱配置管理相关API
export const emailConfigApi = {
  // 获取邮箱配置列表
  getEmailConfigList(params) {
    const p = { ...(params || {}) }
    if (p.page && p.size) {
      p.skip = (Number(p.page) - 1) * Number(p.size)
      p.limit = Number(p.size)
      delete p.page
      delete p.size
    }
    return request.get('/email-configs/', { params: p })
  },

  // 获取单个邮箱配置详情
  getEmailConfig(id) {
    return request.get(`/email-configs/${id}`)
  },

  // 创建邮箱配置
  createEmailConfig(data) {
    return request.post('/email-configs/', data)
  },

  // 更新邮箱配置
  updateEmailConfig(id, data) {
    return request.put(`/email-configs/${id}`, data)
  },

  // 删除邮箱配置
  deleteEmailConfig(id) {
    return request.delete(`/email-configs/${id}`)
  },

  // 测试邮箱连接
  testEmailConnection(id, data) {
    return request.post(`/email-configs/${id}/test`, data)
  },

  // 手动触发简历抓取
  fetchEmails(id) {
    return request.post(`/email-configs/${id}/fetch`)
  },

  // 获取邮箱抓取日志
  getEmailFetchLogs(configId, params) {
    return request.get(`/email-configs/${configId}/logs`, { params })
  }
}

// 系统统计相关API
export const systemApi = {
  // 获取系统统计信息
  getSystemStats() {
    return request.get('/system/stats')
  },

  // 获取系统最近活动
  getRecentActivity(params) {
    return request.get('/system/activity', { params })
  },

  // 获取在线用户数
  getOnlineUsers() {
    return request.get('/system/online-users')
  }
}

