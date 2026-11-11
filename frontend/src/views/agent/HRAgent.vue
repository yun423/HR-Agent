<template>
  <div class="hr-agent-page">
    <section class="agent-header">
      <div class="agent-title-block">
        <div class="agent-kicker">HR Agent Copilot</div>
        <h1>招聘助手</h1>
        <p>直接说你的招聘目标，我会用 ReAct 方式思考、选择动作，并在对话中推进下一步。</p>
      </div>
      <div class="agent-header-actions">
        <el-tag type="success" effect="plain">ReAct Agent</el-tag>
        <el-button type="primary" plain @click="startNewConversation" :disabled="loading">新对话</el-button>
      </div>
    </section>

    <div class="agent-layout">
      <aside class="conversation-sidebar">
        <div class="sidebar-header">
          <div>
            <div class="sidebar-title">对话记录</div>
            <p>切换历史招聘任务</p>
          </div>
          <el-button text type="primary" size="small" @click="startNewConversation" :disabled="loading">
            新建
          </el-button>
        </div>

        <div v-if="conversationsLoading" class="conversation-loading">
          <el-skeleton :rows="5" animated />
        </div>
        <el-empty v-else-if="agentConversations.length === 0" description="暂无历史对话" />
        <div v-else class="conversation-list">
          <div
            v-for="conversation in agentConversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{ active: currentConversationId === conversation.id }"
          >
            <button class="conversation-main" :disabled="loading" @click="switchConversation(conversation)">
              <span>{{ conversation.title }}</span>
              <small>{{ formatConversationTime(conversation.updated_at) }}</small>
            </button>
            <el-popconfirm
              title="确定删除这条对话记录吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="deleteAgentConversation(conversation)"
            >
              <template #reference>
                <el-button
                  class="conversation-delete"
                  text
                  circle
                  type="danger"
                  :icon="Delete"
                  :disabled="loading"
                  @click.stop
                />
              </template>
            </el-popconfirm>
          </div>
        </div>
      </aside>

      <el-card class="chat-card">
        <div class="messages" ref="messagesRef">
          <div
            v-for="message in messages"
            :key="message.id"
            class="message"
            :class="message.role"
          >
            <div class="bubble">
              <div class="role">{{ message.role === 'user' ? '你' : 'HR Agent' }}</div>
              <div v-if="message.thinking" class="thinking-card">
                <div class="thinking-status">
                  <span class="thinking-spinner"></span>
                  <div>
                    <strong>正在理解需求</strong>
                    <p>判断是否需要调用招聘工具</p>
                  </div>
                </div>
              </div>
              <details
                v-if="shouldShowPlan(message)"
                class="chat-plan-card"
              >
                <summary class="chat-plan-header">
                  <span class="chat-plan-title">
                    <span v-if="isPlanRunning(message)" class="plan-live-spinner"></span>
                    <span>执行进度</span>
                  </span>
                  <div class="chat-plan-meta">
                    <small
                      class="plan-current-step"
                      :class="{ 'is-running': isPlanRunning(message), 'is-failed': hasFailedStep(message) }"
                    >
                      {{ currentStepText(message) }}
                    </small>
                    <span v-if="planElapsedText(message)" class="plan-elapsed">
                      {{ planElapsedText(message) }}
                    </span>
                    <em>{{ planProgressText(message) }}</em>
                    <el-tag v-if="message.response.intent" size="small" effect="plain">
                      {{ intentLabel(message.response.intent) }}
                    </el-tag>
                  </div>
                </summary>
                <div class="chat-step-list">
                  <div
                    v-for="(step, index) in message.response.steps"
                    :key="`${message.id}-${step.id}-${index}`"
                    class="chat-step"
                    :class="`is-${displayStepStatus(message, step)}`"
                  >
                    <div class="chat-step-marker">
                      <el-icon v-if="displayStepStatus(message, step) === 'completed'"><Check /></el-icon>
                      <el-icon v-else-if="displayStepStatus(message, step) === 'running'" class="chat-step-loading"><Loading /></el-icon>
                      <span v-else>{{ index + 1 }}</span>
                    </div>
                    <div class="chat-step-body">
                      <div class="chat-step-title">
                        <span>
                          <i v-if="displayStepStatus(message, step) === 'running'" class="step-live-dot"></i>
                          {{ step.title }}
                        </span>
                        <em>{{ step.tool ? toolLabel(step.tool) : statusText(displayStepStatus(message, step)) }}</em>
                      </div>
                      <p v-if="step.detail">{{ step.detail }}</p>
                    </div>
                  </div>
                </div>
              </details>
              <div
                v-if="message.content"
                class="content"
                :class="{ 'markdown-content': message.role === 'assistant' }"
                v-html="formatMessageContent(message)"
              ></div>
              <div v-if="shouldShowSuggestions(message)" class="chat-suggestions">
                <el-button
                  v-for="suggestion in visibleSuggestions(message)"
                  :key="suggestion"
                  size="small"
                  plain
                  round
                  :disabled="loading"
                  @click="sendSuggestion(suggestion)"
                >
                  {{ suggestion }}
                </el-button>
              </div>
              <div v-if="message.response?.intent === 'error'" class="error-recovery-card">
                <el-alert
                  type="error"
                  show-icon
                  :closable="false"
                  :title="message.response.message"
                />
                <p v-if="message.response.artifacts?.[0]?.content?.reason">
                  原因：{{ message.response.artifacts[0].content.reason }}
                </p>
                <p v-if="message.response.artifacts?.[0]?.content?.advice">
                  建议：{{ message.response.artifacts[0].content.advice }}
                </p>
              </div>
              <div v-if="message.kind === 'jd_confirm'" class="chat-tool-panel jd-confirm-panel">
                <el-alert
                  v-if="missingFieldLabels.length"
                  type="warning"
                  show-icon
                  :closable="false"
                  class="confirm-alert"
                  :title="`还需要补充：${missingFieldLabels.join('、')}`"
                />
                <el-form :model="confirmForm" label-width="86px" class="confirm-form" size="small">
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="岗位名称" required>
                        <el-input v-model="confirmForm.job_title" placeholder="如 AI 产品经理" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="工作地点" required>
                        <el-input v-model="confirmForm.location" placeholder="如 长沙/远程" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="薪资范围" required>
                        <el-input v-model="confirmForm.salary" placeholder="如 15-25K" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="经验要求" required>
                        <el-input v-model="confirmForm.experience" placeholder="如 3-5年/不限" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="学历要求" required>
                        <el-input v-model="confirmForm.education" placeholder="如 本科及以上/不限" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="部门">
                        <el-input v-model="confirmForm.department" placeholder="如 产品部" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item label="核心技能">
                        <el-input v-model="confirmForm.skillsText" placeholder="选填，用逗号分隔，如 大模型、需求分析、数据分析" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item label="补充要求">
                        <el-input
                          v-model="confirmForm.additional_requirements"
                          type="textarea"
                          :rows="3"
                          placeholder="岗位职责、业务背景、加分项、福利等"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
                <div class="tool-actions">
                  <el-button @click="markJDConfirmSkipped(message)">先不生成</el-button>
                  <el-button type="primary" :loading="loading" @click="confirmAndGenerate">
                    确认并生成 JD
                  </el-button>
                </div>
              </div>
              <div v-else-if="message.kind === 'email_confirm'" class="chat-tool-panel email-confirm-panel">
                <el-alert
                  v-if="emailMissingFieldLabels.length"
                  type="warning"
                  show-icon
                  :closable="false"
                  class="confirm-alert"
                  :title="`还需要补充：${emailMissingFieldLabels.join('、')}`"
                />
                <el-form :model="emailConfirmForm" label-width="86px" class="confirm-form" size="small">
                  <el-row :gutter="12">
                    <el-col :span="24">
                      <el-form-item label="收件人" required>
                        <el-input v-model="emailConfirmForm.recipient_email" placeholder="如 candidate@example.com" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item label="邮件主题" required>
                        <el-input v-model="emailConfirmForm.subject" placeholder="请输入邮件主题" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item label="邮件正文" required>
                        <el-input
                          v-model="emailConfirmForm.body"
                          type="textarea"
                          :rows="8"
                          placeholder="请确认或编辑邮件正文"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
                <div class="tool-actions">
                  <el-button @click="markEmailConfirmSkipped(message)">先不发送</el-button>
                  <el-button type="primary" :loading="loading" @click="confirmAndSendEmail">
                    确认并发送邮件
                  </el-button>
                </div>
              </div>
              <div v-else-if="message.kind === 'resume_upload'" class="chat-upload-panel">
                <el-alert
                  :type="resumeFileList.length ? 'success' : 'warning'"
                  show-icon
                  :closable="false"
                  :title="resumeFileList.length ? `已从消息附件中选择 ${resumeFileList.length} 份简历` : '请先在底部消息框点击“上传文件”，添加 PDF、DOC 或 DOCX 简历后再发送筛选需求。'"
                />
                <el-select
                  v-if="resumeFileList.length"
                  v-model="selectedScreeningJDId"
                  class="jd-select"
                  placeholder="选择用于匹配的 JD"
                  filterable
                  :loading="jdOptionsLoading"
                  @change="handleScreeningJDChange"
                >
                  <el-option
                    v-for="jd in jdOptions"
                    :key="jd.id"
                    :label="jd.title"
                    :value="jd.id"
                  />
                </el-select>
                <div v-if="resumeFileList.length" class="attached-file-list">
                  <el-tag
                    v-for="file in resumeFileList"
                    :key="file.uid || file.name"
                    closable
                    @close="removeResumeFile(file)"
                  >
                    {{ file.name }}
                  </el-tag>
                </div>
                <div v-if="resumeFileList.length" class="resume-upload-actions">
                  <el-button @click="clearResumeFiles" :disabled="resumeScreeningLoading || resumeFileList.length === 0">
                    清空
                  </el-button>
                  <el-button
                    type="primary"
                    :loading="resumeScreeningLoading"
                    :disabled="resumeFileList.length === 0 || !screeningJobDescriptionId"
                    @click="startResumeScreening"
                  >
                    开始评分（{{ resumeFileList.length }}）
                  </el-button>
                </div>
              </div>
              <div v-else-if="message.kind === 'interview_plan'" class="chat-tool-panel">
                <el-select
                  v-model="selectedInterviewResumeId"
                  class="tool-select"
                  placeholder="选择已评分候选人"
                  filterable
                  :loading="resumeOptionsLoading"
                >
                  <el-option
                    v-for="resume in resumeOptions"
                    :key="resume.id"
                    :label="formatResumeOption(resume)"
                    :value="resume.id"
                  />
                </el-select>
                <div class="tool-actions">
                  <el-button @click="fetchResumeOptions" :loading="resumeOptionsLoading">刷新候选人</el-button>
                  <el-button
                    type="primary"
                    :loading="interviewPlanLoading"
                    :disabled="!selectedInterviewResumeId"
                    @click="startInterviewPlan"
                  >
                    生成面试计划
                  </el-button>
                </div>
              </div>
              <div v-else-if="message.kind === 'exam_document_upload'" class="chat-tool-panel">
                <el-alert
                  type="warning"
                  show-icon
                  :closable="false"
                  title="生成试卷需要先在底部消息框点击附件按钮上传参考文档。"
                />
              </div>
              <div v-else-if="message.kind === 'exam_generate'" class="chat-tool-panel">
                <el-alert
                  type="success"
                  show-icon
                  :closable="false"
                  :title="examForm.interview_plan_context ? `已选择 ${examUsableDocumentCount} 个参考文档，并关联当前面试方案，下面配置试卷参数。` : `已选择 ${examUsableDocumentCount} 个参考文档，下面配置试卷参数。`"
                />
                <el-form :model="examForm" label-width="92px" size="small">
                  <el-form-item label="试卷标题">
                    <el-input v-model="examForm.title" placeholder="如 AI 产品经理笔试" />
                  </el-form-item>
                  <el-form-item label="考察方向">
                    <el-input v-model="examForm.subject" placeholder="如 AI 产品经理/Java/前端" />
                  </el-form-item>
                  <el-form-item label="考试参数">
                    <div class="exam-number-grid">
                      <label class="exam-number-item">
                        <span>总分</span>
                        <el-input-number v-model="examForm.total_score" :min="10" :max="200" />
                      </label>
                      <label class="exam-number-item">
                        <span>时长</span>
                        <el-input-number v-model="examForm.duration" :min="10" :max="240" />
                      </label>
                    </div>
                  </el-form-item>
                  <el-form-item label="题量配置">
                    <div class="exam-number-grid question-counts">
                      <label class="exam-number-item">
                        <span>单选题</span>
                        <el-input-number v-model="examForm.question_counts.single_choice" :min="0" :max="50" />
                      </label>
                      <label class="exam-number-item">
                        <span>多选题</span>
                        <el-input-number v-model="examForm.question_counts.multiple_choice" :min="0" :max="50" />
                      </label>
                      <label class="exam-number-item">
                        <span>简答题</span>
                        <el-input-number v-model="examForm.question_counts.short_answer" :min="0" :max="20" />
                      </label>
                    </div>
                  </el-form-item>
                  <el-form-item label="补充要求">
                    <el-input v-model="examForm.special_requirements" type="textarea" :rows="3" />
                  </el-form-item>
                </el-form>
                <div class="tool-actions">
                  <el-button
                    type="primary"
                    :loading="examGenerating"
                    :disabled="!examForm.title || !examForm.subject || examUsableDocumentCount === 0"
                    @click="startExamGeneration"
                  >
                    基于文档生成试卷
                  </el-button>
                </div>
              </div>
              <div v-if="showMessageActions(message)" class="message-actions">
                <el-button
                  v-if="isCurrentRunningMessage(message)"
                  size="small"
                  type="danger"
                  plain
                  @click="stopGeneration"
                >
                  停止生成
                </el-button>
                <template v-else>
                  <el-button size="small" text type="danger" @click="deleteConversationChatMessage(message)">删除</el-button>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="composer">
          <div v-if="composerFileList.length" class="composer-files">
            <el-tag
              v-for="file in composerFileList"
              :key="file.uid"
              closable
              @close="removeComposerFile(file)"
            >
              {{ file.name }}
            </el-tag>
          </div>
          <el-input
            v-model="input"
            type="textarea"
            :rows="4"
            placeholder="例如：帮我招一个 3-5 年 Java 后端，长沙，12-16K，需要 Spring、MySQL、Redis"
            :disabled="loading"
            @keydown.enter="handleComposerEnter"
          />
          <div class="composer-actions">
            <div class="composer-left-actions">
              <el-upload
                class="composer-upload"
                multiple
                :auto-upload="false"
                :show-file-list="false"
                :file-list="composerFileList"
                :on-change="handleComposerFileChange"
                accept=".pdf,.doc,.docx,.txt,.md"
              >
                <el-button :icon="UploadFilled" :disabled="loading">上传文件</el-button>
              </el-upload>
              <span>Shift+Enter 换行</span>
            </div>
            <el-button v-if="loading" type="danger" plain @click="stopGeneration">
              停止生成
            </el-button>
            <el-button v-else type="primary" :disabled="!canSendMessage" @click="sendMessage">
              发送
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Delete, Loading, UploadFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { agentApi } from '@/api/agent'
import { jobDescriptionApi } from '@/api/jobDescription'
import { resumeApi } from '@/api/resume'
import {
  addConversationMessage,
  createConversation,
  deleteConversation,
  deleteConversationMessage,
  getConversationMessages,
  getConversations
} from '@/api/conversation'

