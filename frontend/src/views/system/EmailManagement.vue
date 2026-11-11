<template>
  <div class="email-management" v-loading="loading">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Message /></el-icon>
            招聘邮箱管理
          </h1>
          <p class="page-description">管理招聘邮箱配置，自动抓取简历邮件，支持IMAP/SMTP协议</p>
        </div>
        <div class="header-actions">
          <el-button @click="createNewEmailConfig" type="primary" size="large">
            <el-icon><Plus /></el-icon>
            新增邮箱
          </el-button>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧邮箱列表 -->
        <div class="email-list-panel">
          <el-card class="list-card">
            <template #header>
              <div class="list-header">
                <span class="list-title">
                  <el-icon><List /></el-icon>
                  邮箱配置 ({{ pagination.total }})
                </span>
                <div class="list-actions">
                  <el-input
                    v-model="searchKeyword"
                    placeholder="搜索邮箱地址..."
                    clearable
                    size="small"
                    style="width: 200px"
                    @input="handleSearch"
                  >
                    <template #prefix>
                      <el-icon><Search /></el-icon>
                    </template>
                  </el-input>
                </div>
              </div>
            </template>

            <!-- 邮箱列表内容 -->
            <div class="email-list-content">
              <div v-if="emailListLoading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>
              
              <div v-else-if="emailList.length === 0" class="empty-container">
                <el-empty description="暂无邮箱配置" :image-size="120">
                  <el-button type="primary" @click="createNewEmailConfig">
                    <el-icon><Plus /></el-icon>
                    创建第一个邮箱
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="email-items">
                <div
                  v-for="email in emailList"
                  :key="email.id"
                  :class="['email-item', { active: selectedEmail?.id === email.id }]"
                  @click="selectEmail(email)"
                >
                  <div class="email-item-header">
                    <div class="email-info">
                      <h4 class="email-name">{{ email.name }}</h4>
                      <p class="email-address">{{ email.email }}</p>
                    </div>
                    <div class="email-status">
                      <el-tag 
                        :type="getStatusType(email.status)" 
                        size="small"
                        :effect="email.status === 'active' ? 'light' : 'plain'"
                      >
                        {{ getStatusText(email.status) }}
                      </el-tag>
                      <el-tag 
                        :type="getConnectionType(email.connection_status)" 
                        size="small"
                        style="margin-left: 8px"
                      >
                        {{ getConnectionText(email.connection_status) }}
                      </el-tag>
                    </div>
                  </div>
                  
                  <div class="email-item-content">
                    <div class="email-config">
                      <span class="config-item">
                        <el-icon><Connection /></el-icon>
                        {{ email.imap_server }}:{{ email.imap_port }}
                      </span>
                      <span class="config-item">
                        <el-icon><Clock /></el-icon>
                        {{ email.fetch_interval }}分钟
                      </span>
                    </div>
                    <div class="email-stats">
                      <span class="stat-item">
                        <el-icon><Document /></el-icon>
                        最近抓取: {{ formatLastFetch(email.last_fetch_at) }}
                      </span>
                    </div>
                    <div class="email-time">
                      创建时间: {{ formatDate(email.created_at) }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分页 -->
              <div v-if="emailList.length > 0" class="pagination-container">
                <el-pagination
                  v-model:current-page="pagination.page"
                  v-model:page-size="pagination.size"
                  :total="pagination.total"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next"
                  small
                  @size-change="handleSizeChange"
                  @current-change="handlePageChange"
                />
              </div>
            </div>
          </el-card>
        </div>

        <!-- 右侧编辑区域 -->
        <div class="email-editor-panel">
          <!-- 欢迎页面 -->
          <div v-if="!selectedEmail && !isCreatingNew" class="welcome-container">
            <el-card class="welcome-card">
              <div class="welcome-content">
                <div class="welcome-icon">
                  <el-icon size="80"><Message /></el-icon>
                </div>
                <h2>欢迎使用邮箱管理</h2>
                <p>选择左侧的邮箱配置进行编辑，或创建新的邮箱配置</p>
                <div class="welcome-actions">
                  <el-button type="primary" @click="createNewEmailConfig" size="large">
                    <el-icon><Plus /></el-icon>
                    创建新邮箱
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>

          <!-- 邮箱编辑区域 -->
          <div v-else class="email-editor-content">
            <!-- 编辑器头部 -->
            <div class="editor-header">
              <div class="editor-title">
                <h3>{{ isCreatingNew ? '创建新邮箱' : `编辑邮箱: ${selectedEmail?.name}` }}</h3>
                <el-tag 
                  :type="getStatusType(selectedEmail?.status)" 
                  size="small"
                  v-if="!isCreatingNew"
                >
                  {{ getStatusText(selectedEmail?.status) }}
                </el-tag>
              </div>
              <div class="editor-actions">
                <el-button @click="testConnection" :loading="testingConnection" v-if="!isCreatingNew">
                  <el-icon><Connection /></el-icon>
                  测试连接
                </el-button>
                <el-button @click="resetEmailForm" :disabled="saving">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
                <el-button type="primary" @click="saveEmail" :loading="saving">
                  <el-icon><Check /></el-icon>
                  保存
                </el-button>
                <el-button v-if="!isCreatingNew" type="danger" @click="deleteEmail" :disabled="saving">
                  <el-icon><Warning /></el-icon>
                  删除
                </el-button>
              </div>
            </div>

            <!-- 编辑器主要内容 -->
            <div class="editor-main">
              <el-form
                ref="emailFormRef"
                :model="emailForm"
                :rules="emailRules"
                label-width="120px"
                label-position="top"
                class="email-form"
              >
                <el-card class="form-card">
                  <template #header>
                    <div class="card-header">
                      <el-icon><InfoFilled /></el-icon>
                      <span>邮箱配置</span>
                    </div>
                  </template>
                  <el-row :gutter="16">
                    <el-col :span="8">
                      <el-form-item label="配置名称" prop="name">
                        <el-input v-model="emailForm.name" placeholder="如：招聘邮箱" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="邮箱地址" prop="email">
                        <el-input v-model="emailForm.email" placeholder="hr@company.com" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="24">
                    <el-col :span="8">
                      <el-form-item label="IMAP服务器" prop="imap_server">
                        <el-input v-model="emailForm.imap_server" placeholder="imap.company.com" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="IMAP端口" prop="imap_port">
                        <el-input-number v-model="emailForm.imap_port" :min="1" :max="65535" controls-position="right" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="IMAP SSL" prop="imap_ssl">
                        <el-switch v-model="emailForm.imap_ssl" />
                      </el-form-item>
                    </el-col>

                  </el-row>
                  <el-row :gutter="24">
                    <el-col :span="8">
                      <el-form-item label="SMTP服务器" prop="smtp_server">
                        <el-input v-model="emailForm.smtp_server" placeholder="smtp.company.com" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="SMTP端口" prop="smtp_port">
                        <el-input-number v-model="emailForm.smtp_port" :min="1" :max="65535" controls-position="right" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="SMTP SSL" prop="smtp_ssl">
                        <el-switch v-model="emailForm.smtp_ssl" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="24">
                    <el-col :span="8">
                      <el-form-item label="邮箱密码" prop="password">
                        <el-input v-model="emailForm.password" type="password" placeholder="请输入邮箱密码" show-password />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="抓取间隔(分钟)" prop="fetch_interval">
                        <el-input-number v-model="emailForm.fetch_interval" :min="1" :max="1440" controls-position="right" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="6">
                      <el-form-item label="自动抓取" prop="auto_fetch">
                        <el-switch v-model="emailForm.auto_fetch" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="24">
                    <el-col :span="16">
                      <el-form-item label="邮件主题关键词" prop="subject_keywords">
                        <el-input v-model="emailForm.subject_keywords" type="text" placeholder="多个关键词用,隔开，如：简历,岗位,招聘" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="示例">
                        <el-text>简历,岗位,招聘,求职,职位,应聘</el-text>
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="16">
                    <el-col :span="12">
                      <el-form-item label="状态" prop="status">
                        <el-radio-group v-model="emailForm.status">
                          <el-radio label="active">启用</el-radio>
                          <el-radio label="inactive">禁用</el-radio>
                        </el-radio-group>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12" v-if="!isCreatingNew">
                      <el-form-item label="连接状态" prop="connection_status">
                        <el-tag :type="getConnectionType(emailForm.connection_status)">{{ getConnectionText(emailForm.connection_status) }}</el-tag>
                      </el-form-item>
                    </el-col>
                  </el-row>

                </el-card>
              </el-form>
            </div>

           
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Message,
  Plus,
  List,
  Search,
  Connection,
  Clock,
  Download,
  Upload,
  Key,
  Refresh,
  Check,
  InfoFilled,
  Document,
  MessageBox,
  Warning
} from '@element-plus/icons-vue'

