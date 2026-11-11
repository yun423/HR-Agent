import { request } from '@/api/index'
import Cookies from 'js-cookie'

export const hrWorkflowsApi = {
  // 获取工作流类型列表
  getWorkflowTypes() {
    return request.get('/hr-workflows/types')
  },

  // 生成JD
  generateJD(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      return fetch(`/api/v1/hr-workflows/generate-jd`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
    }
    
    return request.post('/hr-workflows/generate-jd', data)
  },

  // 解析自然语言需求为结构化表单字段
  parseRequirements(data) {
    return request.post('/hr-workflows/parse-requirements', data)
  },

  // 简历评价
  evaluateResume(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      return fetch(`/api/v1/hr-workflows/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
    }
    
    return request.post('/hr-workflows/evaluate', data)
  },

   // 批量简历评价
  batchEvaluateResume(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      return fetch(`/api/v1/hr-workflows/batch-evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
    }
    
    return request.post('/hr-workflows/batch-evaluate', data)
  },

  // // 生成面试方案
  // generateInterviewPlan(data) {
  //   if (data.stream) {
  //     const token = Cookies.get('token')
  //     return fetch(`/api/v1/hr-workflows/generate-interview-plan`, {
  //       method: 'POST',
  //       headers: {
  //         'Content-Type': 'application/json',
  //         'Authorization': `Bearer ${token}`
  //       },
  //       body: JSON.stringify(data)
  //     })
  //   }
    
  //   return request.post('/hr-workflows/generate-interview-plan', data)
  // },

  // 根据简历ID生成面试方案
  generateInterviewPlanByResume(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      const formData = new FormData()
      formData.append('resume_id', data.resume_id)
      if (data.conversation_id) {
        formData.append('conversation_id', data.conversation_id)
      }
      formData.append('stream', data.stream)

      return fetch(`/api/v1/hr-workflows/generate-interview-plan-by-resume`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
    }
    
    return request.post('/hr-workflows/generate-interview-plan-by-resume', data)
  },

  // 调用自定义工作流
  callCustomWorkflow(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      return fetch(`/api/v1/hr-workflows/custom`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
    }
    
    return request.post('/hr-workflows/custom', data)
  },


  // 面试方案相关API
  // 保存面试方案内容
  saveInterviewPlan(planId, data) {
    return request.post(`/interview-plans/${planId}/save`, data)
  },

  // 创建面试方案
  createInterviewPlan(data) {
    return request.post('/interview-plans', data)
  },

  // 更新面试方案
  updateInterviewPlan(planId, data) {
    return request.put(`/interview-plans/${planId}`, data)
  },

  // 获取面试方案详情
  getInterviewPlan(planId) {
    return request.get(`/interview-plans/${planId}`)
  },

  // 获取面试方案列表
  getInterviewPlanList(params) {
    return request.get('/interview-plans/', { params })
  },

  // 保存生成的面试方案
  saveGeneratedInterviewPlan(data) {
    return request.post('/interview-plans/save-generated', data)
  },

  // 删除面试方案
  deleteInterviewPlan(planId) {
    return request.delete(`/interview-plans/${planId}`)
  },

  // 生成评分标准
  generateScoringCriteria(data) {
    if (data.stream) {
      const token = Cookies.get('token')
      return fetch(`/api/v1/hr-workflows/generate-scoring-criteria`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
    }

    return request.post('/hr-workflows/generate-scoring-criteria', data)
  },

  // 导出简历附件为ZIP
  exportZipResumes(resumeIds) {
    const token = Cookies.get('token')
    return fetch(`/api/v1/resume-evaluation/export-zip`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        resume_ids: resumeIds
      })
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.blob()
    })
  }
}