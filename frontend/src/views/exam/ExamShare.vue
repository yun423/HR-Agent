<template>
  <div class="exam-share-container" v-loading="submitting" element-loading-text="正在阅卷中，请耐心等待">
    <!-- 固定顶部阅卷提示条 -->
    <transition name="fade">
      <div v-if="submitting" class="grading-banner">
        正在阅卷中，请耐心等待
      </div>
    </transition>
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container" v-loading="true" element-loading-text="加载试卷中...">
      <div style="height: 200px;"></div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadExam">重新加载</el-button>
        </template>
      </el-result>
    </div>

    <!-- 考生信息填写 -->
    <div v-else-if="!examStarted && exam" class="student-info-container">
      <div class="exam-header">
        <h1>{{ exam.title }}</h1>
        <div class="exam-meta">
          <el-tag>{{ exam.subject }}</el-tag>
          <el-tag type="info">{{ exam.difficulty }}</el-tag>
          <el-tag type="warning">{{ exam.duration }}分钟</el-tag>
          <el-tag type="success">总分: {{ exam.total_score }}分</el-tag>
        </div>
        <p v-if="exam.description" class="exam-description">{{ exam.description }}</p>
      </div>

      <el-card class="student-form-card">
        <template #header>
          <h3>考生信息</h3>
        </template>
        
        <el-form :model="studentInfo" :rules="studentRules" ref="studentFormRef" label-width="100px">
          <el-form-item label="考生姓名" prop="name">
            <el-input v-model="studentInfo.name" placeholder="请输入您的姓名" />
          </el-form-item>
          <el-form-item label="部门名称" prop="department">
            <el-input v-model="studentInfo.department" placeholder="请输入您的部门" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="startExam" :loading="startingExam">
              开始考试
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 考试结果 -->
    <div v-else-if="examCompleted" class="result-container">
      <div class="result-header">
        <el-result icon="success" title="考试完成" sub-title="评分已完成，以下是您的考试结果">
          <template #extra>
            <div v-if="examResult" class="result-summary">
              <div class="score-card">
                <div class="score-item">
                  <span class="score-label">总得分</span>
                  <span class="score-value">{{ examResult.total_actual_score || 0 }}</span>
                </div>
                <div class="score-divider">/</div>
                <div class="score-item">
                  <span class="score-label">总分</span>
                  <span class="score-value">{{ examResult.total_possible_score || exam.total_score }}</span>
                </div>
              </div>
              <div class="score-percentage">
                得分率: {{ getScorePercentage() }}%
              </div>
            </div>
          </template>
        </el-result>
      </div>

      <!-- 调试信息 -->
      <div v-if="examResult" style="background: #f0f0f0; padding: 10px; margin: 10px 0; font-size: 12px;">
        <strong>调试信息:</strong><br>
        examResult存在: {{ !!examResult }}<br>
        examResult.questions存在: {{ !!(examResult && examResult.questions) }}<br>
        questions数量: {{ examResult.questions ? examResult.questions.length : 0 }}<br>
        完整数据: {{ JSON.stringify(examResult, null, 2) }}
      </div>

      <!-- 详细题目得分 -->
      <div v-if="examResult && examResult.questions" class="questions-detail">
        <el-card class="detail-card">
          <template #header>
            <h3>详细得分情况</h3>
          </template>
          
          <div class="question-results">
            <div 
              v-for="(question, index) in examResult.questions" 
              :key="index"
              class="question-result-item"
            >
              <div class="question-result-header">
                <span class="question-number">第{{ question.题目编号 }}题</span>
                <span class="question-type">{{ question.题目类型 }}</span>
                <span class="question-score" :class="getScoreClass(question.实际得分, question.分值)">
                  {{ question.实际得分 }}/{{ question.分值 }}分
                </span>
              </div>
              
              <div class="question-result-content">
                <p class="question-text">{{ question.题目内容 }}</p>
                
                <!-- 选项显示（单选/多选题） -->
                <div v-if="(question.选项 && question.选项.length > 0) || (question.options && question.options.length > 0)" class="options-display">
                  <div
                    v-for="(option, optIndex) in (question.选项 || question.options)"
                    :key="option.id || optIndex"
                    class="option-display-item"
                  >
                    <span class="option-label">{{ option.id || (optIndex + 1) }}.</span>
                    <span class="option-text">{{ option.text || option }}</span>
                  </div>
                </div>
                
                <!-- 答案对比 -->
                <div class="answer-comparison">
                  <div class="answer-item">
                    <span class="answer-label">标准答案:</span>
                    <span class="answer-value correct">{{ question.标准答案 }}</span>
                  </div>
                  <div class="answer-item">
                    <span class="answer-label">考生答案:</span>
                    <span class="answer-value" :class="question.实际得分 > 0 ? 'correct' : 'incorrect'">
                      {{ Array.isArray(question.考生答案) ? question.考生答案.join(', ') : question.考生答案 }}
                    </span>
                  </div>
                </div>
                
                <!-- 解析 -->
                <div v-if="question.解析" class="question-analysis">
                  <div class="analysis-header">
                    <el-icon><InfoFilled /></el-icon>
                    <span>解析</span>
                  </div>
                  <p class="analysis-content">{{ question.解析 }}</p>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 考试界面 -->
    <div v-else-if="examStarted && exam" class="exam-container">
      <div class="exam-header">
        <h2>{{ exam.title }}</h2>
        <div class="exam-timer">
          <el-icon><Clock /></el-icon>
          剩余时间: {{ formatTime(remainingTime) }}
        </div>
      </div>

      <div class="exam-content">
        <div class="question-list">
          <div 
            v-for="(question, index) in questions" 
            :key="question.id"
            class="question-item"
          >
            <div class="question-header">
              <span class="question-number">{{ index + 1 }}</span>
              <span class="question-type">{{ question.question_type }}</span>
              <span class="question-score">{{ question.score }}分</span>
            </div>
            
            <div class="question-content">
              <p class="question-text">{{ question.question_text }}</p>
              
              <!-- 单选题 -->
              <div v-if="question.question_type === '单选题' || question.question_type === 'single_choice' || question.question_type === '单选'" class="options-container">
                <el-radio-group v-model="answers[question.id]">
                  <div
                    v-for="(option, optIndex) in question.options"
                    :key="optIndex"
                    class="option-item"
                  >
                    <el-radio :label="option.id || option">
                      <span class="option-label">{{ option.id || (optIndex + 1) }}.</span>
                      <span class="option-text">{{ option.text || option }}</span>
                    </el-radio>
                  </div>
                </el-radio-group>
              </div>

              <!-- 多选题 -->
              <div v-else-if="question.question_type === '多选题' || question.question_type === 'multiple_choice' || question.question_type === '多选'" class="options-container">
                <el-checkbox-group v-model="answers[question.id]">
                  <div
                    v-for="(option, optIndex) in question.options"
                    :key="optIndex"
                    class="option-item"
                  >
                    <el-checkbox :label="option.id || option">
                      <span class="option-label">{{ option.id || (optIndex + 1) }}.</span>
                      <span class="option-text">{{ option.text || option }}</span>
                    </el-checkbox>
                  </div>
                </el-checkbox-group>
              </div>
              
              <!-- 填空题/简答题 -->
              <div v-else class="question-input">
                <el-input
                  v-model="answers[question.id]"
                  type="textarea"
                  :rows="question.question_type === '简答题' ? 6 : 3"
                  :placeholder="`请输入${question.question_type}答案`"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="exam-actions">
          <el-button type="primary" @click="submitExam" :loading="submitting">
            提交试卷
          </el-button>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, InfoFilled } from '@element-plus/icons-vue'
