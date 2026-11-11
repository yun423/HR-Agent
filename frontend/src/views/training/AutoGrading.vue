<template>
  <div class="auto-grading">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">
            <el-icon><Checked /></el-icon>
            智能自动阅卷
          </h1>
          <p class="page-subtitle">
            基于AI技术的智能试卷批改与评分系统
          </p>
        </div>
        
        <!-- 头部筛选区域 -->
        <div class="header-filters">
          <div class="filter-row">
            <div class="filter-item">
              <label>考试名称：</label>
              <el-select 
                v-model="examNameFilter" 
                placeholder="请选择考试名称" 
                clearable
                style="width: 200px"
              >
                <el-option label="全部" value="" />
                <el-option label="数学期末考试" value="数学期末考试" />
                <el-option label="英语月考" value="英语月考" />
                <el-option label="物理单元测试" value="物理单元测试" />
                <el-option label="化学实验考核" value="化学实验考核" />
              </el-select>
            </div>
            
            <div class="filter-item">
              <label>学生姓名：</label>
              <el-input
                v-model="studentNameFilter"
                placeholder="请输入学生姓名"
                clearable
                style="width: 200px"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            
            <div class="filter-item">
              <label>状态：</label>
              <el-select 
                v-model="statusFilter" 
                placeholder="请选择状态" 
                clearable
                style="width: 150px"
              >
                <el-option label="全部" value="" />
                <el-option label="待批改" value="pending" />
                <el-option label="批改中" value="processing" />
                <el-option label="已完成" value="completed" />
              </el-select>
            </div>
            
            <div class="filter-item">
              <el-button type="primary" @click="applyFilters">
                <el-icon><Search /></el-icon>
                筛选
              </el-button>
              <el-button @click="resetFilters">重置</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 主要内容区域 - 左右分栏布局 -->
      <div class="main-content">
        <!-- 左侧：考生试卷选择区域 -->
        <div class="left-panel">
          <el-card class="exam-selection-card">
            <template #header>
              <div class="card-header">
                <el-icon><Document /></el-icon>
                <span>考生试卷选择</span>
              </div>
            </template>



            <!-- 考生试卷列表 -->
            <div class="exam-list">
              <div 
                v-for="exam in filteredExams" 
                :key="exam.id"
                class="exam-item"
                :class="{ 'selected': selectedExam?.id === exam.id }"
                @click="selectExam(exam)"
              >
                <div class="exam-content">
                  <div class="exam-header">
                    <div class="student-name">{{ exam.studentName }}</div>
                    <el-tag 
                      :type="getStatusType(exam.status)" 
                      size="small"
                    >
                      {{ getStatusLabel(exam.status) }}
                    </el-tag>
                  </div>
                  <div class="exam-info">
                    <div class="exam-title">{{ exam.examTitle }}</div>
                    <div class="exam-meta">
                      <div class="submit-time">
                        <el-icon><Clock /></el-icon>
                        {{ formatTime(exam.submitTime) }}
                      </div>
                      <div v-if="exam.status === 'completed'" class="score-display">
                        <el-tag 
                          :type="getScoreType(exam.score, exam.totalScore)"
                          effect="plain"
                          size="small"
                        >
                          {{ exam.score }}/{{ exam.totalScore }}分
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 每个试卷项目的操作按钮 -->
                <div class="exam-actions" @click.stop>
                  <el-button 
                    v-if="exam.status === 'pending'"
                    type="primary" 
                    size="small"
                    @click="startGradingForExam(exam)"
                    :loading="gradingLoading && selectedExam?.id === exam.id"
                  >
                    <el-icon><Checked /></el-icon>
                    开始阅卷
                  </el-button>
                  
                  <el-button 
                    v-else-if="exam.status === 'processing'"
                    type="warning" 
                    size="small"
                    loading
                    disabled
                  >
                    <el-icon><Loading /></el-icon>
                    阅卷中...
                  </el-button>
                  
                  <el-button 
                    v-else-if="exam.status === 'completed'"
                    type="success" 
                    size="small"
                    @click="viewExamResult(exam)"
                  >
                    <el-icon><Document /></el-icon>
                    查看结果
                  </el-button>
                </div>
              </div>
            </div>


          </el-card>
        </div>

        <!-- 右侧：阅卷结果展示区域 -->
        <div class="right-panel">
          <el-card class="grading-result-card">
            <template #header>
              <div class="card-header">
                <el-icon><EditPen /></el-icon>
                <span>阅卷结果</span>
              </div>
            </template>

            <!-- 未选择试卷时的提示 -->
            <div v-if="!selectedExam" class="empty-state">
              <el-empty description="请先选择要阅卷的试卷" />
            </div>

            <!-- 选择了试卷但未开始阅卷 -->
            <div v-else-if="selectedExam.status === 'pending'" class="pending-state">
              <div class="exam-preview">
                <h3>{{ selectedExam.studentName }} - {{ selectedExam.examTitle }}</h3>
                <p>提交时间：{{ formatTime(selectedExam.submitTime) }}</p>
                <p>总分：{{ selectedExam.totalScore }}分</p>
                <el-divider />
                <p class="hint">点击左侧"开始阅卷"按钮开始自动批改</p>
              </div>
            </div>

            <!-- 阅卷中状态 -->
            <div v-else-if="selectedExam.status === 'processing'" class="processing-state">
              <div class="loading-content">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <h3>正在智能阅卷中...</h3>
                <p>AI正在分析试卷内容并进行评分，请稍候</p>
                <el-progress :percentage="gradingProgress" :show-text="true" />
              </div>
            </div>

            <!-- 阅卷完成状态 -->
            <div v-else-if="selectedExam.status === 'completed'" class="completed-state"
                 style="flex: 1; overflow-y: auto; padding: 20px;"
            >
              <!-- 试卷头部信息 -->
              <div class="exam-content">
                <div class="exam-header">
                  <h2>{{ selectedExam.examTitle }}</h2>
                  <div class="exam-info">
                    <span>学生姓名：{{ selectedExam.studentName }}</span>
                    <span>总分：{{ selectedExam.totalScore }}分</span>
                    <span>得分：{{ selectedExam.score }}分</span>
                    <span>准确率：{{ selectedExam.accuracy }}%</span>
                  </div>
                </div>

                <!-- 题目详细评分 -->
                <div class="exam-sections">
                  <div class="exam-section">
                    <h3>阅卷结果详情</h3>
                    
                    <div class="questions-list">
                      <div 
                        v-for="(question, index) in selectedExam.questions" 
                        :key="index"
                        class="question-item"
                      >
                        <div class="question-header">
                          <span class="question-number">{{ index + 1 }}.</span>
                          <div class="score-display">
                            <span class="question-score earned-score">得分：{{ question.earnedScore || 0 }}分</span>
                            <span class="question-score total-score">（满分：{{ question.totalScore }}分）</span>
                          </div>
                        </div>
                        
                        <div class="question-content">
                          <p class="question-text">{{ question.content }}</p>
                          
                          <!-- 选择题选项 -->
                          <div v-if="question.options" class="question-options">
                            <div 
                              v-for="(option, optIndex) in question.options" 
                              :key="optIndex"
                              class="option-item"
                              :class="{ 
                                'correct-option': question.correctAnswer === String.fromCharCode(65 + optIndex),
                                'student-option': question.studentAnswer === String.fromCharCode(65 + optIndex)
                              }"
                            >
                              <span class="option-label">{{ String.fromCharCode(65 + optIndex) }}.</span>
                              <span>{{ option }}</span>
                              <span v-if="question.correctAnswer === String.fromCharCode(65 + optIndex)" class="correct-mark">✓ 正确答案</span>
                              <span v-if="question.studentAnswer === String.fromCharCode(65 + optIndex)" class="student-mark">学生选择</span>
                            </div>
                          </div>
                          
                          <!-- 填空题和简答题 -->
                          <div v-if="question.type === '填空题' || question.type === '简答题'" class="answer-comparison">
                            <div class="student-answer">
                              <h5>学生答案：</h5>
                              <div class="answer-content">{{ question.studentAnswer }}</div>
                            </div>
                            <div class="correct-answer">
                              <h5>参考答案：</h5>
                              <div class="answer-content">{{ question.correctAnswer }}</div>
                            </div>
                          </div>
                          
                          <!-- 编程题 -->
                          <div v-if="question.type === '编程题'" class="coding-comparison">
                            <div class="student-code">
                              <h5>学生代码：</h5>
                              <div class="code-content">
                                <pre>{{ question.studentAnswer }}</pre>
                              </div>
                            </div>
                            <div class="reference-code">
                              <h5>参考代码：</h5>
                              <div class="code-content">
                                <pre>{{ question.correctAnswer }}</pre>
                              </div>
                            </div>
                          </div>
                          
                          <!-- 评分理由 -->
                          <div class="grading-feedback">
                            <h5>评分说明：</h5>
                            <p class="feedback-text">{{ question.gradingReason }}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="result-actions">
                  <el-button @click="downloadReport">
                    <el-icon><Download /></el-icon>
                    下载报告
                  </el-button>
                  <el-button @click="exportScore">
                    <el-icon><Document /></el-icon>
                    导出成绩
                  </el-button>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 上传试卷对话框保持不变 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传试卷"
      width="600px"
      :before-close="handleUploadClose"
    >
      <el-form 
        ref="uploadFormRef" 
        :model="uploadForm" 
        :rules="uploadRules" 
        label-width="100px"
      >
        <el-form-item label="试卷标题" prop="title">
          <el-input 
            v-model="uploadForm.title" 
            placeholder="请输入试卷标题"
          />
        </el-form-item>
        
        <el-form-item label="考试科目" prop="subject">
          <el-select 
            v-model="uploadForm.subject" 
            placeholder="请选择考试科目"
            style="width: 100%"
          >
            <el-option label="前端开发" value="frontend" />
            <el-option label="后端开发" value="backend" />
            <el-option label="数据库" value="database" />
            <el-option label="算法与数据结构" value="algorithm" />
            <el-option label="系统设计" value="system" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="总分" prop="totalScore">
          <el-input-number 
            v-model="uploadForm.totalScore" 
            :min="1" 
            :max="1000"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="试卷文件" prop="files">
          <el-upload
            ref="uploadRef"
            :file-list="uploadForm.files"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :before-upload="() => false"
            accept=".pdf,.doc,.docx,.txt"
            drag
            multiple
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、Word、TXT 格式，单个文件不超过 10MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleUploadClose">取消</el-button>
          <el-button 
            type="primary" 
            @click="handleUpload"
            :loading="uploading"
          >
            {{ uploading ? '上传中...' : '确定上传' }}
          </el-button>
        </span>
      </template>
    </el-dialog>


  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Checked, EditPen, Loading, Document, Download, Search } from '@element-plus/icons-vue'