marked.setOptions({
  highlight(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  langPrefix: 'hljs language-',
  breaks: true,
  gfm: true
})

const input = ref('')
const router = useRouter()
const loading = ref(false)
const activeAbortController = ref(null)
const currentRunningMessageId = ref('')
const generationStartedAt = ref(0)
const generationElapsedSeconds = ref(0)
const generationElapsedByMessage = ref({})
const lastRetryContext = ref(null)
const messagesRef = ref(null)
const pendingMessage = ref('')
const missingFields = ref([])
const resumeFileList = ref([])
const resumeScreeningLoading = ref(false)
const selectedScreeningJDId = ref('')
const jdOptions = ref([])
const jdOptionsLoading = ref(false)
const resumeOptions = ref([])
const resumeOptionsLoading = ref(false)
const selectedInterviewResumeId = ref('')
const lastSingleResumeEvaluationId = ref('')
const interviewPlanLoading = ref(false)
const examGenerating = ref(false)
const examDocumentFileList = ref([])
const examDocumentRawFiles = ref([])
const currentExamInterviewContext = ref(null)
const composerFileList = ref([])
const currentConversationId = ref(null)
const agentConversations = ref([])
const conversationsLoading = ref(false)
const examForm = ref({
  title: '',
  subject: '',
  description: '',
  difficulty: 'medium',
  duration: 60,
  total_score: 100,
  question_types: ['single_choice', 'multiple_choice', 'short_answer'],
  question_counts: {
    single_choice: 5,
    multiple_choice: 3,
    short_answer: 2
  },
  special_requirements: '',
  interview_plan_context: null,
  knowledge_files: []
})
const confirmForm = ref({
  job_title: '',
  department: '',
  location: '',
  salary: '',
  experience: '',
  education: '',
  job_type: '全职',
  skillsText: '',
  benefitsText: '',
  additional_requirements: ''
})
const emailConfirmForm = ref({
  recipient_email: '',
  subject: '',
  body: '',
  draft_text: ''
})
const createWelcomeMessage = () => ({
  id: `welcome-${Date.now()}`,
  role: 'assistant',
  content: '你好，我是招聘场景的 HR Agent。你可以让我生成 JD 和评分标准、上传简历做筛选、为候选人生成面试计划、基于文档/面试方案生成试卷、生成邮件草稿，或通过聊天删除已生成内容。'
})
const createDefaultExamForm = () => ({
  title: '',
  subject: '',
  description: '',
  difficulty: 'medium',
  duration: 60,
  total_score: 100,
  question_types: ['single_choice', 'multiple_choice', 'short_answer'],
  question_counts: {
    single_choice: 5,
    multiple_choice: 3,
    short_answer: 2
  },
  special_requirements: '',
  knowledge_files: []
})
const createDefaultConfirmForm = () => ({
  job_title: '',
  department: '',
  location: '',
  salary: '',
  experience: '',
  education: '',
  job_type: '全职',
  skillsText: '',
  benefitsText: '',
  additional_requirements: ''
})
const createDefaultEmailConfirmForm = () => ({
  recipient_email: '',
  subject: '',
  body: '',
  draft_text: ''
})
const messages = ref([createWelcomeMessage()])
const responses = ref([])
const emailMissingFields = ref([])

const lastResponse = computed(() => responses.value[responses.value.length - 1])
const missingFieldLabels = computed(() => missingFields.value.map(fieldLabel))
const emailMissingFieldLabels = computed(() => emailMissingFields.value.map(fieldLabel))
const canSendMessage = computed(() => Boolean(input.value.trim() || composerFileList.value.length))
const savedJobDescriptionId = computed(() => {
  for (let index = responses.value.length - 1; index >= 0; index--) {
    const artifacts = responses.value[index]?.artifacts || []
    for (const artifact of artifacts) {
      const savedId = artifact.metadata?.saved_jd_id
      if (savedId) return savedId
    }
  }
  return ''
})
const screeningJobDescriptionId = computed(() => selectedScreeningJDId.value || savedJobDescriptionId.value)
const examKnowledgeFileCount = computed(() => (examForm.value.knowledge_files || []).length)
const examUsableDocumentCount = computed(() => getExamDocumentFiles().length || examKnowledgeFileCount.value)
let generationElapsedTimer = null

onMounted(() => {
  fetchJDOptions()
  fetchResumeOptions()
  fetchAgentConversations()
})

onBeforeUnmount(() => {
  stopGenerationTimer()
  if (activeAbortController.value) {
    activeAbortController.value.abort()
  }
})

const sendMessage = async () => {
  const attachedFiles = composerFileList.value.slice()
  const content = input.value.trim() || defaultMessageForAttachments(attachedFiles)
  if (!content || loading.value) return

  const fileText = attachedFiles.length ? `\n\n附件：${attachedFiles.map(file => file.name).join('、')}` : ''
  messages.value.push({ id: `${Date.now()}-user`, role: 'user', content: `${content}${fileText}` })
  input.value = ''
  pendingMessage.value = content
  const conversationId = await ensureAgentConversation(content)
  await persistConversationMessage(conversationId, 'user', `${content}${fileText}`)
  if (isWaitingForExamDocuments() && attachedFiles.length) {
    cacheExamDocumentFiles(attachedFiles)
    composerFileList.value = []
    hydrateExamFromWaitingContext()
    const response = createExamConfigResponse()
    responses.value.push(response)
    const examConfigMessageId = `${Date.now()}-exam-config`
    messages.value.push({
      id: examConfigMessageId,
      role: 'assistant',
      content: response.message,
      kind: 'exam_generate',
      response
    })
    const savedAssistantMessage = await persistConversationMessage(conversationId, 'assistant', response.message, {
      intent: response.intent,
      route: response.route,
      kind: 'exam_generate',
      agent_response: response
    })
    attachPersistedMessageId(examConfigMessageId, savedAssistantMessage)
    await scrollToBottom()
    return
  }
  if (isWaitingForResumeFiles() && attachedFiles.length) {
    await continueResumeScreeningWithAttachments(attachedFiles, conversationId)
    return
  }
  await runAgent(
    {
      message: content,
      auto_execute: true,
      conversation_id: conversationId,
      attachments: buildAttachmentMetadata(attachedFiles)
    },
    { attachedFiles, conversationId }
  )
}

const defaultMessageForAttachments = (files = []) => {
  if (!files.length) return ''
  const resumeFiles = files.filter(isResumeFile)
  const documentFiles = files.filter(file => !isResumeFile(file))
  if (isWaitingForExamDocuments()) return '已上传参考文档，请继续生成试卷。'
  if (isWaitingForResumeFiles() && resumeFiles.length) return '已上传简历，请继续评分。'
  if (resumeFiles.length && !documentFiles.length) return '已上传简历，请帮我进行简历评分。'
  if (documentFiles.length && !resumeFiles.length) return '已上传参考文档，请继续处理。'
  return '已上传文件，请继续处理。'
}

const sendSuggestion = async (suggestion) => {
  if (!suggestion || loading.value) return
  const targetRoute = routeForSuggestion(suggestion)
  if (targetRoute) {
    await router.push(targetRoute)
    return
  }
  input.value = suggestion
  await sendMessage()
}

const routeForSuggestion = (suggestion = '') => {
  const text = String(suggestion).trim()
  if (['查看 JD 列表', '去 JD 管理查看职位', '查看 JD 列表并管理'].includes(text)) {
    return '/recruitment/jd-generator'
  }
  if (['查看完整评分详情', '查看简历筛选列表', '查看简历列表'].includes(text)) {
    return '/recruitment/resume-screening'
  }
  if (['查看面试计划列表', '查看面试方案列表', '去智能面试查看'].includes(text)) {
    return '/recruitment/smart-interview'
  }
  if (['查看试卷列表'].includes(text)) {
    return '/training/exam-generator'
  }
  if (['查看试卷管理', '去考试管理', '去考试管理查看'].includes(text)) {
    return '/training/exam-management'
  }
  return ''
}

const handleComposerEnter = (event) => {
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  sendMessage()
}

const ensureAgentConversation = async (firstMessage = '') => {
  if (currentConversationId.value) return currentConversationId.value
  const title = firstMessage ? firstMessage.slice(0, 30) : '新的 HR Agent 对话'
  const response = await createConversation({
    title,
    description: 'HR Agent 对话',
    meta_data: { source: 'hr_agent' }
  })
  const conversation = response?.data || response
  currentConversationId.value = conversation.id
  await fetchAgentConversations()
  return currentConversationId.value
}

const persistConversationMessage = async (conversationId, role, content, context = {}) => {
  if (!conversationId || !content) return
  try {
    const response = await addConversationMessage(conversationId, {
      role,
      content,
      context
    })
    await fetchAgentConversations()
    return response?.data || response
  } catch (error) {
    console.error('保存 Agent 对话消息失败:', error)
  }
}

const attachPersistedMessageId = (localMessageId, savedMessage) => {
  const persistedMessageId = savedMessage?.id ? String(savedMessage.id) : ''
  if (!localMessageId || !persistedMessageId) return
  const index = messages.value.findIndex(message => message.id === localMessageId)
  if (index >= 0) {
    messages.value[index] = {
      ...messages.value[index],
      persistedMessageId
    }
  }
}

const startGenerationTimer = () => {
  stopGenerationTimer()
  generationStartedAt.value = Date.now()
  generationElapsedSeconds.value = 0
  generationElapsedTimer = window.setInterval(() => {
    generationElapsedSeconds.value = Math.max(
      0,
      Math.floor((Date.now() - generationStartedAt.value) / 1000)
    )
  }, 1000)
}

const currentGenerationElapsed = () => {
  if (!generationStartedAt.value) return generationElapsedSeconds.value
  return Math.max(0, Math.floor((Date.now() - generationStartedAt.value) / 1000))
}

const stopGenerationTimer = () => {
  if (generationElapsedTimer) {
    window.clearInterval(generationElapsedTimer)
    generationElapsedTimer = null
  }
  generationStartedAt.value = 0
}

const beginGeneration = (messageId, retryContext = null) => {
  if (activeAbortController.value) {
    activeAbortController.value.abort()
  }
  const controller = new AbortController()
  activeAbortController.value = controller
  currentRunningMessageId.value = messageId
  generationElapsedByMessage.value = {
    ...generationElapsedByMessage.value,
    [messageId]: 0
  }
  startGenerationTimer()
  if (retryContext) {
    lastRetryContext.value = retryContext
    const index = messages.value.findIndex(message => message.id === messageId)
    if (index >= 0) {
      messages.value[index] = {
        ...messages.value[index],
        retryContext
      }
    }
  }
  return controller.signal
}

const finishGeneration = (messageId) => {
  if (!messageId || currentRunningMessageId.value === messageId) {
    const finalElapsedSeconds = currentGenerationElapsed()
    if (messageId) {
      generationElapsedByMessage.value = {
        ...generationElapsedByMessage.value,
        [messageId]: finalElapsedSeconds
      }
      const index = messages.value.findIndex(message => message.id === messageId)
      if (index >= 0) {
        messages.value[index] = {
          ...messages.value[index],
          elapsedSeconds: finalElapsedSeconds
        }
      }
    }
    generationElapsedSeconds.value = finalElapsedSeconds
    activeAbortController.value = null
    currentRunningMessageId.value = ''
    stopGenerationTimer()
  }
}

const stopGeneration = () => {
  if (!activeAbortController.value) return
  activeAbortController.value.abort()
}

const isAbortError = (error) => {
  return error?.name === 'AbortError' || /abort|aborted|取消|停止/i.test(error?.message || '')
}

const markGenerationStopped = (messageId) => {
  const message = messages.value.find(item => item.id === messageId)
  const response = {
    ...(message?.response || createStoppedResponse()),
    message: '已停止生成。你可以修改要求后重试，或重新生成。',
    steps: (message?.response?.steps || []).map(step => (
      step.status === 'running' ? { ...step, status: 'failed', detail: '用户已停止生成' } : step
    ))
  }
  updateAssistantMessage(messageId, response, `${message?.content || ''}\n\n已停止生成。`.trim())
}

const startNewConversation = async () => {
  stopGeneration()
  input.value = ''
  pendingMessage.value = ''
  missingFields.value = []
  resumeFileList.value = []
  resumeScreeningLoading.value = false
  selectedScreeningJDId.value = ''
  selectedInterviewResumeId.value = ''
  lastSingleResumeEvaluationId.value = ''
  interviewPlanLoading.value = false
  examGenerating.value = false
  examDocumentFileList.value = []
  examDocumentRawFiles.value = []
  currentExamInterviewContext.value = null
  composerFileList.value = []
  currentRunningMessageId.value = ''
  stopGenerationTimer()
  lastRetryContext.value = null
  currentConversationId.value = null
  examForm.value = createDefaultExamForm()
  confirmForm.value = createDefaultConfirmForm()
  emailConfirmForm.value = createDefaultEmailConfirmForm()
  emailMissingFields.value = []
  responses.value = []
  messages.value = [createWelcomeMessage()]
  await scrollToBottom()
}

const fetchAgentConversations = async () => {
  try {
    conversationsLoading.value = true
    const response = await getConversations({ limit: 100 })
    const items = response?.data || response || []
    agentConversations.value = items.filter(item => item.meta_data?.source === 'hr_agent')
  } catch (error) {
    console.error('获取 Agent 历史对话失败:', error)
  } finally {
    conversationsLoading.value = false
  }
}

const switchConversation = async (conversation) => {
  if (!conversation?.id || loading.value) return
  try {
    currentConversationId.value = conversation.id
    responses.value = []
    composerFileList.value = []
    examDocumentFileList.value = []
    examDocumentRawFiles.value = []
    currentExamInterviewContext.value = null
    const response = await getConversationMessages(conversation.id, { limit: 100 })
    const items = response?.data || response || []
    messages.value = items.map(item => ({
      id: String(item.id),
      persistedMessageId: String(item.id),
      role: item.role,
      content: item.content,
      kind: item.context?.kind,
      response: item.context?.agent_response
    }))
    lastSingleResumeEvaluationId.value = getLastSingleResumeEvaluationId()
    hydrateLatestJDConfirmForm()
    hydrateLatestEmailConfirmForm()
    if (!messages.value.length) {
      messages.value = [createWelcomeMessage()]
    }
    await scrollToBottom()
  } catch (error) {
    console.error('切换 Agent 对话失败:', error)
    ElMessage.error('切换对话失败')
  }
}

const deleteAgentConversation = async (conversation) => {
  if (!conversation?.id || loading.value) return
  try {
    await deleteConversation(conversation.id)
    agentConversations.value = agentConversations.value.filter(item => item.id !== conversation.id)
    if (currentConversationId.value === conversation.id) {
      await startNewConversation()
    }
    ElMessage.success('对话记录已删除')
  } catch (error) {
    console.error('删除 Agent 对话失败:', error)
    ElMessage.error(error?.response?.data?.detail || '删除对话失败')
  }
}

const getInterviewExecuteArtifact = (response) => {
  return response?.artifacts?.find(artifact => artifact.type === 'interview_plan_execute')
}

const getInterviewExecuteResumeId = (response) => {
  return getInterviewExecuteArtifact(response)?.content?.resume_evaluation_id || ''
}

const hydrateExamFromInterviewContext = (response) => {
  const context = response?.artifacts?.find(item => item.type === 'exam_document_upload_request')?.content?.interview_plan_context
  if (!context) return
  currentExamInterviewContext.value = context
  const candidateTitle = String(context.title || '').replace(/\s*面试计划$/, '')
  examForm.value = {
    ...examForm.value,
    title: examForm.value.title || `${candidateTitle || '候选人'}笔试试卷`,
    subject: examForm.value.subject || candidateTitle || '通用岗位',
    interview_plan_context: context,
    special_requirements: [
      '请结合当前面试方案生成笔试题。',
      context.content ? `面试方案摘要：${String(context.content).slice(0, 1200)}` : ''
    ].filter(Boolean).join('\n\n')
  }
}

const hydrateExamFromWaitingContext = () => {
  const waitingMessage = getLatestAssistantMessageByKind('exam_document_upload')
  if (waitingMessage?.response) {
    hydrateExamForm(waitingMessage.response)
    hydrateExamFromInterviewContext(waitingMessage.response)
  }
}

const runAgent = async (payload, options = {}) => {
  const {
    assistantPrefix = '',
    optimisticResponse = null,
    attachedFiles = [],
    conversationId = currentConversationId.value,
    replaceMessageId = null
  } = options
  const runningResponse = optimisticResponse || createThinkingResponse()
  const runningMessageId = replaceMessageId || `${Date.now()}-agent-thinking`
  loading.value = true
  responses.value.push(runningResponse)
  const replacementIndex = replaceMessageId ? messages.value.findIndex(message => message.id === replaceMessageId) : -1
  const runningMessage = {
    id: runningMessageId,
    role: 'assistant',
    content: optimisticResponse?.message || '',
    thinking: !optimisticResponse,
    response: runningResponse
  }
  if (replacementIndex >= 0) {
    messages.value[replacementIndex] = {
      ...messages.value[replacementIndex],
      ...runningMessage,
      kind: undefined
    }
  } else {
    messages.value.push(runningMessage)
  }
  const signal = beginGeneration(runningMessageId, {
    type: 'chat',
    payload: { ...payload },
    options: { assistantPrefix, attachedFiles, conversationId }
  })
  if (!replaceMessageId) await scrollToBottom()

  try {
    const streamResponse = await agentApi.chatStream(payload, { signal })
    const responseForMessage = await consumeAgentStream(streamResponse, {
      activeMessageId: runningMessageId,
      persist: false,
      keepThinkingForNonFinal: true,
      transformResponse: (response, event) => {
        if (event.type !== 'final') return { response }
        return prepareChatResponse(response, attachedFiles)
      }
    })
    if (!responseForMessage) return
    const directInterviewResumeId = getInterviewExecuteResumeId(responseForMessage)
    if (responseForMessage.intent === 'interview_plan' && directInterviewResumeId) {
      const executeArtifact = getInterviewExecuteArtifact(responseForMessage)
      await startInterviewPlan({
        resumeEvaluationId: directInterviewResumeId,
        activeMessageId: runningMessageId,
        appendUserMessage: false,
        userMessage: executeArtifact?.content?.candidate_name
          ? `请基于候选人 ${executeArtifact.content.candidate_name} 生成面试计划。`
          : '请基于高分候选人生成面试计划。'
      })
      return
    }
    const namedResumeEvaluation = findMentionedResumeEvaluation(payload.message)
    const contextualResumeEvaluationId = getLastSingleResumeEvaluationId()
    const targetResumeEvaluationId = namedResumeEvaluation?.id || (
      shouldUseContextualResumeForInterview(payload.message) ? contextualResumeEvaluationId : ''
    )
    if (responseForMessage.intent === 'interview_plan' && targetResumeEvaluationId) {
      await startInterviewPlan({
        resumeEvaluationId: targetResumeEvaluationId,
        activeMessageId: runningMessageId,
        appendUserMessage: false,
        userMessage: namedResumeEvaluation?.name
          ? `请基于候选人 ${namedResumeEvaluation.name} 生成面试计划。`
          : '请基于刚才评分出的候选人生成面试计划。'
      })
      return
    }
    const messageKind = messageKindForResponse(responseForMessage)
    const assistantMessage = formatAgentMessage(responseForMessage, assistantPrefix)
    const savedAssistantMessage = await persistConversationMessage(conversationId, 'assistant', assistantMessage, {
      intent: responseForMessage.intent,
      route: responseForMessage.route,
      kind: messageKind,
      agent_response: responseForMessage
    })
    attachPersistedMessageId(runningMessageId, savedAssistantMessage)
    handleChatResponseSideEffects(responseForMessage)
  } catch (error) {
    if (isAbortError(error)) {
      markGenerationStopped(runningMessageId)
      ElMessage.info('已停止生成')
    } else {
      const failedResponse = createFailedResponse(error)
      updateAssistantMessage(runningMessageId, failedResponse, failedResponse.message)
      ElMessage.error(error?.response?.data?.detail || error?.message || 'HR Agent 执行失败')
    }
  } finally {
    loading.value = false
    finishGeneration(runningMessageId)
    if (!replaceMessageId) await scrollToBottom()
  }
}

const prepareChatResponse = (response, attachedFiles = []) => {
  let responseForMessage = response
  if (response.intent === 'resume_screening' && attachedFiles.length) {
    const resumeFiles = attachedFiles.filter(isResumeFile)
    composerFileList.value = []
    if (resumeFiles.length) {
      resumeFileList.value = resumeFiles
      responseForMessage = createResumeReadyResponse(resumeFiles.length)
    } else {
      ElMessage.warning('简历筛选仅支持 PDF、DOC、DOCX，请重新上传简历文件')
      resumeFileList.value = []
      responseForMessage = createResumeAwaitingUploadResponse()
    }
  }
  if (response.intent === 'exam_generate' && attachedFiles.length) {
    cacheExamDocumentFiles(attachedFiles)
    composerFileList.value = []
    hydrateExamForm(response)
    responseForMessage = createExamConfigResponse()
  }
  return { response: responseForMessage, kind: messageKindForResponse(responseForMessage) }
}

const handleChatResponseSideEffects = (responseForMessage) => {
  if (responseForMessage.requires_confirmation && responseForMessage.intent === 'jd') {
    hydrateJDConfirmForm(responseForMessage)
  }
  if (responseForMessage.requires_confirmation && responseForMessage.intent === 'email_notification') {
    hydrateEmailConfirmForm(responseForMessage)
  }
  if (responseForMessage.intent === 'resume_screening') {
    selectedScreeningJDId.value = selectedScreeningJDId.value || savedJobDescriptionId.value
    fetchJDOptions()
  }
  if (responseForMessage.intent === 'interview_plan') {
    fetchResumeOptions()
  }
  if (responseForMessage.intent === 'exam_generate') {
    hydrateExamForm(responseForMessage)
    hydrateExamFromInterviewContext(responseForMessage)
  }
}

const messageKindForResponse = (response) => {
  const artifactTypes = (response.artifacts || []).map(item => item.type)
  if (response.intent === 'jd' && response.requires_confirmation && artifactTypes.includes('requirements')) return 'jd_confirm'
  if (response.intent === 'email_notification' && response.requires_confirmation && artifactTypes.includes('email_send_request')) return 'email_confirm'
  if (response.intent === 'resume_screening' && artifactTypes.includes('resume_upload_request')) return 'resume_upload'
  if (response.intent === 'interview_plan' && artifactTypes.includes('interview_plan_request')) return 'interview_plan'
  if (response.intent === 'exam_generate' && artifactTypes.includes('exam_document_upload_request')) return 'exam_document_upload'
  if (response.intent === 'exam_generate' && artifactTypes.includes('exam_generate_request')) return 'exam_generate'
  return undefined
}

const shouldShowSuggestions = (message) => {
  if (!visibleSuggestions(message).length) return false
  const response = message?.response
  const kind = message?.kind || messageKindForResponse(response)
  if (['jd_confirm', 'email_confirm', 'resume_upload', 'interview_plan', 'exam_document_upload', 'exam_generate'].includes(kind)) {
    return false
  }
  if (response.requires_confirmation || response.missing_fields?.length) return false
  const artifactTypes = (response.artifacts || []).map(item => item.type)
  return !artifactTypes.some(type => [
    'requirements',
    'resume_upload_request',
    'interview_plan_request',
    'exam_document_upload_request',
    'exam_generate_request'
  ].includes(type))
}

const visibleSuggestions = (message) => {
  const response = message?.response
  if (response?.intent === 'email_notification') {
    return []
  }
  const suggestions = response?.suggestions || []
  if (response?.intent === 'exam_generate') {
    return suggestions.filter(suggestion => suggestion !== '生成面试计划')
  }
  if (response?.intent === 'resource_delete') {
    return suggestions.filter(suggestion => ![
      '删除最新的 JD',
      '删除某位候选人的简历记录',
      '删除最新的面试方案',
      '删除最新的试卷',
    ].includes(suggestion))
  }
  return suggestions
}

const isWaitingForResumeFiles = () => {
  const message = getLatestAssistantMessageByKind('resume_upload')
  const artifactTypes = (message?.response?.artifacts || []).map(item => item.type)
  return message?.response?.intent === 'resume_screening' &&
    artifactTypes.includes('resume_upload_request') &&
    resumeFileList.value.length === 0
}

const isWaitingForExamDocuments = () => {
  const message = getLatestAssistantMessageByKind('exam_document_upload')
  const artifactTypes = (message?.response?.artifacts || []).map(item => item.type)
  return message?.response?.intent === 'exam_generate' &&
    artifactTypes.includes('exam_document_upload_request') &&
    examDocumentFileList.value.length === 0
}

const getLatestAssistantMessageByKind = (kind) => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    if (messages.value[index]?.role === 'assistant' && messages.value[index]?.kind === kind) {
      return messages.value[index]
    }
  }
  return null
}