import { examApi } from '@/api/exam'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const error = ref('')
const exam = ref(null)
const questions = ref([])
const examStarted = ref(false)
const examCompleted = ref(false)
const startingExam = ref(false)
const submitting = ref(false)
const remainingTime = ref(0)
const examResult = ref(null)

// 考生信息
const studentInfo = reactive({
  name: '',
  department: ''
})

// 表单验证规则
const studentRules = {
  name: [
    { required: true, message: '请输入考生姓名', trigger: 'blur' }
  ],
  department: [
    { required: true, message: '请输入部门名称', trigger: 'blur' }
  ]
}

// 答案数据
const answers = ref({})

// 定时器
let timer = null

// 表单引用
const studentFormRef = ref()

// 加载试卷
const loadExam = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const examId = route.params.examId
    console.log('Loading exam with ID:', examId)
    
    const response = await examApi.getExam(examId)
    console.log('API response:', response)
    
    if (!response) {
      throw new Error('API返回空数据')
    }
    
    exam.value = response
    questions.value = response.questions || []
    
    console.log('Exam loaded:', exam.value)
    console.log('Questions loaded:', questions.value)

    // 调试信息
    console.log('Questions type check:', questions.value.map(q => ({
      id: q.id,
      type: q.question_type,
      isMultiple: q.question_type === '多选题' || q.question_type === 'multiple_choice' || q.question_type === '多选',
      options: q.options
    })))

    // 初始化答案对象
    questions.value.forEach(question => {
      if (question.question_type === '多选题' || question.question_type === 'multiple_choice' || question.question_type === '多选') {
        answers.value[question.id] = []
      } else {
        answers.value[question.id] = ''
      }
    })

    console.log('Answers initialized:', answers.value)
    
    // 设置考试时长
    if (exam.value && exam.value.duration) {
      remainingTime.value = exam.value.duration * 60 // 转换为秒
    } else {
      console.warn('试卷时长信息缺失')
      remainingTime.value = 60 * 60 // 默认60分钟
    }
    
  } catch (err) {
    console.error('加载试卷失败:', err)
    error.value = err.message || '试卷不存在或已失效'
  } finally {
    loading.value = false
  }
}

