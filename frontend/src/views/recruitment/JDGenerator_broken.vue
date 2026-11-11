<template>
  <div class="jd-generator">
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Document /></el-icon>
            智能JD管理
          </h1>
        </div>
        <div class="header-actions">
          <el-button @click="createNewJD" type="primary">
            <el-icon><Plus /></el-icon>
            新建JD
          </el-button>
        </div>
      </div>

      <!-- 左右两栏布局 -->
      <div class="main-content">
        <!-- 左侧JD列表 -->
        <div class="jd-list-panel">
          <el-card class="list-card">
            <template #header>
              <div class="list-header">
                <span class="list-title">
                  <el-icon><List /></el-icon>
                  JD列表
                </span>
                <div class="list-actions">
                  <el-input
                    v-model="searchKeyword"
                    placeholder="搜索JD..."
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

            <!-- JD列表内容 -->
            <div class="jd-list-content">
              <div v-if="jdListLoading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>
              
              <div v-else-if="jdList.length === 0" class="empty-container">
                <el-empty description="暂无JD数据">
                  <el-button type="primary" @click="createNewJD">
                    <el-icon><Plus /></el-icon>
                    创建第一个JD
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="jd-items">
                <div
                  v-for="jd in jdList"
                  :key="jd.id"
                  :class="['jd-item', { active: selectedJD?.id === jd.id }]"
                  @click="selectJD(jd)"
                >
                  <div class="jd-item-header">
                    <h4 class="jd-title">{{ jd.position_title || '未命名职位' }}</h4>
                    <div class="jd-actions">
                      <el-dropdown trigger="click" @command="handleJDAction">
                        <el-button text size="small">
                          <el-icon><MoreFilled /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item :command="{ action: 'edit', jd }">
                              <el-icon><Edit /></el-icon>
                              编辑
                            </el-dropdown-item>
                            <el-dropdown-item :command="{ action: 'duplicate', jd }">
                              <el-icon><CopyDocument /></el-icon>
                              复制
                            </el-dropdown-item>
                            <el-dropdown-item :command="{ action: 'delete', jd }" divided>
                              <el-icon><Delete /></el-icon>
                              删除
                            </el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                  </div>
                  
                  <div class="jd-item-content">
                    <div class="jd-meta">
                      <span class="meta-item">
                        <el-icon><Location /></el-icon>
                        {{ jd.location || '未设置' }}
                      </span>
                      <span class="meta-item">
                        <el-icon><Money /></el-icon>
                        {{ jd.salary || '面议' }}
                      </span>
                    </div>
                    <div class="jd-description">
                      {{ jd.description ? jd.description.substring(0, 100) + '...' : '暂无描述' }}
                    </div>
                    <div class="jd-footer">
                      <span class="jd-date">{{ formatDate(jd.created_at) }}</span>
                      <el-tag :type="getStatusType(jd.status)" size="small">
                        {{ getStatusText(jd.status) }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分页 -->
              <div v-if="jdList.length > 0" class="pagination-container">
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
            </div>
          </el-card>
        </div>

        <!-- 右侧JD编辑/生成/预览区域 -->
        <div class="jd-editor-panel">
          <!-- 当没有选中JD时显示欢迎页面 -->
          <div v-if="!selectedJD && !isCreatingNew" class="welcome-container">
            <el-card class="welcome-card">
              <div class="welcome-content">
                <el-icon class="welcome-icon"><Document /></el-icon>
                <h2>智能JD生成器</h2>
                <p>选择左侧的JD进行编辑，或创建新的JD</p>
                <el-button type="primary" size="large" @click="createNewJD">
                  <el-icon><Plus /></el-icon>
                  创建新JD
                </el-button>
              </div>
            </el-card>
          </div>

          <!-- JD编辑/生成区域 -->
          <div v-else class="jd-editor-content">
            <!-- 编辑器头部 -->
            <div class="editor-header">
              <div class="editor-title">
                <h2 v-if="isCreatingNew">创建新JD</h2>
                <h2 v-else>编辑JD - {{ selectedJD?.position_title || '未命名职位' }}</h2>
              </div>
              <div class="editor-actions">
                <el-button @click="resetForm">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
                <el-button type="primary" @click="generateJD" :loading="generating">
                  <el-icon><Star /></el-icon>
                  {{ generating ? '生成中...' : '生成JD' }}
                </el-button>
              </div>
            </div>

            <!-- 编辑器主要内容 -->
            <div class="editor-main">
              <!-- 左侧配置面板 -->
              <div class="config-panel">
          <el-card class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><Setting /></el-icon>
                <span>职位配置</span>
              </div>
            </template>

            <el-form 
              ref="formRef" 
              :model="form" 
              :rules="rules" 
              label-width="100px"
              label-position="top"
            >
              <!-- 第一行：职位名称和工作地点 -->
              <div class="form-row">
                <el-form-item label="职位名称" prop="jobTitle">
                  <el-input 
                    v-model="form.jobTitle" 
                    placeholder="请输入职位名称，如：前端开发工程师"
                    clearable
                  />
                </el-form-item>

                <el-form-item label="工作地点" prop="location">
                  <el-select 
                    v-model="form.location" 
                    placeholder="请选择工作地点"
                    filterable
                    clearable
                    style="width: 100%"
                  >
                    <el-option 
                      v-for="city in cities" 
                      :key="city" 
                      :label="city" 
                      :value="city" 
                    />
                  </el-select>
                </el-form-item>
              </div>

              <!-- 第二行：工作经验和学历要求 -->
              <div class="form-row">
                <el-form-item label="工作经验" prop="experience">
                  <el-select 
                    v-model="form.experience" 
                    placeholder="请选择工作经验要求"
                    style="width: 100%"
                  >
                    <el-option label="不限" value="不限" />
                    <el-option label="1年以下" value="1年以下" />
                    <el-option label="1-3年" value="1-3年" />
                    <el-option label="3-5年" value="3-5年" />
                    <el-option label="5-10年" value="5-10年" />
                    <el-option label="10年以上" value="10年以上" />
                  </el-select>
                </el-form-item>

                <el-form-item label="学历要求" prop="education">
                  <el-select 
                    v-model="form.education" 
                    placeholder="请选择学历要求"
                    style="width: 100%"
                  >
                    <el-option label="不限" value="不限" />
                    <el-option label="大专" value="大专" />
                    <el-option label="本科" value="本科" />
                    <el-option label="硕士" value="硕士" />
                    <el-option label="博士" value="博士" />
                  </el-select>
                </el-form-item>
              </div>

              <!-- 第三行：薪资范围和工作类型 -->
              <div class="form-row">
                <el-form-item label="薪资范围" prop="salary">
                  <el-input 
                    v-model="form.salary" 
                    placeholder="如：10K-20K"
                    clearable
                  />
                </el-form-item>

                <el-form-item label="工作类型" prop="jobType">
                  <el-radio-group v-model="form.jobType">
                    <el-radio label="全职">全职</el-radio>
                    <el-radio label="兼职">兼职</el-radio>
                    <el-radio label="实习">实习</el-radio>
                    <el-radio label="外包">外包</el-radio>
                  </el-radio-group>
                </el-form-item>
              </div>

              <!-- 技能要求 -->
              <el-form-item label="技能要求" prop="skills">
                <el-select
                  v-model="form.skills"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="请选择或输入技能要求"
                  style="width: 100%"
                >
                  <el-option
                    v-for="skill in commonSkills"
                    :key="skill"
                    :label="skill"
                    :value="skill"
                  />
                </el-select>
              </el-form-item>

              <!-- 公司福利 -->
              <el-form-item label="公司福利">
                <el-checkbox-group v-model="form.benefits">
                  <el-checkbox label="五险一金">五险一金</el-checkbox>
                  <el-checkbox label="年终奖">年终奖</el-checkbox>
                  <el-checkbox label="带薪年假">带薪年假</el-checkbox>
                  <el-checkbox label="弹性工作">弹性工作</el-checkbox>
                  <el-checkbox label="远程办公">远程办公</el-checkbox>
                  <el-checkbox label="股票期权">股票期权</el-checkbox>
                  <el-checkbox label="培训机会">培训机会</el-checkbox>
                  <el-checkbox label="健身房">健身房</el-checkbox>
                </el-checkbox-group>
              </el-form-item>

              <!-- 其他要求 -->
              <el-form-item label="其他要求">
                <el-input
                  v-model="form.additionalRequirements"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入其他特殊要求或补充说明"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 右侧预览面板 -->
        <div class="preview-panel">
          <el-card class="preview-card">
            <template #header>
              <div class="card-header">
                <el-icon><View /></el-icon>
                <span>JD预览</span>
                <div class="header-actions" v-if="generatedJD">
                  <el-button size="small" @click="copyJD">
                    <el-icon><CopyDocument /></el-icon>
                    复制
                  </el-button>
                  <el-button size="small" type="primary" @click="downloadJD">
                    <el-icon><Download /></el-icon>
                    下载
                  </el-button>
                </div>
              </div>
            </template>

            <div class="preview-content">
              <div v-if="!generatedJD && !generating" class="empty-state">
                <el-icon class="empty-icon"><Document /></el-icon>
                <p>请填写左侧职位信息，然后点击"生成JD"按钮</p>
              </div>

              <div v-if="generating && !streamContent" class="loading-state">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <p>AI正在为您生成专业的职位描述...</p>
                <div class="loading-tips">
                  <p>💡 正在分析职位要求</p>
                  <p>🎯 匹配行业标准</p>
                  <p>✨ 优化语言表达</p>
                </div>
              </div>

              <!-- 流式内容显示 -->
              <div v-if="generating && streamContent" class="jd-content">
                <div class="jd-section">
                  <h3>正在生成JD内容...</h3>
                  <div class="stream-content">
                    <div class="jd-text markdown-content" v-html="renderedStreamContent"></div>
                  </div>
                </div>
              </div>

              <!-- 完整JD显示 -->
              <div v-if="generatedJD && !generating" class="jd-content">
                <div class="jd-section">
                  <h3>职位信息</h3>
                  <div class="job-info-grid">
                    <div class="info-item">
                      <span class="label">职位名称：</span>
                      <span class="value">{{ form.jobTitle }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">工作地点：</span>
                      <span class="value">{{ form.location }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">工作经验：</span>
                      <span class="value">{{ form.experience }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">学历要求：</span>
                      <span class="value">{{ form.education }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">薪资范围：</span>
                      <span class="value">{{ form.salary }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">工作类型：</span>
                      <span class="value">{{ form.jobType }}</span>
                    </div>
                  </div>
                </div>

                <div class="jd-section">
                  <div class="jd-header">
                    <h3>生成的JD内容</h3>
                    <div class="jd-actions" v-if="streamContent && !generating">
                      <el-button 
                        v-if="!isEditing" 
                        type="primary" 
                        size="small" 
                        @click="startEdit"
                        :icon="Edit"
                      >
                        编辑
                      </el-button>
                      <el-button 
                        v-if="!isEditing"
                        type="success" 
                        size="small" 
                        @click="saveJD"
                        :loading="saving"
                        :icon="Check"
                      >
                        保存
                      </el-button>
                      <div v-if="isEditing" class="edit-actions">
                        <el-button 
                          type="success" 
                          size="small" 
                          @click="saveJD"
                          :loading="saving"
                          :icon="Check"
                        >
                          保存
                        </el-button>
                        <el-button 
                          size="small" 
                          @click="cancelEdit"
                          :icon="Close"
                        >
                          取消
                        </el-button>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 编辑模式 -->
                  <div v-if="isEditing" class="jd-edit">
                    <el-input
                      v-model="editContent"
                      type="textarea"
                      :rows="20"
                      placeholder="请编辑JD内容..."
                      class="edit-textarea"
                    />
                  </div>
                  
                  <!-- 显示模式 -->
                  <div v-else class="jd-text markdown-content" v-html="renderedStreamContent"></div>
                </div>

                <div class="jd-section" v-if="form.benefits.length > 0">
                  <h3>福利待遇</h3>
                  <div class="benefits-list">
                    <el-tag 
                      v-for="benefit in form.benefits" 
                      :key="benefit" 
                      class="benefit-tag"
                      type="success"
                    >
                      {{ benefit }}
                    </el-tag>
                  </div>
                </div>

                <div class="jd-section" v-if="form.skills.length > 0">
                  <h3>技能要求</h3>
                  <div class="skills-list">
                    <el-tag 
                      v-for="skill in form.skills" 
                      :key="skill" 
                      class="skill-tag"
                      type="primary"
                    >
                      {{ skill }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Edit, Check, Close, Plus, List, Search, MoreFilled, 
  Location, Money, Delete, CopyDocument, Document,
  Star, Refresh
} from '@element-plus/icons-vue'
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

// 响应式数据
const formRef = ref()
const generating = ref(false)
const generatedJD = ref(null)
const streamContent = ref('')

// 编辑模式相关状态
const isEditing = ref(false)
const editContent = ref('')
const saving = ref(false)
const savedJDId = ref(null)

// JD列表相关状态
const jdList = ref([])
const jdListLoading = ref(false)
const selectedJD = ref(null)
const isCreatingNew = ref(false)
const searchKeyword = ref('')

// 分页数据
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// markdown渲染的计算属性
const renderedStreamContent = computed(() => {
  if (!streamContent.value) return ''
  try {
    return marked(streamContent.value)
  } catch (error) {
    console.error('Markdown渲染错误:', error)
    return streamContent.value.replace(/\n/g, '<br>')
  }
})

// 表单数据
const form = reactive({
  jobTitle: '',
  location: '',
  experience: '',
  education: '',
  salary: '',
  jobType: '全职',
  skills: [],
  benefits: [],
  additionalRequirements: ''
})

// 表单验证规则
const rules = {
  jobTitle: [
    { required: true, message: '请输入职位名称', trigger: 'blur' }
  ],
  location: [
    { required: true, message: '请选择工作地点', trigger: 'change' }
  ],
  experience: [
    { required: true, message: '请选择工作经验要求', trigger: 'change' }
  ],
  education: [
    { required: true, message: '请选择学历要求', trigger: 'change' }
  ]
}

// 城市列表
const cities = [
  '北京', '上海', '广州', '深圳', '杭州', '南京', '苏州', '成都', 
  '武汉', '西安', '重庆', '天津', '青岛', '大连', '厦门', '宁波'
]

// 常用技能
const commonSkills = [
  'JavaScript', 'TypeScript', 'Vue.js', 'React', 'Angular', 'Node.js',
  'Python', 'Java', 'Go', 'PHP', 'C++', 'C#', 'Swift', 'Kotlin',
  'HTML', 'CSS', 'SCSS', 'Less', 'Webpack', 'Vite', 'Docker', 'Kubernetes',
  'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Git', 'Linux', 'AWS', 'Azure'
]

// 处理流式响应
const handleStreamResponse = async (response) => {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          
          try {
            const parsed = JSON.parse(data)
            if (parsed.answer) {
              streamContent.value += parsed.answer
            }
          } catch (e) {
            // 如果不是JSON，直接添加到结果中
            streamContent.value += data
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// 生成JD
const generateJD = async () => {
  try {
    await formRef.value.validate()
    
    generating.value = true
    streamContent.value = '' // 清空之前的内容
    generatedJD.value = null // 清空之前的JD
    savedJDId.value = null // 重置JD ID，确保新生成的JD是新增而不是更新
    
    // 构建职位要求描述
    const requirements = `职位：${form.jobTitle}
工作地点：${form.location}
工作经验：${form.experience}
学历要求：${form.education}
薪资范围：${form.salary}
工作类型：${form.jobType}
技能要求：${form.skills.join('、')}
福利待遇：${form.benefits.join('、')}
其他要求：${form.description}`

    // 调用后端API
    const response = await hrWorkflowsApi.generateJD({
      requirements: requirements,
      position_title: form.jobTitle,
      department: '技术部', // 可以后续添加到表单中
      experience_level: form.experience,
      stream: true
    })
    
    // 处理流式响应
    await handleStreamResponse(response)
    
    // 流式响应完成后，解析内容并设置generatedJD
    if (streamContent.value) {
      generatedJD.value = {
        description: `<p>${streamContent.value}</p>`,
        responsibilities: [],
        requirements: []
      }
      ElMessage.success('JD生成成功！')
    } else {
      ElMessage.warning('未收到JD内容，请重试')
    }
  } catch (error) {
    console.error('生成JD失败:', error)
    ElMessage.error('生成JD失败，请重试')
  } finally {
    generating.value = false
  }
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  generatedJD.value = null
  streamContent.value = ''
  Object.assign(form, {
    jobTitle: '',
    location: '',
    experience: '',
    education: '',
    salary: '',
    jobType: '全职',
    skills: [],
    benefits: [],
    additionalRequirements: ''
  })
}

// 复制JD
const copyJD = async () => {
  try {
    const jdText = generateJDText()
    await navigator.clipboard.writeText(jdText)
    ElMessage.success('JD内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 开始编辑
const startEdit = () => {
  console.log('开始编辑，当前显示内容:', streamContent.value)
  isEditing.value = true
  editContent.value = streamContent.value
  console.log('编辑框初始内容:', editContent.value)
}

// 取消编辑
const cancelEdit = () => {
  isEditing.value = false
  editContent.value = ''
}

// 保存JD到后端
const saveJD = async () => {
  if (!editContent.value.trim()) {
    ElMessage.warning('JD内容不能为空')
    return
  }

  try {
    saving.value = true
    
    console.log('保存前的编辑内容:', editContent.value)
    console.log('保存前的显示内容:', streamContent.value)
    console.log('当前JD ID:', savedJDId.value)
    
    const jdData = {
      title: form.jobTitle || '未命名岗位',
      department: form.department || null,
      experience_level: form.experience || null,
      content: editContent.value,
      requirements: form.additionalRequirements || null,
      status: 'draft',
      meta_data: {
        location: form.location,
        salary: form.salary,
        jobType: form.jobType,
        skills: form.skills,
        benefits: form.benefits,
        education: form.education
      }
    }

    console.log('发送到后端的数据:', jdData)
    
    let response
    if (savedJDId.value) {
      // 如果已有ID，执行更新操作
      console.log('执行更新操作，JD ID:', savedJDId.value)
      response = await hrWorkflowsApi.updateJD(savedJDId.value, jdData)
      ElMessage.success('JD更新成功')
    } else {
      // 如果没有ID，执行新增操作
      console.log('执行新增操作')
      response = await hrWorkflowsApi.saveJD(jdData)
      console.log('新增操作完整响应:', response)
      if (response && response.id) {
        savedJDId.value = response.id
        console.log('新增成功，获得JD ID:', savedJDId.value)
      } else {
        console.log('响应中没有ID字段，响应结构:', response)
      }
      ElMessage.success('JD保存成功')
    }
    
    console.log('后端返回的响应:', response)
    
    // 更新显示内容
    streamContent.value = editContent.value
    isEditing.value = false
    
    // 刷新JD列表
    await fetchJDList()
    
    console.log('保存后的显示内容:', streamContent.value)
    
  } catch (error) {
    console.error('保存JD失败:', error)
    ElMessage.error('保存JD失败，请重试')
  } finally {
    saving.value = false
  }
}

// 下载JD文件
const downloadJD = () => {
  const jdText = generateJDText()
  const blob = new Blob([jdText], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${form.jobTitle}_JD.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('JD已保存到本地')
}

// 生成JD文本
const generateJDText = () => {
  if (!streamContent.value) return ''
  
  let text = `${form.jobTitle}\n\n`
  text += `工作地点：${form.location}\n`
  text += `工作经验：${form.experience}\n`
  text += `学历要求：${form.education}\n`
  text += `薪资范围：${form.salary}\n`
  text += `工作类型：${form.jobType}\n\n`
  
  text += `生成的JD内容：\n${streamContent.value}\n\n`
  
  if (form.benefits.length > 0) {
    text += `福利待遇：\n${form.benefits.join('、')}\n`
  }
  
  return text
}

// JD列表相关方法
// 获取JD列表
const fetchJDList = async () => {
  try {
    jdListLoading.value = true
    const params = {
      page: pagination.page,
      size: pagination.size
    }
    
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    
    const response = await hrWorkflowsApi.getJDList(params)
    jdList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('获取JD列表失败:', error)
    ElMessage.error('获取JD列表失败')
  } finally {
    jdListLoading.value = false
  }
}

// 选择JD
const selectJD = async (jd) => {
  selectedJD.value = jd
  isCreatingNew.value = false
  
  // 加载JD详情到表单
  try {
    const response = await hrWorkflowsApi.getJD(jd.id)
    const jdData = response
    
    // 填充表单数据
    form.jobTitle = jdData.position_title || ''
    form.location = jdData.location || ''
    form.experience = jdData.experience || ''
    form.education = jdData.education || ''
    form.salary = jdData.salary || ''
    form.jobType = jdData.job_type || '全职'
    form.skills = jdData.skills ? jdData.skills.split(',') : []
    form.benefits = jdData.benefits ? jdData.benefits.split(',') : []
    form.requirements = jdData.requirements || ''
    
    // 设置生成的内容
    streamContent.value = jdData.description || ''
    generatedJD.value = jdData.description || ''
    savedJDId.value = jd.id
    
  } catch (error) {
    console.error('获取JD详情失败:', error)
    ElMessage.error('获取JD详情失败')
  }
}

// 创建新JD
const createNewJD = () => {
  selectedJD.value = null
  isCreatingNew.value = true
  resetForm()
}

// 处理JD操作
const handleJDAction = async ({ action, jd }) => {
  switch (action) {
    case 'edit':
      await selectJD(jd)
      break
    case 'duplicate':
      await duplicateJD(jd)
      break
    case 'delete':
      await deleteJD(jd)
      break
  }
}

// 复制JD
const duplicateJD = async (jd) => {
  try {
    const response = await hrWorkflowsApi.getJD(jd.id)
    const jdData = response
    
    // 创建新JD
    createNewJD()
    
    // 填充表单数据（不包括ID）
    form.jobTitle = (jdData.position_title || '') + ' (副本)'
    form.location = jdData.location || ''
    form.experience = jdData.experience || ''
    form.education = jdData.education || ''
    form.salary = jdData.salary || ''
    form.jobType = jdData.job_type || '全职'
    form.skills = jdData.skills ? jdData.skills.split(',') : []
    form.benefits = jdData.benefits ? jdData.benefits.split(',') : []
    form.requirements = jdData.requirements || ''
    
    // 设置生成的内容
    streamContent.value = jdData.description || ''
    generatedJD.value = jdData.description || ''
    
    ElMessage.success('JD已复制，请修改后保存')
  } catch (error) {
    console.error('复制JD失败:', error)
    ElMessage.error('复制JD失败')
  }
}

// 删除JD
const deleteJD = async (jd) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除JD "${jd.position_title || '未命名职位'}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await hrWorkflowsApi.deleteJD(jd.id)
    ElMessage.success('JD已删除')
    
    // 如果删除的是当前选中的JD，清空选择
    if (selectedJD.value?.id === jd.id) {
      selectedJD.value = null
      isCreatingNew.value = false
      resetForm()
    }
    
    // 刷新列表
    await fetchJDList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除JD失败:', error)
      ElMessage.error('删除JD失败')
    }
  }
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  fetchJDList()
}

// 分页处理
const handlePageChange = (page) => {
  pagination.page = page
  fetchJDList()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchJDList()
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    'draft': 'info',
    'published': 'success',
    'archived': 'warning'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'draft': '草稿',
    'published': '已发布',
    'archived': '已归档'
  }
  return statusMap[status] || '草稿'
}

// 组件挂载时获取JD列表
onMounted(() => {
  fetchJDList()
})
</script>

<style lang="scss" scoped>
.jd-generator {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
  
  .page-container {
    max-width: 1400px;
    margin: 0 auto;
  }
  
  // 简化的页面头部
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 16px 24px;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    
    .header-left {
      .page-title {
        font-size: 24px;
        font-weight: 600;
        color: #ffffff;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        
        .el-icon {
          font-size: 20px;
        }
      }
    }
    
    .header-actions {
      display: flex;
      gap: 12px;
      
      .el-button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
        
        &:not(.el-button--primary) {
          background: rgba(255, 255, 255, 0.2);
          border: 1px solid rgba(255, 255, 255, 0.3);
          color: #ffffff;
          
          &:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
          }
        }
        
        &.el-button--primary {
          background: linear-gradient(45deg, #56ab2f, #a8e6cf);
          border: none;
          
          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(86, 171, 47, 0.4);
          }
        }
      }
    }
  }
  
  // 左右布局的主要内容
  .main-content {
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 24px;
    align-items: start;
    
    @media (max-width: 1200px) {
      grid-template-columns: 1fr;
      gap: 16px;
    }
  }
  
  // JD列表面板样式
  .jd-list-panel {
    .list-card {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      height: calc(100vh - 200px);
      display: flex;
      flex-direction: column;
      
      :deep(.el-card__header) {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border-radius: 16px 16px 0 0;
        padding: 16px 20px;
        
        .card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-weight: 600;
          
          .header-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
          }
        }
      }
      
      :deep(.el-card__body) {
        padding: 0;
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
    }
    
    .search-section {
      padding: 16px 20px;
      border-bottom: 1px solid #f0f0f0;
      
      .el-input {
        :deep(.el-input__wrapper) {
          border-radius: 8px;
        }
      }
    }
    
    .list-content {
      flex: 1;
      overflow-y: auto;
      
      &.loading {
        display: flex;
        align-items: center;
        justify-content: center;
      }
      
      &.empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #999;
        
        .el-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }
        
        .empty-text {
          font-size: 14px;
        }
      }
    }
    
    .jd-item {
      padding: 16px 20px;
      border-bottom: 1px solid #f0f0f0;
      cursor: pointer;
      transition: all 0.2s ease;
      
      &:hover {
        background: #f8f9fa;
      }
      
      &.active {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
      }
      
      .item-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
        
        .item-title {
          font-weight: 600;
          color: #333;
          font-size: 14px;
          line-height: 1.4;
          flex: 1;
          margin-right: 8px;
        }
        
        .item-actions {
          display: flex;
          gap: 4px;
          opacity: 0;
          transition: opacity 0.2s ease;
          
          .action-btn {
            width: 24px;
            height: 24px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            
            &:hover {
              background: #e0e0e0;
              color: #333;
            }
          }
        }
      }
      
      &:hover .item-actions {
        opacity: 1;
      }
      
      .item-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
        
        .meta-row {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: #666;
          
          .el-icon {
            font-size: 12px;
          }
          
          .meta-text {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
        
        .status-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          
          .el-tag {
            font-size: 11px;
            height: 20px;
            line-height: 18px;
            padding: 0 6px;
          }
          
          .update-time {
            font-size: 11px;
            color: #999;
          }
        }
      }
    }
    
    .pagination-section {
      padding: 16px 20px;
      border-top: 1px solid #f0f0f0;
      
      :deep(.el-pagination) {
        justify-content: center;
        
        .el-pagination__sizes {
          display: none;
        }
        
        .el-pagination__total {
          font-size: 12px;
        }
      }
    }
  }
  
  // JD编辑面板样式
  .jd-editor-panel {
    .welcome-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: calc(100vh - 200px);
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      text-align: center;
      
      .welcome-icon {
        font-size: 64px;
        color: #667eea;
        margin-bottom: 24px;
      }
      
      .welcome-title {
        font-size: 24px;
        font-weight: 600;
        color: #333;
        margin-bottom: 12px;
      }
      
      .welcome-desc {
        font-size: 16px;
        color: #666;
        margin-bottom: 32px;
        line-height: 1.6;
      }
      
      .welcome-actions {
        display: flex;
        gap: 16px;
        
        .el-button {
          border-radius: 8px;
          padding: 12px 24px;
          font-weight: 500;
        }
      }
    }
    
    .editor-content {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      align-items: start;
      
      @media (max-width: 1200px) {
        grid-template-columns: 1fr;
        gap: 16px;
      }
    }
  }
  
  .config-panel, .preview-panel {
    .config-card, .preview-card {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      transition: all 0.3s ease;
      height: 100%;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
      }
      
      :deep(.el-card__header) {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border-radius: 16px 16px 0 0;
        
        .card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-weight: 600;
          
          > span {
            display: flex;
            align-items: center;
            gap: 8px;
          }
          
          .header-actions {
            display: flex;
            gap: 8px;
            
            .el-button {
              background: rgba(255, 255, 255, 0.2);
              border: 1px solid rgba(255, 255, 255, 0.3);
              color: white;
              
              &:hover {
                background: rgba(255, 255, 255, 0.3);
              }
              
              &.el-button--primary {
                background: rgba(255, 255, 255, 0.9);
                color: #667eea;
                
                &:hover {
                  background: white;
                }
              }
            }
          }
        }
      }
      
      :deep(.el-card__body) {
        padding: 24px;
        height: calc(100% - 60px);
        overflow-y: auto;
      }
    }
  }
  
  // 预览面板特殊样式
  .preview-panel {
    .preview-card {
      min-height: 600px;
      
      :deep(.el-card__body) {
        display: flex;
        flex-direction: column;
      }
    }
    
    .preview-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      
      .empty-state, .loading-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }
      
      .jd-content {
        flex: 1;
      }
    }
  }
  
  // 表单样式
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
    
    @media (max-width: 768px) {
      grid-template-columns: 1fr;
      gap: 12px;
    }
  }
  
  :deep(.el-form-item__label) {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 8px;
  }
  
  :deep(.el-input__wrapper) {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    &.is-focus {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
  }
  
  :deep(.el-select) {
    .el-input__wrapper {
      border-radius: 8px;
    }
  }
  
  :deep(.el-textarea__inner) {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    &:focus {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
  }
  
  :deep(.el-radio-group) {
    .el-radio {
      margin-right: 16px;
      
      .el-radio__label {
        color: #2c3e50;
        font-weight: 500;
      }
    }
  }
  
  :deep(.el-checkbox-group) {
    .el-checkbox {
      margin-right: 16px;
      margin-bottom: 8px;
      
      .el-checkbox__label {
        color: #2c3e50;
        font-weight: 500;
      }
    }
  }
  
  // 预览内容样式
  .preview-content {
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: #95a5a6;
      
      .empty-icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
      
      p {
        font-size: 16px;
        margin: 0;
      }
    }
    
    .loading-state {
      text-align: center;
      padding: 60px 20px;
      color: #667eea;
      
      .loading-icon {
        font-size: 48px;
        margin-bottom: 16px;
        animation: spin 2s linear infinite;
      }
      
      p {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 20px;
      }
      
      .loading-tips {
        p {
          font-size: 14px;
          margin: 8px 0;
          opacity: 0.8;
        }
      }
    }
    
    .jd-content {
      .jd-section {
        margin-bottom: 24px;
        
        h3 {
          font-size: 18px;
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 2px solid #ecf0f1;
          position: relative;
          
          &::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 40px;
            height: 2px;
            background: linear-gradient(45deg, #667eea, #764ba2);
          }
        }
        
        .job-info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 12px;
          
          .info-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            
            .label {
              font-weight: 600;
              color: #34495e;
              margin-right: 8px;
            }
            
            .value {
              color: #2c3e50;
              font-weight: 500;
            }
          }
        }
        
        .jd-text {
          color: #5a6c7d;
          line-height: 1.6;
          
          p {
            margin-bottom: 12px;
          }
        }
        
        .benefits-list, .skills-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          
          .benefit-tag, .skill-tag {
            border-radius: 6px;
            font-weight: 500;
          }
        }
        
        // 按钮样式优化
        .jd-actions {
          margin-top: 16px;
          margin-bottom: 16px;
          display: flex;
          gap: 12px;
          align-items: center;
          
          .el-button {
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.3s ease;
            
            &:hover {
              transform: translateY(-1px);
              box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
          }
          
          .edit-actions {
            display: flex;
            gap: 8px;
          }
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .jd-generator {
    padding: 16px;
    
    .page-header {
      flex-direction: column;
      gap: 16px;
      text-align: center;
      
      .header-actions {
        justify-content: center;
      }
    }
    
    .main-content {
      grid-template-columns: 1fr;
    }
    
    .config-panel, .preview-panel {
      .config-card, .preview-card {
        :deep(.el-card__body) {
          padding: 16px;
        }
      }
    }
  }
}

// 动画效果
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.config-panel, .preview-panel {
  animation: fadeInUp 0.6s ease-out;
}

.config-panel {
  animation-delay: 0.1s;
}

.preview-panel {
  animation-delay: 0.2s;
}

// Markdown 内容样式
.markdown-content {
  line-height: 1.6;
  color: #333;

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