const continueResumeScreeningWithAttachments = async (attachedFiles, conversationId) => {
  const resumeFiles = attachedFiles.filter(isResumeFile)
  composerFileList.value = []
  if (!resumeFiles.length) {
    ElMessage.warning('简历筛选仅支持 PDF、DOC、DOCX，请重新上传简历文件')
    await scrollToBottom()
    return
  }

  resumeFileList.value = resumeFiles
  const response = createResumeReadyResponse(resumeFiles.length)
  responses.value.push(response)
  const assistantMessage = response.message
  const resumeReadyMessageId = `${Date.now()}-resume-ready`
  messages.value.push({
    id: resumeReadyMessageId,
    role: 'assistant',
    content: assistantMessage,
    kind: 'resume_upload',
    response
  })
  const savedAssistantMessage = await persistConversationMessage(conversationId, 'assistant', assistantMessage, {
    intent: response.intent,
    route: response.route,
    kind: 'resume_upload',
    agent_response: response
  })
  attachPersistedMessageId(resumeReadyMessageId, savedAssistantMessage)
  selectedScreeningJDId.value = selectedScreeningJDId.value || savedJobDescriptionId.value
  fetchJDOptions()
  await scrollToBottom()
}

const hydrateJDConfirmForm = (response) => {
  const requirements = response.artifacts?.find(item => item.type === 'requirements')?.content || {}
  missingFields.value = response.missing_fields || []
  confirmForm.value = {
    job_title: requirements.job_title || '',
    department: requirements.department || '',
    location: requirements.location || '',
    salary: requirements.salary || '',
    experience: requirements.experience || '',
    education: requirements.education || '',
    job_type: requirements.job_type || '全职',
    skillsText: formatListForInput(requirements.skills),
    benefitsText: formatListForInput(requirements.benefits),
    additional_requirements: requirements.additional_requirements || ''
  }
}

