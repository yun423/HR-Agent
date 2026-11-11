<template>
  <div class="smart-interview">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><VideoCamera /></el-icon>
            智能面试
          </h1>
          <p class="page-subtitle">
            AI辅助面试，提供智能问题推荐和候选人评估
          </p>
        </div>
        
        <!-- 筛选区域 -->
        <div class="filter-section">
          <div class="filter-row">
            <div class="filter-item">
              <label class="filter-label">姓名筛选</label>
              <el-input
                v-model="filters.name"
                placeholder="请输入候选人姓名"
                clearable
                size="default"
                style="width: 200px"
                @input="handleFilterChange"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            
            <div class="filter-item">
              <label class="filter-label">岗位筛选</label>
              <el-select
                v-model="filters.position"
                placeholder="请选择岗位"
                clearable
                size="default"
                style="width: 200px"
                @change="handleFilterChange"
              >
                <el-option
                  v-for="position in availablePositions"
                  :key="position"
                  :label="position"
                  :value="position"
                />
              </el-select>
            </div>
            
            <div class="filter-actions">
              <el-button @click="clearFilters" size="default">
                <el-icon><RefreshLeft /></el-icon>
                重置筛选
              </el-button>
              <el-tag v-if="filteredCandidatesCount !== totalCandidatesCount" type="info" size="default">
                已筛选 {{ filteredCandidatesCount }} / {{ totalCandidatesCount }} 人
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主要内容区域：左右分栏布局 -->
    <div class="main-content">
      <!-- 左侧：候选人列表 -->
      <div class="left-panel">
        <el-card class="candidate-list-card">
          <template #header>
            <div class="card-header">
              <span>候选人列表</span>
              <el-button size="small" @click="refreshCandidates">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <div class="candidate-list">
            <div 
              v-for="candidate in filteredCandidates" 
              :key="candidate.id"
              class="candidate-item"
              :class="{ active: selectedCandidate?.id === candidate.id }"
              @click="selectCandidate(candidate)"
            >
              <!-- 候选人基本信息 -->
              <div class="candidate-info">
                <div class="candidate-header">
                  <h3 class="candidate-name">{{ candidate.name }}</h3>
                  <el-tag :type="getScoreType(candidate.totalScore)" size="small">
                    {{ candidate.totalScore }}分
                  </el-tag>
                </div>
                <p class="candidate-position">{{ candidate.position }}</p>
                <div class="candidate-details">
                  <span class="detail-item">{{ candidate.experience }}年经验</span>
                  <span class="detail-item">{{ candidate.education }}</span>
                  <span class="detail-item">{{ candidate.location }}</span>
                </div>
              </div>



              <!-- 操作按钮 -->
              <div class="candidate-actions">
                <el-button
                  size="small"
                  type="primary"
                  @click.stop="generateInterviewPlan(candidate)"
                  :loading="generatingPlan && selectedCandidate?.id === candidate.id"
                >
                  生成面试方案
                </el-button>
                <el-button size="small" @click.stop="viewResume(candidate)">
                  查看简历
                </el-button>
                <el-button size="small" type="danger" @click.stop="deleteInterviewPlanForCandidate(candidate)">
                  删除方案
                </el-button>
              </div>
            </div>
            
            <!-- 空状态 -->
            <div v-if="filteredCandidates.length === 0" class="empty-candidates">
              <el-empty 
                description="没有找到符合条件的候选人"
                :image-size="120"
              >
                <el-button type="primary" @click="clearFilters">
                  清除筛选条件
                </el-button>
              </el-empty>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：Tab页内容 -->
      <div class="right-panel">
        <el-card class="content-card">
          <el-tabs v-model="activeTab" class="content-tabs">
            <!-- 简历预览Tab -->
            <el-tab-pane label="简历预览" name="resume">
              <div class="resume-preview">
                <div v-if="!selectedCandidate" class="empty-state">
                  <el-empty description="请选择一个候选人查看简历" />
                </div>
                <div v-else class="resume-detail-content">
                  <!-- 详情头部 -->
                  <div class="detail-header">
                    <div class="candidate-profile">
                      <el-avatar :size="60" :src="selectedCandidate.avatar">
                        {{ selectedCandidate.name?.charAt(0) }}
                      </el-avatar>
                      <div class="profile-info">
                        <h3>{{ selectedCandidate.name }}</h3>
                        <p class="current-position">{{ selectedCandidate.position }}</p>
                        <div class="profile-meta">
                          <span class="meta-item">{{ selectedCandidate.experience }}</span>
                          <span class="meta-divider">|</span>
                          <span class="meta-item">{{ selectedCandidate.education }}</span>
                          <span class="meta-divider">|</span>
                          <span class="meta-item">{{ selectedCandidate.originalData?.candidate_age || '未知' }}岁</span>
                        </div>
                      </div>
                    </div>
                    <div class="score-section">
                      <div class="score-display">
                        <el-progress
                          type="circle"
                          :percentage="selectedCandidate.totalScore"
                          :color="getScoreColor(selectedCandidate.totalScore)"
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
                            <div v-if="selectedCandidate.originalData?.evaluation_metrics && selectedCandidate.originalData.evaluation_metrics.length > 0" class="evaluation-content">
                              <div
                                v-for="metric in selectedCandidate.originalData.evaluation_metrics"
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
            </el-tab-pane>

            <!-- 面试方案预览Tab -->
            <el-tab-pane label="面试方案" name="interview-plan">
              <div class="interview-plan-preview">
                
                
                <div v-if="!selectedCandidate" class="empty-state">
                  <el-empty description="请选择一个候选人并生成面试方案" />
                </div>
                <div v-else-if="!interviewPlan" class="empty-state">
                    <el-empty description="暂无面试方案，请点击生成面试方案按钮" />
                  </div>
                <div v-else class="interview-plan-content">
                  <!-- 方案头部 -->
                  <div class="plan-header">
                    <div class="header-info">
                      <h2>{{ interviewPlan.candidateName }} - 面试方案</h2>
                      <p class="position">{{ interviewPlan.position }}</p>
                      <p class="generated-time">生成时间：{{ interviewPlan.generatedAt }}</p>
                    </div>
                    <div class="header-tags">
                      <el-tag type="success" size="large">AI自动生成</el-tag>
                      <el-tag v-if="interviewPlan.isGenerating" type="warning" size="large">
                        <el-icon class="is-loading"><Loading /></el-icon>
                        生成中...
                      </el-tag>
                      <el-tag v-if="isEditingPlan" type="info" size="large">编辑模式</el-tag>
                    </div>
                  </div>

                  <!-- 操作按钮 - 移到内容上方 -->
                  <div class="plan-actions">
                    <div class="action-group">
                      <!-- 统一的保存方案按钮 -->
                      <el-button 
                        v-if="interviewPlan.content" 
                        type="success" 
                        @click="saveInterviewPlan" 
                        :loading="savingPlan"
                      >
                        <el-icon><DocumentAdd /></el-icon>
                        保存方案
                      </el-button>
                      
                      <!-- 已保存状态提示 -->
                      <el-tag 
                        v-if="!isEditingPlan && interviewPlan.isSaved" 
                        type="success" 
                        size="large"
                      >
                        <el-icon><Check /></el-icon>
                        已保存
                      </el-tag>
                      
                      <el-button v-if="!isEditingPlan" type="primary" @click="toggleEditPlan">
                        <el-icon><Edit /></el-icon>
                        编辑方案
                      </el-button>
                      <el-button v-if="isEditingPlan" @click="cancelEditPlan">
                        <el-icon><Close /></el-icon>
                        取消编辑
                      </el-button>
                    </div>
                    <div class="action-group">
                      <el-button type="primary" @click="startInterview" :disabled="isEditingPlan">
                        <el-icon><VideoCamera /></el-icon>
                        开始面试
                      </el-button>
                      <el-dropdown @command="exportPlan" :disabled="isEditingPlan">
                        <el-button>
                          <el-icon><Download /></el-icon>
                          导出方案
                          <el-icon><ArrowDown /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="txt">导出为TXT</el-dropdown-item>
                            <el-dropdown-item command="md">导出为Markdown</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                      <el-button @click="regeneratePlan" :loading="generatingPlan" :disabled="isEditingPlan">
                        <el-icon><Refresh /></el-icon>
                        重新生成
                      </el-button>
                    </div>
                  </div>

                  <!-- 面试方案内容 -->
                  <div class="plan-section">
                    <!-- 编辑模式 -->
                    <div v-if="isEditingPlan" class="edit-container">
                      <el-input
                        v-model="editPlanContent"
                        type="textarea"
                        :rows="20"
                        placeholder="在此编辑面试方案内容..."
                        class="edit-textarea"
                      />
                    </div>
                    <!-- 预览模式 -->
                    <div v-else class="plan-content markdown-content" v-html="formattedInterviewPlan"></div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </div>

    <!-- 创建面试对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      title="创建面试" 
      width="600px"
    >
      <el-form 
        ref="createFormRef" 
        :model="createForm" 
        :rules="createRules" 
        label-width="100px"
      >
        <el-form-item label="候选人" prop="candidateName">
          <el-input v-model="createForm.candidateName" placeholder="请输入候选人姓名" />
        </el-form-item>
        
        <el-form-item label="面试职位" prop="position">
          <el-input v-model="createForm.position" placeholder="请输入面试职位" />
        </el-form-item>
        
        <el-form-item label="面试日期" prop="date">
          <el-date-picker
            v-model="createForm.date"
            type="date"
            placeholder="选择面试日期"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="面试时间" prop="time">
          <el-time-picker
            v-model="createForm.time"
            placeholder="选择面试时间"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="面试官" prop="interviewer">
          <el-input v-model="createForm.interviewer" placeholder="请输入面试官姓名" />
        </el-form-item>
        
        <el-form-item label="面试类型" prop="type">
          <el-radio-group v-model="createForm.type">
            <el-radio label="技术面试">技术面试</el-radio>
            <el-radio label="HR面试">HR面试</el-radio>
            <el-radio label="综合面试">综合面试</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="备注">
          <el-input 
            v-model="createForm.notes" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createInterview">确定</el-button>
      </template>
    </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoCamera,
  Search,
  Edit,
  Check,
  Close,
  DocumentAdd,
  Loading,
  Download,
  ArrowDown
} from '@element-plus/icons-vue'
import { resumeApi } from '@/api/resume'
import { hrWorkflowsApi } from '@/api/hrWorkflows'
import { marked } from 'marked'

