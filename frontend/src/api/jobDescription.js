import { request } from '@/api/index'

export const jobDescriptionApi = {
  // 获取JD列表
  getJDList: (params) => {
    return request.get('/job-descriptions/', { params })
  },

  // 获取JD详情
  getJDDetail: (id) => {
    return request.get(`/job-descriptions/${id}`)
  },

  // 创建/保存JD
  saveJD: (data) => {
    return request.post('/job-descriptions/save', data)
  },

  // 更新JD
  updateJD: (id, data) => {
    return request.put(`/job-descriptions/${id}`, data)
  },

  // 删除JD
  deleteJD: (id) => {
    return request.delete(`/job-descriptions/${id}`)
  }
}

export default jobDescriptionApi