const hydrateLatestJDConfirmForm = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    const message = messages.value[index]
    if (message?.kind === 'jd_confirm' && message.response) {
      hydrateJDConfirmForm(message.response)
      return
    }
  }
  missingFields.value = []
}

const hydrateEmailConfirmForm = (response) => {
  const request = response.artifacts?.find(item => item.type === 'email_send_request')?.content || {}
  emailMissingFields.value = response.missing_fields || []
  emailConfirmForm.value = {
    recipient_email: request.recipient_email || '',
    subject: request.subject || '',
    body: request.body || '',
    draft_text: request.draft_text || ''
  }
}

const hydrateLatestEmailConfirmForm = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    const message = messages.value[index]
    if (message?.kind === 'email_confirm' && message.response) {
      hydrateEmailConfirmForm(message.response)
      return
    }
  }
  emailMissingFields.value = []
}

const markJDConfirmSkipped = (message) => {
  if (!message) return
  message.kind = 'jd_confirm_done'
  message.content = `${message.content || ''}\n\n已暂停生成。你可以继续补充招聘信息，或稍后再让我生成 JD。`.trim()
}

const markEmailConfirmSkipped = (message) => {
  if (!message) return
  message.kind = 'email_confirm_done'
  message.content = `${message.content || ''}\n\n已暂停发送。你可以继续修改邮件内容，或稍后再让我发送。`.trim()
}

const confirmAndGenerate = async () => {
  const missing = validateConfirmForm()
  if (missing.length) {
    ElMessage.warning(`请补充：${missing.map(fieldLabel).join('、')}`)
    return
  }

  const conversationId = await ensureAgentConversation(pendingMessage.value || confirmForm.value.job_title)
  await persistConversationMessage(conversationId, 'user', '已确认招聘信息，请生成 JD。')
  markLatestJDConfirmSubmitted()
  messages.value.push({
    id: `${Date.now()}-confirm`,
    role: 'user',
    content: '已确认招聘信息，请生成 JD。'
  })
  await streamAgent({
    message: pendingMessage.value || confirmForm.value.additional_requirements || confirmForm.value.job_title,
    auto_execute: true,
    conversation_id: conversationId,
    confirmed_requirements: buildConfirmedRequirements()
  }, conversationId)
}

const markLatestJDConfirmSubmitted = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    if (messages.value[index]?.kind === 'jd_confirm') {
      messages.value[index] = {
        ...messages.value[index],
        kind: 'jd_confirm_done'
      }
      return
    }
  }
}

const validateEmailConfirmForm = () => {
  const payload = buildConfirmedEmailRequest()
  return ['recipient_email', 'subject', 'body'].filter(field => !String(payload[field] || '').trim())
}

const buildConfirmedEmailRequest = () => ({
  action: 'send_email',
  recipient_email: emailConfirmForm.value.recipient_email.trim(),
  subject: emailConfirmForm.value.subject.trim(),
  body: emailConfirmForm.value.body.trim(),
  draft_text: emailConfirmForm.value.draft_text.trim()
})

const markLatestEmailConfirmSubmitted = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    if (messages.value[index]?.kind === 'email_confirm') {
      messages.value[index] = {
        ...messages.value[index],
        kind: 'email_confirm_done'
      }
      return
    }
  }
}

const confirmAndSendEmail = async () => {
  const missing = validateEmailConfirmForm()
  if (missing.length) {
    ElMessage.warning(`请补充：${missing.map(fieldLabel).join('、')}`)
    return
  }

  const conversationId = await ensureAgentConversation(pendingMessage.value || emailConfirmForm.value.subject)
  await persistConversationMessage(conversationId, 'user', '已确认邮件内容，请发送。')
  markLatestEmailConfirmSubmitted()
  messages.value.push({
    id: `${Date.now()}-email-confirm`,
    role: 'user',
    content: '已确认邮件内容，请发送。'
  })
  await runAgent(
    {
      message: pendingMessage.value || emailConfirmForm.value.subject || '请发送邮件',
      auto_execute: true,
      conversation_id: conversationId,
      confirmed_requirements: buildConfirmedEmailRequest()
    },
    { conversationId }
  )
}

const streamAgent = async (payload, conversationId = currentConversationId.value, options = {}) => {
  const { replaceMessageId = null } = options
  const runningResponse = createGeneratingResponse()
  const runningMessageId = replaceMessageId || `${Date.now()}-agent-running`
  responses.value.push(runningResponse)
  const runningMessage = {
    id: runningMessageId,
    role: 'assistant',
    content: runningResponse.message,
    response: runningResponse
  }
  const replacementIndex = replaceMessageId ? messages.value.findIndex(message => message.id === replaceMessageId) : -1
  if (replacementIndex >= 0) {
    messages.value[replacementIndex] = {
      ...messages.value[replacementIndex],
      ...runningMessage,
      kind: undefined
    }
  } else {
    messages.value.push(runningMessage)
  }
  loading.value = true
  const signal = beginGeneration(runningMessageId, {
    type: 'jd_stream',
    payload: { ...payload },
    conversationId
  })
  if (!replaceMessageId) await scrollToBottom()

  try {
    const response = await agentApi.stream(payload, { signal })
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let streamedText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''

      for (const chunk of chunks) {
        const line = chunk.split('\n').find(item => item.startsWith('data: '))
        if (!line) continue
        const data = line.slice(6).trim()
        if (!data || data === '[DONE]') continue

        const event = JSON.parse(data)
        if (event.type === 'error') {
          throw new Error(event.error || 'HR Agent 执行失败')
        }
        if (event.type === 'delta') {
          const shouldFollowScroll = isNearMessageBottom()
          streamedText += event.delta || ''
          const currentResponse = responses.value[responses.value.length - 1] || runningResponse
          updateAssistantMessage(runningMessageId, currentResponse, streamedText)
          await scrollToBottomIfNeeded(shouldFollowScroll)
          continue
        }
        if (event.response) {
          const shouldFollowScroll = isNearMessageBottom()
          responses.value.splice(responses.value.length - 1, 1, event.response)
          const visibleContent = streamedText || event.response.message
          updateAssistantMessage(runningMessageId, event.response, visibleContent)
          await scrollToBottomIfNeeded(shouldFollowScroll)
        }
        if (event.type === 'final' && event.response?.message) {
          const shouldFollowScroll = isNearMessageBottom()
          const finalContent = streamedText.trim()
            ? `${streamedText.trim()}\n\n---\n${event.response.message}`
            : event.response.message
          const finalResponse = {
            ...event.response,
            message: finalContent
          }
          responses.value.splice(responses.value.length - 1, 1, finalResponse)
          updateAssistantMessage(runningMessageId, finalResponse, finalContent)
          const savedAssistantMessage = await persistConversationMessage(conversationId, 'assistant', finalContent, {
            intent: finalResponse.intent,
            route: finalResponse.route,
            agent_response: finalResponse
          })
          attachPersistedMessageId(runningMessageId, savedAssistantMessage)
          await scrollToBottomIfNeeded(shouldFollowScroll)
        }
      }
    }
  } catch (error) {
    if (isAbortError(error)) {
      markGenerationStopped(runningMessageId)
      ElMessage.info('已停止生成')
    } else {
      const failedResponse = createFailedResponse(error)
      updateAssistantMessage(runningMessageId, failedResponse, failedResponse.message)
      ElMessage.error(error?.message || 'HR Agent 执行失败')
    }
  } finally {
    loading.value = false
    finishGeneration(runningMessageId)
    if (!replaceMessageId) await scrollToBottom()
  }
}

