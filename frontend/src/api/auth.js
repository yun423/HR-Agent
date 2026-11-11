import { request } from './index'

export const authApi = {
  // 登录
  login: (credentials) => {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    return request.post('/auth/login', formData)
  },

  // 注册
  register: (userData) => {
    return request.post('/auth/register', userData)
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return request.get('/auth/me')
  },

  // 刷新token
  refreshToken: () => {
    return request.post('/auth/refresh')
  },

  // 修改密码
  changePassword: (data) => {
    return request.post('/auth/change-password', data)
  },

  // 更新用户信息
  updateProfile: (data) => {
    return request.put('/auth/profile', data)
  }
}