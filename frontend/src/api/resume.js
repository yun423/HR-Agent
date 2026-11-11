import { request } from './index'

export const resumeApi = {
  // 获取简历评价历史列表
  getResumeHistory: (params = {}) => {
    return request.get('/resume-evaluation/history', { params })
  },

  // 上传简历并进行评价
  uploadResume: (formData) => {
    return request.post('/resume-evaluation/evaluate', formData)
  },

  // 获取特定简历评价详情
  getResumeDetail: (evaluationId) => {
    return request.get(`/resume-evaluation/${evaluationId}`)
  },

  // 获取支持的文件格式
  getSupportedFormats: () => {
    return request.get('/resume-evaluation/supported-formats')
  },

  // 删除简历评价记录
  deleteResume: (evaluationId) => {
    return request.delete(`/resume-evaluation/${evaluationId}`)
  },

  // 更新简历状态
  updateResumeStatus: (evaluationId, status) => {
    return request.put(`/resume-evaluation/${evaluationId}/status?status=${status}`)
  }
}