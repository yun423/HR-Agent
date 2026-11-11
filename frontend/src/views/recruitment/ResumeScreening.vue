<template>
  <div class="resume-screening">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><User /></el-icon>
            简历筛选
          </h1>
          <p class="page-description">智能简历筛选与评估，快速找到合适的候选人</p>
        </div>
        <div class="header-actions">
          <el-button @click="openUploadDialog" type="primary" size="large">
            <el-icon><Upload /></el-icon>
            上传简历
          </el-button>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧简历列表 -->
        <div class="resume-list-panel">
          <el-card class="list-card">
            <template #header>
              <div class="list-header">
                <span class="list-title">
                  <el-icon><List /></el-icon>
                  简历列表 ({{ pagination.total }})
                </span>
                <div class="list-actions">
                  <el-input
                    v-model="filters.keyword"
                    placeholder="搜索简历..."
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

            <!-- 筛选器 -->
            <div class="filters-section">
              
               <!-- 按JD筛选 -->
              <div class="filter-group">
                <el-select
                  v-model="filters.jdId"
                  placeholder="按JD"
                  clearable
                  filterable
                  size="small"
                  style="width: 200px"
                  :loading="jdListLoading"
                  @change="applyFilters"
                >
                  <el-option label="不限" value="" />
                  <el-option
                    v-for="jd in jdList"
                    :key="jd.id"
                    :label="jd.title"
                    :value="jd.id"
                  />
                </el-select>
              </div>
              <div class="filter-group">
                <el-select
                  v-model="filters.scoreBucket"
                  placeholder="按分数"
                  clearable
                  size="small"
                  style="width: 120px"
                  @change="applyFilters"
                >
                  <el-option label="不限" value="" />
                  <el-option label="60分以上" value="60分以上" />
                  <el-option label="70分以上" value="70分以上" />
                  <el-option label="80分以上" value="80分以上" />
                  <el-option label="90分以上" value="90分以上" />
                </el-select>
              </div>

              <div class="filter-group">
                <el-select
                  v-model="filters.dateRange"
                  placeholder="按时间"
                  clearable
                  size="small"
                  style="width: 120px"
                  @change="applyFilters"
                >
                  <el-option label="不限" value="" />
                  <el-option label="今天" value="today" />
                  <el-option label="最近三天" value="last3" />
                  <el-option label="最近一周" value="last7" />
                  <el-option label="最近一个月" value="last30" />
                </el-select>
              </div>

              <div class="filter-group">
                <el-button @click="refreshResumeList" size="small">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>

            <!-- 简历列表内容 -->
            <div class="resume-list-content">
              <div v-if="loading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>
              
              <div v-else-if="filteredResumeList.length === 0" class="empty-container">
                <el-empty description="暂无简历数据" :image-size="120">
                  <el-button type="primary" @click="openUploadDialog">
                    <el-icon><Upload /></el-icon>
                    上传第一份简历
                  </el-button>
                </el-empty>
              </div>

              <div v-else>
                <div class="toolbar">
                  <el-checkbox v-model="selectAll" @change="toggleSelectAll">全选</el-checkbox>
                  <el-button size="small" type="primary" :disabled="selectedIds.length===0 || exportLoading" @click="exportSelected">
                    导出选中（{{ selectedIds.length }}）
                  </el-button>
                </div>
                <div v-if="exportLoading" class="export-progress">
                  <el-progress :percentage="exportProgress" :stroke-width="6" />
                  <span class="export-progress-text">正在导出简历附件...</span>
                </div>
                <div class="resume-items">
                  <div
                    v-for="resume in filteredResumeList"
                    :key="resume.id"
                    :class="['resume-item', { active: selectedResume?.id === resume.id }]"
                    @click="selectResume(resume)"
                  >
                  <div class="resume-item-header">
                    <div class="candidate-info">
                      <el-checkbox
                        v-model="selectionMap[resume.id]"
                        @change="onItemSelectChange(resume)"
                        class="item-checkbox"
                      />
                      <h4 class="candidate-name">{{ resume.name }}</h4>
                      <div class="score-badge">
                        <el-tag :type="getScoreType(resume.matchScore)" size="small">
                          {{ resume.matchScore }}分
                        </el-tag>
                      </div>
                    </div>
                  </div>
                  
                  <div class="resume-item-content">
                    <div class="position-info">
                      <span class="position-text">{{ resume.currentPosition || '未填写职位' }}</span>
                      <span class="created-date">{{ formatDateDay(resume.createdAt || resume.created_at) }}</span>
                    </div>
                    
                    <div class="resume-actions">
                      <el-button @click.stop="viewResumeDetail(resume)" type="primary" size="small">
                        <el-icon><View /></el-icon>
                        简历预览
                      </el-button>
                      <el-button @click.stop="deleteResume(resume)" type="danger" size="small">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
              </div>

              <!-- 分页 -->
              <div v-if="filteredResumeList.length > 0" class="pagination-container">
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

              <div class="export-progress" v-if="exportLoading">
                <el-progress :percentage="exportProgress" :stroke-width="6" />
                <span class="export-progress-text">正在导出简历附件...</span>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 右侧详情区域 -->
        <div class="resume-detail-panel">
          <!-- 欢迎页面 -->
          <div v-if="!selectedResume" class="welcome-container">
            <el-card class="welcome-card">
              <div class="welcome-content">
                <div class="welcome-icon">
                  <el-icon size="80"><User /></el-icon>
                </div>
                <h2>选择简历查看详情</h2>
                <p>点击左侧的简历项目查看详细信息和评价结果</p>
                <div class="welcome-actions">
                  <el-button type="primary" @click="openUploadDialog" size="large">
                    <el-icon><Upload /></el-icon>
                    上传新简历
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>

          <!-- 简历详情内容 -->
          <div v-else class="resume-detail-content">
            <!-- 详情头部 -->
            <div class="detail-header">
              <div class="candidate-profile">
                <el-avatar :size="60" :src="selectedResume.avatar">
                  {{ selectedResume.name?.charAt(0) }}
                </el-avatar>
                <div class="profile-info">
                  <h3>{{ selectedResume.name }}</h3>
                  <p class="current-position">{{ selectedResume.currentPosition }}</p>
                  <div class="profile-meta">
                    <span class="meta-item">{{ formatExperience(selectedResume.experience) }}</span>
                    <span class="meta-divider">|</span>
                    <span class="meta-item">{{ selectedResume.education }}</span>
                    <span class="meta-divider">|</span>
                    <span class="meta-item">{{ selectedResume.age }}岁</span>
                  </div>
                  <!-- 操作按钮行 -->
                  <div class="action-buttons">
                     
                    <el-button type="primary" size="default" @click="handleInterview">
                      <el-icon><Check /></el-icon>
                      面试
                    </el-button>
                  </div>
                </div>
              </div>
              <div class="score-section">
                <div class="score-display">
                  <el-progress
                    type="circle"
                    :percentage="selectedResume.matchScore"
                    :color="getScoreColor(selectedResume.matchScore)"
                    :width="80"
                  >
                    <template #default="{ percentage }">
                      <span class="score-text">{{ percentage }}分</span>
                    </template>
                  </el-progress>
                </div>
                <p class="score-label">匹配度</p>
              </div>
            </div>

            <!-- 详情主要内容 - 两列布局 -->
            <div class="detail-main">
              <div class="two-column-layout">
                <!-- 左列：简历详情 -->
                <div class="left-column">
                  <div class="column-header">
                    <h4 class="column-title">
                      <el-icon><Document /></el-icon>
                      简历详情
                    </h4>
                  </div>
                  <div class="column-content">
                    <div class="resume-content-section">
                      <div class="content-display" v-html="formattedResumeContent"></div>
                    </div>
                  </div>
                </div>

                <!-- 右列：评价结果 -->
                <div class="right-column">
                  <div class="column-header">
                    <h4 class="column-title">
                      <el-icon><Star /></el-icon>
                      评价结果
                    </h4>
                  </div>
                  <div class="column-content">
                    <div class="evaluation-section">
                      <div v-if="selectedResume.evaluationMetrics && selectedResume.evaluationMetrics.length > 0" class="evaluation-content">
                        <div
                          v-for="metric in selectedResume.evaluationMetrics"
                          :key="metric.name"
                          class="evaluation-item"
                        >
                          <div class="metric-header">
                            <h4 class="metric-name">{{ metric.name }}</h4>
                            <div class="metric-score">
                              <el-tag :type="getMetricScoreType(metric.score, metric.max)">
                                {{ metric.score }}/{{ metric.max }}分
                              </el-tag>
                            </div>
                          </div>
                          <div class="metric-reason">
                            <p>{{ metric.reason }}</p>
                          </div>
                        </div>
                      </div>
                      <div v-else class="no-evaluation">
                        <el-empty description="暂无评价数据" :image-size="100" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传简历对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传简历"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="upload-section" v-if="!scoring">
        <!-- JD选择器 -->
        <div class="jd-selector-section">
          <el-form-item label="选择对应JD" required>
            <el-select
              v-model="selectedJDId"
              placeholder="请选择要匹配的职位描述"
              style="width: 100%"
              filterable
              :loading="jdListLoading"
            >
              <el-option
                v-for="jd in jdList"
                :key="jd.id"
                :label="`${jd.title} - ${scoringCriteriaMap[jd.id] ? '已生成评分标准' : '未生成评分标准'}`"
                :value="jd.id"
              >
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span>{{ jd.title }}</span>
                  <span :style="{ color: scoringCriteriaMap[jd.id] ? '#10b981' : '#f56c6c', fontSize: '13px' }">
                    {{ scoringCriteriaMap[jd.id] ? '已生成评分标准' : '未生成评分标准' }}
                  </span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
        </div>

        <el-upload
          ref="uploadRef"
          class="upload-dragger"
          drag
          :auto-upload="false"
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :before-upload="beforeUpload"
          :on-change="handleFileChange"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :file-list="fileList"
          accept=".pdf,.doc,.docx"
          :limit="1"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF、DOC、DOCX 格式，文件大小不超过 10MB
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 评分中状态 -->
      <div v-else class="scoring-section">
        <div class="scoring-status">
          <div class="scoring-icon">
            <el-icon size="56" color="#667eea"><Document /></el-icon>
          </div>
          <h3 class="scoring-title">AI 正在评分简历</h3>
          <p class="scoring-desc">请稍候，正在对简历进行智能分析评分...</p>
          <div class="scoring-steps">
            <div class="scoring-step" :class="{ active: scoringStep >= 1, done: scoringStep > 1 }">
              <div class="step-dot">
                <el-icon v-if="scoringStep > 1"><Check /></el-icon>
                <span v-else>1</span>
              </div>
              <span class="step-label">解析简历内容</span>
            </div>
            <div class="step-line" :class="{ active: scoringStep >= 2 }"></div>
            <div class="scoring-step" :class="{ active: scoringStep >= 2, done: scoringStep > 2 }">
              <div class="step-dot">
                <el-icon v-if="scoringStep > 2"><Check /></el-icon>
                <span v-else>2</span>
              </div>
              <span class="step-label">匹配JD评分标准</span>
            </div>
            <div class="step-line" :class="{ active: scoringStep >= 3 }"></div>
            <div class="scoring-step" :class="{ active: scoringStep >= 3, done: scoringStep > 3 }">
              <div class="step-dot">
                <el-icon v-if="scoringStep > 3"><Check /></el-icon>
                <span v-else>3</span>
              </div>
              <span class="step-label">AI智能评分</span>
            </div>
          </div>
          <div class="scoring-progress">
            <el-progress :percentage="scoringProgress" :stroke-width="8" :show-text="false" />
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button v-if="!scoring" @click="showUploadDialog = false">取消</el-button>
          <el-button v-if="!scoring" type="primary" @click="confirmUpload" :loading="uploading">
            确定上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Star, Close, Check, MagicStick, Upload } from '@element-plus/icons-vue'
