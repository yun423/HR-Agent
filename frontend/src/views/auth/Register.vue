<template>
  <div class="register-container">
    <div class="register-background">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>

    <div class="register-content">
      <div class="register-card">
        <div class="register-header">
          <div class="logo">
            <el-icon class="logo-icon"><TrendCharts /></el-icon>
            <h1 class="logo-text">HR Agent</h1>
          </div>
          <p class="subtitle">创建您的账户</p>
        </div>

        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="register-form"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              size="large"
              :prefix-icon="Message"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少6位）"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请确认密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="register-btn"
              :loading="loading"
              @click="handleRegister"
            >
              {{ loading ? '注册中...' : '注册' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="register-footer">
          <p class="login-link">
            已有账户？
            <el-link type="primary" :underline="false" @click="goToLogin">
              立即登录
            </el-link>
          </p>
        </div>
      </div>

      <div class="feature-showcase">
        <h2 class="showcase-title">智能化HR管理</h2>
        <div class="feature-list">
          <div class="feature-item">
            <el-icon class="feature-icon"><UserFilled /></el-icon>
            <div class="feature-content">
              <h3>智能招聘</h3>
              <p>AI驱动的JD生成、简历筛选和智能面试</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Reading /></el-icon>
            <div class="feature-content">
              <h3>智能培训</h3>
              <p>基于知识库的自动试卷生成和智能阅卷</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><ChatDotRound /></el-icon>
            <div class="feature-content">
              <h3>智能助理</h3>
              <p>知识库检索和智能问答助手</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, UserFilled, Reading, ChatDotRound, TrendCharts } from '@element-plus/icons-vue'

const router = useRouter()

// 响应式数据
const registerFormRef = ref()
const loading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码长度在 6 到 100 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return

  try {
    const valid = await registerFormRef.value.validate()
    if (!valid) return

    loading.value = true

    const result = await authApi.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })

    ElMessage.success('注册成功！请登录')
    router.push('/login')
  } catch (error) {
    console.error('注册失败:', error)
    ElMessage.error(error.response?.data?.detail || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 跳转到登录页
const goToLogin = () => {
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}

.register-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;

  .bg-shape {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    animation: float 6s ease-in-out infinite;

    &.shape-1 {
      width: 200px;
      height: 200px;
      top: 10%;
      left: 10%;
      animation-delay: 0s;
    }

    &.shape-2 {
      width: 150px;
      height: 150px;
      top: 60%;
      right: 10%;
      animation-delay: 2s;
    }

    &.shape-3 {
      width: 100px;
      height: 100px;
      bottom: 20%;
      left: 20%;
      animation-delay: 4s;
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
}

.register-content {
  display: flex;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 40px;
  gap: 80px;
  position: relative;
  z-index: 1;
}

.register-card {
  flex: 0 0 400px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.register-header {
  text-align: center;
  margin-bottom: 32px;

  .logo {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;

    .logo-icon {
      font-size: 32px;
      color: var(--primary-color);
      margin-right: 12px;
    }

    .logo-text {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0;
    }
  }

  .subtitle {
    color: var(--text-secondary);
    font-size: 16px;
    margin: 0;
  }
}

.register-form {
  .el-form-item {
    margin-bottom: 24px;

    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
  }

  .register-btn {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
    border: none;

    &:hover {
      background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
    }
  }
}

.register-footer {
  margin-top: 24px;
  text-align: center;

  .login-link {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-secondary);
    font-size: 14px;
    margin: 0;
  }
}

.feature-showcase {
  flex: 1;
  color: white;

  .showcase-title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 40px;
    text-align: center;
  }

  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .feature-item {
    display: flex;
    align-items: flex-start;
    gap: 20px;
    padding: 24px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: transform 0.3s ease;

    &:hover {
      transform: translateY(-4px);
    }

    .feature-icon {
      font-size: 32px;
      color: #409eff;
      flex-shrink: 0;
    }

    .feature-content {
      h3 {
        font-size: 20px;
        font-weight: 600;
        margin: 0 0 8px 0;
      }

      p {
        font-size: 14px;
        opacity: 0.9;
        margin: 0;
        line-height: 1.6;
      }
    }
  }
}

// 响应式设计
@media (max-width: 1024px) {
  .register-content {
    flex-direction: column;
    gap: 40px;
    padding: 20px;
  }

  .register-card {
    flex: none;
    max-width: 400px;
    margin: 0 auto;
  }

  .feature-showcase {
    .showcase-title {
      font-size: 28px;
    }

    .feature-list {
      flex-direction: row;
      flex-wrap: wrap;
      gap: 20px;
    }

    .feature-item {
      flex: 1;
      min-width: 250px;
    }
  }
}

@media (max-width: 768px) {
  .register-content {
    padding: 16px;
  }

  .register-card {
    padding: 24px;
  }

  .feature-showcase {
    .feature-list {
      flex-direction: column;
    }

    .feature-item {
      min-width: auto;
    }
  }
}
</style>