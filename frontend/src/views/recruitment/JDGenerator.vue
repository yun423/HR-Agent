<template>
  <div class="jd-generator" v-loading="parsingIntent" element-loading-text="正在解析需求为表单数据..." element-loading-background="rgba(255, 255, 255, 0.7)">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Document /></el-icon>
            智能JD管理
          </h1>
          <p class="page-description">创建和管理职位描述，使用AI智能生成专业的JD内容</p>
        </div>
        <div class="header-actions">
          <el-button @click="createNewJD" type="primary" size="large">
            <el-icon><Plus /></el-icon>
            新建JD
          </el-button>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧JD列表 -->
        <div class="jd-list-panel">
          <el-card class="list-card">
            <template #header>
              <div class="list-header">
                <span class="list-title">
                  <el-icon><List /></el-icon>
                  JD列表 ({{ pagination.total }})
                </span>
                <div class="list-actions">
                  <el-input
                    v-model="searchKeyword"
                    placeholder="搜索职位..."
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

            <!-- JD列表内容 -->
            <div class="jd-list-content">
              <div v-if="jdListLoading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>
              
              <div v-else-if="jdList.length === 0" class="empty-container">
                <el-empty description="暂无JD数据" :image-size="120">
                  <el-button type="primary" @click="createNewJD">
                    <el-icon><Plus /></el-icon>
                    创建第一个JD
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="jd-items">
                <div
                  v-for="jd in jdList"
                  :key="jd.id"
                  :class="['jd-item', { active: selectedJD?.id === jd.id }]"
                  @click="selectJD(jd)"
                >
                  <div class="jd-item-header">
                    <h4 class="jd-title">{{ jd.title || '未命名职位' }}</h4>
                    <div class="jd-actions">
                      <el-dropdown trigger="click" @command="handleJDAction">
                        <el-button text size="small">
                          <el-icon><MoreFilled /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item :command="{ action: 'edit', jd }">
                              <el-icon><Edit /></el-icon>
                              编辑
                            </el-dropdown-item>
                            <el-dropdown-item :command="{ action: 'duplicate', jd }">
                              <el-icon><CopyDocument /></el-icon>
                              复制
                            </el-dropdown-item>
                            <el-dropdown-item :command="{ action: 'download', jd }">
                              <el-icon><Download /></el-icon>
                              下载
                            </el-dropdown-item>
                            <el-dropdown-item :command="{ action: 'delete', jd }" divided>
                              <el-icon><Delete /></el-icon>
                              删除
                            </el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                  </div>
                  
                  <div class="jd-item-content">
                    <div class="jd-meta">
                      <span class="meta-item">
                        <el-icon><Location /></el-icon>
                        {{ (jd.meta_data && jd.meta_data.location) || jd.location || '未设置' }}
                      </span>
                      <span class="meta-item">
                        <el-icon><Money /></el-icon>
                        {{ (jd.meta_data && jd.meta_data.salary) || jd.salary_range || '面议' }}
                      </span>
                    </div>

                    <div class="jd-time">
                      {{ formatDate(jd.updated_at) }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分页 -->
              <div v-if="jdList.length > 0" class="pagination-container">
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
        <div class="jd-editor-panel">
          <!-- 欢迎页面 -->
          <div v-if="!selectedJD && !isCreatingNew" class="welcome-container">
            <el-card class="welcome-card">
              <div class="welcome-content">
                <div class="welcome-icon">
                  <el-icon size="80"><Document /></el-icon>
                </div>
                <h2>欢迎使用智能JD管理</h2>
                <p>选择左侧的JD进行编辑，或创建新的职位描述</p>
                <div class="welcome-actions">
                  <el-button type="primary" @click="createNewJD" size="large">
                    <el-icon><Plus /></el-icon>
                    创建新JD
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>

          <!-- JD编辑/生成区域 -->
          <div v-else class="jd-editor-content">
            <!-- 编辑器头部 -->
            <div class="editor-header">
              <div class="editor-title">
                <h3>{{ isCreatingNew ? '创建新JD' : `编辑: ${selectedJD?.title}` }}</h3>
                <el-tag v-if="!isCreatingNew" :type="getStatusType(selectedJD?.status)" size="small">
                  {{ getStatusText(selectedJD?.status) }}
                </el-tag>
              </div>
              <div class="editor-actions">
                <el-button @click="resetForm" :disabled="generating">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
                <el-button @click="saveJD" :loading="saving" :disabled="generating">
                  <el-icon><Check /></el-icon>
                  保存
                </el-button>
                <el-button type="primary" @click="generateJD" :loading="generating">
                  <el-icon><Star /></el-icon>
                  {{ generating ? '生成中...' : 'AI生成' }}
                </el-button>
              </div>
            </div>

            <!-- 编辑器主要内容 -->
            <div class="editor-main">
              <!-- 左侧配置面板 -->
              <div class="config-panel">
                <el-card class="config-card">
                  <template #header>
                    <div class="card-header">
                      <el-icon><Setting /></el-icon>
                      <span>职位配置</span>
                    </div>
                  </template>

                  <el-form
                    ref="formRef"
                    :model="form"
                    :rules="rules"
                    label-width="100px"
                    label-position="top"
                    class="jd-form"
                  >
                    <div class="form-section">
                      <h4 class="section-title">基本信息</h4>
                      <el-row :gutter="16">
                        <el-col :span="12">
                          <el-form-item label="职位名称" prop="jobTitle">
                      <el-input v-model="form.jobTitle" placeholder="如：高级前端工程师" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="12">
                          <el-form-item label="工作地点" prop="location">
                            <el-select v-model="form.location" placeholder="选择工作地点" style="width: 100%">
                              <el-option
                                v-for="city in cities"
                                :key="city"
                                :label="city"
                                :value="city"
                              />
                            </el-select>
                          </el-form-item>
                        </el-col>
                      </el-row>

                      <el-row :gutter="16">
                        <el-col :span="12">
                          <el-form-item label="薪资范围" prop="salary">
                <el-input v-model="form.salary" placeholder="如：15K-25K" clearable />
                          </el-form-item>
                        </el-col>
                        <el-col :span="12">
                          <el-form-item label="工作经验" prop="experience">
                            <el-select v-model="form.experience" placeholder="选择工作经验" style="width: 100%">
                              <el-option label="不限" value="不限" />
                              <el-option label="1年以下" value="1年以下" />
                              <el-option label="1-3年" value="1-3年" />
                              <el-option label="3-5年" value="3-5年" />
                              <el-option label="5-10年" value="5-10年" />
                              <el-option label="10年以上" value="10年以上" />
                            </el-select>
                          </el-form-item>
                        </el-col>
                      </el-row>

                      <el-row :gutter="16">
                        <el-col :span="12">
                          <el-form-item label="学历要求" prop="education">
                            <el-select v-model="form.education" placeholder="选择学历要求" style="width: 100%">
                              <el-option label="不限" value="不限" />
                              <el-option label="大专" value="大专" />
                              <el-option label="本科" value="本科" />
                              <el-option label="硕士" value="硕士" />
                              <el-option label="博士" value="博士" />
                            </el-select>
                          </el-form-item>
                        </el-col>
                        <el-col :span="12">
                          <el-form-item label="工作性质" prop="jobType">
                <el-select v-model="form.jobType" placeholder="选择工作性质" style="width: 100%">
                              <el-option label="全职" value="全职" />
                              <el-option label="兼职" value="兼职" />
                              <el-option label="实习" value="实习" />
                              <el-option label="远程" value="远程" />
                            </el-select>
                          </el-form-item>
                        </el-col>
                      </el-row>
                    </div>

                    <div class="form-section">
                      <h4 class="section-title">技能要求</h4>
                      <el-form-item label="技能标签" prop="skills">
                        <el-select
                          v-model="form.skills"
                          multiple
                          filterable
                          allow-create
                          placeholder="选择或输入技能标签"
                          style="width: 100%"
                        >
                          <el-option
                            v-for="skill in skillOptions"
                            :key="skill"
                            :label="skill"
                            :value="skill"
                          />
                        </el-select>
                      </el-form-item>
                    </div>

                    <div class="form-section">
                      <div class="ai-notice">
                        <el-icon class="notice-icon"><InfoFilled /></el-icon>
                        <span>职位描述（工作职责、任职要求、福利待遇）将由AI智能生成</span>
                      </div>
                    </div>
                  </el-form>
                </el-card>
              </div>

              <!-- 右侧预览面板 -->
              <div class="preview-panel">
                <el-card class="preview-card">
                  <template #header>
                    <div class="card-header">
                      <el-icon><View /></el-icon>
                      <span>{{ showScoringCriteria ? '评分标准' : 'JD预览' }}</span>
                      <div class="preview-actions">
                        <el-button
                          v-if="generatedJD"
                          @click="toggleScoringCriteria"
                          :type="showScoringCriteria ? 'default' : 'primary'"
                        >
                          <el-icon><DataAnalysis /></el-icon>
                          {{ showScoringCriteria ? '返回JD预览' : '生成简历评分标准' }}
                        </el-button>
                        <el-button
                          v-if="generatedJD && !showScoringCriteria"
                          @click="toggleEditMode"
                          :type="isEditing ? 'primary' : 'default'"
                          size="small"
                        >
                          <el-icon><Edit /></el-icon>
                          {{ isEditing ? '预览' : '编辑' }}
                        </el-button>
                        <el-button
                          v-if="generatedJD && !showScoringCriteria"
                          @click="copyJD"
                          size="small"
                        >
                          <el-icon><CopyDocument /></el-icon>
                          复制
                        </el-button>
                      </div>
                    </div>
                  </template>

                  <div class="preview-content">
                    <!-- 简历评分标准界面 -->
                    <div v-if="showScoringCriteria" class="scoring-criteria-container">
                      <!-- 评分标准操作栏 -->
                      <div class="scoring-actions">
                        <el-button 
                          type="primary" 
                          @click="generateScoringCriteria" 
                          :loading="scoringGenerating"
                          :disabled="!generatedJD"
                        >
                          <el-icon><Star /></el-icon>
                          {{ scoringGenerating ? '生成中...' : 'AI生成评分标准' }}
                        </el-button>
                        <el-button 
                          v-if="scoringCriteria || scoringStreamContent"
                          @click="toggleScoringEditMode"
                          :type="isScoringEditing ? 'primary' : 'default'"
                        >
                          <el-icon><Edit /></el-icon>
                          {{ isScoringEditing ? '预览' : '编辑' }}
                        </el-button>
                        <el-button 
                          v-if="scoringCriteria || scoringStreamContent"
                          @click="saveScoringCriteria"
                          :loading="scoringSaving"
                        >
                          <el-icon><Check /></el-icon>
                          保存评分标准
                        </el-button>
                      </div>

                      <!-- 评分标准内容 -->
                      <div class="scoring-content" style="flex-grow: 1; min-height: 0; height: calc(100% - 140px);">
                        <!-- 生成中状态 - 无内容时显示骨架屏 -->
                        <div v-if="scoringGenerating && !scoringDisplayedContent" class="generating-container">
                          <el-skeleton :rows="8" animated />
                          <div class="generating-text">
                            <el-icon class="is-loading"><Loading /></el-icon>
                            AI正在生成评分标准...
                          </div>
                        </div>

                        <!-- 流式生成显示 - 有内容时实时显示 -->
                        <div v-else-if="scoringGenerating && scoringDisplayedContent" class="typewriter-container">
                          <div class="typewriter-header">
                            <el-icon class="is-loading"><Loading /></el-icon>
                            <span>AI正在生成评分标准...</span>
                          </div>
                          <div class="typewriter-content">
                            <div class="markdown-content" v-html="renderedScoringCriteria"></div>
                            <span class="typewriter-cursor">|</span>
                          </div>
                        </div>

                        <!-- 编辑模式 -->
                        <div v-else-if="isScoringEditing && (scoringCriteria || scoringStreamContent)" class="edit-container">
                          <el-input
                            v-model="scoringEditContent"
                            type="textarea"
                            :rows="20"
                            placeholder="在此编辑评分标准..."
                            class="edit-textarea"
                          />
                        </div>

                        <!-- 预览模式 -->
                        <div v-else-if="scoringCriteria || scoringStreamContent" class="preview-container">
                          <div class="markdown-content" v-html="renderedScoringCriteria"></div>
                        </div>

                        <!-- 空状态 -->
                        <div v-else class="empty-preview">
                          <el-empty description="暂无评分标准" :image-size="100">
                            <p>基于当前JD内容生成简历评分标准</p>
                          </el-empty>
                        </div>
                      </div>
                    </div>

                    <!-- JD预览界面（原有内容） -->
                    <div v-else>
                      <!-- 生成中状态 -->
                      <div v-if="generating && !displayedContent" class="generating-container">
                        <el-skeleton :rows="8" animated />
                        <div class="generating-text">
                          <el-icon class="is-loading"><Loading /></el-icon>
                          AI正在生成JD内容...
                        </div>
                      </div>

                      <!-- 打字机效果显示 -->
                      <div v-else-if="generating && displayedContent" class="typewriter-container">
                        <div class="typewriter-header">
                          <el-icon class="is-loading"><Loading /></el-icon>
                          <span>AI正在生成中...</span>
                        </div>
                        <div class="typewriter-content">
                          <div class="markdown-content" v-html="renderedDisplayedContent"></div>
                          <span class="typewriter-cursor">|</span>
                        </div>
                      </div>

                      <!-- 编辑模式 -->
                      <div v-else-if="isEditing" class="edit-container">
                        <el-input
                          v-model="editContent"
                          type="textarea"
                          :rows="20"
                          placeholder="在此编辑JD内容..."
                          class="edit-textarea"
                        />
                      </div>

                      <!-- 预览模式 -->
                      <div v-else-if="generatedJD || streamContent" class="preview-container">
                        <div class="markdown-content" v-html="renderedJD"></div>
                      </div>

                      <!-- 空状态 -->
                      <div v-else class="empty-preview">
                        <el-empty description="暂无内容" :image-size="100">
                          <p>填写左侧表单信息，然后点击"AI生成"按钮</p>
                        </el-empty>
                      </div>
                    </div>
                  </div>
                </el-card>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 评分标准引导对话框 -->
  <el-dialog
    v-model="showScoringGuideDialog"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="true"
    center
  >
    <template #header>
      <div style="display: flex; align-items: center; gap: 10px;">
        <el-icon size="24" color="#667eea"><DataAnalysis /></el-icon>
        <span style="font-size: 18px; font-weight: 600;">下一步：生成简历评分标准</span>
      </div>
    </template>
    <div style="text-align: center; padding: 20px 0;">
      <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
      <p style="font-size: 15px; color: #303133; line-height: 1.8; margin: 0 0 8px 0;">
        JD 已生成完成
      </p>
      <p style="font-size: 14px; color: #606266; line-height: 1.8; margin: 0;">
        请先生成<strong>简历评分标准</strong>，后续才能使用 AI 智能评分功能对候选人简历进行自动评分。
      </p>
    </div>
    <template #footer>
      <div style="display: flex; justify-content: center; gap: 12px;">
        <el-button @click="showScoringGuideDialog = false" size="large">
          稍后再说
        </el-button>
        <el-button type="primary" @click="goGenerateScoring" size="large">
          <el-icon><Star /></el-icon>
          立即生成评分标准
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  Plus,
  List,
  Search,
  MoreFilled,
  Edit,
  CopyDocument,
  Delete,
  Location,
  Money,
  Refresh,
  Star,
  Download,
  Check,
  Close,
  Setting,
  View,
  Loading,
  DataAnalysis,
  Rank
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { hrWorkflowsApi } from '@/api/hrWorkflows'
import { jobDescriptionApi } from '@/api/jobDescription'
import { scoringCriteriaApi } from '@/api/scoringCriteria'

// 配置marked
marked.setOptions({
  highlight: function(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  langPrefix: 'hljs language-',
  breaks: true
})

// 路由实例
const route = useRoute()

// 响应式数据
const formRef = ref()
const generating = ref(false)
const generatedJD = ref('')
const streamContent = ref('')
const saving = ref(false)
const parsingIntent = ref(false)

// 打字机效果相关
const fullStreamContent = ref('') // 存储完整的流式内容
const displayedContent = ref('') // 当前显示的内容（打字机效果）
const typewriterTimer = ref(null)

// 编辑模式相关状态
const isEditing = ref(false)
const editContent = ref('')
const savedJDId = ref(null)

// 简历评分相关状态
const showScoringCriteria = ref(false)
const scoringCriteria = ref('')
const scoringStreamContent = ref('')
const scoringDisplayedContent = ref('')
const scoringFullStreamContent = ref('')
const scoringTypewriterTimer = ref(null)
const isScoringEditing = ref(false)
const scoringEditContent = ref('')
const scoringGenerating = ref(false)
const scoringSaving = ref(false)
const savedScoringId = ref(null)
const showScoringGuideDialog = ref(false)

// JD列表相关状态
const jdList = ref([])
const jdListLoading = ref(false)
const selectedJD = ref(null)
const isCreatingNew = ref(false)
const searchKeyword = ref('')

// 分页数据
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 表单数据
const form = reactive({
  jobTitle: '',
  location: '',
  salary: '',
  experience: '',
  education: '',
  jobType: '全职',
  skills: [],
  benefits: [],
  additionalRequirements: ''
})

// 表单验证规则
const rules = {
  jobTitle: [
    { required: true, message: '请输入职位名称', trigger: 'blur' }
  ],
  location: [
    { required: true, message: '请选择工作地点', trigger: 'change' }
  ],
  experience: [
    { required: true, message: '请选择工作经验要求', trigger: 'change' }
  ],
  education: [
    { required: true, message: '请选择学历要求', trigger: 'change' }
  ]
}

// 城市选项
const cities = [
  '北京', '上海', '广州', '深圳', '杭州', '南京', '苏州', '成都', '武汉', '西安',
  '重庆', '天津', '青岛', '大连', '厦门', '宁波', '无锡', '长沙', '郑州', '济南'
]

// 技能选项
const skillOptions = [
  'JavaScript', 'TypeScript', 'Vue.js', 'React', 'Angular', 'Node.js',
  'Python', 'Java', 'Go', 'PHP', 'C++', 'C#', '.NET',
  'HTML', 'CSS', 'SCSS', 'Less', 'Webpack', 'Vite',
  'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
  'AWS', 'Azure', 'Git', 'Linux', 'Nginx', 'Jenkins'
]

// 安全默认值处理
const ensureDefaultSelections = () => {
  if (!form.location) form.location = cities[0] || ''
  if (!form.experience) form.experience = '不限'
  if (!form.education) form.education = '不限'
  if (!form.jobType) form.jobType = '全职'
}
// 计算属性
const renderedJD = computed(() => {
  if (!generatedJD.value && !streamContent.value) return ''
  const content = isEditing.value ? editContent.value : (generatedJD.value || streamContent.value)
  
  // 确保content是字符串类型
  if (typeof content !== 'string') {
    console.warn('renderedJD: content不是字符串类型:', typeof content, content)
    return ''
  }
  
  return marked(content)
})

// 打字机效果显示内容的计算属性
const renderedDisplayedContent = computed(() => {
  if (!displayedContent.value) return ''
  
  // 确保displayedContent.value是字符串类型
  if (typeof displayedContent.value !== 'string') {
    console.warn('renderedDisplayedContent: displayedContent不是字符串类型:', typeof displayedContent.value, displayedContent.value)
    return ''
  }
  
  return marked(displayedContent.value)
})

const goGenerateScoring = () => {
  showScoringGuideDialog.value = false
  showScoringCriteria.value = true
  generateScoringCriteria()
}

// 评分标准显示内容的计算属性
const renderedScoringCriteria = computed(() => {
  // 优先显示流式显示内容，然后是完整内容
  const content = scoringDisplayedContent.value || scoringCriteria.value || scoringStreamContent.value
  
  if (!content) return ''
  
  // 确保content是字符串类型
  if (typeof content !== 'string') {
    console.warn('renderedScoringCriteria: content不是字符串类型:', typeof content, content)
    return ''
  }
  
  return marked(content)
})

// 方法
const createNewJD = () => {
  isCreatingNew.value = true
  selectedJD.value = null
  resetForm()
}

const selectJD = async (jd) => {
  selectedJD.value = jd
  isCreatingNew.value = false
  
  // 加载JD详情到表单
  try {
    const response = await jobDescriptionApi.getJDDetail(jd.id)
    const jdData = response
    
    // 填充表单数据
    form.jobTitle = jdData.title || ''
    form.location = jdData.location || ''
    form.experience = jdData.experience_level || ''
    form.education = jdData.education || ''
    form.salary = jdData.salary_range || ''
    form.jobType = jdData.job_type || '全职'
    form.skills = jdData.skills ? (Array.isArray(jdData.skills) ? jdData.skills : jdData.skills.split(',')) : []
    form.benefits = jdData.benefits ? jdData.benefits.split(',') : []
    form.additionalRequirements = jdData.requirements || ''
    
    // 设置生成的内容
    streamContent.value = jdData.content || ''
    generatedJD.value = jdData.content || ''
    editContent.value = jdData.content || ''
    savedJDId.value = jd.id
    
    // 加载对应的评分标准
    await loadScoringCriteria(jd.id)
    
  } catch (error) {
    console.error('获取JD详情失败:', error)
    ElMessage.error('获取JD详情失败')
  }
}



const resetForm = () => {
  Object.keys(form).forEach(key => {
    if (Array.isArray(form[key])) {
      form[key] = []
    } else {
      form[key] = ''
    }
  })
  form.jobType = '全职'
  generatedJD.value = ''
  editContent.value = ''
  streamContent.value = ''
  isEditing.value = false
  
  // 清空评分标准相关数据
  scoringCriteria.value = ''
  scoringStreamContent.value = ''
  scoringDisplayedContent.value = ''
  scoringFullStreamContent.value = ''
  savedScoringId.value = null
  isScoringEditing.value = false
  scoringEditContent.value = ''
  showScoringCriteria.value = false
}

// 打字机效果函数
const startTypewriter = (content) => {
  // 清除之前的定时器
  if (typewriterTimer.value) {
    clearInterval(typewriterTimer.value)
  }
  
  displayedContent.value = ''
  let currentIndex = 0
  
  typewriterTimer.value = setInterval(() => {
    if (currentIndex < content.length) {
      displayedContent.value += content[currentIndex]
      currentIndex++
    } else {
      clearInterval(typewriterTimer.value)
      typewriterTimer.value = null
    }
  }, 30) // 每30毫秒显示一个字符
}

// 停止打字机效果
const stopTypewriter = () => {
  if (typewriterTimer.value) {
    clearInterval(typewriterTimer.value)
    typewriterTimer.value = null
  }
}

// 处理流式响应
const handleStreamResponse = async (response) => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('流式响应读取完成')
        break
      }

      const chunk = decoder.decode(value)
      console.log('接收到数据块:', chunk)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.trim() === '') continue // 跳过空行
        if (line.startsWith('event:')) continue
        if (line.startsWith('id:') || line.startsWith('retry:')) continue
        
        if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            const lower = data.toLowerCase()
            if (lower === 'ping' || lower.startsWith('event: ping')) continue
            if (lower.startsWith('event:') || lower.startsWith('id:') || lower.startsWith('retry:')) continue
            console.log('解析数据行:', data)
          
          if (data === '[DONE]') {
            console.log('收到结束标记')
            // 流式响应结束，内容已在实时显示中完整展示，直接设置最终内容
            if (fullStreamContent.value) {
              console.log('完整内容:', fullStreamContent.value)
              streamContent.value = fullStreamContent.value
              displayedContent.value = fullStreamContent.value
            } else {
              console.log('没有接收到任何内容')
            }
            return
          }
          
          try {
            const parsed = JSON.parse(data)
            console.log('解析的JSON数据:', parsed)
            
            // 检查不同可能的字段
            if (parsed.answer) {
              console.log('找到answer字段:', parsed.answer)
              fullStreamContent.value += parsed.answer
              // 实时显示内容（不等待完成）
              displayedContent.value = fullStreamContent.value
            } else if (parsed.content) {
              console.log('找到content字段:', parsed.content)
              fullStreamContent.value += parsed.content
              displayedContent.value = fullStreamContent.value
            } else if (parsed.text) {
              console.log('找到text字段:', parsed.text)
              fullStreamContent.value += parsed.text
              displayedContent.value = fullStreamContent.value
            } else {
              console.log('未找到内容字段，完整数据:', parsed)
            }
          } catch (e) {
            console.log('JSON解析失败，原始数据:', data, '错误:', e)
            // 如果不是JSON，直接添加到结果中
            if (data && data !== '[DONE]' && !data.toLowerCase().startsWith('event:')) {
              fullStreamContent.value += data
              displayedContent.value = fullStreamContent.value
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
// 解析查询文本并智能填充表单
const parseQueryAndFillForm = async (queryText) => {
  try {
    console.log('开始解析查询文本:', queryText)
    
    // 将查询文本放入additionalRequirements字段
    form.additionalRequirements = queryText
    
    // 简单的关键词匹配来智能填充表单
    const text = queryText.toLowerCase()
    
    // 提取职位名称
    if (text.includes('jd') || text.includes('职位') || text.includes('岗位')) {
      // 尝试提取具体职位名称
      const jobMatches = [
        { keywords: ['java', 'java开发', 'java工程师', 'java后端'], title: 'Java开发工程师' },
        { keywords: ['前端', '前端开发', '前端工程师', 'vue', 'react'], title: '前端开发工程师' },
        { keywords: ['产品经理', '产品', 'pm'], title: '产品经理' },
        { keywords: ['ui', 'ui设计师', '设计师'], title: 'UI设计师' },
        { keywords: ['测试', '测试工程师', 'qa'], title: '测试工程师' },
        { keywords: ['运维', '运维工程师', 'devops'], title: '运维工程师' },
        { keywords: ['财务', '财务经理', '会计'], title: '财务经理' },
        { keywords: ['人事', 'hr', '人力资源'], title: '人力资源专员' }
      ]
      
      for (const job of jobMatches) {
        if (job.keywords.some(keyword => text.includes(keyword))) {
          form.jobTitle = job.title
          break
        }
      }
    }
    
    // 提取工作经验
    const expMatches = [
      { keywords: ['3-5年', '3到5年', '三到五年'], value: '3-5年' },
      { keywords: ['1-3年', '1到3年', '一到三年'], value: '1-3年' },
      { keywords: ['5年以上', '5年+', '五年以上'], value: '5年以上' },
      { keywords: ['应届', '无经验', '0年'], value: '应届生' }
    ]
    
    for (const exp of expMatches) {
      if (exp.keywords.some(keyword => text.includes(keyword))) {
        form.experience = exp.value
        break
      }
    }
    
    // 设置默认值
    if (!form.jobTitle) {
      form.jobTitle = '待定职位'
    }
    if (!form.location) {
      form.location = '北京'
    }
    if (!form.experience) {
      form.experience = '3-5年'
    }
    if (!form.education) {
      form.education = '本科'
    }
    if (!form.salary) {
      form.salary = '面议'
    }
    
    console.log('表单填充完成:', form)
    ElMessage.success('已根据需求自动填充表单，正在生成JD...')
    
  } catch (error) {
    console.error('解析查询文本失败:', error)
    ElMessage.warning('解析需求失败，将使用默认配置生成JD')
  }
}

// 使用后端解析结果填充表单
const fillFormFromParsedData = (parsed) => {
  try {
    if (!parsed) return
    // 某些请求库可能将数据包裹在 data 或 result 中
    const data = parsed.data || parsed.result || parsed
    form.jobTitle = data.job_title || form.jobTitle
    form.department = data.department || form.department
    form.location = data.location || form.location
    form.salary = data.salary || form.salary
    form.experience = data.experience || form.experience
    form.education = data.education || form.education
    form.jobType = data.job_type || form.jobType
    form.skills = Array.isArray(data.skills) ? data.skills : form.skills
    form.benefits = Array.isArray(data.benefits) ? data.benefits : form.benefits
    form.additionalRequirements = data.additional_requirements || String(route.query.q || '')
    // 如果关键字段缺失，自动选中第一个选项
    ensureDefaultSelections()
  } catch (e) {
    console.error('填充表单失败，使用默认值', e)
    ensureDefaultSelections()
  }
}

const generateJD = async () => {
  try {
    // 生成前确保缺省值已填充，避免校验报错
    ensureDefaultSelections()
    await formRef.value.validate()
    
    generating.value = true
    streamContent.value = '' // 清空之前的内容
    fullStreamContent.value = '' // 清空完整流式内容
    displayedContent.value = '' // 清空显示内容
    stopTypewriter() // 停止之前的打字机效果
    generatedJD.value = '' // 清空之前的JD，确保是字符串类型
    
    // 只有在创建新JD时才重置ID，编辑现有JD时保留ID以确保更新操作
    if (isCreatingNew.value) {
      savedJDId.value = null // 重置JD ID，确保新生成的JD是新增而不是更新
    }
    // 如果是编辑现有JD（savedJDId.value存在），保留ID以便后续更新
    
    // 验证必填字段
    if (!form.jobTitle.trim()) {
      ElMessage.warning('请输入职位名称')
      return
    }
    
    // 构建职位要求描述
    const requirements = `职位：${form.jobTitle}
工作地点：${form.location}
工作经验：${form.experience}
学历要求：${form.education}
薪资范围：${form.salary}
工作类型：${form.jobType}
技能要求：${form.skills.join('、')}
福利待遇：${form.benefits.join('、')}
其他要求：${form.additionalRequirements}`

    // 调用后端API
    const response = await hrWorkflowsApi.generateJD({
      requirements: requirements,
      position_title: form.jobTitle,
      department: '技术部', // 可以后续添加到表单中
      experience_level: form.experience,
      stream: true
    })
    
    // 处理流式响应
    await handleStreamResponse(response)
    
    // 流式响应完成后，解析内容并设置generatedJD
    if (streamContent.value) {
      // 确保generatedJD.value是字符串类型
      generatedJD.value = streamContent.value
      editContent.value = streamContent.value
      ElMessage.success('JD生成成功，正在自动保存...')
      // 自动保存JD
      await saveJD()
      // 弹出评分标准引导对话框
      showScoringGuideDialog.value = true
    } else {
      ElMessage.warning('未收到JD内容，请重试')
    }
  } catch (error) {
    console.error('生成JD失败:', error)
    ElMessage.error('生成JD失败，请重试')
  } finally {
    generating.value = false
  }
}

const saveJD = async () => {
  if (!editContent.value.trim()) {
    ElMessage.warning('JD内容不能为空')
    return
  }

  try {
    saving.value = true
    
    console.log('保存前的编辑内容:', editContent.value)
    console.log('保存前的显示内容:', streamContent.value)
    console.log('当前JD ID:', savedJDId.value)
    console.log('表单数据:', {
      jobTitle: form.jobTitle,
      location: form.location,
      salary: form.salary,
      experience: form.experience,
      education: form.education,
      jobType: form.jobType,
      skills: form.skills,
      benefits: form.benefits
    })
    
    const jdData = {
      title: form.jobTitle || '未命名岗位',
      department: form.department || null,
      location: form.location || null,
      salary_range: form.salary || null,
      experience_level: form.experience || null,
      education: form.education || null,
      job_type: form.jobType || null,
      skills: form.skills || null,
      content: editContent.value,
      requirements: form.additionalRequirements || null,
      status: 'draft',
      meta_data: {
        benefits: form.benefits
      }
    }

    console.log('发送到后端的数据:', jdData)
    
    let response
    if (savedJDId.value) {
      // 如果已有ID，执行更新操作
      console.log('执行更新操作，JD ID:', savedJDId.value)
      response = await jobDescriptionApi.updateJD(savedJDId.value, jdData)
      ElMessage.success('JD更新成功')
    } else {
      // 如果没有ID，执行新增操作
      console.log('执行新增操作')
      response = await jobDescriptionApi.saveJD(jdData)
      console.log('新增操作完整响应:', response)
      if (response && response.id) {
        savedJDId.value = response.id
        console.log('新增成功，获得JD ID:', savedJDId.value)
      } else {
        console.log('响应中没有ID字段，响应结构:', response)
      }
      ElMessage.success('JD保存成功')
    }
    
    console.log('后端返回的响应:', response)
    
    // 更新显示内容
    streamContent.value = editContent.value
    isEditing.value = false
    
    // 刷新JD列表
    await fetchJDList()
    
    console.log('保存后的显示内容:', streamContent.value)
    
  } catch (error) {
    console.error('保存JD失败:', error)
    ElMessage.error('保存JD失败，请重试')
  } finally {
    saving.value = false
  }
}

const toggleEditMode = () => {
  if (isEditing.value) {
    generatedJD.value = editContent.value
  }
  isEditing.value = !isEditing.value
}

const copyJD = async () => {
  try {
    const content = isEditing.value ? editContent.value : generatedJD.value
    await navigator.clipboard.writeText(content)
    ElMessage.success('JD内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleJDAction = async ({ action, jd }) => {
  switch (action) {
    case 'edit':
      selectJD(jd)
      break
    case 'duplicate':
      await duplicateJD(jd)
      break
    case 'download':
      downloadJD(jd)
      break
    case 'delete':
      await deleteJD(jd)
      break
  }
}

const duplicateJD = async (jd) => {
  try {
    // 获取JD详情
    const response = await jobDescriptionApi.getJDDetail(jd.id)
    const jdData = response
    
    // 创建副本数据
    const newJDData = {
      title: (jdData.title || '') + ' (副本)',
      department: jdData.department || null,
      location: jdData.location || null,
      salary_range: jdData.salary_range || null,
      experience_level: jdData.experience_level || null,
      education: jdData.education || null,
      job_type: jdData.job_type || null,
      skills: jdData.skills || null,
      content: jdData.content || '',
      requirements: jdData.requirements || null,
      status: 'draft',
      meta_data: {
        benefits: jdData.benefits
      }
    }
    
    await jobDescriptionApi.saveJD(newJDData)
    ElMessage.success('JD复制成功')
    await fetchJDList()
  } catch (error) {
    console.error('复制JD失败:', error)
    ElMessage.error('复制JD失败')
  }
}

const downloadJD = (jd) => {
  const content = jd.content || ''
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${jd.title || 'JD'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const deleteJD = async (jd) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除职位"${jd.title || '未命名职位'}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await jobDescriptionApi.deleteJD(jd.id)
    ElMessage.success('JD删除成功')
    
    if (selectedJD.value?.id === jd.id) {
      selectedJD.value = null
      isCreatingNew.value = false
    }
    
    await fetchJDList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除JD失败:', error)
      ElMessage.error('删除JD失败')
    }
  }
}

const fetchJDList = async () => {
  try {
    jdListLoading.value = true
    const params = {
      page: pagination.page,
      size: pagination.size
    }
    
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    
    const response = await jobDescriptionApi.getJDList(params)
    jdList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('获取JD列表失败:', error)
    ElMessage.error('获取JD列表失败')
  } finally {
    jdListLoading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchJDList()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchJDList()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchJDList()
}

const getStatusType = (status) => {
  const statusMap = {
    'draft': 'info',
    'published': 'success',
    'archived': 'warning'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    'draft': '草稿',
    'published': '已发布',
    'archived': '已归档'
  }
  return statusMap[status] || '草稿'
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

// 简历评分相关方法
const toggleScoringCriteria = () => {
  showScoringCriteria.value = !showScoringCriteria.value
  if (showScoringCriteria.value && !scoringCriteria.value && !scoringStreamContent.value) {
    // 如果切换到评分标准页面且没有内容，可以提示用户生成
  }
}

const startScoringTypewriter = (content) => {
  scoringFullStreamContent.value = content
  scoringDisplayedContent.value = ''
  
  let index = 0
  const speed = 20 // 打字速度（毫秒）
  
  scoringTypewriterTimer.value = setInterval(() => {
    if (index < content.length) {
      scoringDisplayedContent.value += content[index]
      index++
    } else {
      clearInterval(scoringTypewriterTimer.value)
      scoringTypewriterTimer.value = null
    }
  }, speed)
}

const stopScoringTypewriter = () => {
  if (scoringTypewriterTimer.value) {
    clearInterval(scoringTypewriterTimer.value)
    scoringTypewriterTimer.value = null
    // 立即显示完整内容
    scoringDisplayedContent.value = scoringFullStreamContent.value
  }
}

// 实时添加内容的打字机效果

const generateScoringCriteria = async () => {
  if (!generatedJD.value && !streamContent.value) {
    ElMessage.warning('请先生成JD内容')
    return
  }

  try {
    scoringGenerating.value = true
    scoringStreamContent.value = ''
    scoringDisplayedContent.value = ''
    scoringFullStreamContent.value = ''
    
    // 停止之前的打字机效果
    stopScoringTypewriter()
    
    // 重新检查当前JD的评分标准状态
    // 如果是新JD或者当前JD没有评分标准，则生成新的评分标准
    if (isCreatingNew.value) {
      savedScoringId.value = null
      console.log('新JD，清除评分ID')
    } else if (savedJDId.value) {
      // 对于已存在的JD，重新加载评分标准状态以确保ID正确
      await loadScoringCriteria(savedJDId.value)
      console.log('重新加载评分标准，当前ID:', savedScoringId.value)
    }

    const jdContent = generatedJD.value || streamContent.value
    
    const response = await hrWorkflowsApi.generateScoringCriteria({
      jd_content: jdContent,
      job_title: form.jobTitle,
      requirements: {
        experience: form.experience,
        education: form.education,
        skills: form.skills,
        location: form.location
      },
      stream: true
    })

    if (response.body) {
      await handleScoringStreamResponse(response)
    } else {
      scoringCriteria.value = response.criteria || response
      scoringStreamContent.value = scoringCriteria.value
      startScoringTypewriter(scoringCriteria.value)
    }

    // 生成完成后自动保存评分标准
    if (scoringCriteria.value || scoringStreamContent.value) {
      ElMessage.success('评分标准生成成功，正在自动保存...')
      await saveScoringCriteria()
    }
  } catch (error) {
    console.error('生成评分标准失败:', error)
    ElMessage.error('生成评分标准失败，请重试')
  } finally {
    scoringGenerating.value = false
  }
}

const handleScoringStreamResponse = async (response) => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  // 初始化显示状态
  scoringStreamContent.value = ''
  scoringDisplayedContent.value = ''
  scoringFullStreamContent.value = ''
  
  console.log('开始处理评分标准流式响应')
  
  try {
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.trim() === '') continue // 跳过空行
        
        // 跳过event类型的行（如 "event: ping"）
        if (line.startsWith('event:')) {
          console.log('跳过event行:', line)
          continue
        }
        
        if (line.startsWith('data: ')) {
          try {
            const data = line.slice(6).trim()
            
            if (data === '[DONE]') {
              // 流式传输完成，设置最终内容
              console.log('评分标准流式传输完成，最终内容长度:', scoringStreamContent.value.length)
              scoringCriteria.value = scoringStreamContent.value
              scoringFullStreamContent.value = scoringStreamContent.value
              return
            }
            
            // 跳过空数据
            if (!data) continue
            
            // 尝试解析JSON数据
            const parsed = JSON.parse(data)
            // 处理Dify返回的原始格式，优先使用answer字段，其次是content字段
            let newContent = ''
            if (parsed.answer) {
              newContent = parsed.answer
            } else if (parsed.content) {
              newContent = parsed.content
            }
            
            if (newContent) {
              console.log('接收到新内容:', newContent)
              // 累加到总内容（参考JD生成的方式）
              scoringStreamContent.value += newContent
              // 实时显示内容，直接更新显示内容
              scoringDisplayedContent.value = scoringStreamContent.value
              console.log('当前显示内容长度:', scoringDisplayedContent.value.length)
            }
          } catch (e) {
            console.warn('解析流式数据失败，跳过该行:', line, '错误:', e.message)
          }
        }
      }
    }
  } catch (error) {
    console.error('处理流式响应失败:', error)
    throw error
  }
}

const toggleScoringEditMode = () => {
  if (isScoringEditing.value) {
    // 取消编辑
    isScoringEditing.value = false
    scoringEditContent.value = ''
  } else {
    // 开始编辑，优先使用已保存的内容，然后是流式内容，最后是显示的内容
    isScoringEditing.value = true
    scoringEditContent.value = scoringCriteria.value || scoringStreamContent.value || scoringDisplayedContent.value || ''
    console.log('进入编辑模式，编辑内容:', scoringEditContent.value.substring(0, 100) + '...')
  }
}

const saveScoringCriteria = async () => {
  const content = isScoringEditing.value ? scoringEditContent.value : (scoringCriteria.value || scoringStreamContent.value)
  
  if (!content.trim()) {
    ElMessage.warning('评分标准内容不能为空')
    return
  }

  try {
    scoringSaving.value = true
    
    const scoringData = {
      title: `${form.jobTitle || '职位'}评分标准`,
      job_title: form.jobTitle,
      content: content,
      job_description_id: savedJDId.value,
      status: 'active',
      meta_data: {
        generated_from_jd: true,
        jd_requirements: {
          experience: form.experience,
          education: form.education,
          skills: form.skills,
          location: form.location
        }
      }
    }

    let response
    if (savedScoringId.value) {
      // 更新现有评分标准
      response = await scoringCriteriaApi.updateScoringCriteria(savedScoringId.value, scoringData)
      ElMessage.success('评分标准更新成功')
    } else {
      // 创建新的评分标准
      response = await scoringCriteriaApi.createScoringCriteria(scoringData)
      savedScoringId.value = response.id
      ElMessage.success('评分标准保存成功')
    }
    
    // 更新本地内容
    scoringCriteria.value = content
    if (isScoringEditing.value) {
      isScoringEditing.value = false
      scoringEditContent.value = ''
    }
    
  } catch (error) {
    console.error('保存评分标准失败:', error)
    ElMessage.error('保存评分标准失败，请重试')
  } finally {
    scoringSaving.value = false
  }
}

// 加载评分标准
const loadScoringCriteria = async (jdId) => {
  try {
    console.log('正在加载评分标准，JD ID:', jdId)
    const response = await scoringCriteriaApi.getScoringCriteriaByJD(jdId)
    console.log('评分标准API响应:', response)
    
    if (response.items && response.items.length > 0) {
      // 取最新的评分标准
      const latestCriteria = response.items[0]
      scoringCriteria.value = latestCriteria.content
      scoringStreamContent.value = latestCriteria.content
      scoringDisplayedContent.value = latestCriteria.content
      savedScoringId.value = latestCriteria.id
    } else {
      // 清空评分标准相关数据
      scoringCriteria.value = ''
      scoringStreamContent.value = ''
      scoringDisplayedContent.value = ''
      savedScoringId.value = null
    }
  } catch (error) {
    console.error('加载评分标准失败:', error)
    // 不显示错误消息，因为可能是没有评分标准
    scoringCriteria.value = ''
    scoringStreamContent.value = ''
    scoringDisplayedContent.value = ''
    savedScoringId.value = null
  }
}

// 生命周期
onMounted(async () => {
  await fetchJDList()
  
  // 检查URL参数q，如果存在则自动触发创建新JD和AI生成
  const queryText = route.query.q
  if (queryText) {
    console.log('检测到URL参数q:', queryText)
    
    // 自动创建新JD
    createNewJD()
    
    // 优先调用后端LLM解析为结构化字段并填充表单
    try {
      parsingIntent.value = true
      const parsed = await hrWorkflowsApi.parseRequirements({ text: String(queryText) })
      fillFormFromParsedData(parsed)
    } catch (e) {
      console.warn('后端解析失败，回退到前端解析：', e)
      await parseQueryAndFillForm(queryText)
    } finally {
      parsingIntent.value = false
    }
    
    // 延迟一下确保表单填充完成，然后自动触发AI生成
    setTimeout(() => {
      generateJD()
    }, 500)
  }
})

onUnmounted(() => {
  // 清理打字机定时器
  stopTypewriter()
  stopScoringTypewriter()
})
</script>

<style lang="scss" scoped>
.jd-generator {
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
    z-index: 1;
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

  .jd-list-panel {
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

      .jd-list-content {
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

        .jd-items {
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

          .jd-item {
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

            .jd-item-header {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              margin-bottom: 12px;

              .jd-title {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                color: #303133;
                flex: 1;
                line-height: 1.4;
              }

              .jd-actions {
                margin-left: 8px;
              }
            }

            .jd-item-content {
              .jd-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-bottom: 8px;

                .meta-item {
                  display: flex;
                  align-items: center;
                  gap: 4px;
                  font-size: 12px;
                  color: #606266;
                }
              }

              .jd-status {
                margin-bottom: 8px;
              }

              .jd-time {
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

  .jd-editor-panel {
    flex: 1;
    min-width: 0;

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

    .jd-editor-content {
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

            &.el-button--success {
              background: linear-gradient(135deg, #10b981, #059669);
              border: none;
              color: white;

              &:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
              }
            }

            &:not(.el-button--primary):not(.el-button--success) {
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
        display: flex;
        gap: 20px;
        min-height: 0;

        .config-panel {
          width: 400px;
          flex-shrink: 0;

          .config-card {
            height: 100%;
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
              padding: 20px;
              height: calc(100% - 60px);
              overflow: hidden;
            }

            .card-header {
              display: flex;
              align-items: center;
              gap: 8px;
              font-weight: 600;
              color: #303133;
            }

            .jd-form {
              height: calc(100% - 140px);
              overflow-y: auto;
              padding-right: 8px;

              .form-section {
                margin-bottom: 24px;

                .section-title {
                  margin: 0 0 16px 0;
                  font-size: 14px;
                  font-weight: 600;
                  color: #303133;
                  padding-bottom: 8px;
                  border-bottom: 1px solid #e4e7ed;
                }

                .ai-notice {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  padding: 16px;
                  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
                  border: 1px solid rgba(102, 126, 234, 0.2);
                  border-radius: 12px;
                  color: #667eea;
                  font-size: 14px;
                  font-weight: 500;

                  .notice-icon {
                    font-size: 18px;
                    color: #667eea;
                  }
                }
              }
            }
          }
        }

        .preview-panel {
          flex: 1;
          min-width: 0;

          .preview-card {

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
              padding: 20px;
              height: calc(100% - 60px);
              overflow: hidden;
            }

            .card-header {
              display: flex;
              align-items: center;
              justify-content: space-between;

              > div:first-child {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
                color: #303133;
              }

              .preview-actions {
                display: flex;
                gap: 8px;
              }
            }

            .preview-content {
              height: calc(100% - 20px);
              overflow-y: auto;
              display: flex;
              flex-direction: column;

              .generating-container {
                .generating-text {
                  text-align: center;
                  margin-top: 16px;
                  color: #409eff;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  gap: 8px;
                }
              }

              .edit-container {
                height: 100%;
                min-height: 400px;

                .edit-textarea {
                  height: 100%;

                  :deep(.el-textarea__inner) {
                    height: 100% !important;
                    resize: none;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-size: 14px;
                    line-height: 1.6;
                  }
                }
              }

              .preview-container {
                height: 100%;
                min-height: 400px;
                
                .markdown-content {
                  line-height: 1.8;
                  color: #303133;

                  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
                    margin: 24px 0 16px 0;
                    font-weight: 600;
                    color: #303133;
                  }

                  :deep(h1) { font-size: 24px; }
                  :deep(h2) { font-size: 20px; }
                  :deep(h3) { font-size: 18px; }
                  :deep(h4) { font-size: 16px; }

                  :deep(p) {
                    margin: 16px 0;
                    line-height: 1.8;
                  }

                  :deep(ul), :deep(ol) {
                    margin: 16px 0;
                    padding-left: 24px;

                    li {
                      margin: 8px 0;
                      line-height: 1.6;
                    }
                  }

                  :deep(blockquote) {
                    margin: 16px 0;
                    padding: 16px;
                    background: #f8f9fa;
                    border-left: 4px solid #409eff;
                    border-radius: 4px;
                  }

                  :deep(code) {
                    background: #f1f2f3;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-size: 13px;
                  }

                  :deep(pre) {
                    background: #f8f9fa;
                    padding: 16px;
                    border-radius: 8px;
                    overflow-x: auto;
                    margin: 16px 0;

                    code {
                      background: none;
                      padding: 0;
                    }
                  }
                }
              }

              .empty-preview {
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;

                p {
                  margin-top: 16px;
                  color: #909399;
                  font-size: 14px;
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
  .jd-generator {
    .main-content {
      .jd-list-panel {
        width: 320px;
      }

      .jd-editor-panel {
        .jd-editor-content {
          .editor-main {
            .config-panel {
              width: 350px;
            }
          }
        }
      }
    }
  }
}

@media (max-width: 1200px) {
  .jd-generator {
    .main-content {
      flex-direction: column;

      .jd-list-panel {
        width: 100%;
        height: 300px;
      }

      .jd-editor-panel {
        .jd-editor-content {
          .editor-main {
            flex-direction: column;

            .config-panel {
              width: 100%;
              height: 400px;
            }

            .preview-panel {
              height: 500px;
            }
          }
        }
      }
    }
  }
}

// 打字机效果样式
.typewriter-container {
  height: 100%;
  min-height: 400px;
  .typewriter-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    color: #409eff;
    font-size: 14px;
    
    .el-icon {
      font-size: 16px;
    }
  }
  
  .typewriter-content {
    position: relative;
    
    .typewriter-cursor {
      display: inline-block;
      background-color: #409eff;
      width: 2px;
      height: 1.2em;
      margin-left: 2px;
      animation: blink 1s infinite;
    }
  }
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}
</style>
