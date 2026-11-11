import { request } from '@/api/index'
import Cookies from 'js-cookie'

export const scoringCriteriaApi = {
  // 保存评分标准
  createScoringCriteria(data) {
    return request.post('/scoring-criteria/save', data)
  },

  // 更新评分标准
  updateScoringCriteria(id, data) {
    return request.put(`/scoring-criteria/${id}`, data)
  },

  // 获取评分标准详情
  getScoringCriteria(id) {
    return request.get(`/scoring-criteria/${id}`)
  },

  // 获取评分标准列表
  getScoringCriteriaList(params) {
    return request.get('/scoring-criteria/', { params })
  },

  // 根据JD ID获取评分标准
  getScoringCriteriaByJD(jdId) {
    console.log('API调用 getScoringCriteriaByJD，参数:', { job_description_id: jdId })
    return request.get('/scoring-criteria/', {
      params: { job_description_id: jdId }
    })
  },

  // 删除评分标准
  deleteScoringCriteria(id) {
    return request.delete(`/scoring-criteria/${id}`)
  }
}

export default scoringCriteriaApi