const startResumeScreening = async () => {
  if (!screeningJobDescriptionId.value) {
    ElMessage.warning('请先选择用于匹配的 JD')
    syncResumeReadyState()
    return
  }
  const files = resumeFileList.value.map(item => item.raw).filter(Boolean)
  if (!files.length) {
    ElMessage.warning('请先选择简历文件')
    return
  }
  if (files.length > 20) {
    ElMessage.warning('单次最多上传 20 份简历')
    return
  }

  const runningResponse = createResumeScreeningResponse(files.length)
  const runningMessageId = `${Date.now()}-resume-running`
  const conversationId = await ensureAgentConversation('上传简历并进行匹配评分')
  const userMessage = `已上传 ${files.length} 份简历，请基于当前 JD 进行评分。`
  markResumeUploadSubmitted()
  messages.value.push({
    id: `${Date.now()}-resume-user`,
    role: 'user',
    content: userMessage
  })
  await persistConversationMessage(conversationId, 'user', userMessage, {
    intent: 'resume_screening',
    file_count: files.length
  })
  responses.value.push(runningResponse)
  messages.value.push({
    id: runningMessageId,
    role: 'assistant',
    content: runningResponse.message,
    response: runningResponse
  })
  resumeScreeningLoading.value = true
  loading.value = true
  const signal = beginGeneration(runningMessageId, {
    type: 'resume_screening',
    jobDescriptionId: screeningJobDescriptionId.value,
    files,
    conversationId
  })
  await scrollToBottom()

  try {
    const response = await agentApi.streamResumeScreening({
      jobDescriptionId: screeningJobDescriptionId.value,
      files,
      conversationId,
      signal
    })
    await consumeAgentStream(response, {
      activeMessageId: runningMessageId,
      keepStreamedTextOnFinal: true
    })
    ElMessage.success('批量简历筛选完成')
  } catch (error) {
    if (isAbortError(error)) {
      markGenerationStopped(runningMessageId)
      ElMessage.info('已停止评分')
    } else {
      const failedResponse = createFailedResponse(error)
      updateAssistantMessage(runningMessageId, failedResponse, failedResponse.message)
      ElMessage.error(error?.message || '批量简历筛选失败')
    }
  } finally {
    resumeScreeningLoading.value = false
    loading.value = false
    finishGeneration(runningMessageId)
    await scrollToBottom()
  }
}

const startInterviewPlan = async (options = {}) => {
  const {
    resumeEvaluationId = selectedInterviewResumeId.value,
    activeMessageId = null,
    appendUserMessage = true,
    userMessage = '请基于已评分候选人生成面试计划。'
  } = options
  if (!resumeEvaluationId) {
    ElMessage.warning('请先选择一位已评分候选人')
    return
  }

  selectedInterviewResumeId.value = resumeEvaluationId
  const runningResponse = createInterviewPlanResponse()
  const runningMessageId = activeMessageId || `${Date.now()}-interview-running`
  const conversationId = await ensureAgentConversation('生成面试计划')
  if (appendUserMessage) {
    messages.value.push({
      id: `${Date.now()}-interview-user`,
      role: 'user',
      content: userMessage
    })
    await persistConversationMessage(conversationId, 'user', userMessage, {
      intent: 'interview_plan',
      resume_evaluation_id: resumeEvaluationId
    })
  }
  responses.value.push(runningResponse)
  if (activeMessageId) {
    updateAssistantMessage(activeMessageId, runningResponse, runningResponse.message)
  } else {
    messages.value.push({
      id: runningMessageId,
      role: 'assistant',
      content: runningResponse.message,
      response: runningResponse
    })
  }
  interviewPlanLoading.value = true
  loading.value = true
  const signal = beginGeneration(runningMessageId, {
    type: 'interview_plan',
    resumeEvaluationId,
    conversationId
  })
  await scrollToBottom()

  try {
    const response = await agentApi.streamInterviewPlan({
      resumeEvaluationId,
      conversationId,
      signal
    })
    await consumeAgentStream(response, {
      activeMessageId: runningMessageId,
      keepStreamedTextOnFinal: true
    })
    ElMessage.success('面试计划生成完成')
  } catch (error) {
    if (isAbortError(error)) {
      markGenerationStopped(runningMessageId)
      ElMessage.info('已停止生成')
    } else {
      const failedResponse = createFailedResponse(error)
      updateAssistantMessage(runningMessageId, failedResponse, failedResponse.message)
      ElMessage.error(error?.message || '面试计划生成失败')
    }
  } finally {
    interviewPlanLoading.value = false
    loading.value = false
    finishGeneration(runningMessageId)
    await scrollToBottom()
  }
}

const startExamGeneration = async (options = {}) => {
  const {
    examRequirements = buildExamRequirements(),
    files: retryFiles = null,
    knowledgeFiles = null,
    conversationId: retryConversationId = null,
    replaceMessageId = null,
    appendUserMessage = true
  } = options
  if (!examRequirements.title || !examRequirements.subject) {
    ElMessage.warning('请补充试卷标题和考察方向')
    return
  }
  const files = retryFiles?.length ? retryFiles : getExamDocumentFiles()
  const reusableKnowledgeFiles = knowledgeFiles?.length ? knowledgeFiles : (examRequirements.knowledge_files || examForm.value.knowledge_files || [])
  if (!files.length && !reusableKnowledgeFiles.length) {
    ElMessage.warning('请先上传用于出题的参考文档')
    return
  }
  if (files.length > 5 || reusableKnowledgeFiles.length > 5) {
    ElMessage.warning('单次最多上传 5 个参考文档')
    return
  }

  const documentCount = files.length || reusableKnowledgeFiles.length
  const runningResponse = createExamGeneratingResponse(documentCount, examRequirements)
  const runningMessageId = replaceMessageId || `${Date.now()}-exam-running`
  const conversationId = retryConversationId || await ensureAgentConversation(examRequirements.title || '基于文档生成试卷')
  const userMessage = examRequirements.interview_plan_context
    ? `已确认试卷配置，请结合当前面试方案和 ${documentCount} 个参考文档生成试卷。`
    : `已确认试卷配置，请基于 ${documentCount} 个参考文档生成试卷。`
  markLatestExamConfigSubmitted(documentCount, examRequirements)
  if (appendUserMessage) {
    messages.value.push({
      id: `${Date.now()}-exam-user`,
      role: 'user',
      content: userMessage
    })
    await persistConversationMessage(conversationId, 'user', userMessage, {
      intent: 'exam_generate',
      exam_requirements: examRequirements,
      file_count: documentCount
    })
  }
  responses.value.push(runningResponse)
  const runningMessage = {
    id: runningMessageId,
    role: 'assistant',
    content: runningResponse.message,
    response: runningResponse
  }
  const replacementIndex = replaceMessageId ? messages.value.findIndex(message => message.id === replaceMessageId) : -1
  if (replacementIndex >= 0) {
    messages.value[replacementIndex] = {
      ...messages.value[replacementIndex],
      ...runningMessage,
      kind: undefined
    }
  } else {
    messages.value.push(runningMessage)
  }
  examGenerating.value = true
  loading.value = true
  const signal = beginGeneration(runningMessageId, {
    type: 'exam_generate',
    examRequirements,
    files,
    knowledgeFiles: reusableKnowledgeFiles,
    conversationId
  })
  if (!replaceMessageId) await scrollToBottom()

  try {
    const response = files.length
      ? await agentApi.streamExamWithDocuments({
        examRequirements,
        files,
        conversationId,
        signal
      })
      : await agentApi.streamExam({
        message: userMessage,
        auto_execute: true,
        conversation_id: conversationId,
        confirmed_requirements: {
          ...examRequirements,
          knowledge_files: reusableKnowledgeFiles
        }
      }, { signal })
    await consumeAgentStream(response, {
      activeMessageId: runningMessageId,
      keepStreamedTextOnFinal: true
    })
    ElMessage.success('考试试卷生成完成')
  } catch (error) {
    if (isAbortError(error)) {
      markGenerationStopped(runningMessageId)
      ElMessage.info('已停止生成')
    } else {
      const failedResponse = createFailedResponse(error)
      updateAssistantMessage(runningMessageId, failedResponse, failedResponse.message)
      ElMessage.error(error?.message || '考试生成失败')
    }
  } finally {
    examGenerating.value = false
    loading.value = false
    finishGeneration(runningMessageId)
    if (!replaceMessageId) await scrollToBottom()
  }
}

const continueExamConfig = async () => {
  if (!examDocumentFileList.value.length) {
    ElMessage.warning('请先上传用于出题的参考文档')
    return
  }
  if (examDocumentFileList.value.length > 5) {
    ElMessage.warning('单次最多上传 5 个参考文档')
    return
  }

  const configResponse = createExamConfigResponse()
  responses.value.push(configResponse)
  messages.value.push({
    id: `${Date.now()}-exam-docs-ready-user`,
    role: 'user',
    content: `已上传 ${examDocumentFileList.value.length} 个参考文档，请继续配置试卷。`
  })
  messages.value.push({
    id: `${Date.now()}-exam-config`,
    role: 'assistant',
    content: configResponse.message,
    kind: 'exam_generate',
    response: configResponse
  })
  await scrollToBottom()
}

const updateAssistantMessage = (messageId, response, content = response?.message, extra = {}) => {
  if (!response) return
  let index = messageId ? messages.value.findIndex(message => message.id === messageId) : -1
  if (index < 0) {
    for (let currentIndex = messages.value.length - 1; currentIndex >= 0; currentIndex--) {
      if (messages.value[currentIndex].role === 'assistant') {
        index = currentIndex
        break
      }
    }
  }
  if (index < 0) return
  messages.value[index] = {
    ...messages.value[index],
    content: content || messages.value[index].content,
    thinking: false,
    response,
    ...extra
  }
}

const showMessageActions = (message) => {
  if (message.thinking) return false
  if (isCurrentRunningMessage(message)) return true
  if (message.role === 'user') {
    return Boolean(message.content)
  }
  return Boolean(message.content && message.response && message.response.intent !== 'thinking')
}

const isCurrentRunningMessage = (message) => {
  return loading.value && currentRunningMessageId.value && message.id === currentRunningMessageId.value
}

const findPreviousUserMessage = (message) => {
  const currentIndex = messages.value.findIndex(item => item.id === message?.id)
  const startIndex = currentIndex >= 0 ? currentIndex - 1 : messages.value.length - 1
  for (let index = startIndex; index >= 0; index--) {
    if (messages.value[index]?.role === 'user' && messages.value[index].content?.trim()) {
      return messages.value[index]
    }
  }
  return null
}

const getExamSourceDocuments = (message) => {
  const artifacts = message?.response?.artifacts || []
  const sourceArtifact = artifacts.find(item => item.type === 'exam_source_documents')
  return Array.isArray(sourceArtifact?.content) ? sourceArtifact.content : []
}

const isPersistedMessageId = (value) => {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ''))
}

const deleteConversationChatMessage = async (message) => {
  if (loading.value || !message?.id) return
  const persistedMessageId = message.persistedMessageId || message.id
  if (currentConversationId.value && isPersistedMessageId(persistedMessageId)) {
    try {
      await deleteConversationMessage(currentConversationId.value, persistedMessageId)
    } catch (error) {
      console.error('删除 HR Agent 对话消息失败:', error)
      ElMessage.error(error?.response?.data?.detail || '删除对话消息失败')
      return
    }
  }
  const index = messages.value.findIndex(item => item.id === message.id)
  if (index >= 0) {
    messages.value.splice(index, 1)
  }
  const responseIndex = responses.value.findIndex(item => item === message.response)
  if (responseIndex >= 0) {
    responses.value.splice(responseIndex, 1)
  } else if (responses.value.length && lastResponse.value === message.response) {
    responses.value.pop()
  }
  await fetchAgentConversations()
}

const consumeAgentStream = async (response, options = {}) => {
  const {
    activeMessageId = null,
    persist = true,
    keepThinkingForNonFinal = false,
    keepStreamedTextOnFinal = false,
    transformResponse = null
  } = options
  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResponse = null
  let streamedText = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''

    for (const chunk of chunks) {
      const line = chunk.split('\n').find(item => item.startsWith('data: '))
      if (!line) continue
      const data = line.slice(6).trim()
      if (!data || data === '[DONE]') continue

      const event = JSON.parse(data)
      if (event.type === 'error') {
        throw new Error(event.error || 'HR Agent 执行失败')
      }
      if (event.type === 'delta') {
        const shouldFollowScroll = isNearMessageBottom()
        streamedText += event.delta || ''
        if (activeMessageId) {
          const messageIndex = messages.value.findIndex(message => message.id === activeMessageId)
          if (messageIndex >= 0) {
            messages.value[messageIndex] = {
              ...messages.value[messageIndex],
              content: streamedText,
              thinking: false
            }
          }
        }
        await scrollToBottomIfNeeded(shouldFollowScroll)
        continue
      }
      if (event.response) {
        const shouldFollowScroll = isNearMessageBottom()
        const transformed = transformResponse ? transformResponse(event.response, event) : { response: event.response }
        const eventResponse = transformed?.response || event.response
        if (responses.value.length) {
          responses.value.splice(responses.value.length - 1, 1, eventResponse)
        } else {
          responses.value.push(eventResponse)
        }
        if (event.type === 'final') {
          captureResumeScreeningContext(eventResponse)
          const finalSummary = formatFinalMessage(eventResponse)
          const finalMessage = eventResponse.intent === 'email_notification'
            ? (streamedText.trim() || finalSummary)
            : (keepStreamedTextOnFinal && streamedText.trim()
            ? `${streamedText.trim()}\n\n---\n${finalSummary}`
            : finalSummary)
          updateAssistantMessage(activeMessageId, eventResponse, finalMessage, { kind: transformed?.kind })
          finalResponse = eventResponse
          if (persist) {
            const savedAssistantMessage = await persistConversationMessage(currentConversationId.value, 'assistant', finalMessage, {
              intent: eventResponse.intent,
              route: eventResponse.route,
              kind: transformed?.kind,
              agent_response: eventResponse
            })
            attachPersistedMessageId(activeMessageId, savedAssistantMessage)
          }
        } else if (event.type === 'plan') {
          updateAssistantMessage(activeMessageId, eventResponse, streamedText, { kind: transformed?.kind })
        } else if (!keepThinkingForNonFinal) {
          updateAssistantMessage(activeMessageId, eventResponse)
        }
        await scrollToBottomIfNeeded(shouldFollowScroll)
      }
    }
  }
  return finalResponse
}