// 响应式数据
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const examNameFilter = ref('')
const studentNameFilter = ref('')
const showUploadDialog = ref(false)
const uploading = ref(false)
const selectedExam = ref(null)
const gradingLoading = ref(false)
const gradingProgress = ref(0)

// 统计数据
const stats = reactive({
  pending: 15,
  processing: 3,
  completed: 127,
  averageScore: 85.6
})

// 上传表单
const uploadForm = reactive({
  title: '',
  subject: '',
  totalScore: 100,
  files: []
})

const uploadRules = {
  title: [
    { required: true, message: '请输入试卷标题', trigger: 'blur' }
  ],
  subject: [
    { required: true, message: '请选择考试科目', trigger: 'change' }
  ],
  totalScore: [
    { required: true, message: '请输入总分', trigger: 'blur' }
  ]
}

// 试卷数据
const exams = ref([
  {
    id: 1,
    studentName: '张三',
    examTitle: 'JavaScript基础测试',
    submitTime: '2024-01-15T14:30:00Z',
    status: 'completed',
    score: 85,
    totalScore: 100,
    accuracy: 85,
    questions: [
      {
        type: '选择题',
        content: '以下哪个选项正确描述了JavaScript中的闭包？',
        options: [
          '闭包是一种特殊的函数，只能在全局作用域中定义',
          '闭包是指函数可以访问其外部作用域的变量，即使外部函数已经执行完毕',
          '闭包只能访问自己内部定义的变量',
          '闭包是JavaScript中的一种数据类型'
        ],
        studentAnswer: 'B',
        correctAnswer: 'B',
        totalScore: 20,
        earnedScore: 20,
        gradingReason: '完全正确！准确理解了闭包的核心概念，选择了正确答案。'
      },
      {
        type: '选择题',
        content: '以下哪个方法可以阻止事件冒泡？',
        options: [
          'event.preventDefault()',
          'event.stopPropagation()',
          'event.stopImmediatePropagation()',
          'event.cancelBubble = true'
        ],
        studentAnswer: 'B',
        correctAnswer: 'B',
        totalScore: 15,
        earnedScore: 15,
        gradingReason: '完全正确！准确选择了阻止事件冒泡的标准方法。'
      },
      {
        type: '简答题',
        content: '请写出数组去重的三种方法（要求给出具体代码实现）',
        studentAnswer: '1. 使用Set: [...new Set(arr)]\n2. 使用filter和indexOf: arr.filter((item, index) => arr.indexOf(item) === index)\n3. 使用reduce方法: arr.reduce((unique, item) => unique.includes(item) ? unique : [...unique, item], [])',
        correctAnswer: '1. 使用Set: [...new Set(arr)]\n2. 使用filter和indexOf: arr.filter((item, index) => arr.indexOf(item) === index)\n3. 使用reduce: arr.reduce((unique, item) => unique.includes(item) ? unique : [...unique, item], [])\n4. 使用Map: [...new Map(arr.map(item => [item, item])).values()]',
        totalScore: 25,
        earnedScore: 25,
        gradingReason: '优秀！提供了三种有效的去重方法，代码实现完全正确，逻辑清晰。'
      },
      {
        type: '填空题',
        content: 'Promise有三种状态：______（等待中）、______（已成功）、______（已失败）',
        studentAnswer: 'pending、fulfilled、rejected',
        correctAnswer: 'pending、fulfilled、rejected',
        totalScore: 20,
        earnedScore: 20,
        gradingReason: '完美回答！准确填写了Promise的三种状态名称。'
      },
      {
        type: '编程题',
        content: '请实现一个简单的防抖函数debounce',
        studentAnswer: 'function debounce(func, delay) {\n  let timer;\n  return function(...args) {\n    clearTimeout(timer);\n    timer = setTimeout(() => func.apply(this, args), delay);\n  };\n}',
        correctAnswer: 'function debounce(func, delay) {\n  let timer;\n  return function(...args) {\n    clearTimeout(timer);\n    timer = setTimeout(() => func.apply(this, args), delay);\n  };\n}',
        totalScore: 20,
        earnedScore: 20,
        gradingReason: '完美实现！代码逻辑正确，正确使用了闭包和setTimeout，处理了this绑定和参数传递。'
      }
    ]
  },
  {
    id: 2,
    studentName: '李四',
    examTitle: 'Vue.js进阶测试',
    submitTime: '2024-01-15T15:45:00Z',
    status: 'pending',
    score: null,
    totalScore: 100,
    accuracy: null,
    questions: [
      {
        content: '请解释Vue 3中Composition API的优势',
        studentAnswer: 'Composition API提供了更好的逻辑复用性，可以将相关的逻辑组织在一起，比Options API更灵活。支持TypeScript更好，代码组织更清晰。',
        totalScore: 25,
        earnedScore: 0, // 待阅卷
        gradingReason: '' // 待生成
      },
      {
        content: '什么是响应式原理？Vue 3相比Vue 2有什么改进？',
        studentAnswer: 'Vue的响应式原理是通过数据劫持实现的。Vue 2使用Object.defineProperty，Vue 3使用Proxy，性能更好，支持数组索引和对象属性的动态添加。',
        totalScore: 30,
        earnedScore: 0,
        gradingReason: ''
      },
      {
        content: '请实现一个自定义指令v-focus',
        studentAnswer: 'app.directive("focus", { mounted(el) { el.focus(); } });',
        totalScore: 20,
        earnedScore: 0,
        gradingReason: ''
      },
      {
        content: '解释Vue Router的导航守卫及其应用场景',
        studentAnswer: '导航守卫包括全局守卫、路由独享守卫和组件内守卫。可以用于权限控制、页面跳转确认、数据预加载等场景。beforeEach是最常用的全局前置守卫。',
        totalScore: 25,
        earnedScore: 0,
        gradingReason: ''
      }
    ]
  },
  {
    id: 3,
    studentName: '王五',
    examTitle: 'React组件开发',
    submitTime: '2024-01-15T16:20:00Z',
    status: 'pending',
    score: null,
    totalScore: 100,
    accuracy: null,
    questions: [
      {
        content: '请解释React Hooks的使用规则',
        studentAnswer: 'Hooks只能在函数组件的顶层调用，不能在循环、条件语句或嵌套函数中调用。这是为了确保每次渲染时Hooks的调用顺序保持一致。',
        totalScore: 20,
        earnedScore: 0,
        gradingReason: ''
      },
      {
        content: '什么是受控组件和非受控组件？',
        studentAnswer: '受控组件的表单数据由React组件的state管理，非受控组件的数据由DOM自身管理。受控组件通过onChange事件更新state，非受控组件使用ref获取值。',
        totalScore: 25,
        earnedScore: 0,
        gradingReason: ''
      },
      {
        content: '请实现一个简单的useCounter自定义Hook',
        studentAnswer: 'function useCounter(initialValue = 0) { const [count, setCount] = useState(initialValue); const increment = () => setCount(count + 1); const decrement = () => setCount(count - 1); return { count, increment, decrement }; }',
        totalScore: 30,
        earnedScore: 0,
        gradingReason: ''
      },
      {
        content: '解释React的虚拟DOM和Diff算法',
        studentAnswer: '虚拟DOM是React在内存中维护的DOM表示，通过比较新旧虚拟DOM树的差异来最小化实际DOM操作。Diff算法采用同层比较，通过key优化列表渲染性能。',
        totalScore: 25,
        earnedScore: 0,
        gradingReason: ''
      }
    ]
  }
])

