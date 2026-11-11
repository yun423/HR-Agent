<template>
  <div class="exam-management">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Management /></el-icon>
            考试管理
          </h1>
          <p class="page-description">查看和管理所有考生的考试结果</p>
        </div>
        <div class="header-actions">
          <el-button @click="refreshData" type="primary" size="large" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧考生考试结果列表 -->
        <div class="exam-list-panel">
          <el-card class="list-card">
            <template #header>
              <div class="list-header">
                <div class="list-title">
                  <el-icon><List /></el-icon>
                  <span>考试结果列表</span>
                </div>
                <div class="list-actions">
                  <el-input
                    v-model="searchKeyword"
                    placeholder="搜索考生姓名..."
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

            <!-- 筛选区域 -->
            <div class="filter-section">
              <div class="filter-row">
                <div class="filter-item">
                  <label>考试名称：</label>
                  <el-select 
                    v-model="examNameFilter" 
                    placeholder="请选择考试名称" 
                    clearable
                    style="width: 180px"
                    @change="handleFilterChange"
                  >
                    <el-option label="全部" value="" />
                    <el-option 
                      v-for="examName in uniqueExamNames" 
                      :key="examName" 
                      :label="examName" 
                      :value="examName" 
                    />
                  </el-select>
                </div>
                
                <div class="filter-item">
                  <label>部门：</label>
                  <el-select 
                    v-model="departmentFilter" 
                    placeholder="请选择部门" 
                    clearable
                    style="width: 150px"
                    @change="handleFilterChange"
                  >
                    <el-option label="全部" value="" />
                    <el-option 
                      v-for="dept in uniqueDepartments" 
                      :key="dept" 
                      :label="dept" 
                      :value="dept" 
                    />
                  </el-select>
                </div>
              </div>
            </div>

            <!-- 考试结果列表内容 -->
            <div class="exam-list-content">
              <div v-if="loading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>
              
              <div v-else-if="filteredExamResults.length === 0" class="empty-container">
                <el-empty description="暂无考试结果数据" :image-size="120">
                  <el-button type="primary" @click="refreshData">
                    <el-icon><Refresh /></el-icon>
                    刷新数据
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="exam-items">
                <div
                  v-for="result in filteredExamResults"
                  :key="result.exam_result_id"
                  :class="['exam-item', { active: selectedResult?.exam_result_id === result.exam_result_id }]"
                  @click="selectResult(result)"
                >
                  <div class="exam-item-header">
                    <h4 class="exam-title">{{ result.student_name }}</h4>
                    <div class="exam-score">
                      <el-tag 
                        :type="getScoreType(result.total_actual_score, result.total_possible_score)"
                        size="large"
                      >
                        {{ result.total_actual_score }}/{{ result.total_possible_score }}分
                      </el-tag>
                    </div>
                  </div>
                  
                  <div class="exam-item-content">
                    <div class="exam-meta">
                      <div class="meta-item">
                        <el-icon><Document /></el-icon>
                        <span>{{ result.exam_name }}</span>
                      </div>
                      <div class="meta-item">
                        <el-icon><OfficeBuilding /></el-icon>
                        <span>{{ result.department || '未填写' }}</span>
                      </div>
                      <div class="meta-item">
                        <el-icon><Clock /></el-icon>
                        <span>{{ formatDateTime(result.submit_time) }}</span>
                      </div>
                      <div class="meta-item">
                        <el-icon><TrendCharts /></el-icon>
                        <span>{{ result.score_percentage }}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分页组件 -->
              <div v-if="filteredExamResults.length > 0" class="pagination-container">
                <el-pagination
                  v-model:current-page="pagination.page"
                  v-model:page-size="pagination.pageSize"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="pagination.total"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handleSizeChange"
                  @current-change="handlePageChange"
                />
              </div>
            </div>
          </el-card>
        </div>

        <!-- 右侧考试结果预览 -->
        <div class="exam-preview-panel">
          <el-card class="preview-card">
            <template #header>
              <div class="preview-header">
                <el-icon><View /></el-icon>
                <span>考试结果预览</span>
              </div>
            </template>

            <!-- 未选择考试结果时的提示 -->
            <div v-if="!selectedResult" class="empty-state">
              <el-empty description="请选择左侧考试结果查看详情" :image-size="120" />
            </div>

            <!-- 考试结果详情 -->
            <div v-else class="exam-result-detail">
              <!-- 加载状态 -->
              <div v-if="detailLoading" class="detail-loading">
                <el-skeleton :rows="5" animated />
                <div style="text-align: center; margin-top: 20px;">
                  <span>加载考试详情中...</span>
                </div>
              </div>
              
              <!-- 考试结果头部信息 -->
              <div v-else class="result-header">
                <h2 class="exam-title">{{ selectedResult.exam_name }}</h2>
                <div class="result-summary">
                  <div class="summary-item">
                    <span class="label">考生姓名：</span>
                    <span class="value">{{ selectedResult.student_name }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">所属部门：</span>
                    <span class="value">{{ selectedResult.department || '未填写' }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">提交时间：</span>
                    <span class="value">{{ formatDateTime(selectedResult.submit_time) }}</span>
                  </div>
                </div>
              </div>

              <!-- 成绩统计 -->
              <div v-if="!detailLoading" class="score-summary">
                <div class="score-card">
                  <div class="score-label">总分</div>
                  <div class="score-value">{{ selectedResult.total_possible_score }}</div>
                </div>
                <div class="score-card actual-score">
                  <div class="score-label">得分</div>
                  <div class="score-value">{{ selectedResult.total_actual_score }}</div>
                </div>
                <div class="score-card percentage">
                  <div class="score-label">得分率</div>
                  <div class="score-value">{{ selectedResult.score_percentage }}%</div>
                </div>
              </div>

              <!-- 题目详情 -->
              <div v-if="!detailLoading" class="questions-section">
                <h3>答题详情</h3>
                <div v-for="(question, index) in getQuestions()" :key="index" class="question-item">
                  <div class="question-header">
                    <span class="question-number">第{{ index + 1 }}题</span>
                    <span class="question-score">{{ question.实际得分 || 0 }}/{{ question.分值 }}分</span>
                  </div>
                  
                  <div class="question-content">
                    <div class="question-text">
                      <strong>题目：</strong>{{ question.题目内容 }}
                    </div>
                    
                    <div v-if="question.选项 && question.选项.length > 0" class="question-options">
                      <strong>选项：</strong>
                      <ul>
                        <li v-for="(option, optIndex) in question.选项" :key="optIndex">
                          {{ option.id }}. {{ option.text }}
                        </li>
                      </ul>
                    </div>
                    
                    <div class="answer-section">
                      <div class="student-answer">
                        <strong>考生答案：</strong>
                        <span :class="{'no-answer': question.考生答案 === '未作答'}">
                          {{ formatAnswer(question.考生答案) }}
                        </span>
                      </div>
                      
                      <div class="standard-answer">
                        <strong>标准答案：</strong>
                        <span>{{ question.标准答案 }}</span>
                      </div>
                      
                      <div v-if="question.解析" class="answer-explanation">
                        <strong>解析：</strong>
                        <span>{{ question.解析 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div v-if="!detailLoading" class="action-buttons">
                <el-button @click="exportResult" type="primary">
                  <el-icon><Download /></el-icon>
                  导出结果
                </el-button>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

// 响应式数据
const loading = ref(true)
const examResults = ref([])
const selectedResult = ref(null)
const selectedResultDetail = ref(null)
const detailLoading = ref(false)
const searchKeyword = ref('')
const searchQuery = ref('')
const examNameFilter = ref('')
const departmentFilter = ref('')
const filters = ref({
  examName: '',
  department: ''
})
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 计算属性
const hasResults = computed(() => examResults.value.length > 0)

const filteredExamResults = computed(() => {
  return examResults.value.filter(result => {
    const matchesSearch = !searchKeyword.value || 
      result.student_name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    const matchesExamName = !examNameFilter.value || result.exam_name === examNameFilter.value
    const matchesDepartment = !departmentFilter.value || result.department === departmentFilter.value
    
    return matchesSearch && matchesExamName && matchesDepartment
  })
})

const uniqueExamNames = computed(() => {
  const names = [...new Set(examResults.value.map(result => result.exam_name))]
  return names.filter(name => name)
})

const uniqueDepartments = computed(() => {
  const departments = [...new Set(examResults.value.map(result => result.department))]
  return departments.filter(dept => dept)
})

// 获取分数颜色
const getScoreColor = (percentage) => {
  if (percentage >= 90) return '#52c41a'
  if (percentage >= 80) return '#1890ff'
  if (percentage >= 70) return '#faad14'
  if (percentage >= 60) return '#13c2c2'
  return '#f5222d'
}

// 方法定义
const handleSearch = () => {
  pagination.value.page = 1
  loadExamResults()
}

const handleFilterChange = () => {
  pagination.value.page = 1
  loadExamResults()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadExamResults()
}

const handleSizeChange = (size) => {
  pagination.value.pageSize = size
  pagination.value.page = 1
  loadExamResults()
}


const resetFilters = () => {
  searchKeyword.value = ''
  examNameFilter.value = ''
  departmentFilter.value = ''
  pagination.value.page = 1
  loadExamResults()
}

// 时间格式化方法
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return timeStr
  }
}

// 答案格式化方法
const formatAnswer = (answer) => {
  if (!answer) return '-'
  if (Array.isArray(answer)) {
    return answer.join(', ')
  }
  return answer
}

// 获取分数类型

// 方法
const loadExamResults = async () => {
  try {
    loading.value = true
    
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    
    // 添加搜索条件
    if (searchKeyword.value.trim()) {
      params.search = searchKeyword.value.trim()
    }
    
    // 添加筛选条件
    if (examNameFilter.value) {
      params.exam_name = examNameFilter.value
    }
    
    if (departmentFilter.value) {
      params.department = departmentFilter.value
    }
    
    const response = await api.get('/exam-management/exam-results', { params })
    
    // 处理响应数据
    console.log('API响应数据:', response)
    if (response && response.items) {
      examResults.value = response.items
      pagination.value.total = response.total || 0
    } else if (Array.isArray(response)) {
      examResults.value = response
      pagination.value.total = response.length
    } else {
      examResults.value = []
      pagination.value.total = 0
    }
    
    // 如果有结果且没有选中的结果，默认选中第一个
    if (examResults.value.length > 0 && !selectedResult.value) {
      selectResult(examResults.value[0])
    }
    
    ElMessage.success('考试结果加载成功')
  } catch (error) {
    console.error('加载考试结果失败:', error)
    ElMessage.error('加载考试结果失败')
    examResults.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

const selectResult = async (result) => {
  selectedResult.value = result
  selectedResultDetail.value = null // 清空之前的详细数据
  console.log('selectResult called with:', result)
  console.log('result.id:', result.id)
  console.log('result.exam_result_id:', result.exam_result_id)

  // 加载详细信息
  try {
    detailLoading.value = true
    // 检查使用哪个字段作为ID
    const resultId = result.exam_result_id || result.id
    console.log('使用的resultId:', resultId)

    if (resultId) {
      console.log('请求考试结果详情，ID:', resultId)
      const detailResponse = await api.get(`/exam-management/exam-results/${resultId}`)
      console.log('考试结果详情API响应 (原始):', detailResponse)
      console.log('detailResponse类型:', typeof detailResponse)
      console.log('detailResponse是否有id属性:', detailResponse && detailResponse.id)

      // 检查响应数据结构 - 由于API拦截器会返回response.data，所以数据直接在detailResponse中
      if (detailResponse && detailResponse.id) {
        console.log('进入设置selectedResultDetail的逻辑')
        // 数据直接在response中（经过拦截器处理后）
        selectedResultDetail.value = detailResponse
        console.log('设置selectedResultDetail:', selectedResultDetail.value)
        console.log('selectedResultDetail.value.exam_data:', selectedResultDetail.value.exam_data)

        // 如果有exam_data字段，解析题目信息
        if (selectedResultDetail.value.exam_data) {
          console.log('发现exam_data字段:', selectedResultDetail.value.exam_data)
          console.log('exam_data类型:', typeof selectedResultDetail.value.exam_data)
          try {
            let questions = []
            if (typeof selectedResultDetail.value.exam_data === 'string') {
              console.log('exam_data是字符串，尝试解析为JSON')
              const parsed = JSON.parse(selectedResultDetail.value.exam_data)
              console.log('解析后的exam_data:', parsed)
              questions = parsed.questions || []
              console.log('从解析后的数据中提取questions:', questions)
            } else if (typeof selectedResultDetail.value.exam_data === 'object') {
              console.log('exam_data是对象，直接获取questions')
              questions = selectedResultDetail.value.exam_data.questions || []
              console.log('从对象中提取questions:', questions)
            }
            // 将题目列表添加到selectedResultDetail中
            selectedResultDetail.value.questions = questions
            console.log('设置selectedResultDetail.questions:', questions)
          } catch (e) {
            console.error('解析exam_data失败:', e)
          }
        } else {
          console.log('没有找到exam_data字段')
        }
      } else {
        console.warn('考试结果详情数据格式异常:', detailResponse)
        console.log('detailResponse为null或没有id属性')
        selectedResultDetail.value = null
      }

      console.log('最终的selectedResultDetail:', selectedResultDetail.value)
    } else {
      console.log('resultId为空或不存在')
    }
  } catch (error) {
    console.error('加载考试结果详情失败:', error)
    ElMessage.error('获取考试结果详情失败')
    selectedResultDetail.value = null
  } finally {
    console.log('finally块执行，detailLoading设为false')
    detailLoading.value = false
  }
}



const refreshData = () => {
  loadExamResults()
}

const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '未知'
  const date = new Date(dateTimeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}



const getScoreType = (actualScore, totalScore) => {
  const percentage = (actualScore / totalScore) * 100
  if (percentage >= 90) return 'success'
  if (percentage >= 80) return 'primary'
  if (percentage >= 70) return 'warning'
  if (percentage >= 60) return 'info'
  return 'danger'
}

// 获取题目列表
const getQuestions = () => {
  console.log('getQuestions called, selectedResultDetail:', selectedResultDetail.value)

  // 首先检查是否有直接的questions字段
  if (selectedResultDetail.value && selectedResultDetail.value.questions) {
    console.log('直接返回questions字段:', selectedResultDetail.value.questions)
    return selectedResultDetail.value.questions
  }

  // 从exam_data中解析题目
  if (selectedResultDetail.value && selectedResultDetail.value.exam_data) {
    console.log('从exam_data中解析题目')
    try {
      const examData = selectedResultDetail.value.exam_data
      console.log('examData:', examData)
      if (typeof examData === 'string') {
        console.log('exam_data是字符串，尝试解析为JSON')
        const parsed = JSON.parse(examData)
        console.log('解析后的exam_data:', parsed)
        const questions = parsed.questions || []
        console.log('从解析后的数据中提取questions:', questions)
        return questions
      } else if (typeof examData === 'object') {
        console.log('exam_data是对象，直接获取questions')
        const questions = examData.questions || []
        console.log('从对象中提取questions:', questions)
        return questions
      }
    } catch (e) {
      console.error('解析exam_data失败:', e)
    }
  } else {
    console.log('没有找到exam_data字段')
  }

  console.log('未找到题目数据，返回空数组')
  return []
}

const exportResult = async () => {
  if (!selectedResult.value) return

  try {
    // 显示导出提示
    ElMessage.info(`正在导出${selectedResult.value.student_name}的考试结果...`)

    // 构造导出URL
    const resultId = selectedResult.value.exam_result_id || selectedResult.value.id
    const exportUrl = `/api/v1/exam-management/exam-results/${resultId}/export`

    // 创建隐藏的下载链接
    const link = document.createElement('a')
    link.href = exportUrl
    link.download = `exam_result_${resultId}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success(`导出${selectedResult.value.student_name}的考试结果成功！`)
  } catch (error) {
    console.error('导出考试结果失败:', error)
    ElMessage.error('导出考试结果失败，请重试')
  }
}

// 生命周期
onMounted(() => {
  loadExamResults()
})
</script>

<style lang="scss" scoped>
.exam-management {
  height: 100%;
  overflow-y: auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.page-container {
  max-width: 95%;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
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
      margin: 0 0 8px 0;
    }
    
    .page-description {
      color: #64748b;
      font-size: 16px;
      margin: 0;
    }
  }
  
  .header-actions {
    .el-button {
      border-radius: 12px;
      padding: 12px 24px;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
      }
    }
  }
}

.main-content {
  display: flex;
  gap: 24px;
  height: calc(100vh - 200px);
  
  .exam-list-panel, .exam-preview-panel {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  .exam-list-panel {
    flex: 1;
    min-width: 400px;
    
    .list-card {
      height: 100%;
      display: flex;
      flex-direction: column;
      
      :deep(.el-card__body) {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 0;
        overflow: hidden;
      }
    }
  }
  
  .exam-preview-panel {
    flex: 1.2;
    min-width: 600px;
    
    .preview-card {
      height: 100%;
      display: flex;
      flex-direction: column;
      
      :deep(.el-card__body) {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 0;
        overflow: hidden;
      }
    }
  }
}

.list-header, .preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .list-title, .preview-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #374151;
  }
}

.filter-section {
  padding: 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  
  .filter-row {
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
  }
  
  .filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    
    label {
      font-size: 14px;
      color: #374151;
      font-weight: 500;
      white-space: nowrap;
    }
  }
}

.exam-list-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: rgba(226, 232, 240, 0.3);
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(102, 126, 234, 0.3);
    border-radius: 4px;
    transition: background 0.3s ease;
    
    &:hover {
      background: rgba(102, 126, 234, 0.5);
    }
  }
}

.exam-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-item {
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:hover {
    border-color: #c7d2fe;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
    transform: translateY(-2px);
  }
  
  &.active {
    border-color: #667eea;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
  }
  
  .exam-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .exam-title {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
      margin: 0;
    }
    
    .exam-score {
      flex-shrink: 0;
    }
  }
  
  .exam-item-content {
    .exam-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      
      .meta-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #64748b;
        
        .el-icon {
          color: #94a3b8;
          font-size: 16px;
        }
        
        span {
          font-weight: 500;
        }
      }
    }
  }
}

.empty-state {
  padding: 40px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.exam-result-detail {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: rgba(226, 232, 240, 0.3);
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(102, 126, 234, 0.3);
    border-radius: 4px;
    transition: background 0.3s ease;
    
    &:hover {
      background: rgba(102, 126, 234, 0.5);
    }
  }
}

// 复用考试结果页面的样式
.result-header {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  
  .exam-title {
    font-size: 24px;
    font-weight: bold;
    color: #333;
    margin-bottom: 15px;
  }
  
  .result-summary {
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
    
    .summary-item {
      display: flex;
      align-items: center;
      
      .label {
        font-weight: 500;
        color: #666;
        margin-right: 8px;
      }
      
      .value {
        color: #333;
      }
    }
  }
}

.score-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  justify-content: center;
  
  .score-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    min-width: 120px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    
    &.actual-score {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    &.percentage {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    
    .score-label {
      font-size: 14px;
      opacity: 0.9;
      margin-bottom: 8px;
    }
    
    .score-value {
      font-size: 28px;
      font-weight: bold;
    }
  }
}

.questions-section {
  margin-bottom: 30px;
  
  h3 {
    font-size: 20px;
    color: #333;
    margin-bottom: 20px;
    border-bottom: 2px solid #e1e8ed;
    padding-bottom: 10px;
  }
  
  .question-item {
    background: white;
    border: 1px solid #e1e8ed;
    border-radius: 8px;
    margin-bottom: 20px;
    overflow: hidden;
    
    .question-header {
      background: #f8f9fa;
      padding: 15px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #e1e8ed;
      
      .question-number {
        font-weight: 600;
        color: #333;
      }
      
      .question-score {
        font-weight: 600;
        color: #1890ff;
      }
    }
    
    .question-content {
      padding: 20px;
      
      .question-text {
        margin-bottom: 15px;
        line-height: 1.6;
      }
      
      .question-options {
        margin-bottom: 15px;
        
        ul {
          margin: 8px 0 0 20px;
          padding: 0;
          
          li {
            margin-bottom: 5px;
            line-height: 1.5;
          }
        }
      }
      
      .answer-section {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        
        > div {
          margin-bottom: 10px;
          line-height: 1.6;
          
          &:last-child {
            margin-bottom: 0;
          }
        }
        
        .student-answer .no-answer {
          color: #999;
          font-style: italic;
        }
        
        .standard-answer {
          color: #52c41a;
        }
        
        .answer-explanation {
          color: #666;
          font-size: 14px;
        }
      }
    }
  }
}

.action-buttons {
  text-align: center;
  padding: 20px 0;
  border-top: 1px solid #e1e8ed;
  margin-top: 30px;
  
  .el-button {
    margin: 0 10px;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    
    &:hover {
      transform: translateY(-2px);
    }
  }
}

.loading-container, .empty-container {
  padding: 40px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
    height: auto;
    
    .exam-list-panel, .exam-preview-panel {
      min-width: auto;
      height: 500px;
    }
  }
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  
  :deep(.el-pagination) {
    .el-pager li {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: white;
      
      &:hover {
        background: rgba(255, 255, 255, 0.2);
      }
      
      &.is-active {
        background: #409eff;
        border-color: #409eff;
      }
    }
    
    .btn-prev, .btn-next {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: white;
      
      &:hover {
        background: rgba(255, 255, 255, 0.2);
      }
    }
    
    .el-select .el-input__wrapper {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      
      .el-input__inner {
        color: white;
      }
    }
    
    .el-pagination__total,
    .el-pagination__jump {
      color: white;
    }
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .filter-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .score-summary {
    flex-direction: column;
    align-items: center;
  }
  
  .result-summary {
    flex-direction: column;
    gap: 10px;
  }
  
  .exam-item-content .exam-meta {
    grid-template-columns: 1fr;
  }
}
</style>