const createResumeScreeningResponse = (count) => ({
  message: `收到 ${count} 份简历，我会按当前 JD 逐份评分并保存结果。`,
  intent: 'resume_screening',
  route: '/recruitment/resume-screening',
  steps: [
    { id: 'upload', title: '接收简历文件', status: 'completed', detail: `已选择 ${count} 份简历` },
    { id: 'evaluate', title: '批量 AI 评分', status: 'running', detail: '等待后端开始逐份评分', tool: 'evaluate_resume' },
    { id: 'summary', title: '生成筛选摘要', status: 'pending', detail: '等待评分完成' }
  ],
  artifacts: [],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createResumeReadyResponse = (count, hasSelectedJD = false, submitted = false) => {
  if (count <= 0) return createResumeAwaitingUploadResponse()

  return {
    message: submitted
      ? `已确认 ${count} 份简历和匹配 JD，正在进入批量评分。`
      : hasSelectedJD
        ? `我已收到 ${count} 份简历，并已选择匹配 JD。点击“开始评分”后我会逐份评分并保存结果。`
        : `我已收到 ${count} 份简历。现在请选择用于匹配的 JD，确认后我再开始逐份评分并保存结果。`,
    intent: 'resume_screening',
    route: '/recruitment/resume-screening',
    steps: [
      { id: 'upload', title: '接收简历文件', status: 'completed', detail: `已选择 ${count} 份简历` },
      {
        id: 'select_jd',
        title: '选择匹配 JD',
        status: hasSelectedJD || submitted ? 'completed' : 'running',
        detail: hasSelectedJD || submitted ? '已选择用于评分匹配的 JD' : '请选择用于评分匹配的 JD'
      },
      {
        id: 'evaluate',
        title: '批量 AI 评分',
        status: submitted ? 'completed' : 'pending',
        detail: submitted ? '已提交到批量评分任务' : '点击开始评分后逐份评分',
        tool: 'evaluate_resume'
      }
    ],
    artifacts: [
      {
        type: 'resume_upload_request',
        title: '选择 JD 并开始评分',
        content: { requires_job_description: true, file_count: count },
        metadata: {}
      }
    ],
    suggestions: [],
    requires_confirmation: false,
    missing_fields: []
  }
}

const createResumeAwaitingUploadResponse = () => ({
  message: '我需要先拿到简历文件才能评分。请在底部消息框点击“上传文件”，添加 PDF、DOC 或 DOCX 简历后再发送筛选需求；收到简历后，我再让你选择用于匹配的 JD。',
  intent: 'resume_screening',
  route: '/recruitment/resume-screening',
  steps: [
    { id: 'plan', title: '选择执行工具', status: 'completed', detail: '判断需要调用简历评分工具，但前置条件尚未满足。', tool: 'evaluate_resume' },
    { id: 'upload', title: '等待上传简历', status: 'running', detail: '请先上传 PDF、DOC 或 DOCX 简历。' },
    { id: 'select_jd', title: '选择匹配 JD', status: 'pending', detail: '收到简历后再选择用于评分匹配的 JD。' },
    { id: 'evaluate', title: '批量 AI 评分', status: 'pending', detail: '简历和 JD 都确认后开始逐份评分。', tool: 'evaluate_resume' }
  ],
  artifacts: [
    {
      type: 'resume_upload_request',
      title: '上传简历后开始评分',
      content: { requires_job_description: true, accepted_formats: ['pdf', 'doc', 'docx'] },
      metadata: {}
    }
  ],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createInterviewPlanResponse = () => ({
  message: '收到候选人信息，我正在读取简历评分、关联 JD，并生成面试计划。',
  intent: 'interview_plan',
  route: '/recruitment/smart-interview',
  steps: [
    { id: 'load_resume', title: '读取候选人资料', status: 'running', detail: '等待后端读取简历评分' },
    { id: 'generate_plan', title: '生成面试计划', status: 'pending', tool: 'generate_interview_plan' },
    { id: 'save_plan', title: '保存面试计划', status: 'pending' }
  ],
  artifacts: [],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createExamConfigResponse = () => ({
  message: `我已收到 ${examDocumentFileList.value.length} 个参考文档。现在请确认试卷配置：标题、考察方向、总分、时长和题量。确认后我会解析文档并生成试卷。`,
  intent: 'exam_generate',
  route: '/training/exam-generator',
  steps: [
    { id: 'upload_docs', title: '等待上传参考文档', status: 'completed', detail: `已选择 ${examDocumentFileList.value.length} 个文档` },
    { id: 'confirm_exam', title: '确认考试配置', status: 'running', detail: '请确认试卷配置' },
    { id: 'generate_exam', title: '基于文档生成试卷', status: 'pending', tool: 'generate_exam' },
    { id: 'save_exam', title: '保存试卷', status: 'pending' }
  ],
  artifacts: [
    {
      type: 'exam_generate_request',
      title: '确认考试配置',
      content: buildExamRequirements(),
      metadata: {}
    }
  ],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createExamGeneratingResponse = (fileCount = examDocumentFileList.value.length, requirements = buildExamRequirements()) => ({
  message: requirements.interview_plan_context
    ? `考试配置、${fileCount} 个参考文档和当前面试方案已确认。我会先解析文档，再结合面试方案的考察重点生成试卷并保存到考试管理。`
    : `考试配置和 ${fileCount} 个参考文档已确认，我会先解析文档，再基于文档生成试卷并保存到考试管理。`,
  intent: 'exam_generate',
  route: '/training/exam-generator',
  steps: [
    { id: 'upload_docs', title: '接收参考文档', status: 'completed', detail: `已选择 ${fileCount} 个文档` },
    { id: 'process_docs', title: '解析文档内容', status: 'running', detail: '等待后端提取文本' },
    { id: 'generate_exam', title: '基于文档生成试卷', status: 'pending', detail: `${requirements.title} / ${requirements.subject}`, tool: 'generate_exam' },
    { id: 'save_exam', title: '保存试卷', status: 'pending' }
  ],
  artifacts: [],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createThinkingResponse = () => ({
  message: '思考中',
  intent: 'thinking',
  route: null,
  steps: [
    { id: 'understand', title: '识别用户意图', status: 'running', detail: '正在判断是普通聊天，还是需要调用 HR 工具。' },
    { id: 'plan', title: '规划下一步', status: 'pending', detail: '识别完成后展示执行计划或直接回复。' }
  ],
  artifacts: [],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const createFailedResponse = (error) => ({
  message: 'HR Agent 执行失败',
  intent: 'error',
  route: null,
  steps: [
    { id: 'failed', title: '执行失败', status: 'failed', detail: getErrorReason(error) }
  ],
  artifacts: [
    {
      type: 'error_recovery',
      title: '错误恢复建议',
      content: {
        reason: getErrorReason(error),
        advice: getErrorAdvice(error)
      },
      metadata: {}
    }
  ],
  suggestions: ['重试', '修改输入后重试', '检查配置'],
  requires_confirmation: false,
  missing_fields: []
})

const getErrorReason = (error) => {
  const raw = error?.response?.data?.detail || error?.message || ''
  if (!raw) return '暂时没有拿到具体错误信息。'
  if (/HTTP 401|unauthorized|token/i.test(raw)) return '登录状态可能已过期或接口鉴权失败。'
  if (/HTTP 404|not_found|Conversation Not Exists/i.test(raw)) return '服务端没有找到对应资源或会话上下文。'
  if (/HTTP 5|timeout|network|Failed to fetch/i.test(raw)) return '后端服务、模型服务或网络连接暂时异常。'
  return raw.length > 180 ? `${raw.slice(0, 180)}...` : raw
}

const getErrorAdvice = (error) => {
  const raw = error?.response?.data?.detail || error?.message || ''
  if (/401|unauthorized|token/i.test(raw)) return '请刷新页面或重新登录后再重试。'
  if (/404|not_found|Conversation Not Exists/i.test(raw)) return '建议开启新对话后重试；如果是生成任务，可以重新点击生成。'
  if (/5\\d\\d|timeout|network|Failed to fetch/i.test(raw)) return '可以直接点“重试”；如果仍失败，再稍微缩短输入或检查后端日志。'
  return '你可以直接点“重试”；如果需要调整要求，也可以在输入框补充说明后重新发送。'
}

const createStoppedResponse = () => ({
  message: '已停止生成。你可以修改要求后重试，或重新生成。',
  intent: 'stopped',
  route: null,
  steps: [
    { id: 'stopped', title: '已停止', status: 'failed', detail: '用户主动停止了本次生成。' }
  ],
  artifacts: [],
  suggestions: ['重新生成', '修改要求'],
  requires_confirmation: false,
  missing_fields: []
})

const createGeneratingResponse = () => ({
  message: '收到确认信息，我已经规划好工具链：先生成 JD，再生成简历评分标准并保存。这个过程可能需要几十秒，请不要关闭页面。',
  intent: 'jd',
  route: '/recruitment/jd-generator',
  steps: [
    { id: 'plan', title: '理解需求并规划工具', status: 'completed', detail: '选择 JD 生成工具，并串联评分标准生成' },
    { id: 'parse', title: '确认招聘需求', status: 'completed', detail: '已收到用户确认的信息' },
    { id: 'jd', title: '生成岗位 JD', status: 'pending', detail: '等待后端开始执行', tool: 'generate_jd' },
    { id: 'save_jd', title: '保存 JD', status: 'pending', detail: '生成完成后会自动保存到 JD 管理' },
    { id: 'criteria', title: '生成简历评分标准', status: 'pending', detail: 'JD 保存后自动生成', tool: 'generate_scoring_criteria' },
    { id: 'save_criteria', title: '保存评分标准', status: 'pending', detail: '生成完成后会自动保存' }
  ],
  artifacts: [
    {
      type: 'requirements',
      title: '已确认招聘需求',
      content: buildConfirmedRequirements(),
      metadata: {}
    }
  ],
  suggestions: [],
  requires_confirmation: false,
  missing_fields: []
})

const getResumeUploadMessageIndex = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    if (messages.value[index].kind === 'resume_upload') {
      return index
    }
  }
  return -1
}

const syncResumeReadyState = () => {
  const index = getResumeUploadMessageIndex()
  if (index < 0) return
  const response = createResumeReadyResponse(resumeFileList.value.length, Boolean(screeningJobDescriptionId.value))
  messages.value[index] = {
    ...messages.value[index],
    content: response.message,
    response
  }
}

const getExamDocumentMessageIndex = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    if (messages.value[index].kind === 'exam_document_upload') {
      return index
    }
  }
  return -1
}

const syncExamDocumentReadyState = () => {
  const index = getExamDocumentMessageIndex()
  if (index < 0) return
  const response = createExamConfigResponse()
  messages.value[index] = {
    ...messages.value[index],
    content: response.message,
    response
  }
}

const handleScreeningJDChange = () => {
  syncResumeReadyState()
}

const markResumeUploadSubmitted = () => {
  const index = getResumeUploadMessageIndex()
  if (index < 0) return
  const response = createResumeReadyResponse(resumeFileList.value.length, true, true)
  messages.value[index] = {
    ...messages.value[index],
    kind: 'resume_upload_done',
    content: response.message,
    response
  }
}

const markLatestExamConfigSubmitted = (documentCount, requirements) => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    const message = messages.value[index]
    if (message?.kind !== 'exam_generate' || message.role !== 'assistant') continue
    const response = message.response || createExamConfigResponse()
    const steps = (response.steps || []).map(step => {
      if (step.id === 'confirm_exam') {
        return { ...step, status: 'completed', detail: '试卷配置已确认' }
      }
      if (step.id === 'generate_exam') {
        return { ...step, status: 'pending', detail: `${requirements.title} / ${requirements.subject}`, tool: step.tool || 'generate_exam' }
      }
      return step
    })
    const updatedResponse = {
      ...response,
      message: `试卷配置和 ${documentCount} 个参考文档已确认，正在进入生成流程。`,
      steps
    }
    messages.value[index] = {
      ...message,
      kind: 'exam_generate_done',
      content: updatedResponse.message,
      response: updatedResponse
    }
    return
  }
}

const getRawFile = (file) => {
  const candidate = file?.raw || file
  if (!candidate) return null
  if (typeof Blob !== 'undefined' && candidate instanceof Blob) return candidate
  return candidate?.size !== undefined && candidate?.name ? candidate : null
}

const cacheExamDocumentFiles = (files = []) => {
  examDocumentFileList.value = files
  examDocumentRawFiles.value = files.map(getRawFile).filter(Boolean)
  syncExamDocumentReadyState()
}

const getExamDocumentFiles = () => {
  const rawFiles = examDocumentRawFiles.value.filter(Boolean)
  if (rawFiles.length) return rawFiles
  return examDocumentFileList.value.map(getRawFile).filter(Boolean)
}

const clearResumeFiles = () => {
  resumeFileList.value = []
  selectedScreeningJDId.value = ''
  syncResumeReadyState()
}

const removeResumeFile = (file) => {
  resumeFileList.value = resumeFileList.value.filter(item => item.uid !== file.uid)
  syncResumeReadyState()
}

const handleComposerFileChange = (uploadFile, uploadFiles) => {
  composerFileList.value = uploadFiles.slice(0, 20)
  if (uploadFiles.length > 20) {
    ElMessage.warning('单次最多上传 20 个文件')
  }
}

const buildAttachmentMetadata = (files = []) => {
  return files.map(file => ({
    name: file.name,
    size: file.size || file.raw?.size,
    content_type: file.raw?.type || file.type || ''
  }))
}

const removeComposerFile = (file) => {
  composerFileList.value = composerFileList.value.filter(item => item.uid !== file.uid)
}

const isResumeFile = (file) => {
  return /\.(pdf|doc|docx)$/i.test(file.name || '')
}

const extractSuccessfulResumeResults = (response) => {
  if (response?.intent !== 'resume_screening') return ''
  const resultArtifact = response.artifacts?.find(artifact => artifact.type === 'resume_screening_results')
  const results = Array.isArray(resultArtifact?.content) ? resultArtifact.content : []
  return results.filter(result => result.status !== 'failed' && result.id)
}

const extractSingleSuccessfulResumeId = (response) => {
  const successfulResults = extractSuccessfulResumeResults(response)
  return successfulResults.length === 1 ? successfulResults[0].id : ''
}

const captureResumeScreeningContext = (response) => {
  const resumeEvaluationId = extractSingleSuccessfulResumeId(response)
  if (resumeEvaluationId) {
    lastSingleResumeEvaluationId.value = resumeEvaluationId
    selectedInterviewResumeId.value = resumeEvaluationId
  } else if (response?.intent === 'resume_screening') {
    lastSingleResumeEvaluationId.value = ''
  }
}

const getLastSingleResumeEvaluationId = () => {
  if (lastSingleResumeEvaluationId.value) return lastSingleResumeEvaluationId.value
  for (let index = messages.value.length - 1; index >= 0; index--) {
    const resumeEvaluationId = extractSingleSuccessfulResumeId(messages.value[index]?.response)
    if (resumeEvaluationId) return resumeEvaluationId
  }
  return ''
}

const getRecentResumeScreeningResults = () => {
  for (let index = messages.value.length - 1; index >= 0; index--) {
    const results = extractSuccessfulResumeResults(messages.value[index]?.response)
    if (results.length) return results
  }
  return []
}

const normalizeCandidateText = (text = '') => {
  return String(text)
    .toLowerCase()
    .replace(/\.(pdf|docx?|txt|md)$/gi, '')
    .replace(/[_\-()[\]【】（）\s]/g, '')
}

const findMentionedResumeEvaluation = (message = '') => {
  const normalizedMessage = normalizeCandidateText(message)
  if (!normalizedMessage) return null
  const matches = getRecentResumeScreeningResults().filter(result => {
    const names = [result.name, result.filename].filter(Boolean).map(normalizeCandidateText)
    return names.some(name => name && (normalizedMessage.includes(name) || name.includes(normalizedMessage)))
  })
  return matches.length === 1 ? matches[0] : null
}

const shouldUseContextualResumeForInterview = (message = '') => {
  return /他|她|其|这个|这位|该候选人|该简历|刚才|上面|前面|上一位|刚刚|这份简历/.test(message)
}

const formatFinalMessage = (response) => {
  const lines = [response.message]
  const emailDraft = response.artifacts?.find(artifact => artifact.type === 'email_draft')?.content
  if (emailDraft) {
    lines.push('', '邮件草稿：', String(emailDraft).trim())
  }

  if (response.intent !== 'resume_screening') {
    return lines.join('\n')
  }

  const resultArtifact = response.artifacts?.find(artifact => artifact.type === 'resume_screening_results')
  const results = Array.isArray(resultArtifact?.content) ? resultArtifact.content : []
  if (!results.length) {
    return lines.join('\n')
  }

  const successfulResults = results.filter(result => result.status !== 'failed')
  const failedResults = results.filter(result => result.status === 'failed')
  const topResult = successfulResults[0]
  const strongResults = successfulResults.filter(result => Number(result.score || 0) >= 80)
  const cautiousResults = successfulResults.filter(result => Number(result.score || 0) < 60)

  if (topResult) {
    lines.push(
      '',
      `简要结论：${topResult.name || topResult.filename} 综合匹配度最高（${topResult.score || 0}分）。` +
        (strongResults.length ? ` ${strongResults.length} 位候选人达到 80 分以上，建议优先沟通。` : '') +
        (cautiousResults.length ? ` ${cautiousResults.length} 位候选人低于 60 分，建议谨慎推进。` : '') +
        (failedResults.length ? ` ${failedResults.length} 份简历评分失败，需要重新上传或检查文件。` : '')
    )
  }

  lines.push('', '评分结果：')
  results.forEach((result, index) => {
    if (result.status === 'failed') {
      lines.push(`${index + 1}. ${result.filename}：评分失败（${result.error || '未知错误'}）`)
      return
    }
    const name = result.name || result.filename
    lines.push(`${index + 1}. ${name}：${result.score || 0}分`)
  })
  lines.push('', '你可以继续让我为某位候选人生成面试题，或去“简历筛选”页查看完整评价。')
  return lines.join('\n')
}

const formatAgentMessage = (response, prefix = '') => {
  const lines = [`${prefix}${response.message}`]
  const emailDraft = response.artifacts?.find(artifact => artifact.type === 'email_draft')?.content
  if (emailDraft) {
    lines.push('', '邮件草稿：', String(emailDraft).trim())
  }
  return lines.join('\n')
}

const escapeHtml = (text = '') => {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const formatMessageContent = (message) => {
  const content = message?.content || ''
  if (message?.role !== 'assistant') {
    return escapeHtml(content).replace(/\n/g, '<br>')
  }
  return marked(escapeHtml(content))
}

const fetchJDOptions = async () => {
  try {
    jdOptionsLoading.value = true
    const response = await jobDescriptionApi.getJDList({ page: 1, size: 100 })
    jdOptions.value = response?.items || []
    if (!selectedScreeningJDId.value && savedJobDescriptionId.value) {
      selectedScreeningJDId.value = savedJobDescriptionId.value
    }
    syncResumeReadyState()
  } catch (error) {
    console.error('获取 JD 列表失败:', error)
  } finally {
    jdOptionsLoading.value = false
  }
}

const fetchResumeOptions = async () => {
  try {
    resumeOptionsLoading.value = true
    const response = await resumeApi.getResumeHistory({ skip: 0, limit: 100 })
    resumeOptions.value = response?.items || response?.data?.items || []
    if (!selectedInterviewResumeId.value && resumeOptions.value.length) {
      selectedInterviewResumeId.value = resumeOptions.value[0].id
    }
  } catch (error) {
    console.error('获取候选人列表失败:', error)
  } finally {
    resumeOptionsLoading.value = false
  }
}

const hydrateExamForm = (response) => {
  const parsed = response.artifacts?.find(item => (
    item.type === 'exam_generate_request' || item.type === 'exam_document_upload_request'
  ))?.content || {}
  const existingContext = parsed.interview_plan_context || examForm.value.interview_plan_context || currentExamInterviewContext.value
  if (parsed.interview_plan_context) {
    currentExamInterviewContext.value = parsed.interview_plan_context
  }
  examForm.value = {
    title: parsed.title || '',
    subject: parsed.subject || '',
    description: parsed.description || '',
    difficulty: parsed.difficulty || 'medium',
    duration: Number(parsed.duration || 60),
    total_score: Number(parsed.total_score || 100),
    question_types: parsed.question_types || ['single_choice', 'multiple_choice', 'short_answer'],
    question_counts: {
      single_choice: Number(parsed.question_counts?.single_choice ?? 5),
      multiple_choice: Number(parsed.question_counts?.multiple_choice ?? 3),
      short_answer: Number(parsed.question_counts?.short_answer ?? 2)
    },
    special_requirements: parsed.special_requirements || '',
    interview_plan_context: existingContext,
    knowledge_files: parsed.knowledge_files || []
  }
}

const buildExamRequirements = () => ({
  ...examForm.value,
  interview_plan_context: examForm.value.interview_plan_context || currentExamInterviewContext.value || null,
  knowledge_files: examForm.value.knowledge_files || [],
  question_counts: { ...examForm.value.question_counts },
  question_types: Object.entries(examForm.value.question_counts)
    .filter(([, count]) => Number(count) > 0)
    .map(([type]) => type)
})

const formatResumeOption = (resume) => {
  const name = resume.candidate_name || resume.name || resume.original_filename || '候选人'
  const score = resume.total_score ?? resume.score
  const position = resume.candidate_position || resume.position || ''
  return `${name}${position ? `｜${position}` : ''}${score !== undefined && score !== null ? `｜${score}分` : ''}`
}

const formatConversationTime = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

const validateConfirmForm = () => {
  const requiredFields = ['job_title', 'location', 'salary', 'experience', 'education']
  const values = buildConfirmedRequirements()
  return requiredFields.filter(field => {
    const value = values[field]
    return value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)
  })
}

const buildConfirmedRequirements = () => ({
  job_title: confirmForm.value.job_title.trim(),
  department: confirmForm.value.department.trim(),
  location: confirmForm.value.location.trim(),
  salary: confirmForm.value.salary.trim(),
  experience: confirmForm.value.experience.trim(),
  education: confirmForm.value.education.trim(),
  job_type: confirmForm.value.job_type.trim(),
  skills: splitTextList(confirmForm.value.skillsText),
  benefits: splitTextList(confirmForm.value.benefitsText),
  additional_requirements: confirmForm.value.additional_requirements.trim()
})

const splitTextList = (value) => {
  return String(value || '')
    .split(/[,，、\/]/)
    .map(item => item.trim())
    .filter(Boolean)
}

const formatListForInput = (value) => {
  if (Array.isArray(value)) return value.join('、')
  return value || ''
}

const fieldLabel = (field) => {
  const labels = {
    job_title: '岗位名称',
    location: '工作地点',
    salary: '薪资范围',
    experience: '经验要求',
    education: '学历要求',
    skills: '核心技能',
    recipient_email: '收件人',
    subject: '邮件主题',
    body: '邮件正文'
  }
  return labels[field] || field
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const isNearMessageBottom = (threshold = 96) => {
  const element = messagesRef.value
  if (!element) return true
  return element.scrollHeight - element.scrollTop - element.clientHeight <= threshold
}

const scrollToBottomIfNeeded = async (shouldFollow) => {
  if (shouldFollow) {
    await scrollToBottom()
  }
}

const stepType = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'primary'
  if (status === 'failed') return 'danger'
  return 'info'
}

const statusText = (status) => {
  const labels = {
    completed: '已完成',
    running: '执行中',
    pending: '等待中',
    failed: '失败'
  }
  return labels[status] || status
}

const displayStepStatus = (message, step) => {
  if (
    step?.id === 'collect_changes' &&
    step?.status === 'running' &&
    (hasArtifact(message?.response, 'jd_edit_request') || hasArtifact(message?.response, 'criteria_edit_request'))
  ) {
    return 'pending'
  }
  return step?.status
}

const shouldShowPlan = (message) => {
  return message.role === 'assistant' &&
    !message.thinking &&
    message.response?.intent !== 'general' &&
    message.response?.intent !== 'thinking' &&
    message.response?.steps?.length
}

const hasRunningStep = (message) => {
  if (hasArtifact(message.response, 'jd_edit_request') || hasArtifact(message.response, 'criteria_edit_request')) return false
  return Boolean(message.response?.steps?.some(step => step.status === 'running'))
}

const hasFailedStep = (message) => {
  return Boolean(message.response?.steps?.some(step => step.status === 'failed'))
}

const isPlanRunning = (message) => {
  return isCurrentRunningMessage(message) || hasRunningStep(message)
}

const planElapsedText = (message) => {
  if (isCurrentRunningMessage(message)) return `已用 ${generationElapsedSeconds.value}s`
  const elapsedSeconds = message.elapsedSeconds ?? generationElapsedByMessage.value[message.id]
  if (elapsedSeconds === undefined || elapsedSeconds === null) return ''
  return `耗时 ${elapsedSeconds}s`
}

const currentStepText = (message) => {
  const steps = message.response?.steps || []
  if (hasArtifact(message.response, 'jd_edit_request')) return '等待：确认修改要求'
  if (hasArtifact(message.response, 'criteria_edit_request')) return '等待：确认修改要求'
  const runningStep = steps.find(step => step.status === 'running')
  const failedStep = steps.find(step => step.status === 'failed')
  if (runningStep) return `正在：${runningStep.title}`
  if (failedStep) return `失败：${failedStep.title}`
  const lastCompleted = [...steps].reverse().find(step => step.status === 'completed')
  const nextPending = steps.find(step => step.status === 'pending')
  if (nextPending && lastCompleted) return `等待：${nextPending.title}`
  return lastCompleted ? `已完成：${lastCompleted.title}` : '等待开始'
}

const planProgressText = (message) => {
  const steps = message.response?.steps || []
  const completed = steps.filter(step => step.status === 'completed').length
  if (steps.some(step => step.status === 'failed')) return '需要处理'
  if (hasArtifact(message.response, 'jd_edit_request') || hasArtifact(message.response, 'criteria_edit_request')) return `${completed}/${steps.length}`
  if (steps.some(step => step.status === 'running')) return `${completed}/${steps.length}`
  if (steps.some(step => step.status === 'pending') && completed > 0) return `${completed}/${steps.length}`
  return '已完成'
}

const hasArtifact = (response, type) => {
  return Boolean(response?.artifacts?.some(artifact => artifact.type === type))
}

const intentLabel = (intent) => {
  const labels = {
    jd: 'JD 生成',
    jd_edit: 'JD 修改',
    criteria_edit: '评分标准修改',
    resume_screening: '简历筛选',
    interview_plan: '面试计划',
    exam_generate: '试卷生成',
    email_notification: '邮件草稿',
    resource_delete: '删除操作',
    thinking: '思考中',
    error: '执行失败'
  }
  return labels[intent] || intent
}

const toolLabel = (tool) => {
  const labels = {
    parse_requirements: '解析',
    generate_jd: '生成 JD',
    edit_jd: '修改 JD',
    edit_scoring_criteria: '修改评分标准',
    generate_scoring_criteria: '评分标准',
    evaluate_resume: '简历评分',
    generate_interview_plan: '面试计划',
    generate_exam: '生成试卷',
    delete_resource: '删除资源',
    draft_email: '邮件草稿'
  }
  return labels[tool] || tool
}

</script>

<style scoped lang="scss">
.hr-agent-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  margin: 0;
  padding: 16px 20px 18px;
  box-sizing: border-box;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #172033;
  overflow: hidden;
}

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 16px 40px rgba(31, 41, 55, 0.16);
  backdrop-filter: blur(10px);

  h1 {
    margin: 0 0 2px;
    color: #1e293b;
    font-size: 22px;
    line-height: 1.15;
  }

  p {
    margin: 0;
    color: #64748b;
    font-size: 13px;
  }
}

.agent-title-block {
  min-width: 0;
}

.agent-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.agent-kicker {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.14), rgba(118, 75, 162, 0.14));
  color: #667eea;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.agent-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}

.chat-card {
  height: 100%;
  min-height: 0;
  border: 0;
  border-radius: 16px;
  box-shadow: 0 18px 45px rgba(31, 41, 55, 0.16);
  overflow: hidden;
}

.chat-card {
  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    box-sizing: border-box;
    padding: 14px;
  }
}

.conversation-sidebar {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  box-sizing: border-box;
  padding: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 45px rgba(31, 41, 55, 0.14);
  backdrop-filter: blur(10px);
}

.sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;

  p {
    margin: 3px 0 0;
    color: #94a3b8;
    font-size: 12px;
  }
}

.sidebar-title {
  color: #1e293b;
  font-size: 15px;
  font-weight: 800;
}

.conversation-loading {
  padding: 4px 2px;
}

.conversation-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  transition: 0.18s ease;

  &:hover,
  &.active {
    border-color: #a5b4fc;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  }
}

.conversation-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 7px;
  border: 0;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;

  span {
    overflow: hidden;
    color: #0f172a;
    font-size: 13px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: #94a3b8;
    font-size: 11px;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }
}

