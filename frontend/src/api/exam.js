import { request } from '@/api/index'
import Cookies from 'js-cookie'

// 生成UUID
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export const examApi = {
  // 生成试卷
  async generateExam(data, onProgress) {
    if (data.stream) {
      const token = Cookies.get('token')
      const response = await fetch(`/api/v1/hr-workflows/papers/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          title: data.title,
          subject: data.subject,
          total_score: data.total_score,
          question_types: data.question_types || [],
          question_counts: data.question_counts || {},
          knowledge_files: data.knowledge_files || [],
          special_requirements: data.special_requirements,
          stream: true
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() // 保留最后一个可能不完整的行

          let currentEvent = null
          let currentData = null
          
          for (const line of lines) {
            const trimmedLine = line.trim()
            if (trimmedLine === '') {
              // 空行表示一个SSE事件的结束，处理当前事件
              if (currentData !== null) {
                if (currentData === '[DONE]') {
                  return { data: fullContent }
                }
                
                try {
                  const parsed = JSON.parse(currentData)
                  const evt = parsed.event
                  const ans = parsed.answer || (parsed.data && parsed.data.answer) || ''
                  if ((evt === 'message' || evt === 'message_delta') && ans) {
                    fullContent += ans
                    if (onProgress) {
                      onProgress(ans, fullContent)
                    }
                  }
                  // 忽略控制事件，如 workflow_started、message_completed 等
                } catch (e) {
                  // 忽略解析错误，可能是ping等非JSON数据
                }
              }
              // 重置当前事件和数据
              currentEvent = null
              currentData = null
              continue
            }
            
            if (trimmedLine.startsWith('event: ')) {
              currentEvent = trimmedLine.slice(7).trim()
            } else if (trimmedLine.startsWith('data: ')) {
              currentData = trimmedLine.slice(6).trim()
            }
            // 忽略其他类型的行（如id:, retry:等）
          }
          
          // 处理可能存在的最后一个事件（如果流结束时没有空行）
          if (currentData !== null) {
            if (currentData === '[DONE]') {
              return { data: fullContent }
            }
            
            try {
              const parsed = JSON.parse(currentData)
              const evt = parsed.event
              const ans = parsed.answer || (parsed.data && parsed.data.answer) || ''
              if ((evt === 'message' || evt === 'message_delta') && ans) {
                fullContent += ans
                if (onProgress) {
                  onProgress(ans, fullContent)
                }
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      } finally {
        reader.releaseLock()
      }

      return { data: fullContent }
    }
    
    return request.post('/exam-management/papers/generate', {
      title: data.title,
      subject: data.subject,
      total_score: data.total_score,
      question_types: data.question_types || [],
      question_counts: data.question_counts || {},
      knowledge_files: data.knowledge_files || [],
      special_requirements: data.special_requirements,
      stream: false
    })
  },

  // 解析试卷意图为结构化字段
  parseIntent(data) {
    return request.post('/hr-workflows/papers/parse-intent', data)
  },

  // 构建试卷生成查询
  buildExamQuery(data) {
    const queryParts = [`请生成一份${data.subject}试卷`]
    
    if (data.title) {
      queryParts.push(`试卷标题：${data.title}`)
    }
    
    if (data.description) {
      queryParts.push(`试卷描述：${data.description}`)
    }
    
    if (data.difficulty) {
      const difficultyMap = {
        'easy': '简单',
        'medium': '中等',
        'hard': '困难'
      }
      queryParts.push(`难度等级：${difficultyMap[data.difficulty] || data.difficulty}`)
    }
    
    if (data.duration) {
      queryParts.push(`考试时长：${data.duration}分钟`)
    }
    
    if (data.questionTypes && data.questionTypes.length > 0) {
      const typeMap = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'fill_blank': '填空题',
        'short_answer': '简答题',
        'essay': '论述题',
        'coding': '编程题'
      }
      const types = data.questionTypes.map(type => typeMap[type] || type).join('、')
      queryParts.push(`题目类型：${types}`)
    }
    
    if (data.questionCounts) {
      const counts = Object.entries(data.questionCounts)
        .filter(([_, count]) => count > 0)
        .map(([type, count]) => {
          const typeMap = {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'fill_blank': '填空题',
            'short_answer': '简答题',
            'essay': '论述题',
            'coding': '编程题'
          }
          return `${typeMap[type] || type}${count}道`
        })
        .join('，')
      if (counts) {
        queryParts.push(`题目数量：${counts}`)
      }
    }
    
    if (data.knowledgeFiles && data.knowledgeFiles.length > 0) {
      const fileNames = data.knowledgeFiles.map(file => file.filename).join('、')
      queryParts.push(`基于知识库文件：${fileNames}`)
    }
    
    return queryParts.join('\n')
  },

  // 构建额外输入参数
  buildAdditionalInputs(data) {
    const inputs = {
      subject: data.subject,
      difficulty: data.difficulty,
      duration: data.duration
    }
    
    if (data.title) inputs.title = data.title
    if (data.description) inputs.description = data.description
    if (data.questionTypes) inputs.question_types = data.questionTypes
    if (data.questionCounts) inputs.question_counts = data.questionCounts
    if (data.knowledgeFiles) inputs.knowledge_files = data.knowledgeFiles
    
    return inputs
  },

  // 获取试卷列表
  getExamList(params = {}) {
    return request.get('/exam-management/papers', { params })
  },

  // 保存试卷
  saveExam(data) {
    return request.post('/exam-management/papers', data)
  },

  // 获取试卷详情
  getExamDetail(id) {
    return request.get(`/exam-management/papers/${id}`)
  },

  // 更新试卷
  updateExam(id, data) {
    return request.put(`/exam-management/papers/${id}`, data)
  },

  // 删除试卷
  deleteExam(id) {
    return request.delete(`/exam-management/papers/${id}`)
  },

  // 复制试卷
  duplicateExam(id) {
    return request.post(`/exam-management/papers/${id}/duplicate`)
  },

  // 预览试卷
  previewExam(id) {
    return request.get(`/exam-management/papers/${id}/preview`)
  },

  // 获取知识库列表
  getKnowledgeBases(params = {}) {
    return request.get('/knowledge-base/', {
      params: {
        skip: params.skip || 0,
        limit: params.limit || 100,
        ...params
      }
    })
  },

  // 获取知识库文档列表
  getKnowledgeBaseDocuments(knowledgeBaseId, params = {}) {
    return request.get('/knowledge-assistant/documents', {
      params: {
        knowledge_base_id: knowledgeBaseId,
        skip: params.skip || 0,
        limit: params.limit || 20,
        ...params
      }
    })
  },

  // 获取知识库文件列表（保持向后兼容）
  getKnowledgeFiles(params = {}) {
    return request.get('/knowledge-assistant/documents', { params })
  },

  // 搜索知识库文件
  searchKnowledgeFiles(keyword) {
    return request.get('/knowledge-base/documents/search', {
      params: { keyword }
    })
  },

  // 获取单个试卷（用于分享页面）
  getExam(examId) {
    return request.get(`/exam-management/papers/${examId}/share`)
  },

  // 提交考试答案
  submitExam(data) {
    return request.post('/hr-workflows/papers/submit', data)
  },

  // 获取考试结果列表
  async getExamResults(params = {}) {
    try {
      const response = await request.get('/exam-management/exam-results', { params })
      return response
    } catch (error) {
      console.error('获取考试结果列表失败:', error)
      throw error
    }
  },

  // 获取考试结果
  async getExamResult(examResultId) {
    try {
      const response = await request.get(`/exam-management/exam-results/${examResultId}`)
      return response
    } catch (error) {
      console.error('获取考试结果失败:', error)
      throw error
    }
  },

  // 获取单个考试结果详情
  async getExamResultDetail(examResultId) {
    try {
      const response = await request.get(`/exam-management/exam-results/${examResultId}`)
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      console.error('获取考试结果详情失败:', error)
      return {
        success: false,
        error: error.response?.data?.message || '获取考试结果详情失败'
      }
    }
  }
}

export default examApi