// 计算属性
const filteredExams = computed(() => {
  return exams.value.filter(exam => {
    const matchesExamName = !examNameFilter.value || exam.examTitle.includes(examNameFilter.value)
    const matchesStudentName = !studentNameFilter.value || exam.studentName.includes(studentNameFilter.value)
    const matchesStatus = !statusFilter.value || exam.status === statusFilter.value
    
    return matchesExamName && matchesStudentName && matchesStatus
  })
})

// 方法
const formatTime = (timeString) => {
  return new Date(timeString).toLocaleString('zh-CN')
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    processing: 'primary',
    completed: 'success'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待批改',
    processing: '批改中',
    completed: '已完成'
  }
  return labels[status] || '未知'
}

// 选择试卷
const selectExam = (exam) => {
  selectedExam.value = exam
}

// 模拟AI阅卷逻辑
const simulateAIGrading = (question) => {
  const { content, studentAnswer, totalScore } = question
  
  // 根据题目类型和答案质量模拟评分
  let earnedScore = 0
  let gradingReason = ''
  
  // 简单的关键词匹配和长度评估
  const answerLength = studentAnswer.length
  const hasCodeExample = studentAnswer.includes('(') || studentAnswer.includes('{') || studentAnswer.includes('function')
  
  if (content.includes('解释') || content.includes('什么是')) {
    // 概念解释题
    if (answerLength > 50) {
      earnedScore = Math.floor(totalScore * (0.8 + Math.random() * 0.2))
      gradingReason = '概念理解基本正确，表述较为清晰。'
    } else {
      earnedScore = Math.floor(totalScore * (0.5 + Math.random() * 0.3))
      gradingReason = '概念理解基本正确，但表述过于简单，缺少详细说明。'
    }
  } else if (content.includes('实现') || content.includes('写出')) {
    // 代码实现题
    if (hasCodeExample) {
      earnedScore = Math.floor(totalScore * (0.85 + Math.random() * 0.15))
      gradingReason = '代码实现正确，语法规范，逻辑清晰。'
    } else {
      earnedScore = Math.floor(totalScore * (0.4 + Math.random() * 0.3))
      gradingReason = '思路正确但缺少具体代码实现，建议提供完整的代码示例。'
    }
  } else if (content.includes('优势') || content.includes('改进')) {
    // 比较分析题
    if (answerLength > 80) {
      earnedScore = Math.floor(totalScore * (0.75 + Math.random() * 0.25))
      gradingReason = '分析较为全面，能够指出主要优势和改进点。'
    } else {
      earnedScore = Math.floor(totalScore * (0.6 + Math.random() * 0.2))
      gradingReason = '分析基本正确，但不够深入，可以补充更多细节。'
    }
  } else {
    // 其他类型题目
    earnedScore = Math.floor(totalScore * (0.7 + Math.random() * 0.3))
    gradingReason = '回答基本符合题意，理解正确。'
  }
  
  // 确保分数不超过总分
  earnedScore = Math.min(earnedScore, totalScore)
  
  return { earnedScore, gradingReason }
}