.conversation-delete {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.18s ease;
}

.conversation-item:hover .conversation-delete,
.conversation-item.active .conversation-delete {
  opacity: 1;
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
  border-radius: 14px;
}

.message {
  display: flex;
  margin-bottom: 14px;

  &.user {
    justify-content: flex-end;

    .bubble {
      color: #fff;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
  }

  &.assistant .bubble {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #dbe4f0;
  }
}

.bubble {
  position: relative;
  max-width: min(760px, 84%);
  padding: 12px 15px;
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.08);
}

.role {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  opacity: 0.7;
}

.content {
  white-space: pre-wrap;
  line-height: 1.6;
}

.markdown-content {
  white-space: normal;
  line-height: 1.7;
  color: #1f2937;

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4),
  :deep(h5),
  :deep(h6) {
    margin: 14px 0 8px;
    color: #0f172a;
    font-weight: 800;
    line-height: 1.35;
  }

  :deep(h1) { font-size: 22px; }
  :deep(h2) { font-size: 19px; }
  :deep(h3) { font-size: 17px; }
  :deep(h4),
  :deep(h5),
  :deep(h6) { font-size: 15px; }

  :deep(p) {
    margin: 8px 0;
  }

  :deep(ul),
  :deep(ol) {
    margin: 8px 0;
    padding-left: 22px;
  }

  :deep(li) {
    margin: 4px 0;
  }

  :deep(hr) {
    margin: 14px 0;
    border: 0;
    border-top: 1px solid #e2e8f0;
  }

  :deep(blockquote) {
    margin: 10px 0;
    padding: 8px 12px;
    border-left: 4px solid #93c5fd;
    border-radius: 8px;
    background: #eff6ff;
    color: #475569;
  }

  :deep(code) {
    padding: 2px 5px;
    border-radius: 5px;
    background: #f1f5f9;
    color: #0f172a;
    font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
    font-size: 12px;
  }

  :deep(pre) {
    margin: 10px 0;
    padding: 12px;
    overflow-x: auto;
    border-radius: 10px;
    background: #f8fafc;

    code {
      padding: 0;
      background: transparent;
    }
  }

  :deep(table) {
    width: 100%;
    margin: 10px 0;
    border-collapse: collapse;
    font-size: 13px;
  }

  :deep(th),
  :deep(td) {
    padding: 8px 10px;
    border: 1px solid #e2e8f0;
    text-align: left;
  }

  :deep(th) {
    background: #f8fafc;
    font-weight: 700;
  }

  :deep(:first-child) {
    margin-top: 0;
  }

  :deep(:last-child) {
    margin-bottom: 0;
  }
}

