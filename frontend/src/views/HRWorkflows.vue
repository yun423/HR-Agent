<template>
  <div class="hr-workflows">
     
    <div class="workflow-tabs">
      <el-tabs v-model="activeTab" @tab-click="handleTabClick">
        <el-tab-pane label="生成JD" name="jd">
          <div class="workflow-form">
            <h3>岗位JD生成</h3>
            <el-form :model="jdForm" label-width="120px">
              <el-form-item label="岗位名称">
                <el-input v-model="jdForm.positionTitle" placeholder="请输入岗位名称" />
              </el-form-item>
              <el-form-item label="部门">
                <el-input v-model="jdForm.department" placeholder="请输入部门" />
              </el-form-item>
              <el-form-item label="经验要求">
                <el-select v-model="jdForm.experienceLevel" placeholder="请选择经验要求">
                  <el-option label="应届生" value="应届生" />
                  <el-option label="1-3年" value="1-3年" />
                  <el-option label="3-5年" value="3-5年" />
                  <el-option label="5-10年" value="5-10年" />
                  <el-option label="10年以上" value="10年以上" />
                </el-select>
              </el-form-item>
              <el-form-item label="岗位要求">
                <el-input
                  v-model="jdForm.requirements"
                  type="textarea"
                  :rows="4"
                  placeholder="请详细描述岗位要求、技能要求、工作职责等"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="generateJD" :loading="loading">
                  生成JD
                </el-button>
                <el-button @click="clearJDForm">清空</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- <el-tab-pane label="简历评价" name="resume">
          <div class="workflow-form">
            <h3>简历评价模型</h3>
            <el-form :model="resumeForm" label-width="120px">
              <el-form-item label="简历内容">
                <el-input
                  v-model="resumeForm.resumeContent"
                  type="textarea"
                  :rows="6"
                  placeholder="请粘贴简历内容或上传简历文件"
                />
              </el-form-item>
              <el-form-item label="岗位要求">
                <el-input
                  v-model="resumeForm.jobRequirements"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入岗位要求（可选）"
                />
              </el-form-item>
              <el-form-item label="评价标准">
                <el-input
                  v-model="resumeForm.evaluationCriteria"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入评价标准（可选）"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="evaluateResume" :loading="loading">
                  评价简历
                </el-button>
                <el-button @click="clearResumeForm">清空</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane> -->

        <el-tab-pane label="面试方案" name="interview">
          <div class="workflow-form">
            <h3>面试方案生成</h3>
            <el-form :model="interviewForm" label-width="120px">
              <el-form-item label="岗位名称">
                <el-input v-model="interviewForm.positionTitle" placeholder="请输入岗位名称" />
              </el-form-item>
              <el-form-item label="候选人背景">
                <el-input
                  v-model="interviewForm.candidateBackground"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入候选人背景信息（可选）"
                />
              </el-form-item>
              <el-form-item label="面试类型">
                <el-select v-model="interviewForm.interviewType" placeholder="请选择面试类型">
                  <el-option label="技术面试" value="技术面试" />
                  <el-option label="行为面试" value="行为面试" />
                  <el-option label="综合面试" value="综合面试" />
                  <el-option label="终面" value="终面" />
                </el-select>
              </el-form-item>
              <el-form-item label="面试时长">
                <el-select v-model="interviewForm.interviewDuration" placeholder="请选择面试时长">
                  <el-option label="30分钟" value="30分钟" />
                  <el-option label="45分钟" value="45分钟" />
                  <el-option label="60分钟" value="60分钟" />
                  <el-option label="90分钟" value="90分钟" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="generateInterviewPlan" :loading="loading">
                  生成面试方案
                </el-button>
                <el-button @click="clearInterviewForm">清空</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="自定义工作流" name="custom">
          <div class="workflow-form">
            <h3>自定义工作流调用</h3>
            <el-form :model="customForm" label-width="120px">
              <el-form-item label="工作流类型">
                <el-select v-model="customForm.workflowType" placeholder="请选择工作流类型">
                  <el-option
                    v-for="type in workflowTypes"
                    :key="type.type"
                    :label="`${type.type} - ${type.description}`"
                    :value="type.type"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="查询内容">
                <el-input
                  v-model="customForm.query"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入查询内容"
                />
              </el-form-item>
              <el-form-item label="额外参数">
                <el-input
                  v-model="customForm.additionalInputs"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入额外参数（JSON格式，可选）"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="callCustomWorkflow" :loading="loading">
                  调用工作流
                </el-button>
                <el-button @click="clearCustomForm">清空</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="result-section" v-if="showResult">
      <h3>生成结果</h3>
      <div class="result-content">
        <div v-if="loading" class="loading-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在生成中...</span>
        </div>
        <div v-else class="result-text markdown-content">
          <div v-html="renderedResult"></div>
        </div>
      </div>
      <div class="result-actions">
        <el-button @click="copyResult">复制结果</el-button>
        <el-button @click="clearResult">清空结果</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { hrWorkflowsApi } from '@/api/hrWorkflows'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 配置marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {}
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