// 开始考试
const startExam = async () => {
  if (!studentFormRef.value) return
  
  try {
    await studentFormRef.value.validate()
    startingExam.value = true
    
    // 这里可以调用API记录考试开始
    examStarted.value = true
    startTimer()
    
    ElMessage.success('考试已开始，请认真答题')
  } catch (error) {
    console.log('表单验证失败:', error)
  } finally {
    startingExam.value = false
  }
}

// 开始计时
const startTimer = () => {
  timer = setInterval(() => {
    if (remainingTime.value > 0) {
      remainingTime.value--
    } else {
      // 时间到，自动提交
      ElMessage.warning('考试时间已到，系统将自动提交试卷')
      submitExam()
    }
  }, 1000)
}

// 格式化时间
const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  } else {
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }
}

// 提交试卷
const submitExam = async () => {
  try {
    await ElMessageBox.confirm('确定要提交试卷吗？提交后将无法修改答案。', '确认提交', {
      confirmButtonText: '确定提交',
      cancelButtonText: '继续答题',
      type: 'warning'
    })
    
    submitting.value = true
    // 提交时自动滚动到页面顶部，确保可见等待提示
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      // 兼容不支持行为参数的环境
      window.scrollTo(0, 0)
    }
    
    // 准备提交数据
    const submitData = {
      exam_id: exam.value.id,
      student_name: studentInfo.name,
      department: studentInfo.department,
      answers: answers.value,
      exam_content: JSON.stringify({
        title: exam.value.title,
        questions: questions.value,
        total_score: exam.value.total_score,
        duration: exam.value.duration * 60 - remainingTime.value // 实际用时
      })
    }
    
    // 提交到后端
    const result = await examApi.submitExam(submitData)

    // 调试日志
    console.log('提交结果:', result)
    console.log('考试结果数据:', result.questions)
    
    // 停止计时器
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    
    ElMessage.success('试卷提交成功，正在跳转到结果页面...')
    
    // 跳转到考试结果页面
    if (result.exam_result_id) {
      router.push(`/exam-result/${result.exam_result_id}`)
    } else {
      ElMessage.error('无法获取考试结果ID')
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('提交试卷失败:', error)
      ElMessage.error('提交失败，请重试')
    }
  } finally {
    submitting.value = false
  }
}