.thinking-card {
  min-width: 240px;
}

.thinking-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  color: #1e3a8a;

  strong {
    display: block;
    font-size: 13px;
    font-weight: 800;
  }

  p {
    margin: 2px 0 0;
    color: #64748b;
    font-size: 12px;
  }
}

.thinking-spinner {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 2px solid #bfdbfe;
  border-top-color: #2563eb;
  border-radius: 999px;
  animation: spin 0.9s linear infinite;
}

.chat-plan-card {
  margin-bottom: 12px;
  padding: 0;
  border: 1px solid #c7d2fe;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  overflow: hidden;

  &[open] .chat-plan-header {
    border-bottom: 1px solid #dbeafe;
  }
}

.chat-plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  list-style: none;

  &::-webkit-details-marker {
    display: none;
  }

  &::before {
    content: '▸';
    color: #60a5fa;
    transition: transform 0.18s ease;
  }
}

.chat-plan-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}

.plan-live-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #bfdbfe;
  border-top-color: #667eea;
  border-radius: 999px;
  animation: spin 0.85s linear infinite;
}

.chat-plan-card[open] .chat-plan-header::before {
  transform: rotate(90deg);
}

.chat-plan-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  em {
    color: #94a3b8;
    font-size: 12px;
    font-style: normal;
    font-weight: 700;
  }

  small {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
  }
}

.plan-current-step {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &.is-running {
    color: #1d4ed8;
    font-weight: 900;
  }

  &.is-failed {
    color: #dc2626;
    font-weight: 900;
  }
}

.plan-elapsed {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.chat-step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}

.chat-step {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  color: #475569;

  &.is-completed {
    .chat-step-marker {
      color: #fff;
      background: #16a34a;
      border-color: #16a34a;
    }
  }

  &.is-running {
    padding: 8px;
    margin: -8px;
    border-radius: 12px;
    background: linear-gradient(90deg, rgba(37, 99, 235, 0.08), rgba(37, 99, 235, 0.02));
    box-shadow: inset 0 0 0 1px rgba(147, 197, 253, 0.5);

    .chat-step-marker {
      color: #2563eb;
      background: #eff6ff;
      border-color: #93c5fd;
    }

    .chat-step-title span {
      color: #1d4ed8;
    }
  }

  &.is-failed {
    .chat-step-marker {
      color: #fff;
      background: #dc2626;
      border-color: #dc2626;
    }
  }
}

.chat-step-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.chat-step-body {
  min-width: 0;
  padding-bottom: 8px;
  border-bottom: 1px dashed #e2e8f0;

  p {
    margin: 3px 0 0;
    color: #64748b;
    font-size: 12px;
    line-height: 1.45;
  }
}

.chat-step:last-child .chat-step-body {
  padding-bottom: 0;
  border-bottom: none;
}

.chat-step-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;

  > span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    color: #0f172a;
  }

  em {
    flex-shrink: 0;
    color: #94a3b8;
    font-size: 12px;
    font-style: normal;
    font-weight: 600;
  }
}

.step-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.45);
  animation: livePulse 1.2s ease-out infinite;
}

.chat-step-loading {
  animation: spin 1s linear infinite;
}

@keyframes livePulse {
  70% {
    box-shadow: 0 0 0 7px rgba(37, 99, 235, 0);
  }

  100% {
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.composer-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.attached-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}

.composer-left-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-upload-panel,
.chat-tool-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(560px, 100%);
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.jd-select,
.tool-select,
.resume-upload {
  width: 100%;
}

.resume-upload-actions,
.tool-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.chat-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.message-actions {
  position: absolute;
  right: 10px;
  bottom: -18px;
  z-index: 2;
  display: flex;
  gap: 8px;
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #dbe4f0;
  border-radius: 999px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-2px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.message .bubble:hover .message-actions,
.message .message-actions:focus-within {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.error-recovery-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(560px, 100%);
  margin-top: 12px;

  p {
    margin: 0;
    color: #64748b;
    font-size: 14px;
    line-height: 1.7;
  }
}

.composer {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.08);
}

.composer-actions {
  margin-top: 12px;
}

.exam-number-grid {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.question-counts {
  grid-template-columns: repeat(3, minmax(140px, 1fr));
}

.exam-number-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;

  span {
    color: #64748b;
    font-size: 13px;
    font-weight: 600;
  }

  :deep(.el-input-number) {
    width: 100%;
  }
}

.confirm-alert {
  margin-bottom: 18px;
}

.confirm-form {
  padding-top: 4px;
}

@media (max-width: 1100px) {
  .agent-layout {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .chat-upload-panel,
  .chat-tool-panel {
    min-width: auto;
  }

  .question-counts {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
}

@media (max-width: 720px) {
  .agent-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .agent-header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .agent-layout {
    grid-template-columns: 1fr;
  }

  .conversation-sidebar {
    position: static;
    height: auto;
    max-height: 200px;
    min-height: 0;
  }

  .messages {
    min-height: 360px;
  }

  .bubble {
    max-width: 92%;
  }

  .composer-actions {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;

    .el-button {
      width: 100%;
    }
  }
}
</style>