// 应用筛选
const applyFilters = () => {
  ElMessage.success('筛选条件已应用')
}

// 重置筛选
const resetFilters = () => {
  examNameFilter.value = ''
  studentNameFilter.value = ''
  statusFilter.value = ''
  ElMessage.info('筛选条件已重置')
}

// 为特定试卷开始阅卷
const startGradingForExam = async (exam) => {
  selectedExam.value = exam
  await startGrading()
}

// 查看试卷结果
const viewExamResult = (exam) => {
  selectedExam.value = exam
  ElMessage.success(`正在查看${exam.studentName}的阅卷结果`)
}

// 开始阅卷
const startGrading = async () => {
  if (!selectedExam.value) return
  
  try {
    gradingLoading.value = true
    gradingProgress.value = 0
    selectedExam.value.status = 'processing'
    
    ElMessage.info('开始AI智能阅卷...')
    
    // 模拟逐题阅卷过程
    const questions = selectedExam.value.questions
    const totalQuestions = questions.length
    
    for (let i = 0; i < totalQuestions; i++) {
      // 更新进度
      gradingProgress.value = ((i + 1) / totalQuestions) * 100
      
      // 模拟阅卷延迟
      await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 400))
      
      // 为当前题目生成评分
      const gradingResult = simulateAIGrading(questions[i])
      questions[i].earnedScore = gradingResult.earnedScore
      questions[i].gradingReason = gradingResult.gradingReason
      
      ElMessage.info(`正在阅卷第${i + 1}题...`)
    }
    
    // 完成阅卷，更新状态和分数
    selectedExam.value.status = 'completed'
    selectedExam.value.score = selectedExam.value.questions.reduce((total, q) => total + q.earnedScore, 0)
    selectedExam.value.accuracy = Math.floor((selectedExam.value.score / selectedExam.value.totalScore) * 100)
    
    // 更新统计数据
    stats.pending--
    stats.completed++
    
    gradingLoading.value = false
    ElMessage.success(`${selectedExam.value.studentName}的试卷阅卷完成！得分：${selectedExam.value.score}分`)
  } catch (error) {
    selectedExam.value.status = 'pending'
    gradingLoading.value = false
    ElMessage.error('阅卷失败，请重试')
  }
}