// 计算得分百分比
const getScorePercentage = () => {
  if (!examResult.value || !examResult.value.total_possible_score) return 0
  const percentage = (examResult.value.total_actual_score / examResult.value.total_possible_score) * 100
  return percentage.toFixed(1)
}

// 获取得分样式类
const getScoreClass = (actualScore, totalScore) => {
  const percentage = (actualScore / totalScore) * 100
  if (percentage >= 80) return 'score-excellent'
  if (percentage >= 60) return 'score-good'
  return 'score-poor'
}

// 获取答案样式类
const getAnswerClass = (studentAnswer, correctAnswer) => {
  if (!studentAnswer || studentAnswer === '未作答') return 'answer-unanswered'
  if (studentAnswer === correctAnswer) return 'answer-correct'
  return 'answer-incorrect'
}

// 页面加载时获取试卷
onMounted(() => {
  loadExam()
})

// 页面卸载时清理定时器
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.grading-banner {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 10px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 3000; /* 高于Element Plus默认遮罩层 */
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
.exam-share-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
}

.loading-container,
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.student-info-container {
  max-width: 800px;
  margin: 0 auto;
}

.exam-header {
  text-align: center;
  margin-bottom: 30px;
  padding: 30px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.exam-header h1 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 28px;
}

.exam-header h2 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.exam-meta {
  margin-bottom: 15px;
}

.exam-meta .el-tag {
  margin: 0 8px;
}

.exam-description {
  color: #606266;
  font-size: 16px;
  line-height: 1.6;
  margin: 0;
}

.student-form-card {
  max-width: 500px;
  margin: 0 auto;
}

.exam-container {
  max-width: 1000px;
  margin: 0 auto;
}

.exam-timer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 10px 20px;
  border-radius: 6px;
  margin-top: 15px;
}

