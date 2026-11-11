<template>
  <div class="exam-result-container" v-loading="loading" element-loading-text="加载考试结果中...">
    <div v-if="loading" class="loading-container">
      <div>加载考试结果中...</div>
    </div>
    
    <div v-else-if="examResult" class="exam-result-content">
      <!-- 考试结果头部信息 -->
      <div class="result-header">
        <h1 class="exam-title">{{ examResult.exam_name }}</h1>
        <div class="result-summary">
          <div class="summary-item">
            <span class="label">考生姓名：</span>
            <span class="value">{{ examResult.student_name }}</span>
          </div>
          <div class="summary-item">
            <span class="label">所属部门：</span>
            <span class="value">{{ examResult.department || '未填写' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">提交时间：</span>
            <span class="value">{{ formatDateTime(examResult.submit_time) }}</span>
          </div>
        </div>
      </div>

      <!-- 成绩统计 -->
      <div class="score-summary">
        <div class="score-card">
          <div class="score-label">总分</div>
          <div class="score-value">{{ examResult.total_possible_score }}</div>
        </div>
        <div class="score-card">
          <div class="score-label">得分</div>
          <div class="score-value actual-score">{{ examResult.total_actual_score }}</div>
        </div>
        <div class="score-card">
          <div class="score-label">得分率</div>
          <div class="score-value percentage">{{ examResult.score_percentage }}%</div>
        </div>
      </div>



      <!-- 详细题目得分 -->
      <div v-if="examResult && examResult.questions" class="questions-detail">
        <el-card class="detail-card">
          <template #header>
            <h3>详细得分情况</h3>
          </template>
          
          <div class="question-results">
            <div 
              v-for="question in examResult.questions" 
              :key="question.题目编号"
              class="question-result-item"
            >
              <div class="question-result-header">
                <div class="question-info">
                  <span class="question-number">第{{ question.题目编号 }}题</span>
                  <span class="question-type">{{ question.题目类型 }}</span>
                </div>
                <span class="score-info">
                  <span :class="getScoreClass(question.实际得分, question.分值)">
                    {{ question.实际得分 }}
                  </span>
                  /{{ question.分值 }}分
                </span>
              </div>
              
              <div class="question-result-content">
                <p class="question-text">{{ question.题目内容 }}</p>
                
                <!-- 选项显示（单选/多选题） -->
                <div v-if="question.选项 && question.选项.length > 0" class="options-display">
                  <div 
                    v-for="option in question.选项" 
                    :key="option.id"
                    class="option-display-item"
                  >
                    <span class="option-label">{{ option.id }}.</span>
                    <span class="option-text">{{ option.text }}</span>
                  </div>
                </div>
                
                <!-- 答案对比 -->
                <div class="answer-comparison">
                  <div class="answer-item">
                    <span class="answer-label correct">标准答案：</span>
                    <span class="answer-value correct">{{ question.标准答案 }}</span>
                  </div>
                  <div class="answer-item">
                    <span class="answer-label">考生答案：</span>
                    <span 
                      class="answer-value"
                      :class="{
                        'correct': question.实际得分 === question.分值,
                        'incorrect': question.实际得分 < question.分值 && question.考生答案,
                        'unanswered': !question.考生答案
                      }"
                    >
                      {{ formatAnswer(question.考生答案) || '未作答' }}
                    </span>
                  </div>
                </div>
                
                <!-- 解析 -->
                <div v-if="question.解析" class="question-analysis">
                  <div class="analysis-header">
                    <el-icon><InfoFilled /></el-icon>
                    <span>解析</span>
                  </div>
                  <div class="analysis-content">{{ question.解析 }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button @click="goBack">返回</el-button>
        <el-button type="primary" @click="exportResult">导出结果</el-button>
      </div>
    </div>

    <div v-else class="error-container">
      <el-result
        icon="error"
        title="加载失败"
        :sub-title="errorMessage"
      >
        <template #extra>
          <el-button type="primary" @click="loadExamResult">重新加载</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import api from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const examResult = ref(null)
const errorMessage = ref('')

const examResultId = route.params.examResultId

// 加载考试结果
const loadExamResult = async () => {
  try {
    loading.value = true
    const response = await api.get(`/exam-management/exam-results/${examResultId}`)

    // 调试信息
    console.log('API Response:', response)

    // 检查响应数据结构
    if (response && response.id) {
      // 数据直接在response中
      examResult.value = response
      // 如果有exam_data字段且是JSON字符串，解析它
      if (response.exam_data) {
        try {
          if (typeof response.exam_data === 'string') {
            const parsed = JSON.parse(response.exam_data)
            examResult.value.questions = parsed.questions || []
          } else if (typeof response.exam_data === 'object') {
            examResult.value.questions = response.exam_data.questions || []
          }
        } catch (e) {
          console.error('Failed to parse exam_data:', e)
        }
      }
    } else if (response && response.data && response.data.id) {
      // 数据在response.data中
      examResult.value = response.data
      // 如果有exam_data字段且是JSON字符串，解析它
      if (response.data.exam_data) {
        try {
          if (typeof response.data.exam_data === 'string') {
            const parsed = JSON.parse(response.data.exam_data)
            examResult.value.questions = parsed.questions || []
          } else if (typeof response.data.exam_data === 'object') {
            examResult.value.questions = response.data.exam_data.questions || []
          }
        } catch (e) {
          console.error('Failed to parse exam_data:', e)
        }
      }
    } else {
      console.error('Unexpected response structure:', response)
      throw new Error('无法找到响应数据')
    }

    console.log('Processed examResult:', examResult.value)
  } catch (error) {
    console.error('加载考试结果失败:', error)
    errorMessage.value = error.response?.data?.detail || error.message || '加载考试结果失败'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '未知'
  const date = new Date(dateTimeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化答案
const formatAnswer = (answer) => {
  if (!answer || answer === '未作答') return '未作答'
  if (Array.isArray(answer)) {
    return answer.join(', ')
  }
  return answer
}

// 获取分数样式类
const getScoreClass = (actualScore, totalScore) => {
  const percentage = (actualScore / totalScore) * 100
  if (percentage === 100) return 'score-perfect'
  if (percentage >= 80) return 'score-good'
  if (percentage >= 60) return 'score-pass'
  return 'score-fail'
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 导出结果
const exportResult = async () => {
  try {
    // 显示导出提示
    ElMessage.info('正在导出考试结果...')

    // 构造导出URL
    const exportUrl = `/api/v1/exam-management/exam-results/${examResultId}/export`

    // 创建隐藏的下载链接
    const link = document.createElement('a')
    link.href = exportUrl
    link.download = `exam_result_${examResultId}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('导出考试结果成功！')
  } catch (error) {
    console.error('导出考试结果失败:', error)
    ElMessage.error('导出考试结果失败，请重试')
  }
}

onMounted(() => {
  if (examResultId) {
    loadExamResult()
  } else {
    errorMessage.value = '缺少考试结果ID'
    loading.value = false
  }
})
</script>

<style scoped>
.exam-result-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.loading-container {
  height: 400px;
  position: relative;
}

.result-header {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

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
}

.summary-item {
  display: flex;
  align-items: center;
}

.summary-item .label {
  font-weight: 500;
  color: #666;
  margin-right: 8px;
}

.summary-item .value {
  color: #333;
}

.score-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  justify-content: center;
}

.score-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  min-width: 120px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.score-card.actual-score {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.score-card.percentage {
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

.questions-detail {
  margin-bottom: 30px;
}

.detail-card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.detail-card .el-card__header {
  background: #f8fafc;
  border-bottom: 2px solid #e2e8f0;
}

.detail-card h3 {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 600;
}

.question-results {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.question-result-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s ease;
}

.question-result-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.question-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e2e8f0;
}

.question-number {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.question-type {
  background: #e7f3ff;
  color: #409eff;
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 12px;
  font-weight: 500;
}

.question-score {
  font-size: 18px;
  font-weight: bold;
  padding: 6px 12px;
  border-radius: 8px;
}

.score-perfect {
  background: #f0f9ff;
  color: #67c23a;
}

.score-good {
  background: #fff7e6;
  color: #e6a23c;
}

.score-pass {
  background: #f0f9ff;
  color: #409eff;
}

.score-fail {
  background: #fef2f2;
  color: #f56c6c;
}

.question-result-content {
  margin-top: 16px;
}

.question-text {
  font-size: 16px;
  line-height: 1.6;
  color: #303133;
  margin-bottom: 16px;
  font-weight: 500;
}

.options-display {
  margin: 16px 0;
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.option-display-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.option-display-item:last-child {
  margin-bottom: 0;
}

.option-label {
  font-weight: 600;
  color: #667eea;
  margin-right: 8px;
  flex-shrink: 0;
}

.option-text {
  color: #606266;
}

.answer-comparison {
  margin: 20px 0;
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.answer-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}

.answer-item:last-child {
  margin-bottom: 0;
}

.answer-label {
  font-weight: 600;
  font-size: 14px;
  min-width: 80px;
  flex-shrink: 0;
  color: #409eff;
}

.answer-value {
  flex: 1;
  font-size: 14px;
  line-height: 1.5;
  padding: 6px 12px;
  border-radius: 6px;
  word-wrap: break-word;
}

.answer-value.correct {
  background: #f0f9ff;
  color: #67c23a;
  border: 1px solid #b3e19d;
}

.answer-value.incorrect {
  background: #fef2f2;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
}

.question-analysis {
  margin-top: 20px;
  padding: 16px;
  background: #fef9e7;
  border: 1px solid #f7d794;
  border-radius: 8px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #e6a23c;
  font-weight: 600;
  font-size: 14px;
}

.analysis-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.action-buttons {
  text-align: center;
  padding: 20px 0;
  border-top: 1px solid #e1e8ed;
  margin-top: 30px;
}

.action-buttons .el-button {
  margin: 0 10px;
}

.error-container {
  padding: 50px 0;
}


@media (max-width: 768px) {
  .score-summary {
    flex-direction: column;
    align-items: center;
  }
  
  .result-summary {
    flex-direction: column;
    gap: 10px;
  }
  
  .question-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>