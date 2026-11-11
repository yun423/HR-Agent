<template>
  <div class="profile">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">
            <el-icon><User /></el-icon>
            个人中心
          </h1>
          <p class="page-subtitle">
            管理您的个人信息和系统设置
          </p>
        </div>
      </div>

      <div class="profile-layout">
        <!-- 左侧个人信息卡片 -->
        <div class="profile-sidebar">
          <el-card class="profile-card">
            <div class="profile-header">
              <div class="avatar-section">
                <el-avatar :size="80" :src="userInfo.avatar">
                  <el-icon><User /></el-icon>
                </el-avatar>
                <el-button size="small" text @click="changeAvatar">
                  <el-icon><Camera /></el-icon>
                  更换头像
                </el-button>
              </div>
              
              <div class="user-info">
                <h3>{{ userInfo.name }}</h3>
                <p class="user-title">{{ userInfo.title }}</p>
                <p class="user-department">{{ userInfo.department }}</p>
              </div>
            </div>
            
            <div class="profile-stats">
              <div class="stat-item">
                <div class="stat-number">{{ userStats.loginDays }}</div>
                <div class="stat-label">连续登录</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ userStats.totalQuestions }}</div>
                <div class="stat-label">提问次数</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ userStats.documentsUploaded }}</div>
                <div class="stat-label">上传文档</div>
              </div>
            </div>
            
            <div class="quick-actions">
              <el-button type="primary" @click="activeTab = 'basic'">
                <el-icon><Edit /></el-icon>
                编辑资料
              </el-button>
              <el-button @click="activeTab = 'security'">
                <el-icon><Lock /></el-icon>
                安全设置
              </el-button>
            </div>
          </el-card>
          
          <!-- 最近活动 -->
          <el-card class="activity-card">
            <template #header>
              <div class="card-header">
                <el-icon><Clock /></el-icon>
                <span>最近活动</span>
              </div>
            </template>
            
            <div class="activity-list">
              <div 
                v-for="activity in recentActivities"
                :key="activity.id"
                class="activity-item"
              >
                <div class="activity-icon">
                  <el-icon>
                    <component :is="activity.icon" />
                  </el-icon>
                </div>
                <div class="activity-content">
                  <div class="activity-title">{{ activity.title }}</div>
                  <div class="activity-time">{{ formatTime(activity.time) }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 右侧详细设置 -->
        <div class="profile-main">
          <el-card class="settings-card">
            <el-tabs v-model="activeTab" @tab-change="handleTabChange">
              <!-- 基本信息 -->
              <el-tab-pane label="基本信息" name="basic">
                <el-form 
                  ref="basicFormRef"
                  :model="basicForm" 
                  :rules="basicRules"
                  label-width="120px"
                  class="profile-form"
                >
                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item label="姓名" prop="name">
                        <el-input v-model="basicForm.name" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="工号" prop="employeeId">
                        <el-input v-model="basicForm.employeeId" disabled />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item label="邮箱" prop="email">
                        <el-input v-model="basicForm.email" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="手机号" prop="phone">
                        <el-input v-model="basicForm.phone" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item label="部门" prop="department">
                        <el-select v-model="basicForm.department" style="width: 100%">
                          <el-option label="人力资源部" value="hr" />
                          <el-option label="技术部" value="tech" />
                          <el-option label="市场部" value="marketing" />
                          <el-option label="财务部" value="finance" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="职位" prop="title">
                        <el-input v-model="basicForm.title" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item label="入职日期" prop="joinDate">
                        <el-date-picker
                          v-model="basicForm.joinDate"
                          type="date"
                          placeholder="选择日期"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="生日" prop="birthday">
                        <el-date-picker
                          v-model="basicForm.birthday"
                          type="date"
                          placeholder="选择日期"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-form-item label="个人简介">
                    <el-input
                      v-model="basicForm.bio"
                      type="textarea"
                      :rows="4"
                      placeholder="请输入个人简介"
                    />
                  </el-form-item>
                  
                  <el-form-item>
                    <el-button type="primary" @click="saveBasicInfo" :loading="saving">
                      保存修改
                    </el-button>
                    <el-button @click="resetBasicForm">重置</el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>

              <!-- 安全设置 -->
              <el-tab-pane label="安全设置" name="security">
                <div class="security-section">
                  <!-- 修改密码 -->
                  <el-card class="security-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Lock /></el-icon>
                        <span>修改密码</span>
                      </div>
                    </template>
                    
                    <el-form 
                      ref="passwordFormRef"
                      :model="passwordForm" 
                      :rules="passwordRules"
                      label-width="120px"
                    >
                      <el-form-item label="当前密码" prop="currentPassword">
                        <el-input 
                          v-model="passwordForm.currentPassword" 
                          type="password" 
                          show-password
                          placeholder="请输入当前密码"
                        />
                      </el-form-item>
                      
                      <el-form-item label="新密码" prop="newPassword">
                        <el-input 
                          v-model="passwordForm.newPassword" 
                          type="password" 
                          show-password
                          placeholder="请输入新密码"
                        />
                      </el-form-item>
                      
                      <el-form-item label="确认密码" prop="confirmPassword">
                        <el-input 
                          v-model="passwordForm.confirmPassword" 
                          type="password" 
                          show-password
                          placeholder="请再次输入新密码"
                        />
                      </el-form-item>
                      
                      <el-form-item>
                        <el-button type="primary" @click="changePassword" :loading="changingPassword">
                          修改密码
                        </el-button>
                      </el-form-item>
                    </el-form>
                  </el-card>
                  
                  <!-- 登录记录 -->
                  <el-card class="security-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Monitor /></el-icon>
                        <span>登录记录</span>
                      </div>
                    </template>
                    
                    <el-table :data="loginRecords" style="width: 100%">
                      <el-table-column prop="time" label="登录时间" width="180">
                        <template #default="{ row }">
                          {{ formatDateTime(row.time) }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="ip" label="IP地址" width="150" />
                      <el-table-column prop="location" label="登录地点" width="200" />
                      <el-table-column prop="device" label="设备信息" />
                      <el-table-column prop="status" label="状态" width="100">
                        <template #default="{ row }">
                          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                            {{ row.status === 'success' ? '成功' : '失败' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </div>
              </el-tab-pane>

              <!-- 系统设置 -->
              <el-tab-pane label="系统设置" name="system">
                <div class="system-section">
                  <el-card class="system-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Setting /></el-icon>
                        <span>界面设置</span>
                      </div>
                    </template>
                    
                    <div class="setting-group">
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>主题模式</span>
                          <p>选择您喜欢的界面主题</p>
                        </div>
                        <el-radio-group v-model="systemSettings.theme">
                          <el-radio label="light">浅色</el-radio>
                          <el-radio label="dark">深色</el-radio>
                          <el-radio label="auto">跟随系统</el-radio>
                        </el-radio-group>
                      </div>
                      
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>语言设置</span>
                          <p>选择系统显示语言</p>
                        </div>
                        <el-select v-model="systemSettings.language" style="width: 200px">
                          <el-option label="简体中文" value="zh-CN" />
                          <el-option label="English" value="en-US" />
                        </el-select>
                      </div>
                      
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>侧边栏折叠</span>
                          <p>默认折叠侧边栏导航</p>
                        </div>
                        <el-switch v-model="systemSettings.sidebarCollapsed" />
                      </div>
                    </div>
                  </el-card>
                  
                  <el-card class="system-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Bell /></el-icon>
                        <span>通知设置</span>
                      </div>
                    </template>
                    
                    <div class="setting-group">
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>邮件通知</span>
                          <p>接收系统邮件通知</p>
                        </div>
                        <el-switch v-model="systemSettings.emailNotification" />
                      </div>
                      
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>浏览器通知</span>
                          <p>接收浏览器推送通知</p>
                        </div>
                        <el-switch v-model="systemSettings.browserNotification" />
                      </div>
                      
                      <div class="setting-item">
                        <div class="setting-label">
                          <span>声音提醒</span>
                          <p>新消息声音提醒</p>
                        </div>
                        <el-switch v-model="systemSettings.soundNotification" />
                      </div>
                    </div>
                  </el-card>
                  
                  <div class="setting-actions">
                    <el-button type="primary" @click="saveSystemSettings" :loading="savingSettings">
                      保存设置
                    </el-button>
                    <el-button @click="resetSystemSettings">恢复默认</el-button>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 响应式数据
const activeTab = ref('basic')
const saving = ref(false)
const changingPassword = ref(false)
const savingSettings = ref(false)

// 表单引用
const basicFormRef = ref()
const passwordFormRef = ref()

// 用户信息
const userInfo = reactive({
  name: '张三',
  title: 'HR专员',
  department: '人力资源部',
  avatar: ''
})

// 用户统计
const userStats = reactive({
  loginDays: 15,
  totalQuestions: 128,
  documentsUploaded: 23
})

// 基本信息表单
const basicForm = reactive({
  name: '张三',
  employeeId: 'HR001',
  email: 'zhangsan@company.com',
  phone: '13800138000',
  department: 'hr',
  title: 'HR专员',
  joinDate: new Date('2023-01-15'),
  birthday: new Date('1990-05-20'),
  bio: '负责公司人力资源管理工作，包括招聘、培训、绩效管理等。'
})

// 基本信息验证规则
const basicRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

// 密码表单
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 密码验证规则
const passwordRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 系统设置
const systemSettings = reactive({
  theme: 'light',
  language: 'zh-CN',
  sidebarCollapsed: false,
  emailNotification: true,
  browserNotification: true,
  soundNotification: false
})

// 最近活动
const recentActivities = ref([
  {
    id: 1,
    title: '登录系统',
    icon: 'User',
    time: new Date(Date.now() - 1000 * 60 * 30)
  },
  {
    id: 2,
    title: '生成JD文档',
    icon: 'Document',
    time: new Date(Date.now() - 1000 * 60 * 60 * 2)
  },
  {
    id: 3,
    title: '上传培训资料',
    icon: 'Upload',
    time: new Date(Date.now() - 1000 * 60 * 60 * 4)
  },
  {
    id: 4,
    title: '智能问答',
    icon: 'ChatDotRound',
    time: new Date(Date.now() - 1000 * 60 * 60 * 6)
  }
])

// 登录记录
const loginRecords = ref([
  {
    time: new Date(Date.now() - 1000 * 60 * 30),
    ip: '192.168.1.100',
    location: '北京市朝阳区',
    device: 'Chrome 120.0 / Windows 10',
    status: 'success'
  },
  {
    time: new Date(Date.now() - 1000 * 60 * 60 * 24),
    ip: '192.168.1.100',
    location: '北京市朝阳区',
    device: 'Chrome 120.0 / Windows 10',
    status: 'success'
  },
  {
    time: new Date(Date.now() - 1000 * 60 * 60 * 48),
    ip: '192.168.1.101',
    location: '北京市海淀区',
    device: 'Safari 17.0 / macOS',
    status: 'success'
  }
])

// 方法
const handleTabChange = (tabName) => {
  // 切换标签页时的逻辑
}

const changeAvatar = () => {
  ElMessage.info('头像上传功能开发中')
}

const saveBasicInfo = async () => {
  try {
    await basicFormRef.value.validate()
    
    saving.value = true
    
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 更新用户信息
    Object.assign(userInfo, {
      name: basicForm.name,
      title: basicForm.title,
      department: getDepartmentLabel(basicForm.department)
    })
    
    ElMessage.success('个人信息保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

const resetBasicForm = () => {
  basicFormRef.value?.resetFields()
}

const changePassword = async () => {
  try {
    await passwordFormRef.value.validate()
    
    changingPassword.value = true
    
    // 模拟修改密码
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 重置表单
    passwordFormRef.value.resetFields()
    Object.assign(passwordForm, {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
    
    ElMessage.success('密码修改成功')
  } catch (error) {
    console.error('修改密码失败:', error)
  } finally {
    changingPassword.value = false
  }
}

const saveSystemSettings = async () => {
  savingSettings.value = true
  
  try {
    // 模拟保存设置
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('系统设置保存成功')
  } catch (error) {
    ElMessage.error('保存设置失败')
  } finally {
    savingSettings.value = false
  }
}

const resetSystemSettings = () => {
  Object.assign(systemSettings, {
    theme: 'light',
    language: 'zh-CN',
    sidebarCollapsed: false,
    emailNotification: true,
    browserNotification: true,
    soundNotification: false
  })
  ElMessage.success('已恢复默认设置')
}

const getDepartmentLabel = (department) => {
  const labels = {
    hr: '人力资源部',
    tech: '技术部',
    marketing: '市场部',
    finance: '财务部'
  }
  return labels[department] || department
}

const formatTime = (time) => {
  const now = new Date()
  const diff = now - time
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  
  return time.toLocaleDateString('zh-CN')
}

const formatDateTime = (time) => {
  return time.toLocaleString('zh-CN')
}

onMounted(() => {
  // 初始化数据
})
</script>

<style lang="scss" scoped>
.profile {
  height: 100%;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
  
  .header-content {
    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 8px 0;
    }
    
    .page-subtitle {
      color: var(--text-secondary);
      margin: 0;
    }
  }
}

.profile-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  height: calc(100vh - 200px);
}

.profile-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  
  .profile-card {
    .profile-header {
      text-align: center;
      margin-bottom: 24px;
      
      .avatar-section {
        margin-bottom: 16px;
        
        .el-avatar {
          margin-bottom: 8px;
        }
      }
      
      .user-info {
        h3 {
          margin: 0 0 4px 0;
          color: var(--text-primary);
          font-size: 18px;
        }
        
        .user-title {
          margin: 0 0 2px 0;
          color: var(--primary);
          font-weight: 500;
        }
        
        .user-department {
          margin: 0;
          color: var(--text-secondary);
          font-size: 14px;
        }
      }
    }
    
    .profile-stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 24px;
      padding: 16px 0;
      border-top: 1px solid var(--border-lighter);
      border-bottom: 1px solid var(--border-lighter);
      
      .stat-item {
        text-align: center;
        
        .stat-number {
          font-size: 20px;
          font-weight: 600;
          color: var(--primary);
          line-height: 1;
        }
        
        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
          margin-top: 4px;
        }
      }
    }
    
    .quick-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
  }
  
  .activity-card {
    flex: 1;
    
    :deep(.el-card__body) {
      height: calc(100% - 60px);
      overflow-y: auto;
    }
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
    
    .activity-list {
      .activity-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid var(--border-lighter);
        
        &:last-child {
          border-bottom: none;
        }
        
        .activity-icon {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: var(--primary-light);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--primary);
          flex-shrink: 0;
        }
        
        .activity-content {
          flex: 1;
          
          .activity-title {
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 2px;
          }
          
          .activity-time {
            font-size: 12px;
            color: var(--text-secondary);
          }
        }
      }
    }
  }
}

.profile-main {
  .settings-card {
    height: 100%;
    
    :deep(.el-card__body) {
      height: calc(100% - 60px);
      overflow-y: auto;
    }
    
    :deep(.el-tabs__content) {
      height: calc(100% - 60px);
      overflow-y: auto;
    }
  }
}

.profile-form {
  max-width: 800px;
}

.security-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  
  .security-card {
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
}

.system-section {
  .system-card {
    margin-bottom: 24px;
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
    
    .setting-group {
      .setting-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 0;
        border-bottom: 1px solid var(--border-lighter);
        
        &:last-child {
          border-bottom: none;
        }
        
        .setting-label {
          flex: 1;
          
          span {
            font-weight: 500;
            color: var(--text-primary);
            display: block;
            margin-bottom: 4px;
          }
          
          p {
            margin: 0;
            font-size: 14px;
            color: var(--text-secondary);
          }
        }
      }
    }
  }
  
  .setting-actions {
    display: flex;
    gap: 12px;
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .profile-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .profile-sidebar {
    order: 2;
    flex-direction: row;
    
    .activity-card {
      flex: 1;
      
      :deep(.el-card__body) {
        height: 300px;
      }
    }
  }
  
  .profile-main {
    order: 1;
    
    .settings-card {
      height: auto;
      
      :deep(.el-card__body) {
        height: auto;
      }
      
      :deep(.el-tabs__content) {
        height: auto;
      }
    }
  }
}

@media (max-width: 768px) {
  .profile-layout {
    gap: 16px;
  }
  
  .profile-sidebar {
    flex-direction: column;
  }
  
  .profile-stats {
    .stat-item {
      .stat-number {
        font-size: 16px;
      }
      
      .stat-label {
        font-size: 11px;
      }
    }
  }
  
  .system-section .system-card .setting-group .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>