import { resumeApi } from '@/api/resume'
import { jdApi } from '@/api/jd'
import { hrWorkflowsApi } from '@/api/hrWorkflows'
import { scoringCriteriaApi } from '@/api/scoringCriteria'
import { marked } from 'marked'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

// 用户存储
const authStore = useAuthStore()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const selectedResume = ref(null)
const activeTab = ref('content')

// 简历列表数据
const resumeList = ref([])
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 筛选条件
const filters = reactive({
  keyword: '',
  jdId: '',
  scoreBucket: '',
  scoreRange: [0, 100],
  dateRange: ''
})

// 上传相关
const uploadRef = ref(null)
const fileList = ref([])
const pendingFiles = ref([])
const scoring = ref(false)
const scoringStep = ref(1)
const scoringProgress = ref(0)
let scoringTimer = null
const uploadUrl = ref('/api/v1/hr-workflows/evaluate')
const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${authStore.token}`
}))
const uploadData = ref({})

// 导出相关
const exportLoading = ref(false)
const exportProgress = ref(0)

// JD相关数据
const jdList = ref([])
const jdListLoading = ref(false)
const selectedJDId = ref('')
const scoringCriteriaMap = ref({})


// 筛选所有简历数据
const filterAllResumes = () => {
  let filtered = allResumeList.value

  // 关键词搜索
  if (filters.keyword) {
    const keyword = filters.keyword.toLowerCase()
    filtered = filtered.filter(resume => 
      resume.name?.toLowerCase().includes(keyword) ||
      resume.currentPosition?.toLowerCase().includes(keyword) ||
      resume.school?.toLowerCase().includes(keyword) ||
      resume.skills?.some(skill => skill.toLowerCase().includes(keyword))
    )
  }

  // 工作经验筛选已移除

  // 分数区间筛选（按 total_score 映射的 matchScore）
  if (filters.scoreBucket) {
    const s = filters.scoreBucket
    filtered = filtered.filter(resume => {
      const sc = Number(resume.matchScore || 0)
      if (s === '60分以上') return sc >= 60
      if (s === '70分以上') return sc >=70
      if (s === '80分以上') return sc >= 80
      if (s === '90分以上') return sc >= 90
      return true
    })
  }

  // 按创建时间筛选
  if (filters.dateRange) {
    const now = new Date()
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const inRange = (d) => {
      const dt = d ? new Date(d) : null
      if (!dt || isNaN(dt.getTime())) return false
      const diffMs = now.getTime() - dt.getTime()
      const oneDay = 24 * 60 * 60 * 1000
      if (filters.dateRange === 'today') {
        return dt >= startOfToday
      }
      if (filters.dateRange === 'last3') {
        return diffMs <= 3 * oneDay
      }
      if (filters.dateRange === 'last7') {
        return diffMs <= 7 * oneDay
      }
      if (filters.dateRange === 'last30') {
        return diffMs <= 30 * oneDay
      }
      return true
    }
    filtered = filtered.filter(resume => inRange(resume.createdAt || resume.created_at))
  }


  // 评分范围筛选
  filtered = filtered.filter(resume => 
    resume.matchScore >= filters.scoreRange[0] && 
    resume.matchScore <= filters.scoreRange[1]
  )

  // 按JD筛选
  if (filters.jdId) {
    filtered = filtered.filter(resume => String(resume.jobDescriptionId || '') === String(filters.jdId))
  }

  // 确保筛选后的列表仍然按创建时间降序排序
  return filtered.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

// 计算属性 - 当前页显示的简历列表
const filteredResumeList = computed(() => {
  const allFiltered = filterAllResumes()
  
  // 更新分页总数
  pagination.total = allFiltered.length
  
  // 返回当前页的数据
  const startIndex = (pagination.page - 1) * pagination.size
  const endIndex = startIndex + pagination.size
  return allFiltered.slice(startIndex, endIndex)
})

const formattedResumeContent = computed(() => {
  if (!selectedResume.value?.resumeContent) return ''
  return marked(selectedResume.value.resumeContent)
})

// 方法
const selectionMap = reactive({})
const selectedIds = ref([])
const selectAll = ref(false)

const onItemSelectChange = (resume) => {
  const checked = !!selectionMap[resume.id]
  const idx = selectedIds.value.indexOf(resume.id)
  if (checked && idx === -1) selectedIds.value.push(resume.id)
  if (!checked && idx !== -1) selectedIds.value.splice(idx, 1)
}

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = filteredResumeList.value.map(r => r.id)
    filteredResumeList.value.forEach(r => selectionMap[r.id] = true)
  } else {
    selectedIds.value = []
    Object.keys(selectionMap).forEach(k => selectionMap[k] = false)
  }
}

const exportSelected = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要导出的简历')
    return
  }
  
  exportLoading.value = true
  exportProgress.value = 0
  
  try {
    // 模拟进度条动画
    const progressTimer = setInterval(() => {
      if (exportProgress.value < 90) {
        exportProgress.value += 10
      }
    }, 200)
    
    const response = await hrWorkflowsApi.exportZipResumes(selectedIds.value)
    
    clearInterval(progressTimer)
    exportProgress.value = 100
    
    // 创建 Blob 并下载
    const blob = new Blob([response], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ts = new Date().toISOString().slice(0,19).replace(/[:T]/g, '-')
    a.download = `简历附件导出-${ts}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    ElMessage.success('简历附件导出成功')
    
    // 重置进度条
    setTimeout(() => {
      exportLoading.value = false
      exportProgress.value = 0
    }, 1000)
    
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('简历附件导出失败，请重试')
    exportLoading.value = false
    exportProgress.value = 0
  }
}