// 响应式数据
const activeTab = ref('resume')
const selectedCandidate = ref(null)
const generatingPlan = ref(false)
const interviewPlan = ref(null)

// 编辑相关数据
const isEditingPlan = ref(false)
const editPlanContent = ref('')
const savingPlan = ref(false)
const originalPlanContent = ref('')

// 筛选相关数据
const filters = reactive({
  name: '',
  position: '',
  status: 'interview' // 默认只显示面试状态的简历
})

// 加载状态
const loading = ref(false)

// 候选人数据
const candidates = ref([])

// 计算属性
const availablePositions = computed(() => {
  const positions = [...new Set(candidates.value.map(c => c.position))]
  return positions.sort()
})

const filteredCandidates = computed(() => {
  return candidates.value.filter(candidate => {
    const nameMatch = !filters.name || 
      candidate.name.toLowerCase().includes(filters.name.toLowerCase())
    
    const positionMatch = !filters.position || 
      candidate.position === filters.position
    
    return nameMatch && positionMatch
  })
})

const filteredCandidatesCount = computed(() => filteredCandidates.value.length)
const totalCandidatesCount = computed(() => candidates.value.length)

// 格式化简历内容
const formattedResumeContent = computed(() => {
  if (!selectedCandidate.value?.originalData?.resume_content) return ''
  return marked(selectedCandidate.value.originalData.resume_content)
})