// 导入API服务
import { emailConfigApi } from '@/api/admin'

// 响应式数据
const loading = ref(false)
const saving = ref(false)
const testingConnection = ref(false)
const logsLoading = ref(false)
const fetching = ref(false)

// 邮箱列表相关
const emailList = ref([])
const emailListLoading = ref(false)
const selectedEmail = ref(null)
const isCreatingNew = ref(false)
const searchKeyword = ref('')

// 日志相关
const logs = ref([])

// 分页数据
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 邮箱表单
const emailFormRef = ref()
const emailForm = reactive({
  name: '',
  email: '',
  imap_server: '',
  imap_port: 993,
  imap_ssl: true,
  smtp_server: '',
  smtp_port: 587,
  smtp_ssl: true,
  password: '',
  fetch_interval: 30,
  auto_fetch: false,
  status: 'active',
  connection_status: 'unknown'
})

// 表单验证规则
const emailRules = {
  name: [
    { required: true, message: '请输入配置名称', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  imap_server: [
    { required: true, message: '请输入IMAP服务器地址', trigger: 'blur' }
  ],
  imap_port: [
    { required: true, message: '请输入IMAP端口', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口范围1-65535', trigger: 'blur' }
  ],
  smtp_server: [
    { required: true, message: '请输入SMTP服务器地址', trigger: 'blur' }
  ],
  smtp_port: [
    { required: true, message: '请输入SMTP端口', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口范围1-65535', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入邮箱密码', trigger: 'blur' }
  ],
  fetch_interval: [
    { required: true, message: '请输入抓取间隔', trigger: 'blur' },
    { type: 'number', min: 1, max: 1440, message: '间隔范围1-1440分钟', trigger: 'blur' }
  ]
}

// 方法
const createNewEmailConfig = () => {
  isCreatingNew.value = true
  selectedEmail.value = null
  resetEmailForm()
}

const selectEmail = (email) => {
  selectedEmail.value = email
  isCreatingNew.value = false
  
  // 填充表单数据
  emailForm.name = email.name
  emailForm.email = email.email
  emailForm.imap_server = email.imap_server
  emailForm.imap_port = email.imap_port
  emailForm.imap_ssl = email.imap_ssl
  emailForm.smtp_server = email.smtp_server
  emailForm.smtp_port = email.smtp_port
  emailForm.smtp_ssl = email.smtp_ssl
  emailForm.password = '' // 密码不显示
  emailForm.fetch_interval = email.fetch_interval
  emailForm.auto_fetch = email.auto_fetch
  emailForm.status = email.status
  emailForm.subject_keywords = email.subject_keywords || ''
  emailForm.connection_status = email.connection_status
  
  // 加载日志
  fetchLogs()
}

const resetEmailForm = () => {
  emailForm.name = ''
  emailForm.email = ''
  emailForm.imap_server = ''
  emailForm.imap_port = 993
  emailForm.imap_ssl = true
  emailForm.smtp_server = ''
  emailForm.smtp_port = 587
  emailForm.smtp_ssl = true
  emailForm.password = ''
  emailForm.fetch_interval = 30
  emailForm.auto_fetch = false
  emailForm.status = 'active'
  emailForm.subject_keywords = ''
  emailForm.connection_status = 'unknown'
  
  if (emailFormRef.value) {
    emailFormRef.value.clearValidate()
  }
}

const saveEmail = async () => {
  try {
    await emailFormRef.value.validate()
    saving.value = true
    
  const emailData = {
    name: emailForm.name,
    email: emailForm.email,
    imap_server: emailForm.imap_server,
    imap_port: emailForm.imap_port,
    imap_ssl: emailForm.imap_ssl,
    smtp_server: emailForm.smtp_server,
    smtp_port: emailForm.smtp_port,
    smtp_ssl: emailForm.smtp_ssl,
    fetch_interval: emailForm.fetch_interval,
    auto_fetch: emailForm.auto_fetch,
    status: emailForm.status,
    subject_keywords: emailForm.subject_keywords
  }
    
    // 对于新建邮箱，密码是必填的；对于更新邮箱，只有当密码不为空时才更新
    if (isCreatingNew.value) {
      // 创建时必须包含密码
      emailData.password = emailForm.password
    } else {
      // 更新时，只有当密码不为空时才更新（避免覆盖现有密码）
      if (emailForm.password) {
        emailData.password = emailForm.password
      }
    }
    
    if (isCreatingNew.value) {
      // 调用创建邮箱配置API
      await emailConfigApi.createEmailConfig(emailData)
      ElMessage.success('邮箱配置创建成功')
    } else {
      // 调用更新邮箱配置API
      await emailConfigApi.updateEmailConfig(selectedEmail.value.id, emailData)
      ElMessage.success('邮箱配置更新成功')
    }
    
    await fetchEmailList()
  } catch (error) {
    console.error('保存邮箱配置失败:', error)
    ElMessage.error('保存邮箱配置失败，请重试')
  } finally {
    saving.value = false
  }
}

const testConnection = async () => {
  try {
    await emailFormRef.value.validate()
    testingConnection.value = true
    
    const testData = {
      imap_server: emailForm.imap_server,
      imap_port: emailForm.imap_port,
      imap_ssl: emailForm.imap_ssl,
      email: emailForm.email,
      password: emailForm.password
    }
    
    // 调用测试连接API
    const result = await emailConfigApi.testEmailConnection(selectedEmail.value.id, testData)
    if (result.success) {
      ElMessage.success('邮箱连接测试成功')
      emailForm.connection_status = 'connected'
    } else {
      ElMessage.error('邮箱连接测试失败: ' + result.message)
      emailForm.connection_status = 'error'
    }
    
  } catch (error) {
    console.error('测试连接失败:', error)
    ElMessage.error('测试连接失败')
  } finally {
    testingConnection.value = false
  }
}

const manualFetch = async () => {
  try {
    fetching.value = true
    
    // 调用手动抓取API
    await emailConfigApi.fetchEmails(selectedEmail.value.id)
    ElMessage.success('手动抓取简历成功')
    await fetchLogs()
    
  } catch (error) {
    console.error('手动抓取失败:', error)
    ElMessage.error('手动抓取失败')
  } finally {
    fetching.value = false
  }
}

const fetchLogs = async () => {
  try {
    logsLoading.value = true
    
    // 调用获取日志API
    const response = await emailConfigApi.getEmailFetchLogs(selectedEmail.value.id)
    logs.value = response.items || []
    
  } catch (error) {
    console.error('获取日志失败:', error)
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

const fetchEmailList = async () => {
  try {
    emailListLoading.value = true
    const params = {
      page: pagination.page,
      size: pagination.size
    }
    
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    
    // 调用获取邮箱列表API
    const response = await emailConfigApi.getEmailConfigList(params)
    if (Array.isArray(response)) {
      emailList.value = response
      pagination.total = response.length || 0
    } else {
      emailList.value = response.items || []
      pagination.total = response.total || (emailList.value.length || 0)
    }
    
  } catch (error) {
    console.error('获取邮箱列表失败:', error)
    ElMessage.error('获取邮箱列表失败')
  } finally {
    emailListLoading.value = false
  }
}

const deleteEmail = async () => {
  try {
    if (!selectedEmail.value?.id) {
      ElMessage.error('请选择要删除的邮箱配置')
      return
    }
    await ElMessageBox.confirm('确定要删除该邮箱配置吗？该操作不可恢复。', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await emailConfigApi.deleteEmailConfig(selectedEmail.value.id)
    ElMessage.success('删除成功')
    selectedEmail.value = null
    isCreatingNew.value = false
    resetEmailForm()
    await fetchEmailList()
  } catch (error) {
    if (error) {
      console.error('删除邮箱配置失败:', error)
      ElMessage.error('删除邮箱配置失败')
    }
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchEmailList()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchEmailList()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchEmailList()
}

const getStatusType = (status) => {
  const statusMap = {
    'active': 'success',
    'inactive': 'info',
    'error': 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    'active': '启用',
    'inactive': '禁用',
    'error': '错误'
  }
  return statusMap[status] || '未知'
}

const getConnectionType = (status) => {
  const statusMap = {
    'connected': 'success',
    'connecting': 'warning',
    'error': 'danger',
    'unknown': 'info'
  }
  return statusMap[status] || 'info'
}

const getConnectionText = (status) => {
  const statusMap = {
    'connected': '已连接',
    'connecting': '连接中',
    'error': '连接失败',
    'unknown': '未测试'
  }
  return statusMap[status] || '未知'
}

const getLogStatusType = (status) => {
  const statusMap = {
    'success': 'success',
    'failed': 'danger',
    'running': 'warning'
  }
  return statusMap[status] || 'info'
}

const getLogStatusText = (status) => {
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '进行中'
  }
  return statusMap[status] || '未知'
}

const formatDate = (dateString) => {
  if (!dateString) return '从未'
  const date = parseUtcDate(dateString)
  return date.toLocaleDateString('zh-CN')
}

const formatDateTime = (dateString) => {
  if (!dateString) return ''
  const date = parseUtcDate(dateString)
  return date.toLocaleString('zh-CN')
}

const parseUtcDate = (dateString) => {
  // 后端存储的是UTC时间，序列化时无时区标识（naive datetime）
  // JS会将无时区的ISO字符串当作本地时间解析，导致8小时偏差
  // 手动追加'Z'强制按UTC解析
  if (!dateString) return null
  // 如果已经有时区标识（Z 或 +/-HH:MM），直接解析
  if (/[+-]\d{2}:\d{2}$/.test(dateString) || dateString.endsWith('Z')) {
    return new Date(dateString)
  }
  return new Date(dateString + 'Z')
}

const formatLastFetch = (dateString) => {
  const date = parseUtcDate(dateString)
  if (!date) return '从未抓取'
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`
  return date.toLocaleDateString('zh-CN')
}

// 生命周期
onMounted(async () => {
  await fetchEmailList()
})
</script>

<style lang="scss" scoped>
.email-management {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  
  // 添加背景装饰
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: float 20s linear infinite;
    pointer-events: none;
  }
  
  .page-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
    max-width: 95%;
    margin: 0 auto;
    width: 100%;
    position: relative;
    z-index: 2;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 24px;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

    .header-left {
      .page-title {
        margin: 0 0 8px 0;
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 12px;
        
        .el-icon {
          font-size: 32px;
          color: #667eea;
        }
      }

      .page-description {
        margin: 0;
        color: #64748b;
        font-size: 16px;
      }
    }

    .header-actions {
      display: flex;
      gap: 12px;
      
      .el-button {
        border-radius: 12px;
        font-weight: 600;
        padding: 12px 24px;
        transition: all 0.3s ease;
        
        &.el-button--primary {
          background: linear-gradient(135deg, #667eea, #764ba2);
          border: none;
          color: white;
          
          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
          }
        }
      }
    }
  }

  .main-content {
    flex: 1;
    display: flex;
    gap: 20px;
    min-height: 0;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    position: relative;
    z-index: 1;
  }

  .email-list-panel {
    width: 400px;
    height: 600px;
    flex-shrink: 0;

    .list-card {
      height: 100%;
      display: flex;
      flex-direction: column;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #f8fafc, #e2e8f0);
        border-bottom: 1px solid rgba(226, 232, 240, 0.5);
        border-radius: 16px 16px 0 0;
      }

      :deep(.el-card__body) {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 0;
      }

      .list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #ebeef5;

        .list-title {
          font-weight: 600;
          color: #303133;
          display: flex;
          align-items: center;
          gap: 6px;
        }
      }

      .email-list-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 0;
        max-height: 500px;

        .loading-container,
        .empty-container {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .email-items {
          flex: 1;
          max-height: 500px;
          overflow-y: scroll;
          padding: 0;
          
          // 自定义滚动条样式
          &::-webkit-scrollbar {
            width: 8px;
          }
          
          &::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.1);
            border-radius: 4px;
          }
          
          &::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.6);
            border-radius: 4px;
            
            &:hover {
              background: rgba(102, 126, 234, 0.8);
            }
          }

          .email-item {
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            cursor: pointer;
            transition: all 0.3s;
            border-radius: 12px;
            margin: 0 16px 8px 16px;
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);

            &:hover {
              background: rgba(255, 255, 255, 0.9);
              box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
              transform: translateY(-2px);
              border-color: #667eea;
            }

            &.active {
              background: rgba(102, 126, 234, 0.1);
              border-left: 3px solid #667eea;
              box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
            }

            .email-item-header {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              margin-bottom: 12px;

              .email-info {
                .email-name {
                  margin: 0 0 4px 0;
                  font-size: 16px;
                  font-weight: 600;
                  color: #303133;
                  line-height: 1.4;
                }

                .email-address {
                  margin: 0;
                  font-size: 12px;
                  color: #909399;
                }
              }

              .email-status {
                display: flex;
                align-items: center;
                gap: 4px;
              }
            }
            
            .email-item-content {
              .email-config {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-bottom: 8px;

                .config-item {
                  display: flex;
                  align-items: center;
                  gap: 4px;
                  font-size: 12px;
                  color: #606266;
                }
              }

              .email-stats {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;

                .stat-item {
                  display: flex;
                  align-items: center;
                  gap: 4px;
                  font-size: 12px;
                  color: #606266;
                }
              }

              .email-time {
                font-size: 12px;
                color: #909399;
              }
            }
          }
        }

        .pagination-container {
          margin-top: 16px;
          display: flex;
          justify-content: center;
        }
      }
    }
  }

  .email-editor-panel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;

    .welcome-container {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;

      .welcome-card {
        width: 100%;
        max-width: 500px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

        .welcome-content {
          text-align: center;
          padding: 40px 20px;

          .welcome-icon {
            margin-bottom: 24px;
            color: #409eff;
          }

          h2 {
            margin: 0 0 16px 0;
            color: #303133;
            font-size: 24px;
          }

          p {
            margin: 0 0 32px 0;
            color: #606266;
            font-size: 16px;
          }

          .welcome-actions {
            display: flex;
            justify-content: center;
            gap: 16px;
          }
        }
      }
    }

    .email-editor-content {
      height: 100%;
      display: flex;
      flex-direction: column;

      .editor-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 20px 24px;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

        .editor-title {
          display: flex;
          align-items: center;
          gap: 12px;

          h3 {
            margin: 0;
            color: #303133;
            font-size: 18px;
            font-weight: 600;
          }
        }

        .editor-actions {
          display: flex;
          gap: 12px;

          .el-button {
            border-radius: 12px;
            font-weight: 600;
            padding: 12px 24px;
            transition: all 0.3s ease;

            &.el-button--primary {
              background: linear-gradient(135deg, #667eea, #764ba2);
              border: none;
              color: white;

              &:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
              }
            }

            &:not(.el-button--primary) {
              background: rgba(255, 255, 255, 0.8);
              border: 1px solid rgba(226, 232, 240, 0.8);
              color: #64748b;

              &:hover {
                background: rgba(248, 250, 252, 0.9);
                border-color: rgba(102, 126, 234, 0.3);
                color: #667eea;
                transform: translateY(-2px);
              }
            }
          }
        }
      }

      .editor-main {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding-right: 8px;

        .email-form {
          .form-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;

            :deep(.el-card__header) {
              background: linear-gradient(135deg, #f8fafc, #e2e8f0);
              border-bottom: 1px solid rgba(226, 232, 240, 0.5);
              border-radius: 16px 16px 0 0;
            }

            :deep(.el-card__body) {
              padding: 20px;
            }

            .card-header {
              display: flex;
              align-items: center;
              gap: 8px;
              font-weight: 600;
              color: #303133;
            }
          }
        }
      }

      .logs-section {
        margin-top: 20px;

        .logs-card {
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

          :deep(.el-card__header) {
            background: linear-gradient(135deg, #f8fafc, #e2e8f0);
            border-bottom: 1px solid rgba(226, 232, 240, 0.5);
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }

          :deep(.el-card__body) {
            padding: 20px;
          }

          .card-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: #303133;

            .logs-actions {
              display: flex;
              gap: 8px;
            }
          }

          .logs-content {
            .empty-logs {
              text-align: center;
              padding: 40px 0;
            }

            .logs-list {
              .log-item {
                padding: 16px;
                border: 1px solid #e4e7ed;
                border-radius: 8px;
                margin-bottom: 12px;
                background: #fafafa;

                &.success {
                  border-color: #67c23a;
                  background: #f0f9ff;
                }

                &.failed {
                  border-color: #f56c6c;
                  background: #fef0f0;
                }

                &.running {
                  border-color: #e6a23c;
                  background: #fdf6ec;
                }

                .log-header {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  margin-bottom: 8px;

                  .log-time {
                    font-size: 12px;
                    color: #909399;
                  }
                }

                .log-stats {
                  display: flex;
                  gap: 16px;
                  margin-bottom: 8px;

                  .stat {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 14px;
                    color: #606266;
                  }
                }

                .log-error {
                  display: flex;
                  align-items: center;
                  gap: 4px;
                  font-size: 12px;
                  color: #f56c6c;
                  margin-top: 8px;
                }
              }
            }
          }
        }
      }
    }
  }
}

// 背景动画
@keyframes float {
  0% {
    transform: translate(0, 0) rotate(0deg);
  }
  33% {
    transform: translate(30px, -30px) rotate(120deg);
  }
  66% {
    transform: translate(-20px, 20px) rotate(240deg);
  }
  100% {
    transform: translate(0, 0) rotate(360deg);
  }
}

// 响应式设计
@media (max-width: 1400px) {
  .email-management {
    .main-content {
      .email-list-panel {
        width: 320px;
      }
    }
  }
}

@media (max-width: 1200px) {
  .email-management {
    .main-content {
      flex-direction: column;

      .email-list-panel {
        width: 100%;
        height: 300px;
      }
    }
  }
}
</style>