.exam-content {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.question-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 36px;
  margin-bottom: 28px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.question-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.question-item:hover {
  transform: translateY(-4px);
  border-color: #c7d2fe;
  box-shadow: 0 16px 48px rgba(102, 126, 234, 0.15);
}

.question-item:hover::before {
  opacity: 1;
}

.question-item:last-child {
  margin-bottom: 0;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 2px solid #f1f5f9;
}

.question-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 20px;
  font-weight: 700;
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.question-type {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  padding: 10px 20px;
  border-radius: 25px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.question-score {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
  padding: 10px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
}

.question-text {
  font-size: 16px;
  line-height: 1.6;
  color: #1e293b;
  margin-bottom: 20px;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.options-container {
  display: grid;
  gap: 12px;
}

.option-item {
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.option-item:hover {
  background: #f1f5f9;
  border-color: #c7d2fe;
  transform: translateX(4px);
}

.option-item :deep(.el-radio) {
  width: 100%;
  margin: 0;
}

.option-item :deep(.el-radio__input) {
  margin-right: 16px;
}

.option-item :deep(.el-radio__inner) {
  width: 24px;
  height: 24px;
  border: 3px solid #d1d5db;
  background: #ffffff;
}

.option-item :deep(.el-radio__inner::after) {
  width: 10px;
  height: 10px;
  background: #667eea;
  border-radius: 50%;
}

.option-item :deep(.el-radio__input.is-checked .el-radio__inner) {
  border-color: #667eea;
  background: #ffffff;
}

.option-item :deep(.el-radio__label) {
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
  font-weight: 500;
  word-wrap: break-word;
  word-break: break-all;
  white-space: normal;
  display: flex;
  align-items: flex-start;
}

.option-item :deep(.el-checkbox) {
  width: 100%;
  margin: 0;
}

.option-item :deep(.el-checkbox__input) {
  margin-right: 16px;
}

.option-item :deep(.el-checkbox__inner) {
  width: 24px;
  height: 24px;
  border: 3px solid #d1d5db;
  background: #ffffff;
  border-radius: 6px;
}

.option-item :deep(.el-checkbox__inner::after) {
  border: 3px solid #667eea;
  border-left: 0;
  border-top: 0;
  height: 12px;
  left: 6px;
  top: 2px;
  width: 6px;
}

.option-item :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  border-color: #667eea;
  background: #ffffff;
}

.option-item :deep(.el-checkbox__label) {
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
  font-weight: 500;
  word-wrap: break-word;
  word-break: break-all;
  white-space: normal;
  display: flex;
  align-items: flex-start;
}

.option-label {
  font-weight: 700;
  color: #667eea;
  margin-right: 8px;
  flex-shrink: 0;
}

.option-text {
  flex: 1;
  word-wrap: break-word;
  word-break: break-all;
  white-space: normal;
}

.question-input {
  margin-left: 20px;
}

.exam-actions {
  text-align: center;
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid #ebeef5;
}

.result-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-top: 50px;
}

.result-header {
  margin-bottom: 40px;
}

.result-summary {
  text-align: center;
  margin-top: 20px;
}

.score-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 15px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.score-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.score-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}

.score-divider {
  font-size: 24px;
  color: #c0c4cc;
  font-weight: bold;
}

.score-percentage {
  font-size: 18px;
  color: #67c23a;
  font-weight: 600;
}

.detailed-results {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.results-title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
  font-size: 24px;
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

.question-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.question-number {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.question-type-tag {
  background: #e7f3ff;
  color: #409eff;
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 12px;
  font-weight: 500;
}

.score-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.actual-score {
  font-size: 18px;
  font-weight: bold;
  padding: 6px 12px;
  border-radius: 8px;
}

.score-excellent {
  background: #f0f9ff;
  color: #67c23a;
}

.score-good {
  background: #fff7e6;
  color: #e6a23c;
}

.score-poor {
  background: #fef2f2;
  color: #f56c6c;
}

.total-score {
  color: #909399;
  font-size: 14px;
}

.question-content {
  margin-top: 16px;
}

.question-text {
  font-size: 16px;
  line-height: 1.6;
  color: #303133;
  margin-bottom: 16px;
  font-weight: 500;
}

.question-options {
  margin: 16px 0;
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.option-display {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.option-display:last-child {
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

.answer-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}

.answer-row:last-child {
  margin-bottom: 0;
}

.answer-label {
  font-weight: 600;
  font-size: 14px;
  min-width: 80px;
  flex-shrink: 0;
}

.answer-label.correct {
  color: #67c23a;
}

.answer-label.student {
  color: #409eff;
}

.answer-content {
  flex: 1;
  font-size: 14px;
  line-height: 1.5;
  padding: 6px 12px;
  border-radius: 6px;
  word-wrap: break-word;
}

.answer-content.correct {
  background: #f0f9ff;
  color: #67c23a;
  border: 1px solid #b3e19d;
}

.answer-content.answer-correct {
  background: #f0f9ff;
  color: #67c23a;
  border: 1px solid #b3e19d;
}

.answer-content.answer-incorrect {
  background: #fef2f2;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
}

.answer-content.answer-unanswered {
  background: #f5f5f5;
  color: #909399;
  border: 1px solid #d3d3d3;
  font-style: italic;
}

.question-explanation {
  margin-top: 20px;
  padding: 16px;
  background: #fef9e7;
  border: 1px solid #f7d794;
  border-radius: 8px;
}

.explanation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #e6a23c;
  font-weight: 600;
  font-size: 14px;
}

.explanation-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}
</style>