const activeTab = ref('jd')
const loading = ref(false)
const showResult = ref(false)
const result = ref('')
const workflowTypes = ref([])

// markdown渲染的计算属性
const renderedResult = computed(() => {
  if (!result.value) return ''
  try {
    return marked(result.value)
  } catch (error) {
    console.error('Markdown渲染错误:', error)
    return result.value.replace(/\n/g, '<br>')
  }
})

// 表单数据
const jdForm = reactive({
  positionTitle: '',
  department: '',
  experienceLevel: '',
  requirements: ''
})

const resumeForm = reactive({
  resumeContent: '',
  jobRequirements: '',
  evaluationCriteria: ''
})

const interviewForm = reactive({
  positionTitle: '',
  candidateBackground: '',
  interviewType: '',
  interviewDuration: ''
})

const customForm = reactive({
  workflowType: null,
  query: '',
  additionalInputs: ''
})

// 获取工作流类型列表
const fetchWorkflowTypes = async () => {
  try {
    const response = await hrWorkflowsApi.getWorkflowTypes()
    workflowTypes.value = response.workflow_types
  } catch (error) {
    console.error('获取工作流类型失败:', error)
  }
}

// 生成JD
const generateJD = async () => {
  if (!jdForm.requirements) {
    ElMessage.warning('请输入岗位要求')
    return
  }

  loading.value = true
  showResult.value = true
  result.value = ''

  try {
    const response = await hrWorkflowsApi.generateJD({
      requirements: jdForm.requirements,
      position_title: jdForm.positionTitle,
      department: jdForm.department,
      experience_level: jdForm.experienceLevel,
      stream: true
    })

    await handleStreamResponse(response)
  } catch (error) {
    ElMessage.error('生成JD失败: ' + error.message)
    console.error('生成JD失败:', error)
  } finally {
    loading.value = false
  }
}

// 评价简历
const evaluateResume = async () => {
  if (!resumeForm.resumeContent) {
    ElMessage.warning('请输入简历内容')
    return
  }

  loading.value = true
  showResult.value = true
  result.value = ''

  try {
    const response = await hrWorkflowsApi.evaluateResume({
      resume_content: resumeForm.resumeContent,
      job_requirements: resumeForm.jobRequirements,
      evaluation_criteria: resumeForm.evaluationCriteria,
      stream: true
    })

    await handleStreamResponse(response)
  } catch (error) {
    ElMessage.error('简历评价失败: ' + error.message)
    console.error('简历评价失败:', error)
  } finally {
    loading.value = false
  }
}

// 生成面试方案
const generateInterviewPlan = async () => {
  if (!interviewForm.positionTitle) {
    ElMessage.warning('请输入岗位名称')
    return
  }

  loading.value = true
  showResult.value = true
  result.value = ''

  try {
    const response = await hrWorkflowsApi.generateInterviewPlan({
      position_title: interviewForm.positionTitle,
      candidate_background: interviewForm.candidateBackground,
      interview_type: interviewForm.interviewType,
      interview_duration: interviewForm.interviewDuration,
      stream: true
    })

    await handleStreamResponse(response)
  } catch (error) {
    ElMessage.error('生成面试方案失败: ' + error.message)
    console.error('生成面试方案失败:', error)
  } finally {
    loading.value = false
  }
}