// 获取分数等级
const getScoreLevel = (score, totalScore) => {
  const percentage = (score / totalScore) * 100
  if (percentage >= 90) return '优秀'
  if (percentage >= 80) return '良好'
  if (percentage >= 70) return '中等'
  if (percentage >= 60) return '及格'
  return '不及格'
}

// 获取分数类型（用于标签颜色）
const getScoreType = (score, totalScore) => {
  const percentage = (score / totalScore) * 100
  if (percentage >= 90) return 'success'
  if (percentage >= 80) return 'primary'
  if (percentage >= 70) return 'warning'
  if (percentage >= 60) return 'info'
  return 'danger'
}

// 下载报告
const downloadReport = () => {
  if (!selectedExam.value) return
  ElMessage.success(`正在下载${selectedExam.value.studentName}的阅卷报告...`)
}

// 导出成绩
const exportScore = () => {
  if (!selectedExam.value) return
  ElMessage.success(`正在导出${selectedExam.value.studentName}的成绩...`)
}

// 刷新数据
const refreshData = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    ElMessage.success('数据刷新成功')
  }, 1000)
}
</script>

<style lang="scss" scoped>
.auto-grading {
  height: 100%;
  overflow-y: auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
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
  }
  
  .header-filters {
    margin-top: 20px;
    
    .filter-row {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
      
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
        
        .el-select, .el-input {
          min-width: 150px;
        }
      }
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

// 主要内容区域
.main-content {
  display: flex;
  gap: 24px;
  height: calc(100vh - 200px);
  
  .left-panel, .right-panel {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  .left-panel {
    flex: 1;
    min-width: 400px;
    
    .exam-selection-card {
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
  
  .right-panel {
    flex: 1.2;
    min-width: 600px;
    
    .grading-result-card {
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

// 试卷列表
.exam-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  
  // 自定义滚动条样式
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
  
  .exam-item {
    padding: 16px;
    border: 2px solid transparent;
    border-radius: 12px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: #f8fafc;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    &:hover {
      background: #e2e8f0;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    &.selected {
      border-color: #667eea;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
      box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
    }
    
    .exam-content {
      flex: 1;
      
      .exam-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .student-name {
          font-weight: 600;
          font-size: 16px;
          color: #1e293b;
        }
      }
      
      .exam-info {
        display: flex;
        flex-direction: column;
        gap: 4px;
        
        .exam-title {
          color: #64748b;
          font-size: 14px;
        }
        
        .exam-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
          color: #94a3b8;
          
          .submit-time {
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }
      }
    }
    
    .exam-actions {
      margin-left: 16px;
      flex-shrink: 0;
    }
  }
}

// 右侧阅卷结果区域滚动条样式
.grading-result-card {
  :deep(.el-card__body) {
    .empty-state,
    .pending-state,
    .processing-state,
    .completed-state {
      // 自定义滚动条样式
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
    
    .pending-state,
    .processing-state {
      padding: 40px 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
    
    .empty-state {
      padding: 40px 20px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

// 阅卷结果展示样式（与试卷生成页面一致）
.completed-state {
  .exam-content {
    .exam-header {
      text-align: center;
      margin-bottom: 32px;
      padding: 24px;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
      border-radius: 12px;
      border: 1px solid rgba(102, 126, 234, 0.1);
      
      h2 {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 12px 0;
      }
      
      .exam-info {
        display: flex;
        justify-content: center;
        gap: 24px;
        color: #64748b;
        font-size: 14px;
        font-weight: 500;
        
        span {
          padding: 4px 12px;
          background: rgba(255, 255, 255, 0.8);
          border-radius: 6px;
          border: 1px solid rgba(226, 232, 240, 0.5);
        }
      }
    }
    
    .exam-sections {
      .exam-section {
        margin-bottom: 32px;
        
        h3 {
          font-size: 18px;
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 16px 0;
          padding: 12px 16px;
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
          border-radius: 8px;
          border-left: 4px solid #667eea;
        }
      }
    }
  }
}

.questions-list {
  .question-item {
    margin-bottom: 24px;
    padding: 20px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
    border: 1px solid rgba(226, 232, 240, 0.5);
    border-radius: 12px;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
      border-color: rgba(102, 126, 234, 0.3);
    }
    
    .question-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      
      .question-number {
        font-weight: 600;
        color: #667eea;
        font-size: 16px;
      }
      
      .score-display {
        display: flex;
        gap: 8px;
        align-items: center;
        
        .earned-score {
          color: #059669;
          font-weight: 600;
          background: rgba(5, 150, 105, 0.1);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
        }
        
        .total-score {
          color: #64748b;
          font-size: 12px;
          background: rgba(102, 126, 234, 0.1);
          padding: 2px 8px;
          border-radius: 4px;
        }
      }
    }
    
    .question-content {
      .question-text {
        color: #374151;
        line-height: 1.6;
        margin: 0 0 16px 0;
        font-weight: 500;
        font-size: 15px;
      }
      
      .question-options {
        margin-bottom: 16px;
        
        .option-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-bottom: 8px;
          color: #374151;
          padding: 8px 12px;
          background: rgba(248, 250, 252, 0.8);
          border-radius: 6px;
          border: 1px solid rgba(226, 232, 240, 0.5);
          position: relative;
          
          .option-label {
            font-weight: 600;
            min-width: 20px;
            color: #667eea;
          }
          
          &.correct-option {
            background: rgba(5, 150, 105, 0.1);
            border-color: rgba(5, 150, 105, 0.3);
            
            .correct-mark {
              position: absolute;
              right: 8px;
              top: 50%;
              transform: translateY(-50%);
              color: #059669;
              font-weight: 600;
              font-size: 12px;
            }
          }
          
          &.student-option {
            background: rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.3);
            
            .student-mark {
              position: absolute;
              right: 8px;
              top: 50%;
              transform: translateY(-50%);
              color: #3b82f6;
              font-weight: 600;
              font-size: 12px;
            }
          }
          
          &.correct-option.student-option {
            background: rgba(5, 150, 105, 0.15);
            border-color: rgba(5, 150, 105, 0.4);
            
            .student-mark {
              right: 80px;
            }
          }
        }
      }
      
      .answer-comparison {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 16px;
        
        .student-answer, .correct-answer {
          h5 {
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
          }
          
          .answer-content {
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.5;
            white-space: pre-wrap;
          }
        }
        
        .student-answer {
          h5 {
            color: #3b82f6;
          }
          
          .answer-content {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
          }
        }
        
        .correct-answer {
          h5 {
            color: #059669;
          }
          
          .answer-content {
            background: rgba(5, 150, 105, 0.1);
            border: 1px solid rgba(5, 150, 105, 0.2);
          }
        }
      }
      
      .coding-comparison {
        margin-bottom: 16px;
        
        .student-code, .reference-code {
          margin-bottom: 16px;
          
          h5 {
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
          }
          
          .code-content {
            background: linear-gradient(135deg, #1e293b, #334155);
            border-radius: 8px;
            padding: 16px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            
            pre {
              margin: 0;
              font-family: 'Courier New', monospace;
              font-size: 14px;
              color: #e2e8f0;
              line-height: 1.5;
              white-space: pre-wrap;
            }
          }
        }
        
        .student-code h5 {
          color: #3b82f6;
        }
        
        .reference-code h5 {
          color: #059669;
        }
      }
      
      .grading-feedback {
        margin-top: 16px;
        padding: 16px;
        background: rgba(102, 126, 234, 0.05);
        border-radius: 8px;
        border-left: 4px solid #667eea;
        
        h5 {
          margin: 0 0 8px 0;
          font-size: 14px;
          font-weight: 600;
          color: #667eea;
        }
        
        .feedback-text {
          margin: 0;
          color: #374151;
          line-height: 1.6;
          font-size: 14px;
        }
      }
    }
  }
}

.result-actions {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid rgba(226, 232, 240, 0.5);
  display: flex;
  gap: 12px;
  justify-content: center;
  
  .el-button {
    border-radius: 8px;
    font-weight: 500;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
  }
}

// 阅卷结果区域
.grading-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  
  .result-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    
    .question-item {
      background: #f8fafc;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      border-left: 4px solid #e2e8f0;
      
      &.correct {
        border-left-color: #10b981;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(5, 150, 105, 0.05));
      }
      
      &.incorrect {
        border-left-color: #ef4444;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.05), rgba(220, 38, 38, 0.05));
      }
      
      &.partial {
        border-left-color: #f59e0b;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), rgba(217, 119, 6, 0.05));
      }
      
      .question-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        
        .question-number {
          font-weight: 600;
          color: #1e293b;
        }
        
        .question-score {
          display: flex;
          align-items: center;
          gap: 8px;
          
          .earned-score {
            font-weight: 600;
            font-size: 16px;
          }
          
          .total-score {
            color: #94a3b8;
          }
        }
      }
      
      .question-content {
        margin-bottom: 12px;
        
        .question-text {
          color: #374151;
          line-height: 1.6;
          margin-bottom: 8px;
        }
        
        .student-answer {
          background: white;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
          
          .answer-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
          }
          
          .answer-text {
            color: #1e293b;
            line-height: 1.5;
          }
        }
      }
      
      .grading-feedback {
        background: white;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        
        .feedback-label {
          font-size: 12px;
          color: #64748b;
          margin-bottom: 4px;
        }
        
        .feedback-text {
          color: #374151;
          line-height: 1.5;
        }
      }
    }
  }
  
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    
    .empty-icon {
      font-size: 64px;
      margin-bottom: 16px;
      opacity: 0.5;
    }
    
    .empty-text {
      font-size: 16px;
      margin-bottom: 8px;
    }
    
    .empty-description {
      font-size: 14px;
      opacity: 0.8;
    }
  }
}

// 进度条样式
.grading-progress {
  margin: 16px 0;
  
  :deep(.el-progress-bar__outer) {
    background: #e2e8f0;
    border-radius: 8px;
  }
  
  :deep(.el-progress-bar__inner) {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 8px;
  }
}

// 通用样式
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #1e293b;
    
    .el-icon {
      font-size: 18px;
      color: #667eea;
    }
  }
  
  .header-right {
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.score-pending,
.accuracy-pending {
  color: #94a3b8;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.exam-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
    padding: 20px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
    border-radius: 12px;
    border: 1px solid rgba(102, 126, 234, 0.2);
    
    .student-info {
      h3 {
        margin: 0 0 8px 0;
        font-size: 20px;
        font-weight: 600;
        color: #1e293b;
      }
      
      p {
        margin: 0;
        color: #64748b;
      }
    }
    
    .score-info {
      text-align: right;
      
      .final-score {
        font-size: 24px;
        font-weight: 700;
        color: #059669;
        margin-bottom: 4px;
        
        .total {
          font-size: 16px;
          color: #64748b;
        }
      }
      
      .accuracy {
        color: #7c3aed;
        font-weight: 600;
      }
    }
  }
  
  .questions-review {
    .question-review {
      margin-bottom: 24px;
      padding: 20px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
      border: 1px solid rgba(226, 232, 240, 0.5);
      border-radius: 12px;
      
      .question-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        
        .question-number {
          font-weight: 600;
          color: #667eea;
          font-size: 16px;
        }
        
        .question-score {
          font-weight: 600;
          color: #059669;
        }
      }
      
      .question-content {
        .question-text {
          font-weight: 500;
          color: #374151;
          margin-bottom: 16px;
          line-height: 1.6;
        }
        
        .answer-section {
          .student-answer,
          .correct-answer,
          .ai-comment {
            margin-bottom: 16px;
            
            h4 {
              font-size: 14px;
              font-weight: 600;
              margin: 0 0 8px 0;
              color: #1e293b;
            }
            
            p {
              margin: 0;
              padding: 12px;
              background: rgba(248, 250, 252, 0.8);
              border-radius: 8px;
              border: 1px solid rgba(226, 232, 240, 0.5);
              line-height: 1.6;
              color: #374151;
            }
          }
          
          .student-answer h4 {
            color: #3b82f6;
          }
          
          .correct-answer h4 {
            color: #059669;
          }
          
          .ai-comment h4 {
            color: #7c3aed;
          }
        }
      }
    }
  }
}

