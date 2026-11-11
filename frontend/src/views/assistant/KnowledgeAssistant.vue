<template>
  <div class="knowledge-assistant">
    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧智能对话区域 -->
      <div class="chat-section">
        <el-card class="chat-card">
          <!-- 智能对话头部 -->
          <template #header>
            <div class="chat-header">
              <div class="header-left">
                <h3 class="section-title">
                  <el-icon><ChatDotRound /></el-icon>
                  智能对话
                </h3>
              </div>
              <div class="header-right">
                <!-- 知识库选择器 -->
                <el-select
                  v-model="selectedKnowledgeBase"
                  placeholder="选择知识库"
                  style="width: 200px"
                  @change="handleKnowledgeBaseChange"
                >
                  <el-option
                    v-for="kb in knowledgeBases"
                    :key="kb.id"
                    :label="kb.name"
                    :value="kb.id"
                  >
                    <div class="kb-option">
                      <span class="kb-name">{{ kb.name }}</span>
                      <span class="kb-count">{{ kb.document_count }}个文档</span>
                    </div>
                  </el-option>
                </el-select>
                
                <!-- 历史对话按钮 -->
                <el-button 
                  type="primary" 
                  :icon="Clock" 
                  @click="openChatHistory"
                  circle
                  title="历史对话"
                />
                
                <!-- 清空对话按钮 -->
                <el-button 
                  type="danger" 
                  :icon="Delete" 
                  @click="clearChat"
                  circle
                  title="清空对话"
                />
              </div>
            </div>
          </template>
          
          <!-- 聊天消息区域 -->
          <div class="chat-messages" ref="messagesContainer">
            <div v-if="messages.length === 0" class="empty-chat">
              <el-empty description="开始您的智能问答之旅">
                <template #image>
                  <el-icon size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
                </template>
              </el-empty>
            </div>
            
            <div v-for="(message, index) in messages" :key="index" class="message-item">
              <!-- 用户消息 -->
              <div v-if="message.type === 'user'" class="user-message">
                <div class="message-content">
                  <div class="message-text">{{ message.content }}</div>
                </div>
                <div class="message-avatar">
                  <el-avatar :size="32" :icon="UserFilled" />
                </div>
              </div>
              
              <!-- 助手消息 -->
              <div v-else class="assistant-message">
                <div class="message-avatar">
                  <el-avatar :size="32" :icon="UserFilled" />
                </div>
                <div class="message-content">
                  <div class="message-text" v-html="formatMarkdown(message.content)"></div>
                  <!-- 流式输入指示器 -->
                  <div v-if="message.isStreaming" class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 加载状态 -->
            <div v-if="isLoading" class="loading-message">
              <div class="message-avatar">
                <el-avatar :size="32" :icon="UserFilled" />
              </div>
              <div class="message-content">
                <el-skeleton :rows="2" animated />
              </div>
            </div>
          </div>
          
          <!-- 输入区域 -->
          <div class="chat-input">
            <div class="input-container">
              <el-input
                v-model="currentMessage"
                type="textarea"
                :rows="3"
                placeholder="请输入您的问题..."
                @keydown.ctrl.enter="sendMessage"
                :disabled="isLoading"
              />
              <div class="input-actions">
                <div class="input-tips">
                  <span>Ctrl + Enter 发送</span>
                </div>
                <el-button 
                  type="primary" 
                  :icon="Promotion" 
                  @click="sendMessage"
                  :loading="isLoading"
                  :disabled="!currentMessage.trim()"
                >
                  发送
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧文档片段区域 -->
      <div class="chunks-section">
        <el-card class="chunks-card">
          <template #header>
            <div class="chunks-header">
              <h3 class="section-title">
                <el-icon><Document /></el-icon>
                相关文档片段
              </h3>
              <el-badge :value="documentChunks.length" class="item-count" />
            </div>
          </template>
          
          <div class="chunks-content">
            <div v-if="documentChunks.length === 0" class="empty-chunks">
              <el-empty description="暂无相关文档片段">
                <template #image>
                  <el-icon size="64" color="#c0c4cc"><Document /></el-icon>
                </template>
              </el-empty>
            </div>
            
            <div v-else class="chunks-list">
              <div 
                v-for="(chunk, index) in documentChunks" 
                :key="index" 
                class="chunk-item"
                :class="{ highlighted: chunk.highlighted }"
              >
                <div class="chunk-header">
                  <div class="chunk-source">
                    <el-icon class="doc-icon"><Document /></el-icon>
                    <span class="doc-title">{{ chunk.source || '未知文档' }}</span>
                  </div>
                  <el-tag 
                    :type="getScoreType(chunk.score)" 
                    size="small" 
                    class="chunk-score"
                  >
                    {{ (chunk.score * 100).toFixed(0) }}%
                  </el-tag>
                </div>
                
                <div class="chunk-content">
                  <p>{{ chunk.content }}</p>
                </div>
                
                <div class="chunk-meta">
                  <span class="chunk-index">片段 #{{ index + 1 }}</span>
                  <span class="chunk-size">{{ formatFileSize(chunk.content.length) }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
    
    <!-- 历史对话抽屉 -->
    <el-drawer
      v-model="showChatHistory"
      title="历史对话"
      direction="rtl"
      size="400px"
    >
      <div class="chat-history-content">
        <div v-if="chatHistory.length === 0" class="empty-history">
          <el-empty description="暂无历史对话">
            <template #image>
              <el-icon size="64" color="#c0c4cc"><Clock /></el-icon>
            </template>
          </el-empty>
        </div>
        
        <div v-else class="history-list">
          <div 
            v-for="(session, index) in chatHistory" 
            :key="index" 
            class="history-item"
            @click="loadChatSession(session)"
          >
            <div class="history-header">
              <h4 class="history-title">{{ session.title || `对话 ${index + 1}` }}</h4>
              <span class="history-time">{{ formatTime(session.timestamp) }}</span>
            </div>
            <p class="history-preview">{{ session.preview }}</p>
            <div class="history-meta">
              <span class="message-count">{{ session.messageCount }}条消息</span>
              <el-button 
                type="danger" 
                size="small" 
                :icon="Delete" 
                @click.stop="deleteChatSession(index)"
                text
              />
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
    
    <!-- 文档上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="600px"
      :before-close="resetUploadForm"
    >
      <div class="upload-content">
        <el-form :model="uploadForm" label-width="100px">
          <el-form-item label="知识库">
            <el-select v-model="uploadForm.knowledgeBaseId" placeholder="选择知识库" style="width: 100%">
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="文档分类">
            <el-input v-model="uploadForm.category" placeholder="请输入文档分类" />
          </el-form-item>
          
          <el-form-item label="文档描述">
            <el-input 
              v-model="uploadForm.description" 
              type="textarea" 
              :rows="3" 
              placeholder="请输入文档描述" 
            />
          </el-form-item>
        </el-form>
        
        <div class="upload-demo">
          <el-upload
            ref="uploadRef"
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadData"
            :before-upload="beforeUpload"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :on-remove="handleRemove"
            :file-list="fileList"
            multiple
            drag
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
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetUploadForm">取消</el-button>
          <el-button type="primary" @click="confirmUpload" :loading="uploading">
            确认上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Upload,
  Search,
  Document,
  DocumentCopy,
  Tickets,
  Delete,
  UserFilled,
  Position,
  UploadFilled,
  Clock,
  Promotion
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { getKnowledgeBases } from '@/api/knowledgeBase'
import { 
  getConversations, 
  createConversation, 
  deleteConversation,
  getConversationMessages,
  saveConversationMessages 
} from '@/api/conversation'
import { useRoute } from 'vue-router'

const authStore = useAuthStore()
const route = useRoute()

// 响应式数据
const messages = ref([])
const documentChunks = ref([])
const currentMessage = ref('')
const isLoading = ref(false)
const showUploadDialog = ref(false)
const showChatHistory = ref(false)
const uploading = ref(false)
const fileList = ref([])
const messagesContainer = ref(null)
const contextLimit = ref(10) // 默认值，将从后端获取

// 历史对话列表
const chatHistory = ref([])
// 自动提问防抖标记，避免重复触发
const autoAsked = ref(false)

// 知识库相关
const knowledgeBases = ref([])
const selectedKnowledgeBase = ref('')

// 当前对话ID
const currentConversationId = ref(null)

// 生命周期
onMounted(async () => {
  await loadKnowledgeBases()
  await loadChatHistory()
  applyRouteParamsAndMaybeAsk()
})

// 从路由应用参数并必要时触发提问
const applyRouteParamsAndMaybeAsk = async () => {
  const kbIdFromQuery = (route.query.kb_id || route.query.kbId || '').toString()
  const questionFromQuery = (route.query.q || '').toString().trim()

  if (kbIdFromQuery) {
    const hasKb = (knowledgeBases.value || []).some(kb => kb.id === kbIdFromQuery)
    if (hasKb) {
      selectedKnowledgeBase.value = kbIdFromQuery
    } else if (import.meta.env.DEV) {
      // 开发环境允许直接使用路由中的kb_id作为演示选择
      selectedKnowledgeBase.value = kbIdFromQuery
      if (!(knowledgeBases.value || []).length) {
        knowledgeBases.value = [{ id: kbIdFromQuery, name: '演示知识库', document_count: 0 }]
      }
    }
  }
  // 若未选择，回退到默认第一个知识库
  if (!selectedKnowledgeBase.value && knowledgeBases.value.length > 0) {
    selectedKnowledgeBase.value = knowledgeBases.value[0].id
  }

  if (questionFromQuery && !autoAsked.value) {
    currentMessage.value = questionFromQuery
    // 允许在未选择知识库时也发起提问（后端将搜索用户可访问的全部文档）
    autoAsked.value = true
    await sendMessage()
  }
}

// 路由参数变化时，重试应用与提问（提高健壮性）
watch(() => route.query, async () => {
  // 等待知识库列表加载完成后再尝试
  if (!knowledgeBases.value || knowledgeBases.value.length === 0) return
  await applyRouteParamsAndMaybeAsk()
})

const openChatHistory = async () => {
  showChatHistory.value = true
  await loadChatHistory()
}

// 方法
const loadConfig = async () => {
  try {
    const response = await fetch(`${api.defaults.baseURL}/knowledge-assistant/config`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (response.ok) {
      const config = await response.json()
      contextLimit.value = config.context_limit
      console.log('Loaded config:', config)
    }
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

const loadKnowledgeBases = async () => {
  try {
    const response = await getKnowledgeBases()
    knowledgeBases.value = response || []
    // 移除原本的默认自动选中逻辑，交由 applyRouteParams 处理

  } catch (error) {
    console.error('加载知识库失败:', error)
    ElMessage.error('加载知识库失败')
    // 开发环境兜底：提供一个演示知识库，支持根据路由kb_id设置
    if (import.meta.env.DEV) {
      const fallbackKbId = (route.query.kb_id || route.query.kbId || 'demo-kb').toString()
      knowledgeBases.value = [{ id: fallbackKbId, name: '演示知识库', document_count: 0 }]
    }
  }
}

const handleKnowledgeBaseChange = (value) => {
  selectedKnowledgeBase.value = value
  // 清空当前对话和文档片段
  messages.value = []
  documentChunks.value = []
  currentConversationId.value = null
}

const generateOfflineAnswer = (q) => {
  const question = (q || '').trim()
  return [
    `问题：${question}`,
    '演示回答（后端未启动，离线生成）：',
    '1) 明确责任与协调机制：建立由当地政府牵头的水利建设小组，统筹发改、财政、水利、生态环境、应急等部门，形成协同机制。',
    '2) 制定规划与合规：依据流域与区域总体规划，开展可研、环评与用地审核，确保项目合规与可持续。',
    '3) 融资与资金管理：通过财政资金、专项债、PPP、政策性银行等多元融资方式，建立透明的资金管控与绩效评估。',
    '4) 工程建设与质量安全：完善招投标与第三方监理机制，落实质量安全、汛期施工与应急预案。',
    '5) 环保与生态修复：实施生态流量保障、沿岸绿化与湿地修复，降低工程对生态的影响。',
    '6) 数字化运维：建设智慧水利平台，集成监测预警、调度与资产管理，提高运行效率。',
    '7) 公共参与与信息公开：加强科普宣传、征求公众意见并依法依规进行信息披露。',
    '提示：当前为演示模式，启用后端服务可获得基于知识库的权威回答与引用来源。'
  ].join('\n')
}

const sendMessage = async () => {
  if (!currentMessage.value.trim()) {
    return
  }
  
  if (!selectedKnowledgeBase.value) {
    // 未选择知识库时提示，但继续执行提问
    ElMessage.info('未选择知识库，将在可访问范围内进行搜索')
  }
  
  const question = currentMessage.value.trim()
  currentMessage.value = ''
  
  // 添加用户消息
  const userMessage = {
    type: 'user',
    content: question,
    timestamp: new Date()
  }
  messages.value.push(userMessage)
  
  // 添加AI消息占位符
  const assistantMessage = {
    type: 'assistant',
    content: '',
    sources: [],
    timestamp: new Date(),
    isStreaming: true
  }
  messages.value.push(assistantMessage)
  
  isLoading.value = true
  
  try {
    // 若当前无会话，先创建会话
    if (!currentConversationId.value) {
      const conversationData = {
        title: question.length > 50 ? question.slice(0, 50) + '...' : question,
        description: question.slice(0, 100),
        meta_data: {
          knowledge_base_id: selectedKnowledgeBase.value,
          source: 'knowledge_assistant'
        }
      }
      const resp = await createConversation(conversationData)
      if (resp?.id) {
        currentConversationId.value = resp.id
      } else {
        throw new Error('创建会话失败')
      }
    }
    // 滚动到底部
    await nextTick()
    scrollToBottom()
    
    // 准备对话历史（最近10条消息，排除当前流式消息）
    const conversationHistory = messages.value
      .filter(msg => !msg.isStreaming)
      .slice(-10)
      .map(msg => ({ role: msg.type === 'user' ? 'user' : 'assistant', content: msg.content }))
    
    // 使用 FormData 发送数据，因为后端期望 Form 格式
    const formData = new FormData()
    formData.append('question', question)
    if (selectedKnowledgeBase.value) {
      formData.append('knowledge_base_id', selectedKnowledgeBase.value)
    }
    formData.append('context_limit', contextLimit.value.toString())  // 动态获取的值
    formData.append('conversation_history', JSON.stringify(conversationHistory))
    formData.append('conversation_id', String(currentConversationId.value))
    
    console.log('发送问题:', question)
    console.log('知识库ID:', selectedKnowledgeBase.value || '(未选择)')
    
    // 使用 fetch 进行流式请求
    const response = await fetch(`${api.defaults.baseURL}/knowledge-assistant/ask`, {
      method: 'POST',
      body: formData,
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // 保留不完整的行在缓冲区
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'start') {
              // 设置来源信息
              assistantMessage.sources = data.sources || []
              if (data.conversation_id) {
                currentConversationId.value = data.conversation_id
              }
              documentChunks.value = (data.sources || []).map((source, index) => ({
                content: source.content || source.page_content,
                source: source.document_title || source.title || '未知文档',
                score: Math.max(0, Math.min(1, Number(
                  (source.rerank_score ?? source.combined_score ?? source.combined_score_raw ?? source.content_score_norm ??
                   source.similarity ?? source.similarity_score ?? source.score ??
                   source.content_score ?? source.text_score ?? 0)
                ))),
                highlighted: false
              }))
              console.log('流式开始，来源数量:', data.sources?.length || 0)
            } else if (data.type === 'chunk') {
              // 追加内容并强制触发响应式更新
              assistantMessage.content += data.content
              console.log('接收到chunk:', data.content, '当前总长度:', assistantMessage.content.length)
              
              // 强制触发Vue响应式更新
              messages.value = [...messages.value]
              
              // 确保DOM更新后滚动
              await nextTick()
              scrollToBottom()
            } else if (data.type === 'end') {
              // 流式传输完成
              assistantMessage.isStreaming = false
              if (data.conversation_id) {
                currentConversationId.value = data.conversation_id
              }
              
              // 如果end响应中包含sources，更新相关文档片段
              if (data.sources && data.sources.length > 0) {
                assistantMessage.sources = data.sources
                documentChunks.value = data.sources.map((source, index) => ({
                  content: source.content || source.page_content,
                  source: source.document_title || source.title || '未知文档',
                  score: Math.max(0, Math.min(1, Number(
                    (source.rerank_score ?? source.combined_score ?? source.combined_score_raw ?? source.content_score_norm ??
                     source.similarity ?? source.similarity_score ?? source.score ??
                     source.content_score ?? source.text_score ?? 0)
                  ))),
                  highlighted: false
                }))
                console.log('流式完成，更新来源数量:', data.sources.length)
              }
              
              console.log('流式传输完成，最终内容长度:', assistantMessage.content.length)
              // 刷新历史对话列表
              loadChatHistory()
            } else if (data.type === 'error') {
              console.error('流式传输错误:', data.error)
              throw new Error(data.error)
            }
          } catch (parseError) {
            console.warn('解析流式数据失败:', parseError)
          }
        }
      }
    }
    
    // 如果没有接收到任何内容，显示错误
    if (!assistantMessage.content.trim()) {
      assistantMessage.content = '抱歉，我暂时无法回答您的问题，请稍后重试。'
      assistantMessage.isStreaming = false
    }
    
  } catch (error) {
    console.error('提问失败:', error)
    console.error('错误详情:', error.response?.data || error.message)
    
    // 更新助手消息为错误内容
    assistantMessage.isStreaming = false
    
    // 检查是否是网络错误或服务器错误
    if (error.message.includes('401') || error.message.includes('403')) {
      assistantMessage.content = '认证失败，请重新登录。'
      ElMessage.error('认证失败，请重新登录')
    } else if (error.message.includes('500')) {
      assistantMessage.content = '服务器内部错误，请稍后重试。'
      ElMessage.error('服务器内部错误，请稍后重试')
    } else if (error.message.includes('Failed to fetch')) {
      assistantMessage.content = '网络连接失败，请检查网络连接。'
      ElMessage.error('网络连接失败，请检查网络连接')
    } else {
      assistantMessage.content = '抱歉，我暂时无法回答您的问题，请稍后重试。'
      ElMessage.error(`请求失败: ${error.message}`)
    }
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const clearChat = async () => {
  try {
    await ElMessageBox.confirm('确定要清空当前对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    messages.value = []
    documentChunks.value = []
    currentConversationId.value = null // 清空当前对话ID
    ElMessage.success('对话已清空')
  } catch {
    // 用户取消
  }
}

const getScoreType = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'info'
}

// 历史对话相关方法
const loadChatHistory = async () => {
  try {
    const response = await getConversations()
    const list = Array.isArray(response) ? response : (response.items || response.data || [])
    if (Array.isArray(list)) {
      chatHistory.value = list.map(conv => ({
        id: conv.id,
        title: conv.title || `对话 ${conv.id}`,
        preview: conv.description || '',
        messages: conv.messages || [],
        messageCount: conv.message_count || 0,
        timestamp: new Date(conv.created_at || conv.timestamp),
        knowledgeBaseId: conv.meta_data?.knowledge_base_id || null,
        source: conv.meta_data?.source || null
      })).filter(session => session.source === 'knowledge_assistant' || session.knowledgeBaseId)
    }
  } catch (error) {
    console.error('加载历史对话失败:', error)
    ElMessage.error('加载历史对话失败')
    chatHistory.value = []
  }
}

const saveChatSession = async () => {
  if (messages.value.length === 0) return
  
  try {
    // 创建新对话，只使用后端支持的字段
    const conversationData = {
      title: messages.value[0]?.content?.substring(0, 30) + '...',
      description: messages.value[0]?.content?.substring(0, 100) + '...',
      meta_data: {
        knowledge_base_id: selectedKnowledgeBase.value,
        message_count: messages.value.length,
        source: 'knowledge_assistant'
      }
    }
    
    const response = await createConversation(conversationData)
    if (response.data) {
      currentConversationId.value = response.data.id
      
      // 重新加载历史对话列表
      await loadChatHistory()
    }
  } catch (error) {
    console.error('保存对话失败:', error)
    ElMessage.error('保存对话失败')
  }
}

const loadChatSession = async (session) => {
  try {
    // 从后端加载完整的对话消息
    const response = await getConversationMessages(session.id)
    const list = Array.isArray(response) ? response : (response.items || response.data || [])
    if (Array.isArray(list)) {
      messages.value = list.map(msg => ({
        type: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
        sources: msg.sources || [],
        isStreaming: false
      }))
    } else {
      // 如果后端没有消息数据，使用本地保存的消息
      messages.value = session.messages || []
    }

    currentConversationId.value = session.id
    selectedKnowledgeBase.value = session.knowledgeBaseId || null
    showChatHistory.value = false

    // 重新生成文档片段（如果有助手消息）
    const lastAssistantMessage = messages.value.filter(m => m.type === 'assistant').pop()
    if (lastAssistantMessage && lastAssistantMessage.sources) {
      documentChunks.value = lastAssistantMessage.sources.map((source, index) => ({
        content: source.content,
        source: source.document_title || source.title,
        score: Math.max(0, Math.min(1, Number(
          (source.rerank_score ?? source.combined_score ?? source.combined_score_raw ?? source.content_score_norm ??
           source.similarity ?? source.similarity_score ?? source.score ??
           source.content_score ?? source.text_score ?? 0)
        ))),
        highlighted: false
      }))
    }

    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    console.error('加载对话失败:', error)
    ElMessage.error('加载对话失败')
    // 如果加载失败，使用本地数据
    messages.value = session.messages || []
    selectedKnowledgeBase.value = session.knowledgeBaseId
    showChatHistory.value = false
  }
}


const deleteChatSession = async (index) => {
  try {
    const session = chatHistory.value[index]
    if (!session || !session.id) {
      ElMessage.error('无法删除对话：对话信息不完整')
      return
    }
    
    // 调用后端API删除对话
    await deleteConversation(session.id)
    
    // 从本地列表中移除
    chatHistory.value.splice(index, 1)
    
    // 如果删除的是当前对话，清空当前对话
    if (currentConversationId.value === session.id) {
      currentConversationId.value = null
      messages.value = []
      documentChunks.value = []
      selectedKnowledgeBase.value = null
    }
    
    ElMessage.success('历史对话已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除对话失败:', error)
      ElMessage.error('删除对话失败')
    }
  }
}

// 文档上传相关方法
const beforeUpload = (file) => {
  const isValidType = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.type)
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isValidType) {
    ElMessage.error('只支持 PDF、Word、TXT 格式的文件!')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  return true
}

const handleUploadSuccess = (response, file) => {
  ElMessage.success(`${file.name} 上传成功`)
  
  // 检查是否所有文件都已上传完成
  const remainingFiles = fileList.value.filter(f => f.status !== 'success')
  if (remainingFiles.length === 0) {
    setTimeout(() => {
      showUploadDialog.value = false
      resetUploadForm()
      loadKnowledgeBases() // 重新加载知识库列表
    }, 1000)
  }
}

const handleUploadError = (error, file) => {
  console.error('上传失败:', error)
  ElMessage.error(`${file.name} 上传失败`)
}

const handleRemove = (file) => {
  const index = fileList.value.findIndex(item => item.uid === file.uid)
  if (index > -1) {
    fileList.value.splice(index, 1)
  }
}

const confirmUpload = () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  
  if (!uploadForm.knowledgeBaseId) {
    ElMessage.warning('请选择知识库')
    return
  }
  
  uploading.value = true
  // 触发上传
  uploadRef.value.submit()
}