// 格式化面试方案内容
const formattedInterviewPlan = computed(() => {
  if (!interviewPlan.value?.content) return ''
  
  // 清理内容，移除可能包含的SSE事件数据
  let cleanedContent = interviewPlan.value.content
  
  // 如果内容包含workflow_started等事件数据，记录警告并返回空内容
  if (cleanedContent.includes('"event": "workflow_started"') || 
      cleanedContent.includes('"conversation_id"') ||
      cleanedContent.includes('"message_id"')) {
    console.warn('面试方案内容包含SSE事件数据，需要清理:', cleanedContent)
    return marked('正在生成面试方案，请稍候...')
  }
  
  return marked(cleanedContent)
})

// 方法
const getScoreType = (score) => {
  if (score >= 90) return 'success'
  if (score >= 80) return 'warning'
  if (score >= 70) return 'info'
  return 'danger'
}

const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#e6a23c'
  if (score >= 70) return '#409eff'
  return '#f56c6c'
}

const getMetricScoreType = (score, max) => {
  const percentage = (score / max) * 100
  if (percentage >= 80) return 'success'
  if (percentage >= 60) return 'warning'
  if (percentage >= 40) return 'info'
  return 'danger'
}

// 获取简历数据
const fetchCandidates = async () => {
  try {
    loading.value = true
    const response = await resumeApi.getResumeHistory({
      status: filters.status,
      limit: 100 // 获取更多数据
    })

    // 转换数据格式以适配现有的UI
    let mappedCandidates = response.items.map(resume => {
      // 从evaluation_metrics中提取评分数据
      const getMetricScore = (metricName) => {
        if (!resume.evaluation_metrics || !Array.isArray(resume.evaluation_metrics)) {
          return 0
        }
        const metric = resume.evaluation_metrics.find(m => m.name === metricName)
        if (!metric) return 0
        // 将分数转换为5分制（假设max为25分）
        return Math.min(5, Math.max(0, Math.round((metric.score / metric.max) * 5)))
      }

      return {
        id: resume.id,
        name: resume.candidate_name || '未知',
        position: resume.candidate_position || '未知职位',
        experience: resume.work_years || '未知',
        education: resume.education_level || '未知',
        location: '未知', // 简历数据中没有地址信息
        totalScore: resume.total_score || 0,
        status: resume.status,
        scores: {
         // 动态生成评分维度映射
          ...(() => {
            const dynamicScores = {}
            if (resume.evaluation_metrics && Array.isArray(resume.evaluation_metrics)) {
              resume.evaluation_metrics.forEach(metric => {
                // 使用维度名称作为key，转换为camelCase格式
                const key = metric.name.replace(/匹配度|经验|背景|技能|素质/g, '')
                  .replace(/^[A-Z]/, m => m.toLowerCase())
                  .replace(/[-_\s]+(.)?/g, (_, c) => c ? c.toUpperCase() : '')
                dynamicScores[key] = Math.min(5, Math.max(0, Math.round((metric.score / metric.max) * 5)))
              })
            }
            return dynamicScores
          })()
        },
        // 保存原始评价维度数据用于详细展示
        evaluationMetrics: resume.evaluation_metrics || [],
        // 只显示五大类评价维度：学历、工作经验、技能、项目经验、综合素质
        fiveMajorMetrics: (() => {
          if (!resume.evaluation_metrics || !Array.isArray(resume.evaluation_metrics)) {
            return []
          }
          
          // 定义五大类关键词映射
          const categoryKeywords = {
            '学历': ['学历', '教育', '学位', '学历匹配度'],
            '工作经验': ['工作经验', '工作经历', '经验', '工作经验匹配度'],
            '技能': ['技能', '技术', '能力', '技能匹配度'],
            '项目经验': ['项目', '项目经验', '项目经历', '项目经验匹配度'],
            '综合素质': ['综合素质', '综合能力', '素质', '综合匹配度']
          }
          
          // 筛选出属于五大类的评价维度
          const majorMetrics = []
          const processedCategories = new Set()
          
          // 遍历所有评价维度，找到属于五大类的维度
          resume.evaluation_metrics.forEach(metric => {
            const metricName = metric.name
            
            // 检查是否属于五大类
            for (const [category, keywords] of Object.entries(categoryKeywords)) {
              if (keywords.some(keyword => metricName.includes(keyword))) {
                // 如果这个类别还没有处理过，添加它
                if (!processedCategories.has(category)) {
                  majorMetrics.push({
                    name: category,
                    score: metric.score,
                    max: metric.max,
                    reason: metric.reason
                  })
                  processedCategories.add(category)
                }
                return
              }
            }
          })
          
          // 如果没有匹配到任何类别，返回原始数据的前5项
          if (majorMetrics.length === 0) {
            return resume.evaluation_metrics.slice(0, 5)
          }
          
          return majorMetrics
        })(),
        resume: {
          personalInfo: {
            name: resume.candidate_name || '未知',
            age: resume.candidate_age || '未知',
            phone: '***',
            email: '***',
            location: '未知'
          },
          workExperience: [],
          education: [],
          skills: [],
          content: resume.resume_content || ''
        },
        originalData: resume, // 保存原始数据
        updatedAt: resume.updated_at // 添加更新时间用于排序
      }
    })

    // 按更新时间倒序排列，确保最新更新为interview状态的候选人排在前面
    mappedCandidates.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))

    candidates.value = mappedCandidates

  } catch (error) {
    console.error('获取候选人数据失败:', error)
    ElMessage.error('获取候选人数据失败')
  } finally {
    loading.value = false
  }
}

