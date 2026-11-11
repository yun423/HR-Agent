<template>
  <div class="knowledge-base-management">
    <div class="page-container">
      <!-- 头部标题区域 -->
      <div class="header-section">
        <div class="header-content">
          <h1 class="page-title">
            <el-icon><Collection /></el-icon>
            知识库管理
          </h1>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索知识库..."
              clearable
              class="search-input"
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="showCreateKnowledgeBaseDialog = true">
              <el-icon><Plus /></el-icon>
              新建知识库
            </el-button>
          </div>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧知识库列表 -->
        <div class="left-panel">
          <el-card class="knowledge-base-list-card">
            <template #header>
              <div class="card-header">
                <span>知识库列表</span>
                <el-badge :value="filteredKnowledgeBases.length" class="item-count" />
              </div>
            </template>
            <div class="knowledge-base-list">
              <div
                v-for="kb in filteredKnowledgeBases"
                :key="kb.id"
                class="knowledge-base-item"
                :class="{ active: selectedKnowledgeBase?.id === kb.id }"
                @click="selectKnowledgeBase(kb)"
              >
                <div class="kb-icon">
                  <el-icon><Folder /></el-icon>
                </div>
                <div class="kb-info">
                  <div class="kb-name">{{ kb.name }}</div>
                  <div class="kb-meta">
                    <span class="doc-count">{{ kb.document_count }} 个文档</span>
                    <span class="update-time">{{ formatTime(kb.updatedAt) }}</span>
                  </div>
                </div>
                <div class="kb-actions">
                  <el-dropdown @command="handleKnowledgeBaseAction">
                    <el-button text>
                      <el-icon><MoreFilled /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item :command="{ action: 'edit', kb }">编辑</el-dropdown-item>
                        <el-dropdown-item :command="{ action: 'delete', kb }" divided>删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
              <el-empty v-if="filteredKnowledgeBases.length === 0" description="暂无知识库" />
            </div>
          </el-card>
        </div>

        <!-- 右侧文档列表 -->
        <div class="right-panel">
          <el-card class="document-list-card">
            <template #header>
              <div class="card-header">
                <span>文档列表</span>
                <div class="header-actions">
                  <el-button @click="showUploadDialog = true" :disabled="!selectedKnowledgeBase">
                    <el-icon><Upload /></el-icon>
                    上传文档
                  </el-button>
                </div>
              </div>
            </template>
            <div class="document-content">
              <div v-if="!selectedKnowledgeBase" class="empty-state">
                <el-empty description="请先选择一个知识库" />
              </div>
              <div v-else>
                <!-- 文档列表表格 -->
                <el-table
                  :data="documents"
                  v-loading="documentsLoading"
                  class="document-table"
                  @selection-change="handleSelectionChange"
                >
                  <el-table-column type="selection" width="55" />
                  <el-table-column prop="filename" label="文档名称" min-width="200">
                    <template #default="{ row }">
                      <div class="document-name">
                        <el-icon class="doc-icon">
                          <Document v-if="row.mime_type?.includes('pdf')" />
                          <DocumentCopy v-else-if="row.mime_type?.includes('word') || row.mime_type?.includes('document')" />
                          <Tickets v-else />
                        </el-icon>
                        <span>{{ row.filename }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="file_size" label="文件大小" width="120">
                    <template #default="{ row }">
                      {{ formatFileSize(row.file_size) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="category" label="分类" width="100" />
                  <el-table-column prop="created_at" label="上传时间" width="180">
                    <template #default="{ row }">
                      {{ formatTime(row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150" fixed="right">
                    <template #default="{ row }">
                      <el-button text @click="previewDocumentHandler(row)">
                        <el-icon><View /></el-icon>
                        预览
                      </el-button>
                      <el-button text type="danger" @click="deleteDocument(row)">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                
                <!-- 分页 -->
                <div class="pagination-wrapper">
                  <el-pagination
                    v-model:current-page="currentPage"
                    v-model:page-size="pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="totalDocuments"
                    layout="total, sizes, prev, pager, next, jumper"
                    @size-change="handleSizeChange"
                    @current-change="handleCurrentChange"
                  />
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 新建知识库对话框 -->
      <el-dialog
        v-model="showCreateKnowledgeBaseDialog"
        :title="editingKnowledgeBase ? '编辑知识库' : '新建知识库'"
        width="500px"
        @close="resetKnowledgeBaseForm"
      >
        <el-form :model="knowledgeBaseForm" :rules="knowledgeBaseRules" ref="knowledgeBaseFormRef" label-width="80px">
          <el-form-item label="名称" prop="name">
            <el-input v-model="knowledgeBaseForm.name" placeholder="请输入知识库名称" />
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="knowledgeBaseForm.description"
              type="textarea"
              :rows="3"
              placeholder="请输入知识库描述"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreateKnowledgeBaseDialog = false">取消</el-button>
          <el-button type="primary" @click="createKnowledgeBaseHandler" :loading="creating">
            {{ editingKnowledgeBase ? '更新' : '创建' }}
          </el-button>
        </template>
      </el-dialog>

      <!-- 上传文档对话框 -->
      <el-dialog
        v-model="showUploadDialog"
        title="上传文档"
        width="600px"
        @close="resetUploadForm"
      >
        <el-upload
          ref="uploadRef"
          class="upload-demo"
          drag
          :action="uploadAction"
          :headers="uploadHeaders"
          :data="uploadData"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :file-list="fileList"
          multiple
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF、DOC、DOCX、TXT 格式，单个文件不超过 10MB
            </div>
          </template>
        </el-upload>
        <template #footer>
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="uploadAndProcess" :loading="uploading || processing" :disabled="uploadedDocIds.length === 0">开始上传</el-button>
        </template>
      </el-dialog>

      <!-- 文档预览对话框 -->
      <el-dialog
        v-model="showPreviewDialog"
        :title="`文档预览 - ${previewDocument?.name}`"
        width="80%"
        class="preview-dialog"
      >
        <div class="document-preview">
          <div v-if="documentChunks.length === 0" class="loading-state">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else class="chunks-list">
            <div
              v-for="(chunk, index) in documentChunks"
              :key="index"
              class="chunk-item"
            >
              <div class="chunk-header">
                <span class="chunk-title">分段 {{ index + 1 }}</span>
                <el-tag size="small">{{ chunk.content.length }} 字符</el-tag>
              </div>
              <div class="chunk-content">
                {{ chunk.content }}
              </div>
            </div>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Search,
  Plus,
  Folder,
  MoreFilled,
  Upload,
  Document,
  DocumentCopy,
  Tickets,
  View,
  Delete,
  UploadFilled
} from '@element-plus/icons-vue'
import {
  getKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBaseDocuments,
  deleteDocument as deleteDocumentAPI,
  getDocumentChunks,
  processDocument
} from '@/api/knowledgeBase'
import { useAuthStore } from '@/stores/auth'

// 认证store
const authStore = useAuthStore()

// 响应式数据
const searchQuery = ref('')
const selectedKnowledgeBase = ref(null)
const documentsLoading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalDocuments = ref(0)
const selectedDocuments = ref([])

// 对话框状态
const showCreateKnowledgeBaseDialog = ref(false)
const showUploadDialog = ref(false)
const showPreviewDialog = ref(false)
const creating = ref(false)
const uploading = ref(false)
const processing = ref(false)
const uploadedDocIds = ref([])

// 表单数据
const knowledgeBaseForm = reactive({
  name: '',
  description: ''
})

const knowledgeBaseRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 表单引用
const knowledgeBaseFormRef = ref()

// 上传相关
const uploadRef = ref()
const fileList = ref([])
const uploadAction = '/api/v1/documents/upload'
const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${authStore.token}`
}))
const uploadData = computed(() => ({
  knowledge_base_id: selectedKnowledgeBase.value?.id
}))

// 预览相关
const previewDocument = ref(null)
const documentChunks = ref([])

// 数据状态
const knowledgeBases = ref([])
const documents = ref([])
const loading = ref(false)
const editingKnowledgeBase = ref(null)

// 计算属性
const filteredKnowledgeBases = computed(() => {
  if (!searchQuery.value) return knowledgeBases.value
  return knowledgeBases.value.filter(kb =>
    kb.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    kb.description.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 方法
const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    const response = await getKnowledgeBases()
    knowledgeBases.value = response || []
  } catch (error) {
    console.error('加载知识库列表失败:', error)
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  // 搜索逻辑
}

const selectKnowledgeBase = (kb) => {
  selectedKnowledgeBase.value = kb
  loadDocuments()
}

const loadDocuments = async () => {
  if (!selectedKnowledgeBase.value) return
  
  documentsLoading.value = true
  try {
    const response = await getKnowledgeBaseDocuments(selectedKnowledgeBase.value.id, {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    })
    documents.value = response.documents || []
    totalDocuments.value = response.total || 0
  } catch (error) {
    console.error('加载文档失败:', error)
    ElMessage.error('加载文档失败')
  } finally {
    documentsLoading.value = false
  }
}

const handleKnowledgeBaseAction = async ({ action, kb }) => {
  if (action === 'edit') {
    // 编辑知识库
    knowledgeBaseForm.name = kb.name
    knowledgeBaseForm.description = kb.description
    editingKnowledgeBase.value = kb
    showCreateKnowledgeBaseDialog.value = true
  } else if (action === 'delete') {
    // 删除知识库
    ElMessageBox.confirm(
      `确定要删除知识库"${kb.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(async () => {
      try {
        await deleteKnowledgeBase(kb.id)
        
        if (selectedKnowledgeBase.value?.id === kb.id) {
          selectedKnowledgeBase.value = null
          documents.value = []
        }
        
        ElMessage.success('删除成功')
        await loadKnowledgeBases()
      } catch (error) {
        console.error('删除知识库失败:', error)
        ElMessage.error('删除失败')
      }
    }).catch(() => {
      // 取消删除
    })
  }
}

const createKnowledgeBaseHandler = async () => {
  if (!knowledgeBaseFormRef.value) return
  
  try {
    await knowledgeBaseFormRef.value.validate()
    creating.value = true
    
    const kbData = {
      name: knowledgeBaseForm.name,
      description: knowledgeBaseForm.description,
      is_public: true,
      is_searchable: true,
      category: null,
      tags: [],
      meta_data: {}
    }
    
    if (editingKnowledgeBase.value) {
      // 编辑模式
      await updateKnowledgeBase(editingKnowledgeBase.value.id, kbData)
      ElMessage.success('知识库更新成功')
    } else {
      // 创建模式
      await createKnowledgeBase(kbData)
      ElMessage.success('知识库创建成功')
    }
    
    showCreateKnowledgeBaseDialog.value = false
    resetKnowledgeBaseForm()
    
    // 重新加载知识库列表
    await loadKnowledgeBases()
  } catch (error) {
    console.error('操作知识库失败:', error)
    if (error !== false) { // 验证失败时不显示错误
      ElMessage.error(editingKnowledgeBase.value ? '更新知识库失败' : '创建知识库失败')
    }
  } finally {
    creating.value = false
  }
}

const resetKnowledgeBaseForm = () => {
  knowledgeBaseForm.name = ''
  knowledgeBaseForm.description = ''
  editingKnowledgeBase.value = null
  if (knowledgeBaseFormRef.value) {
    knowledgeBaseFormRef.value.clearValidate()
  }
}

const handleSelectionChange = (selection) => {
  selectedDocuments.value = selection
}

const previewDocumentHandler = (doc) => {
  previewDocument.value = doc
  showPreviewDialog.value = true
  loadDocumentChunks(doc.id)
}

const loadDocumentChunks = async (documentId) => {
  documentChunks.value = []
  try {
    const response = await getDocumentChunks(documentId)
    documentChunks.value = response.chunks || []
  } catch (error) {
    console.error('加载文档分块失败:', error)
    ElMessage.error('加载文档内容失败')
  }
}

const deleteDocument = (doc) => {
  ElMessageBox.confirm(
    `确定要删除文档"${doc.name}"吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteDocumentAPI(doc.id)
      
      // 从选中列表中移除
      const selectedIndex = selectedDocuments.value.findIndex(item => item.id === doc.id)
      if (selectedIndex > -1) {
        selectedDocuments.value.splice(selectedIndex, 1)
      }
      
      ElMessage.success('删除成功')
      // 重新加载文档列表
      await loadDocuments()
    } catch (error) {
      console.error('删除文档失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const beforeUpload = (file) => {
  const isValidType = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.type)
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isValidType) {
    ElMessage.error('只支持 PDF、DOC、DOCX、TXT 格式的文件!')
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
  // 记录上传成功的文档ID
  if (response && response.id) {
    uploadedDocIds.value.push(response.id)
  }
}

const handleUploadError = (error, file) => {
  ElMessage.error(`${file.name} 上传失败`)
}

const uploadAndProcess = async () => {
  if (uploadedDocIds.value.length === 0) return

  processing.value = true
  let successCount = 0
  let failCount = 0

  for (const docId of uploadedDocIds.value) {
    try {
      await processDocument(docId)
      successCount++
    } catch (e) {
      console.error(`处理文档 ${docId} 失败:`, e)
      failCount++
    }
  }

  processing.value = false

  if (failCount === 0) {
    ElMessage.success(`${successCount} 个文档处理完成`)
  } else {
    ElMessage.warning(`${successCount} 个成功, ${failCount} 个失败`)
  }

  showUploadDialog.value = false
  resetUploadForm()
  loadDocuments()
}

const resetUploadForm = () => {
  fileList.value = []
  uploadedDocIds.value = []
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadDocuments()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadDocuments()
}

// 工具函数
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 生命周期
onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.knowledge-base-management {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.page-container {
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header-section {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 30px 40px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title .el-icon {
  color: #409eff;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  width: 300px;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 20px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.left-panel {
  width: 350px;
  display: flex;
  flex-direction: column;
}

.knowledge-base-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.knowledge-base-list-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.item-count :deep(.el-badge__content) {
  background-color: #409eff;
}

.knowledge-base-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.knowledge-base-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid transparent;
}

.knowledge-base-item:hover {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
}

.knowledge-base-item.active {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.knowledge-base-item.active .kb-name {
  color: #409eff;
}

.kb-icon {
  margin-right: 12px;
  color: #909399;
  font-size: 20px;
}

.kb-info {
  flex: 1;
  min-width: 0;
}

.kb-name {
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
}

.kb-actions {
  opacity: 0;
  transition: opacity 0.3s;
}

.knowledge-base-item:hover .kb-actions {
  opacity: 1;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.document-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.document-list-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.document-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.document-table {
  flex: 1;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: #409eff;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

/* 自定义滚动条 */
:deep(.knowledge-base-list::-webkit-scrollbar),
:deep(.chunks-list::-webkit-scrollbar) {
  width: 6px;
}

:deep(.knowledge-base-list::-webkit-scrollbar-track),
:deep(.chunks-list::-webkit-scrollbar-track) {
  background: #f1f1f1;
  border-radius: 3px;
}

:deep(.knowledge-base-list::-webkit-scrollbar-thumb),
:deep(.chunks-list::-webkit-scrollbar-thumb) {
  background: #c1c1c1;
  border-radius: 3px;
}

:deep(.knowledge-base-list::-webkit-scrollbar-thumb:hover),
:deep(.chunks-list::-webkit-scrollbar-thumb:hover) {
  background: #a8a8a8;
}

.document-preview {
  max-height: 60vh;
  overflow-y: auto;
}

.loading-state {
  padding: 20px;
}

.chunks-list {
  /* 分块列表样式 */
}

.chunk-item {
  margin-bottom: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.chunk-header {
  background-color: #f5f7fa;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
}

.chunk-title {
  font-weight: 600;
  color: #303133;
}

.chunk-content {
  padding: 16px;
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
}

/* 上传组件样式 */
.upload-demo :deep(.el-upload-dragger) {
  width: 100%;
  height: 180px;
}
</style>