// 表单样式优化
:deep(.el-form) {
  .el-form-item {
    margin-bottom: 20px;
    
    .el-form-item__label {
      color: #374151;
      font-weight: 600;
    }
  }
  
  .el-input__wrapper {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    &.is-focus {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
    }
  }
  
  .el-select {
    .el-input__wrapper {
      border-radius: 8px;
    }
  }
  
  .el-input-number {
    .el-input__wrapper {
      border-radius: 8px;
    }
  }
}

:deep(.el-upload-dragger) {
  border-radius: 8px;
  border: 2px dashed #cbd5e1;
  background: rgba(248, 250, 252, 0.5);
  transition: all 0.3s ease;
  
  &:hover {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .auto-grading {
    padding: 12px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    padding: 20px;
    
    .header-actions {
      width: 100%;
      justify-content: center;
    }
  }
  
  .card-header {
    flex-direction: column;
    gap: 16px;
    
    .header-right {
      width: 100%;
      justify-content: space-between;
    }
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-card {
    padding: 16px;
    
    .stat-icon {
      width: 50px;
      height: 50px;
      font-size: 20px;
    }
    
    .stat-content .stat-number {
      font-size: 24px;
    }
  }
  
  .detail-header {
    flex-direction: column !important;
    gap: 16px;
    
    .score-info {
      text-align: left !important;
    }
  }
}
</style>