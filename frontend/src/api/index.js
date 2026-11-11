import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus' // 确保引入了 ElMessage
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import Cookies from 'js-cookie'

// 定义一个全局变量锁，防止 401 弹窗重复出现
let isRelogin = false

// 创建axios实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json'
  },
  paramsSerializer: (params) => {
    const searchParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined) {
        searchParams.append(key, params[key])
      }
    })
    return searchParams.toString()
  },
  withCredentials: true
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    if (config.data instanceof FormData) {
      config.headers['Content-Type'] = 'multipart/form-data'
    } else if (config.method === 'post' && config.url.includes('/auth/login')) {
      config.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    }
    
    return config
  },
  (error) => {
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const { response } = error
    
    if (response) {
      const { status, data } = response
      
      switch (status) {
        case 401:
          // 修改 401 处理逻辑：加锁
          if (!isRelogin) {
            isRelogin = true // 马上锁住，后续请求进不来这个 if
            
            // 清理屏幕上已有的所有消息（防止红框堆叠）
            ElMessage.closeAll()
            
            const authStore = useAuthStore()
            // 注意：store 里的 logout 可能会弹“已退出登录”，这里我们只负责处理报错
            authStore.logout()
            
            if (router.currentRoute.value.path !== '/login') {
              // 使用 grouping: true 防止极端情况下的重复
              ElMessage.error({
                message: '登录已过期，请重新登录',
                grouping: true
              })
              
              router.push('/login').then(() => {
                // 跳转完成后，稍微延迟一下再解锁（可选，防止跳转过程中的请求触发）
                setTimeout(() => {
                  isRelogin = false
                }, 1000)
              })
            } else {
                isRelogin = false
            }
          }
          // 如果 isRelogin 为 true，说明已经有一个请求在处理 401 了，这里直接忽略后续的 401
          break
          
        case 403:
          ElMessage.error('没有权限访问该资源')
          break
          
        case 404:
          ElMessage.error('请求的资源不存在')
          break
          
        case 422:
          if (data && data.error && data.error.details && Array.isArray(data.error.details.errors)) {
            const errors = data.error.details.errors.map(e => `${e.field}: ${e.message}`).join('；')
            ElMessage.error(`参数错误: ${errors}`)
          } else if (data.detail && Array.isArray(data.detail)) {
            const errors = data.detail.map(item => item.msg).join(', ')
            ElMessage.error(`参数错误: ${errors}`)
          } else {
            const msg = data?.error?.message || data?.message || '参数验证失败'
            ElMessage.error(msg)
          }
          break
          
        case 500:
          ElMessage.error('服务器内部错误，请稍后重试')
          break
          
        default:
          const errorMessage = data?.error?.message || data?.message || '请求失败'
          ElMessage.error(errorMessage)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查网络连接')
    } else {
      // 避免 Cancel 的请求（页面跳转中断请求）弹出网络错误
      if (axios.isCancel(error)) {
         return Promise.reject(error)
      }
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

export const request = {
  get: (url, config = {}) => api.get(url, config),
  post: (url, data = {}) => api.post(url, data),
  put: (url, data = {}) => api.put(url, data),
  delete: (url) => api.delete(url),
  patch: (url, data = {}) => api.patch(url, data)
}

export default api