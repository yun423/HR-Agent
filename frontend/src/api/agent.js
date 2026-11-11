import { request } from '@/api/index'
import Cookies from 'js-cookie'

export const agentApi = {
  chat(data) {
    return request.post('/agent/chat', data)
  },

  chatStream(data, options = {}) {
    const token = Cookies.get('token')
    return fetch('/api/v1/agent/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data),
      signal: options.signal
    })
  },

  stream(data, options = {}) {
    const token = Cookies.get('token')
    return fetch('/api/v1/agent/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data),
      signal: options.signal
    })
  },

  streamResumeScreening({ jobDescriptionId, files, conversationId, signal }) {
    const token = Cookies.get('token')
    const formData = new FormData()
    formData.append('job_description_id', jobDescriptionId)
    if (conversationId) {
      formData.append('conversation_id', conversationId)
    }
    files.forEach(file => {
      formData.append('files', file)
    })

    return fetch('/api/v1/agent/resume-screen/stream', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: formData,
      signal
    })
  },

  streamInterviewPlan({ resumeEvaluationId, conversationId, signal }) {
    const token = Cookies.get('token')
    const formData = new FormData()
    formData.append('resume_evaluation_id', resumeEvaluationId)
    if (conversationId) {
      formData.append('conversation_id', conversationId)
    }

    return fetch('/api/v1/agent/interview-plan/stream', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: formData,
      signal
    })
  },

  streamExam(data, options = {}) {
    const token = Cookies.get('token')
    return fetch('/api/v1/agent/exam/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data),
      signal: options.signal
    })
  },

  streamExamWithDocuments({ examRequirements, files, conversationId, signal }) {
    const token = Cookies.get('token')
    const formData = new FormData()
    formData.append('exam_requirements', JSON.stringify(examRequirements))
    if (conversationId) {
      formData.append('conversation_id', conversationId)
    }
    files.forEach(file => {
      formData.append('files', file)
    })

    return fetch('/api/v1/agent/exam/document-stream', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: formData,
      signal
    })
  }
}
