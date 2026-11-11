import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'
import Cookies from 'js-cookie'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref(Cookies.get('token') || '')
  const user = ref(null)
  const roles = ref([])
  const loading = ref(false)
  const offlineLogin = ref(false)

  // 定义一个标记，防止短时间内重复登出
  const isLogoutProcessing = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdminByRole = computed(() => roles.value.some(r => r.name === '超级管理员'))

  // 设置token
  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      Cookies.set('token', newToken, { expires: 7 }) // 7天过期
    } else {
      Cookies.remove('token')
    }
  }

  // 设置用户信息
  const setUser = (userInfo) => {
    user.value = userInfo
  }

  const setRoles = (roleList) => {
    roles.value = Array.isArray(roleList) ? roleList : []
  }

  // 登录
  const login = async (credentials) => {
    try {
      loading.value = true
      // 登录时重置登出标记，确保后续能正常登出
      isLogoutProcessing.value = false 
      const response = await authApi.login(credentials)
      
      if (response.access_token) {
        setToken(response.access_token)
        
        // 获取用户信息
        await getCurrentUser()
        
        ElMessage.success('登录成功')
        return { success: true }
      } else {
        throw new Error('登录失败：未获取到访问令牌')
      }
    } catch (error) {
      console.error('登录失败:', error)
      ElMessage.error(error.message || '登录失败，请检查用户名和密码')
      return { success: false, error: error.message }
    } finally {
      loading.value = false
    }
  }

  // 获取当前用户信息
  const getCurrentUser = async () => {
    try {
      if (!token.value) {
        throw new Error('未找到访问令牌')
      }
      
      const userInfo = await authApi.getCurrentUser()
      setUser(userInfo)
      try {
        const { accountApi } = await import('@/api/admin')
        const myRoles = await accountApi.getMyRoles()
        setRoles(myRoles)
      } catch (e) {
        setRoles([])
      }
      return userInfo
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 如果获取用户信息失败，清除token
      if (!offlineLogin.value) {
        logout()
      }
      throw error
    }
  }

  // 刷新token
  const refreshToken = async () => {
    try {
      const response = await authApi.refreshToken()
      if (response.access_token) {
        setToken(response.access_token)
        return true
      }
      return false
    } catch (error) {
      console.error('刷新token失败:', error)
      logout()
      return false
    }
  }

  // 登出
  const logout = () => {
    // 如果正在处理登出，直接返回，防止重复弹窗
    if (isLogoutProcessing.value) return
    isLogoutProcessing.value = true

    // 核心步骤：关闭屏幕上所有已存在的 Message（消除堆叠的红色报错框）
    ElMessage.closeAll()

    setToken('')
    setUser(null)
    setRoles([])

    // 使用 grouping: true 防止自己重复，并显示提示
    ElMessage.success({
      message: '已退出登录',
      grouping: true,
    })
    
    // 如果有路由跳转逻辑（比如 router.push('/login')），建议放在这里或者组件调用处
  }

  // 检查认证状态
  const checkAuth = async () => {
    if (token.value && !user.value) {
      try {
        await getCurrentUser()
      } catch (error) {
        console.error('检查认证状态失败:', error)
        logout()
      }
    }
  }

  // 更新用户信息
  const updateUser = (userInfo) => {
    user.value = { ...user.value, ...userInfo }
  }

  return {
    // 状态
    token: computed(() => token.value),
    user: computed(() => user.value),
    roles: computed(() => roles.value),
    loading: computed(() => loading.value),
    isAuthenticated,
    isAdminByRole,
    
    // 方法
    login,
    logout,
    getCurrentUser,
    refreshToken,
    checkAuth,
    updateUser,
    setToken,
    setUser,
    setRoles
  }
})