const refreshResumeList = () => {
  pagination.page = 1
  fetchResumeList()
}

// 存储所有简历数据的变量
const allResumeList = ref([])

const fetchResumeList = async () => {
  try {
    loading.value = true
    // 一次性获取所有简历数据，不进行分页
    const params = {
      skip: 0,
      limit: 1000 // 获取足够多的数据
    }
    
    console.log('获取简历列表，参数:', params)
    const response = await resumeApi.getResumeHistory(params)
    console.log('完整的API响应:', response)
    console.log('后端返回的简历数据:', response)

    if (response && Array.isArray(response.items)) {
      // 映射后端数据到前端格式
      allResumeList.value = response.items.map(item => ({
        id: item.id,
        name: item.candidate_name,
        currentPosition: item.candidate_position,
        experience: item.work_years,
        education: item.education_level,
        age: item.candidate_age,
        gender: item.candidate_gender,
        school: item.school,
        matchScore: (typeof item.total_score === 'number' ? item.total_score : Number(item.total_score || 0)),
        skills: item.skills || [],
        highlights: item.highlights || [],
        resumeContent: item.resume_content,
        originalFilename: item.original_filename,
        resume_content: item.resume_content,
        fileType: item.file_type,
        evaluationMetrics: item.evaluation_metrics || [],
        createdAt: item.created_at,
        jobDescriptionId: item.job_description_id
      }))
      
      // 按创建时间降序排列
      allResumeList.value.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      console.log('排序后的所有简历列表:', allResumeList.value)
      
      // 设置总数为所有简历的数量
      pagination.total = response.total || allResumeList.value.length
      
      // 更新当前页显示的简历列表
updateCurrentPageResumes()
    } else {
      allResumeList.value = []
      resumeList.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('获取简历列表失败:', error)
    ElMessage.error('获取简历列表失败')
    allResumeList.value = []
    resumeList.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

// 更新当前页显示的简历列表
const updateCurrentPageResumes = () => {
  const allFiltered = filterAllResumes()
  
  // 更新分页总数
  pagination.total = allFiltered.length
  
  // 确保当前页不超过最大页数
  const maxPage = Math.ceil(allFiltered.length / pagination.size)
  if (pagination.page > maxPage && maxPage > 0) {
    pagination.page = maxPage
  }
  
  // 设置当前页显示的简历
  const startIndex = (pagination.page - 1) * pagination.size
  const endIndex = startIndex + pagination.size
  resumeList.value = allFiltered.slice(startIndex, endIndex)
}

// 获取JD列表
const fetchJDList = async () => {
  try {
    jdListLoading.value = true
    const response = await jdApi.getJDList({
      page: 1,
      size: 100, // 获取所有可用的JD
      // status_filter: 'published' // 只获取已发布的JD
    })

    if (response && Array.isArray(response.items)) {
      jdList.value = response.items
      // 批量获取所有JD的评分标准状态
      await fetchScoringCriteriaStatus(response.items)
    } else {
      jdList.value = []
    }
  } catch (error) {
    console.error('获取JD列表失败:', error)
    ElMessage.error('获取JD列表失败')
    jdList.value = []
  } finally {
    jdListLoading.value = false
  }
}

// 批量获取评分标准状态
const fetchScoringCriteriaStatus = async (jdItems) => {
  try {
    const map = {}
    // 并行请求所有JD的评分标准
    const results = await Promise.allSettled(
      jdItems.map(jd => scoringCriteriaApi.getScoringCriteriaByJD(jd.id))
    )
    results.forEach((result, index) => {
      const jdId = jdItems[index].id
      if (result.status === 'fulfilled' && result.value?.items?.length > 0) {
        map[jdId] = true
      } else {
        map[jdId] = false
      }
    })
    scoringCriteriaMap.value = map
  } catch (error) {
    console.error('获取评分标准状态失败:', error)
  }
}

const selectResume = (resume) => {
  selectedResume.value = resume
  activeTab.value = 'content'
}

const viewResumeDetail = (resume) => {
  selectResume(resume)
}

const deleteResume = async (resume) => {
  try {
    console.log('删除简历:', resume)
    await ElMessageBox.confirm(
      `确定要删除 ${resume.name} 的简历吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await resumeApi.deleteResume(resume.id)
    ElMessage.success('删除成功')
    
    // 如果删除的是当前选中的简历，清空选中状态
    if (selectedResume.value?.id === resume.id) {
      selectedResume.value = null
    }
    
    await fetchResumeList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除简历失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleSearch = () => {
  // 重置到第一页
  pagination.page = 1
  // 更新当前页显示的简历列表
  updateCurrentPageResumes()
}

const applyFilters = () => {
  // 重置到第一页
  pagination.page = 1
  // 更新当前页显示的简历列表
  updateCurrentPageResumes()
}

const resetFilters = () => {
  filters.keyword = ''
  filters.scoreBucket = ''
  filters.scoreRange = [0, 100]
  filters.dateRange = ''
  // 重置到第一页
  pagination.page = 1
  // 更新当前页显示的简历列表
  updateCurrentPageResumes()
}

// 操作按钮处理函数
const handleReject = async () => {
  if (!selectedResume.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要将候选人 ${selectedResume.value.name} 标记为不通过吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 调用API更新简历状态
    await resumeApi.updateResumeStatus(selectedResume.value.id, 'rejected')
    ElMessage.success('已标记为不通过')
    
    // 刷新列表
    await fetchResumeList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('操作失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

const handleInterview = async () => {
  if (!selectedResume.value) return

  try {
    await ElMessageBox.confirm(
      `确定要将候选人 ${selectedResume.value.name} 安排面试吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info',
      }
    )

    // 调用API更新简历状态
    await resumeApi.updateResumeStatus(selectedResume.value.id, 'interview')
    ElMessage.success('已安排面试')

    // 刷新列表
    await fetchResumeList()

    // 跳转到智能面试页面
    await router.push('/recruitment/smart-interview')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('操作失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  updateCurrentPageResumes()
}

const handlePageChange = (page) => {
  pagination.page = page
  updateCurrentPageResumes()
}

// 上传相关方法
const beforeUpload = (file) => {
  const isValidType = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(file.type)
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isValidType) {
    ElMessage.error('只能上传 PDF、DOC、DOCX 格式的文件!')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }

  return true
}

const handleFileChange = (uploadFile) => {
  pendingFiles.value = uploadFile ? [uploadFile] : []
}

const startScoringTimer = () => {
  scoringStep.value = 1
  scoringProgress.value = 0
  let progress = 0

  scoringTimer = setInterval(() => {
    progress += Math.random() * 15 + 5
    if (progress >= 90) {
      progress = 90
      clearInterval(scoringTimer)
    }
    scoringProgress.value = Math.floor(progress)

    if (progress >= 60 && scoringStep.value < 3) {
      scoringStep.value = 3
    } else if (progress >= 25 && scoringStep.value < 2) {
      scoringStep.value = 2
    }
  }, 500)
}

const stopScoringTimer = () => {
  if (scoringTimer) {
    clearInterval(scoringTimer)
    scoringTimer = null
  }
  scoringProgress.value = 100
  scoringStep.value = 3
}

const handleUploadSuccess = (response) => {
  stopScoringTimer()
  uploading.value = false
  scoring.value = false
  showUploadDialog.value = false
  fileList.value = []

  // 后端直接返回评价结果数据，检查是否有id字段表示成功
  if (response && response.id) {
    ElMessage.success('简历评分完成')
    fetchResumeList()
  } else {
    ElMessage.error('上传失败：返回数据格式错误')
  }
}

const handleUploadError = (error) => {
  stopScoringTimer()
  uploading.value = false
  scoring.value = false
  console.error('上传失败:', error)
  ElMessage.error('评分失败，请重试')
}

// 打开上传弹窗
const openUploadDialog = () => {
  selectedJDId.value = ''
  fileList.value = []
  pendingFiles.value = []
  uploadData.value = {}
  scoring.value = false
  scoringStep.value = 1
  scoringProgress.value = 0
  showUploadDialog.value = true
}

const confirmUpload = async () => {
  // 检查是否选择了JD
  if (!selectedJDId.value) {
    ElMessage.warning('请先选择对应的JD')
    return
  }
  if (pendingFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  scoring.value = true
  startScoringTimer()
  try {
    const file = pendingFiles.value[0].raw
    const formData = new FormData()
    formData.append('file', file)
    formData.append('job_description_id', selectedJDId.value)

    const token = authStore.token
    const response = await fetch('/api/v1/hr-workflows/evaluate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    handleUploadSuccess(data)
  } catch (error) {
    handleUploadError(error)
  }
}

// 工具方法
const getScoreType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

const getScoreColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const formatExperience = (years) => {
  if (years === null || years === undefined) return '未填写'
  const y = Number(years)
  if (Number.isNaN(y)) return '未填写'
  if (y === 0) return '应届生'
  return `${y}年`
}

const getMetricScoreType = (score, max) => {
  const percentage = (score / max) * 100
  if (percentage >= 80) return 'success'
  if (percentage >= 60) return 'warning'
  return 'danger'
}


// 日期格式化（到天）
const formatDateDay = (dateStr) => {
  if (!dateStr) return ''
  try {
    const dt = new Date(dateStr)
    if (isNaN(dt.getTime())) return ''
    const y = dt.getFullYear()
    const m = String(dt.getMonth() + 1).padStart(2, '0')
    const d = String(dt.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  } catch (e) {
    return ''
  }
}

// 生命周期
onMounted(() => {
  fetchResumeList()
  fetchJDList()
})

onUnmounted(() => {
  stopScoringTimer()
})
</script>

<style lang="scss" scoped>
.resume-screening {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
}

.resume-screening::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 20px 20px;
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
  align-items: center;
  margin-bottom: 24px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  
  .header-left {
    .page-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 8px 0;
    }

    .page-description {
      color: #606266;
      margin: 0;
      font-size: 14px;
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
}

.resume-list-panel {
  width: 400px;
  height: 600px;
  flex-shrink: 0;
  
  .list-card {
    display: flex;
    flex-direction: column;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    
    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 0;
    }
  }
  
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .list-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .filters-section {
    display: flex;
    gap: 10px;
    padding: 16px;
    border-bottom: 1px solid #ebeef5;
    flex-wrap: wrap;
  }
  
  .resume-list-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    max-height: 600px;
  }
  
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
  }

  .resume-items {
    flex: 1;
    max-height: 500px;
    overflow-y: scroll;
    padding: 0 16px;
    margin: 0 -16px;
    
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
  }
  
  .resume-item {
    padding: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    cursor: pointer;
    transition: all 0.3s;
    border-radius: 12px;
    margin-bottom: 8px;
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
    
    .resume-item-header {
      .candidate-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .candidate-name {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
          margin: 0;
        }
        
        .score-badge {
          flex-shrink: 0;
        }
      }
    }
    
    .resume-item-content {
      .position-info {
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        .position-text {
          color: #606266;
          font-size: 14px;
        }
        .created-date {
          color: #909399;
          font-size: 12px;
        }
      }
      
      .resume-actions {
        display: flex;
        gap: 8px;
        
        .el-button {
          flex: 1;
        }
      }
    }
    .item-checkbox { margin-right: 8px; }
  }
  
  .pagination-container {
    padding: 16px;
    border-top: 1px solid #ebeef5;
    display: flex;
    justify-content: center;
  }
}

.resume-detail-panel {
  flex: 1;
  min-width: 0;
  
  .welcome-container {
    height: 100%;
    
    .welcome-card {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.95);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      
      .welcome-content {
        text-align: center;
        
        .welcome-icon {
          margin-bottom: 20px;
          color: #c0c4cc;
        }
        
        h2 {
          color: #303133;
          margin-bottom: 12px;
        }
        
        p {
          color: #606266;
          margin-bottom: 24px;
        }
      }
    }
  }
  
  .resume-detail-content {
    height: 100%;
    display: flex;
    flex-direction: column;
    
    .detail-header {
      background: rgba(255, 255, 255, 0.95);
      padding: 24px;
      border-radius: 16px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      
      .candidate-profile {
        display: flex;
        align-items: center;
        gap: 16px;
        
        .profile-info {
          h3 {
            margin: 0 0 4px 0;
            color: #303133;
            font-size: 20px;
          }
          
          .current-position {
            color: #606266;
            margin: 0 0 8px 0;
            font-size: 14px;
          }
          
          .profile-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #909399;
            margin-bottom: 16px;
            
            .meta-divider {
              color: #dcdfe6;
            }
          }
          
          .action-buttons {
            display: flex;
            gap: 12px;
            
            .el-button {
              border-radius: 8px;
              font-weight: 500;
              transition: all 0.3s ease;
              
              &.el-button--danger {
                background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                border: none;
                
                &:hover {
                  background: linear-gradient(135deg, #ff5252, #e53935);
                  transform: translateY(-1px);
                  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
                }
              }
              
              &.el-button--primary {
                background: linear-gradient(135deg, #667eea, #764ba2);
                border: none;
                
                &:hover {
                  background: linear-gradient(135deg, #5a6fd8, #6a4190);
                  transform: translateY(-1px);
                  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                }
              }
            }
          }
        }
      }
      
      .score-section {
        text-align: center;
        
        .score-display {
          margin-bottom: 8px;
          
          .score-text {
            font-size: 14px;
            font-weight: 600;
          }
        }
        
        .score-label {
          margin: 0;
          font-size: 12px;
          color: #909399;
        }
      }
    }
    
    .detail-main {
      flex: 1;
      background: rgba(255, 255, 255, 0.95);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      min-height: 0;
      padding: 20px;
      
      .two-column-layout {
        display: flex;
        gap: 20px;
        height: 100%;
        
        .left-column,
        .right-column {
          flex: 1;
          display: flex;
          flex-direction: column;
          background: rgba(255, 255, 255, 0.8);
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.3);
          overflow: hidden;
        }
        
        .column-header {
          background: rgba(102, 126, 234, 0.1);
          padding: 16px 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.2);
          
          .column-title {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 8px;
            
            .el-icon {
              font-size: 18px;
            }
          }
        }
        
        .column-content {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          
          &::-webkit-scrollbar {
            width: 6px;
          }
          
          &::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
          }
          
          &::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.3);
            border-radius: 3px;
            
            &:hover {
              background: rgba(102, 126, 234, 0.5);
            }
          }
        }
      }
    }
  }
}