const resetUploadForm = () => {
  showUploadDialog.value = false
  fileList.value = []
  uploading.value = false
  uploadForm.knowledgeBaseId = ''
  uploadForm.category = ''
  uploadForm.description = ''
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

const formatMarkdown = (text) => {
  // 简单的 Markdown 格式化
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.knowledge-assistant {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
  padding: 20px;
  min-height: 0;
}

.chat-section {
  flex: 1;
  min-width: 0;
}

.chunks-section {
  width: 400px;
  flex-shrink: 0;
}

.chat-card,
.chunks-card {
  height: 100%;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.chat-header,
.chunks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left,
.chunks-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.kb-name {
  font-weight: 500;
}

.kb-count {
  font-size: 12px;
  color: #909399;
}

.item-count {
  margin-left: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-height: calc(100vh - 300px);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 20px;
}

.empty-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.message-item {
  margin-bottom: 20px;
}

.user-message {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  justify-content: flex-end;
}

.assistant-message {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
}

.user-message .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.assistant-message .message-content {
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 16px;
  border-radius: 4px 18px 18px 18px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
}

.loading-message {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.chat-input {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 20px;
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-tips {
  font-size: 12px;
  color: #909399;
}

.chunks-content {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.empty-chunks {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.chunk-item {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  height: 300px;
  display: flex;
  flex-direction: column;
}

.chunk-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  border-color: #667eea;
}

.chunk-item.highlighted {
  border-color: #667eea;
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
  background: rgba(102, 126, 234, 0.1);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chunk-source {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.doc-icon {
  color: #667eea;
  flex-shrink: 0;
}

.doc-title {
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunk-score {
  flex-shrink: 0;
}

.chunk-content {
  margin-bottom: 12px;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.chunk-content p {
  margin: 0;
  line-height: 1.6;
  color: #606266;
  font-size: 14px;
}

.chunk-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.chunk-index {
  font-weight: 500;
}

.chunk-size {
  color: #c0c4cc;
}

/* 文档段落滚动条样式 */
.chunk-content::-webkit-scrollbar {
  width: 4px;
}

.chunk-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 2px;
}

.chunk-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.chunk-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* 历史对话抽屉样式 */
.chat-history-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.empty-history {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.history-item {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.history-time {
  font-size: 12px;
  color: #909399;
}

.history-preview {
  margin: 8px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.message-count {
  font-size: 12px;
  color: #909399;
}

/* 上传对话框样式 */
.upload-content {
  padding: 20px 0;
}

.upload-demo {
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .chunks-section {
    width: 350px;
  }
}

@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }
  
  .chunks-section {
    width: 100%;
    height: 300px;
  }
  
  .header-right {
    flex-wrap: wrap;
    gap: 8px;
  }
}

/* Element Plus 组件样式覆盖 */
:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

:deep(.el-card__header) {
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
}

:deep(.el-drawer__body) {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* 打字指示器样式 */
.typing-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  gap: 4px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: #409eff;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

:deep(.el-empty__description) {
  color: #909399;
}
</style>