// 删除面试方案
const deleteInterviewPlanForCandidate = async (candidate) => {
  try {
    // 先查询该候选人是否有面试方案
    const response = await hrWorkflowsApi.getInterviewPlanList({
      resume_evaluation_id: candidate.id,
      limit: 1
    })

    if (!response || !response.items || response.items.length === 0) {
      ElMessage.warning('该候选人暂无面试方案')
      return
    }

    const planId = response.items[0].id

    await ElMessageBox.confirm(
      `确定要删除候选人 "${candidate.name}" 的面试方案吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await hrWorkflowsApi.deleteInterviewPlan(planId)

    // 如果当前正在查看此候选人的面试方案，清除显示
    if (selectedCandidate.value?.id === candidate.id) {
      interviewPlan.value = null
    }

    ElMessage.success('面试方案删除成功')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('删除面试方案失败:', error)
      ElMessage.error('删除面试方案失败')
    }
  }
}

const selectCandidate = async (candidate) => {
  // 如果选择的是同一个候选人，不需要重新加载
  if (selectedCandidate.value?.id === candidate.id) {
    console.log('选择了同一个候选人，不重新加载面试方案')
    return
  }
  
  selectedCandidate.value = candidate
  activeTab.value = 'resume'
  // 清除之前的面试方案
  interviewPlan.value = null
  
  // 检查是否已有保存的面试方案
  try {
    console.log('开始获取面试方案，候选人ID:', candidate.id)
    const response = await hrWorkflowsApi.getInterviewPlanList({
      resume_evaluation_id: candidate.id,
      limit: 1
    })
    
    console.log('API响应:', response)
    console.log('响应数据:', response)
    
    if (response && response.items && response.items.length > 0) {
      const savedPlan = response.items[0]
      console.log('找到已保存的面试方案:', savedPlan)
      console.log('候选人信息:', candidate)
      interviewPlan.value = {
        id: savedPlan.id,
        candidateId: candidate.id,
        candidateName: savedPlan.candidate_name || candidate.name,
        position: savedPlan.candidate_position || candidate.position,
        title: savedPlan.title,
        content: savedPlan.content,
        status: savedPlan.status,
        createdAt: savedPlan.created_at,
        updatedAt: savedPlan.updated_at,
        isGenerating: false,
        isSaved: true
      }
      console.log('设置的面试方案对象:', interviewPlan.value)
      console.log('当前activeTab:', activeTab.value)
      // 切换到面试方案标签页
      activeTab.value = 'interview-plan'
      console.log('切换后activeTab:', activeTab.value)
      ElMessage.success(`已选择候选人：${candidate.name}，发现已保存的面试方案`)
    } else {
      ElMessage.success(`已选择候选人：${candidate.name}`)
    }
  } catch (error) {
    console.error('检查面试方案失败:', error)
    console.error('错误详情:', error.message)
    console.error('错误堆栈:', error.stack)
    ElMessage.success(`已选择候选人：${candidate.name}`)
  }
}

const refreshCandidates = async () => {
  await fetchCandidates()
  ElMessage.success('候选人列表已刷新')
}

const viewResume = (candidate) => {
  selectCandidate(candidate)
  activeTab.value = 'resume'
}

const generateInterviewPlan = async (candidate) => {
  try {
    selectedCandidate.value = candidate
    generatingPlan.value = true
    activeTab.value = 'interview-plan'
    
    // 清空之前的面试方案
    interviewPlan.value = null
    
    ElMessage.info('正在生成面试方案，请稍候...')
    
    // 调用新的API生成面试方案
    const response = await hrWorkflowsApi.generateInterviewPlanByResume({
      resume_id: candidate.id,
      stream: true
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 处理流式响应（缓冲分片并过滤控制事件）
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let planContent = ''
    let buffer = ''

    // 初始化面试方案对象
    interviewPlan.value = {
      candidateId: candidate.id,
      candidateName: candidate.name,
      position: candidate.position,
      generatedAt: new Date().toLocaleString(),
      content: '',
      isGenerating: true
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // 按流式方式解码并累积到缓冲区，避免半截JSON被渲染
        buffer += decoder.decode(value, { stream: true })

        // 事件以"\n\n"分隔，逐个消费完整事件块
        let sepIndex = buffer.indexOf('\n\n')
        while (sepIndex !== -1) {
          const eventChunk = buffer.slice(0, sepIndex)
          buffer = buffer.slice(sepIndex + 2)
          sepIndex = buffer.indexOf('\n\n')

          const lines = eventChunk.split('\n')
          for (const line of lines) {
            const l = line.trim()
            if (!l) continue

            // 调试：输出原始行数据
            if (l.startsWith('data:')) {
              console.log('原始SSE数据行:', l)
            }

            if (l.startsWith('event:') || l.startsWith('id:') || l.startsWith('retry:')) continue
            if (!l.startsWith('data: ')) continue

            const dataStr = l.slice(6).trim()
            if (!dataStr) continue
            if (dataStr === '[DONE]') break
            const lowerData = dataStr.toLowerCase()
            if (lowerData === 'ping' || lowerData.startsWith('event: ping')) continue

            try {
              const parsed = JSON.parse(dataStr)
              const evt = parsed.event || parsed.type
              const newContent = parsed.answer || parsed.content || parsed.text || ''

              // 调试日志
              if (evt && evt !== 'message') {
                console.log('SSE事件:', evt, '内容:', newContent)
              }

              if (evt && evt !== 'message' && !newContent) continue
              if (newContent) {
                planContent += newContent
                interviewPlan.value.content = planContent
              } else if (evt && evt === 'message') {
                // 如果是message事件但没有内容，记录日志
                console.log('Message事件无有效内容:', parsed)
              }
            } catch (e) {
              const lower = dataStr.toLowerCase()
              if ((lower.startsWith('{') || lower.startsWith('[')) && lower.includes('"event"')) {
                console.log('跳过SSE事件数据:', dataStr)
                continue
              }
              // 检查是否包含workflow相关关键词
              if (lower.includes('workflow') || lower.includes('conversation_id') || lower.includes('message_id')) {
                console.log('跳过workflow相关数据:', dataStr)
                continue
              }
              if (dataStr && dataStr !== '[DONE]') {
                planContent += dataStr
                interviewPlan.value.content = planContent
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }

    // 生成完成，更新状态
    if (interviewPlan.value) {
      interviewPlan.value.isGenerating = false
      if (planContent) {
        // 更新本地显示的面试方案内容，保留可能存在的ID
        const existingId = interviewPlan.value.id
        interviewPlan.value = {
          ...interviewPlan.value,
          id: existingId, // 保留现有的ID（如果有的话）
          candidateId: candidate.id,
          candidateName: candidate.name,
          position: candidate.position,
          generatedAt: new Date().toLocaleString(),
          content: planContent,
          isGenerating: false,
          isSaved: false  // 标记为未保存
        }
        ElMessage.success('面试方案生成成功！请点击保存按钮保存到数据库')
      } else {
        ElMessage.warning('未收到面试方案内容，请重试')
      }
    }
    
  } catch (error) {
    console.error('生成面试方案失败:', error)
    ElMessage.error('生成面试方案失败，请重试')
  } finally {
    generatingPlan.value = false
  }
}

const startInterview = () => {
  if (!selectedCandidate.value || !interviewPlan.value) {
    ElMessage.warning('请先选择候选人并生成面试方案')
    return
  }
  ElMessage.success(`开始面试：${selectedCandidate.value.name}`)
  // 这里可以跳转到面试界面或打开面试窗口
}

const exportPlan = (format = 'txt') => {
  if (!interviewPlan.value) {
    ElMessage.warning('暂无面试方案可导出')
    return
  }

  const plan = interviewPlan.value
  const content = `面试方案 - ${plan.candidateName}
职位：${plan.position}
生成时间：${plan.generatedAt || new Date().toLocaleString()}

${plan.content}`

  // 创建文件名
  const fileName = `面试方案_${plan.candidateName}_${new Date().toISOString().slice(0, 10)}.${format}`

  // 根据格式导出
  switch (format) {
    case 'txt':
      exportAsText(content, fileName)
      break
    case 'md':
      exportAsMarkdown(plan, fileName)
      break
    default:
      exportAsText(content, fileName)
  }

  ElMessage.success(`面试方案已导出为 ${format.toUpperCase()} 格式`)
}

// 导出为文本文件
const exportAsText = (content, fileName) => {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = fileName
  link.click()
  URL.revokeObjectURL(link.href)
}

// 导出为Markdown文件
const exportAsMarkdown = (plan, fileName) => {
  const markdownContent = `# 面试方案

## 候选人信息
- **姓名**：${plan.candidateName}
- **应聘职位**：${plan.position}
- **生成时间**：${plan.generatedAt || new Date().toLocaleString()}

## 面试方案内容
${plan.content}`

  const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = fileName
  link.click()
  URL.revokeObjectURL(link.href)
}

const regeneratePlan = () => {
  if (!selectedCandidate.value) {
    ElMessage.warning('请先选择候选人')
    return
  }
  generateInterviewPlan(selectedCandidate.value)
}

// 编辑面试方案相关方法
const toggleEditPlan = () => {
  console.log('toggleEditPlan 被调用')
  console.log('当前 interviewPlan:', interviewPlan.value)
  console.log('interviewPlan.value?.id:', interviewPlan.value?.id)
  
  if (!interviewPlan.value?.content) {
    ElMessage.warning('暂无面试方案内容可编辑')
    return
  }
  
  isEditingPlan.value = true
  originalPlanContent.value = interviewPlan.value.content
  editPlanContent.value = interviewPlan.value.content
  
  console.log('编辑模式开启后，interviewPlan.value?.id:', interviewPlan.value?.id)
}

const cancelEditPlan = () => {
  isEditingPlan.value = false
  editPlanContent.value = ''
  originalPlanContent.value = ''
}



// 统一的保存面试方案方法
const saveInterviewPlan = async () => {
  // 获取要保存的内容
  const contentToSave = isEditingPlan.value ? editPlanContent.value : interviewPlan.value?.content
  
  if (!contentToSave?.trim()) {
    ElMessage.warning('面试方案内容不能为空')
    return
  }
  
  if (!selectedCandidate.value) {
    ElMessage.warning('请先选择候选人')
    return
  }
  
  try {
    savingPlan.value = true
    
    // 根据是否有ID决定是新建还是更新
    const hasId = interviewPlan.value?.id
    console.log('保存面试方案，hasId:', hasId, 'ID:', interviewPlan.value?.id)
    
    let response
    
    if (hasId) {
      // 更新现有方案
      console.log('更新现有面试方案，ID:', interviewPlan.value.id)
      response = await hrWorkflowsApi.updateInterviewPlan(interviewPlan.value.id, {
        content: contentToSave,
        candidate_name: interviewPlan.value.candidateName,
        candidate_position: interviewPlan.value.position
      })
    } else {
      // 创建新方案
      console.log('创建新面试方案')
      response = await hrWorkflowsApi.saveGeneratedInterviewPlan({
        resume_evaluation_id: selectedCandidate.value.id,
        candidate_name: selectedCandidate.value.name,
        candidate_position: selectedCandidate.value.position,
        content: contentToSave
      })
    }
    
    console.log('保存接口响应:', response)
    console.log('响应数据:', response)
    
    if (response) {
      // 更新本地数据
      interviewPlan.value = {
        id: response.id,
        candidateId: selectedCandidate.value.id,
        candidateName: selectedCandidate.value.name,
        position: selectedCandidate.value.position,
        content: response.content || contentToSave,
        createdAt: response.created_at,
        updatedAt: response.updated_at,
        generatedAt: interviewPlan.value?.generatedAt || new Date().toLocaleString(),
        isGenerating: false,
        isSaved: true,
        savedAt: new Date().toLocaleString()
      }
      
      // 如果是编辑模式，退出编辑
      if (isEditingPlan.value) {
        isEditingPlan.value = false
        editPlanContent.value = ''
        originalPlanContent.value = ''
      }
      
      console.log('面试方案保存成功，ID:', response.id)
      console.log('更新后的 interviewPlan:', interviewPlan.value)
      
      // 强制切换到面试方案标签页以显示更新的内容
      activeTab.value = 'interview-plan'
      
      // 使用 nextTick 确保 DOM 更新
      await nextTick()
      
      ElMessage.success(hasId ? '面试方案更新成功' : '面试方案保存成功')
    } else {
      console.error('响应中没有数据:', response)
    }
  } catch (error) {
    console.error('保存面试方案失败:', error)
    ElMessage.error('保存面试方案失败，请重试')
  } finally {
    savingPlan.value = false
  }
}

// 保持向后兼容的方法
const saveGeneratedPlan = saveInterviewPlan

// 筛选相关方法
const handleFilterChange = () => {
  // 筛选变化时的处理逻辑
  if (selectedCandidate.value && !filteredCandidates.value.find(c => c.id === selectedCandidate.value.id)) {
    // 如果当前选中的候选人被筛选掉了，清除选择
    selectedCandidate.value = null
    interviewPlan.value = null
    activeTab.value = 'resume'
  }
}

const clearFilters = () => {
  filters.name = ''
  filters.position = ''
  ElMessage.success('筛选条件已重置')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchCandidates()
})
</script>

<style lang="scss" scoped>
.smart-interview {
  height: 100%;
  overflow-y: auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.page-container {
  max-width: 95%;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    
    .header-left {
      flex: 1;
    }
    
    .page-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin: 0 0 8px 0;
      
      .el-icon {
        font-size: 32px;
        color: #667eea;
      }
    }
    
    .page-subtitle {
      color: #64748b;
      margin: 0;
      font-size: 16px;
    }
    
    .filter-section {
      flex-shrink: 0;
      
      .filter-row {
        display: flex;
        align-items: flex-end;
        gap: 16px;
        flex-wrap: wrap;
      }
      
      .filter-item {
        display: flex;
        flex-direction: column;
        gap: 6px;
        
        .filter-label {
          font-size: 14px;
          font-weight: 500;
          color: #374151;
          margin: 0;
        }
      }
      
      .filter-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .el-button {
          background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
          border: 1px solid #d1d5db;
          color: #374151;
          border-radius: 8px;
          font-weight: 500;
          transition: all 0.3s ease;
          
          &:hover {
            background: linear-gradient(135deg, #e5e7eb, #d1d5db);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          }
        }
        
        .el-tag {
          font-weight: 500;
        }
      }
    }
  }
  
  .header-actions {
    .el-button {
      background: linear-gradient(135deg, #667eea, #764ba2);
      border: none;
      color: white;
      padding: 12px 24px;
      border-radius: 12px;
      font-weight: 600;
      transition: all 0.3s ease;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
      }
    }
  }
}

.main-content {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
}

.left-panel {
  width: 400px;
  flex-shrink: 0;
  max-width: 30%;
}

.right-panel {
  flex: 1;
  min-width: 0;
}

.candidate-list-card {
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
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    color: #1e293b;
  }
}

.candidate-list {
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.candidate-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fff;
  
  &:hover {
    border-color: #409eff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
  }
  
  &.active {
    border-color: #409eff;
    background: #f0f9ff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  }
}

.candidate-info {
  margin-bottom: 12px;
}

.candidate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.candidate-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.candidate-position {
  margin: 0 0 8px 0;
  color: #606266;
  font-size: 14px;
}

.candidate-details {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.detail-item {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.score-items {
  margin-bottom: 12px;
}

.score-row {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  align-items: center;
  
  &:last-child {
    margin-bottom: 0;
  }
}

.score-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  
  .score-label {
    display: block;
    font-size: 12px;
    color: #606266;
    font-weight: 500;
    min-width: 80px;
    text-align: right;
  }
  
  .score-display {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    
    .actual-score {
      font-size: 12px;
      font-weight: 600;
      color: #303133;
      min-width: 50px;
    }
    
    .el-progress {
      flex: 1;
      max-width: 120px;
    }
  }
}

.candidate-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.empty-candidates {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  
  :deep(.el-empty) {
    .el-empty__description {
      color: #64748b;
      font-size: 14px;
    }
    
    .el-button {
      background: linear-gradient(135deg, #667eea, #764ba2);
      border: none;
      color: white;
      border-radius: 8px;
      font-weight: 500;
      
      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      }
    }
  }
}

.content-card {
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  
  :deep(.el-card__body) {
    height: calc(100% - 60px);
    padding: 0;
  }
}

.content-tabs {
  height: 100%;
  
  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 20px;
    background: linear-gradient(135deg, #f8fafc, #e2e8f0);
    border-radius: 16px 16px 0 0;
  }
  
  :deep(.el-tabs__content) {
    height: calc(100% - 60px);
    padding: 20px;
  }
  
  :deep(.el-tab-pane) {
    height: 100%;
  }
}

.resume-preview {
  height: 100%;
  overflow-y: auto;
  
  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
  }
  
  .resume-content {
    .resume-section {
      margin-bottom: 24px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
      }
    }
    
    .personal-info {
      .info-row {
        display: flex;
        gap: 24px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .info-item {
          flex: 1;
          
          label {
            font-weight: 600;
            color: #64748b;
            margin-right: 8px;
          }
          
          span {
            color: #1e293b;
          }
        }
      }
    }
    
    .experience-list {
      .experience-item {
        padding: 16px;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .exp-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          
          h4 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
          }
          
          .duration {
            font-size: 14px;
            color: #64748b;
            background: #e2e8f0;
            padding: 4px 8px;
            border-radius: 4px;
          }
        }
        
        .company {
          margin: 0 0 8px 0;
          font-weight: 500;
          color: #475569;
        }
        
        .description {
          margin: 0;
          color: #64748b;
          line-height: 1.5;
        }
      }
    }
    
    .education-list {
      .education-item {
        padding: 16px;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .edu-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          
          h4 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
          }
          
          .duration {
            font-size: 14px;
            color: #64748b;
            background: #e2e8f0;
            padding: 4px 8px;
            border-radius: 4px;
          }
        }
        
        .major {
          margin: 0;
          color: #475569;
          font-weight: 500;
        }
      }
    }
    
    .skills-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      
      .skill-tag {
        margin: 0;
      }
    }
  }
}

.interview-plan-preview {
  height: 100%;
  overflow-y: auto;
  
  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
  }
  
  .interview-plan-content {
    .plan-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      padding: 20px;
      background: linear-gradient(135deg, #f8fafc, #e2e8f0);
      border-radius: 8px;
      
      .header-info {
        h2 {
          margin: 0 0 8px 0;
          font-size: 20px;
          font-weight: 600;
          color: #1e293b;
        }
        
        .position {
          margin: 0 0 4px 0;
          color: #475569;
          font-weight: 500;
        }
        
        .generated-time {
          margin: 0;
          font-size: 14px;
          color: #64748b;
        }
      }
    }
    
    // Markdown内容样式优化
    .markdown-content {
      line-height: 1.6;
      color: #374151;
      
      h1, h2, h3, h4, h5, h6 {
        color: #1e293b;
        font-weight: 600;
        margin: 24px 0 16px 0;
        
        &:first-child {
          margin-top: 0;
        }
      }
      
      h1 {
        font-size: 24px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
      }
      
      h2 {
        font-size: 20px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 6px;
      }
      
      h3 {
        font-size: 18px;
        color: #667eea;
      }
      
      h4 {
        font-size: 16px;
      }
      
      p {
        margin: 12px 0;
        line-height: 1.7;
      }
      
      ul, ol {
        margin: 16px 0;
        padding-left: 24px;
        
        li {
          margin: 8px 0;
          line-height: 1.6;
          
          &::marker {
            color: #667eea;
          }
        }
      }
      
      ul {
        li {
          position: relative;
          
          &::before {
            content: '•';
            color: #667eea;
            font-weight: bold;
            position: absolute;
            left: -16px;
          }
        }
      }
      
      blockquote {
        margin: 16px 0;
        padding: 16px 20px;
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border-left: 4px solid #667eea;
        border-radius: 0 8px 8px 0;
        
        p {
          margin: 0;
          color: #1e40af;
          font-style: italic;
        }
      }
      
      code {
        background: #f1f5f9;
        color: #e11d48;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 0.9em;
      }
      
      pre {
        background: #1e293b;
        color: #e2e8f0;
        padding: 16px;
        border-radius: 8px;
        overflow-x: auto;
        margin: 16px 0;
        
        code {
          background: none;
          color: inherit;
          padding: 0;
        }
      }
      
      table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        
        th, td {
          padding: 12px 16px;
          text-align: left;
          border-bottom: 1px solid #e2e8f0;
        }
        
        th {
          background: linear-gradient(135deg, #f8fafc, #e2e8f0);
          font-weight: 600;
          color: #1e293b;
        }
        
        tr:hover {
          background: #f8fafc;
        }
      }
      
      strong {
        color: #1e293b;
        font-weight: 600;
      }
      
      em {
        color: #667eea;
        font-style: italic;
      }
      
      hr {
        border: none;
        height: 2px;
        background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
        margin: 24px 0;
        border-radius: 1px;
      }
    }
    
    .plan-section {
      margin-bottom: 24px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
      }
    }
    
    .overview-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      
      .overview-item {
        &.full-width {
          grid-column: 1 / -1;
        }
        
        label {
          font-weight: 600;
          color: #64748b;
          margin-right: 8px;
        }
        
        span {
          color: #1e293b;
        }
        
        .focus-areas {
          margin-top: 8px;
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          
          .area-tag {
            margin: 0;
          }
        }
      }
    }
    
    .sections-list {
      .section-item {
        padding: 16px;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          
          h4 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
          }
          
          .duration {
            font-size: 14px;
            color: #64748b;
            background: #e2e8f0;
            padding: 4px 8px;
            border-radius: 4px;
          }
        }
        
        .questions-list {
          .question-item {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            
            &:last-child {
              margin-bottom: 0;
            }
            
            .question-number {
              font-weight: 600;
              color: #667eea;
              flex-shrink: 0;
            }
            
            .question-text {
              color: #475569;
              line-height: 1.5;
            }
          }
        }
      }
    }
    
    .criteria-list {
      .criteria-item {
        padding: 16px;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .criteria-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          
          h4 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
          }
        }
        
        .criteria-description {
          margin: 0;
          color: #64748b;
          line-height: 1.5;
        }
      }
    }
    
    .tips-list {
      .tip-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 12px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .tip-icon {
          color: #667eea;
          margin-top: 2px;
          flex-shrink: 0;
        }
        
        span {
          color: #475569;
          line-height: 1.5;
        }
      }
    }
    
    .plan-actions {
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      gap: 16px;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      
      .action-group {
        display: flex;
        gap: 12px;
        align-items: center;
      }
      
      .el-button {
        border-radius: 8px;
        font-weight: 500;
        
        &.el-button--primary {
          background: linear-gradient(135deg, #667eea, #764ba2);
          border: none;
        }
        
        &.el-button--success {
          background: linear-gradient(135deg, #10b981, #059669);
          border: none;
        }
        
        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
    
    .edit-container {
      margin-top: 16px;
      
      .edit-textarea {
        :deep(.el-textarea__inner) {
          border-radius: 8px;
          border: 2px solid #e2e8f0;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 14px;
          line-height: 1.6;
          padding: 16px;
          transition: all 0.3s ease;
          
          &:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
          }
        }
      }
    }
  }
}

.interview-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.interview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
  border: 1px solid rgba(226, 232, 240, 0.5);
  border-radius: 12px;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.15);
    border-color: rgba(102, 126, 234, 0.3);
  }
  
  .interview-info {
    flex: 1;
    
    .candidate-info {
      margin-bottom: 12px;
      
      h3 {
        font-size: 18px;
        font-weight: 600;
        background: linear-gradient(135deg, #1e293b, #475569);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 4px 0;
      }
      
      p {
        color: #64748b;
        margin: 0;
        font-weight: 500;
      }
    }
    
    .interview-details {
      display: flex;
      gap: 24px;
      
      .detail-item {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #64748b;
        font-size: 14px;
        font-weight: 500;
        
        .el-icon {
          font-size: 16px;
          color: #667eea;
        }
      }
    }
  }
  
  .interview-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 12px;
    
    .status-tag {
      margin: 0;
      font-weight: 600;
      border-radius: 8px;
      
      &.el-tag--warning {
        background: linear-gradient(135deg, #fbbf24, #f59e0b);
        color: white;
        border: none;
      }
      
      &.el-tag--success {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border: none;
      }
    }
    
    .action-buttons {
      display: flex;
      gap: 8px;
      
      .el-button {
        border-radius: 8px;
        font-weight: 500;
        
        &.el-button--primary {
          background: linear-gradient(135deg, #667eea, #764ba2);
          border: none;
          
          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
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
          }
        }
      }
    }
  }
}

// 对话框样式优化
:deep(.el-dialog) {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  
  .el-dialog__header {
    background: linear-gradient(135deg, #f8fafc, #e2e8f0);
    border-radius: 16px 16px 0 0;
    padding: 20px 24px;
    
    .el-dialog__title {
      font-weight: 600;
      color: #1e293b;
    }
  }
  
  .el-dialog__body {
    padding: 24px;
  }
  
  .el-dialog__footer {
    padding: 20px 24px;
    background: rgba(248, 250, 252, 0.5);
    border-radius: 0 0 16px 16px;
    
    .el-button {
      border-radius: 8px;
      font-weight: 500;
      
      &.el-button--primary {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border: none;
      }
    }
  }
}

// 表单样式优化
:deep(.el-form) {
  .el-form-item__label {
    color: #374151;
    font-weight: 600;
  }
  
  .el-input__wrapper {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    
    &:hover {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
  }
  
  .el-radio {
    .el-radio__label {
      color: #374151;
      font-weight: 500;
    }
  }
  
  .el-textarea__inner {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    
    &:hover {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .left-panel {
    width: 350px;
    max-width: 35%;
  }
}

@media (max-width: 768px) {
  .smart-interview {
    padding: 12px;
  }
  
  .page-header {
    padding: 20px;
    
    .header-content {
      flex-direction: column;
      gap: 20px;
      
      .filter-section {
        .filter-row {
          flex-direction: column;
          gap: 12px;
          align-items: stretch;
        }
        
        .filter-item {
          .el-input,
          .el-select {
            width: 100% !important;
          }
        }
        
        .filter-actions {
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 8px;
          
          .el-button {
            flex: 1;
            min-width: 120px;
          }
        }
      }
    }
    
    .header-actions {
      width: 100%;
      display: flex;
      justify-content: center;
    }
  }
  
  .main-content {
    flex-direction: column;
    height: auto;
    gap: 16px;
  }
  
  .left-panel {
    width: 100%;
  }
  
  .candidate-list {
    max-height: 400px;
  }
  
  .candidate-item {
    .candidate-details {
      flex-direction: column;
      gap: 8px;
    }
    
    .score-row {
      flex-direction: column;
      gap: 8px;
      align-items: stretch;
      
      .score-item {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
        
        .score-label {
          text-align: left;
          min-width: auto;
        }
      }
    }
    
    .candidate-actions {
      flex-direction: column;
      gap: 8px;
      
      .el-button {
        width: 100%;
      }
    }
  }
  
  .overview-grid {
    grid-template-columns: 1fr !important;
  }
  
  .plan-actions {
    flex-direction: column;
    
    .el-button {
      width: 100%;
    }
  }
}

// 简历预览样式
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
          
          .meta-divider {
            color: #dcdfe6;
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
  
  .no-evaluation {
    padding: 40px 20px;
    text-align: center;
  }
}
</style>