.basic-info-section {
  .info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
    
    .info-item {
      display: flex;
      
      label {
        font-weight: 600;
        color: #606266;
        width: 80px;
        flex-shrink: 0;
      }
      
      span {
        color: #303133;
      }
    }
  }
  
  .skills-section,
  .highlights-section {
    margin-bottom: 24px;
    
    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
    }
    
    .skills-tags,
    .highlights-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    
    .skill-tag,
    .highlight-tag {
      margin: 0;
    }
  }
}

.resume-content-section {
  .content-display {
    line-height: 1.6;
    color: #303133;
    
    :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
      color: #303133;
      margin-top: 24px;
      margin-bottom: 12px;
    }
    
    :deep(p) {
      margin-bottom: 12px;
    }
    
    :deep(ul), :deep(ol) {
      padding-left: 20px;
      margin-bottom: 12px;
    }
  }
}

.evaluation-section {
  .evaluation-content {
    .evaluation-item {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      
      .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        
        .metric-name {
          margin: 0;
          color: #303133;
          font-size: 16px;
        }
      }
      
      .metric-reason {
        p {
          margin: 0;
          color: #606266;
          line-height: 1.6;
        }
      }
    }
  }
}

.loading-container,
.empty-container {
  padding: 40px 20px;
  text-align: center;
}