// 调用自定义工作流
const callCustomWorkflow = async () => {
  if (!customForm.workflowType || !customForm.query) {
    ElMessage.warning('请选择工作流类型并输入查询内容')
    return
  }

  loading.value = true
  showResult.value = true
  result.value = ''

  try {
    const response = await hrWorkflowsApi.callCustomWorkflow({
      workflow_type: customForm.workflowType,
      query: customForm.query,
      additional_inputs: customForm.additionalInputs,
      stream: true
    })

    await handleStreamResponse(response)
  } catch (error) {
    ElMessage.error('调用工作流失败: ' + error.message)
    console.error('调用工作流失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理流式响应（缓冲分片并过滤控制事件）
const handleStreamResponse = async (response) => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

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
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (!dataStr) continue
          if (dataStr === '[DONE]') {
            return
          }
          try {
            const parsed = JSON.parse(dataStr)
            const eventType = parsed.event
            // 仅处理包含内容的消息事件，忽略诸如workflow_started等控制事件
            if (parsed.answer && (!eventType || eventType === 'message' || eventType === 'message_delta')) {
              result.value += parsed.answer
            }
          } catch (e) {
            // 非完整JSON分片，不渲染，等待后续分片补齐
            // 这里不将原始data追加到结果中，避免把控制事件或半截JSON展示出来
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// 清空表单
const clearJDForm = () => {
  Object.assign(jdForm, {
    positionTitle: '',
    department: '',
    experienceLevel: '',
    requirements: ''
  })
}

const clearResumeForm = () => {
  Object.assign(resumeForm, {
    resumeContent: '',
    jobRequirements: '',
    evaluationCriteria: ''
  })
}

const clearInterviewForm = () => {
  Object.assign(interviewForm, {
    positionTitle: '',
    candidateBackground: '',
    interviewType: '',
    interviewDuration: ''
  })
}

const clearCustomForm = () => {
  Object.assign(customForm, {
    workflowType: null,
    query: '',
    additionalInputs: ''
  })
}

// 复制结果
const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('结果已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 清空结果
const clearResult = () => {
  result.value = ''
  showResult.value = false
}

// 标签页切换
const handleTabClick = (tab) => {
  clearResult()
}

onMounted(() => {
  fetchWorkflowTypes()
})
</script>

<style scoped>
.hr-workflows {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.header p {
  color: #7f8c8d;
  font-size: 16px;
}

.workflow-tabs {
  margin-bottom: 30px;
}

.workflow-form {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.workflow-form h3 {
  color: #2c3e50;
  margin-bottom: 20px;
  border-bottom: 2px solid #3498db;
  padding-bottom: 10px;
}

.result-section {
  background: #ffffff;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.result-section h3 {
  color: #2c3e50;
  margin-bottom: 15px;
}

.result-content {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 15px;
  min-height: 200px;
  margin-bottom: 15px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3498db;
  font-size: 16px;
}

.loading-indicator .el-icon {
  margin-right: 8px;
  font-size: 20px;
}

.result-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  line-height: 1.6;
  color: #2c3e50;
}

.result-actions {
  display: flex;
  gap: 10px;
}

.el-form-item {
  margin-bottom: 20px;
}

.el-textarea {
  font-family: inherit;
}

.el-button {
  margin-right: 10px;
}

// Markdown 内容样式
.markdown-content {
  line-height: 1.6;
  color: #333;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

  h1, h2, h3, h4, h5, h6 {
    margin: 1.2em 0 0.6em 0;
    font-weight: 600;
    line-height: 1.3;
  }

  h1 {
    font-size: 1.8em;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.3em;
  }

  h2 {
    font-size: 1.5em;
    color: #34495e;
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.2em;
  }

  h3 {
    font-size: 1.3em;
    color: #2c3e50;
  }

  h4 {
    font-size: 1.1em;
    color: #34495e;
  }

  p {
    margin: 0.8em 0;
    text-align: justify;
  }

  ul, ol {
    margin: 0.8em 0;
    padding-left: 2em;
  }

  li {
    margin: 0.3em 0;
  }

  blockquote {
    margin: 1em 0;
    padding: 0.8em 1.2em;
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    border-radius: 4px;
    font-style: italic;
  }

  code {
    background-color: #f1f2f6;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
    color: #e74c3c;
  }

  pre {
    background-color: #2c3e50;
    color: #ecf0f1;
    padding: 1em;
    border-radius: 6px;
    overflow-x: auto;
    margin: 1em 0;

    code {
      background-color: transparent;
      padding: 0;
      color: inherit;
    }
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    
    th, td {
      border: 1px solid #ddd;
      padding: 0.6em;
      text-align: left;
    }
    
    th {
      background-color: #f8f9fa;
      font-weight: 600;
    }
    
    tr:nth-child(even) {
      background-color: #f8f9fa;
    }
  }

  strong {
    font-weight: 600;
    color: #2c3e50;
  }

  em {
    font-style: italic;
    color: #7f8c8d;
  }

  a {
    color: #3498db;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }

  hr {
    border: none;
    border-top: 2px solid #ecf0f1;
    margin: 2em 0;
  }
}
</style>