.upload-section {
  .jd-selector-section {
    margin-bottom: 20px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    :deep(.el-form-item__label) {
      color: #333;
      font-weight: 500;
    }

    :deep(.el-select) {
      .el-input__wrapper {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #dcdfe6;
        border-radius: 6px;

        &:hover {
          border-color: #c0c4cc;
        }

        &.is-focus {
          border-color: #409eff;
          box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
        }
      }
    }
  }

  .upload-dragger {
    width: 100%;
  }
}

.scoring-section {
  padding: 40px 20px;
  text-align: center;

  .scoring-status {
    .scoring-icon {
      margin-bottom: 20px;
    }

    .scoring-title {
      margin: 0 0 12px 0;
      font-size: 20px;
      font-weight: 700;
      color: #303133;
    }

    .scoring-desc {
      margin: 0 0 32px 0;
      color: #909399;
      font-size: 14px;
    }

    .scoring-steps {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 28px;
      padding: 0 40px;

      .scoring-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;

        .step-dot {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          font-weight: 600;
          background: #e4e7ed;
          color: #909399;
          transition: all 0.4s ease;
        }

        .step-label {
          font-size: 12px;
          color: #909399;
          white-space: nowrap;
          transition: color 0.4s ease;
        }

        &.active {
          .step-dot {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: #fff;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            animation: pulse-step 1.5s infinite;
          }
          .step-label {
            color: #667eea;
            font-weight: 600;
          }
        }

        &.done {
          .step-dot {
            background: #10b981;
            color: #fff;
            animation: none;
          }
          .step-label {
            color: #10b981;
          }
        }
      }

      .step-line {
        flex: 1;
        height: 2px;
        background: #e4e7ed;
        margin: 0 12px;
        margin-bottom: 24px;
        transition: background 0.4s ease;

        &.active {
          background: linear-gradient(135deg, #667eea, #764ba2);
        }
      }
    }

    .scoring-progress {
      padding: 0 60px;
    }
  }
}

@keyframes pulse-step {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
  50% {
    box-shadow: 0 4px 24px rgba(102, 126, 234, 0.7);
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
  }
  
  .resume-list-panel {
    width: 100%;
    height: 400px;
  }
  
  .resume-detail-panel {
    height: 600px;
  }
}

.export-progress {
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.export-progress-text {
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
  text-align: center;
}

@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .filters-section {
    flex-direction: column;
    gap: 8px;
  }
  
  .detail-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .info-grid {
    grid-template-columns: 1fr !important;
  }
}
</style>