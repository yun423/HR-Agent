import { request } from '@/api/index'

export const statsApi = {
  // 获取仪表板统计数据
  getDashboardStats() {
    return request.get('/stats/dashboard')
  },

  // 获取招聘趋势数据
  getRecruitmentTrend(days = 30) {
    return request.get('/stats/recruitment-trend', { params: { days } })
  },

  // 获取简历评价分布统计
  getTrainingCompletionStats() {
    return request.get('/stats/training-completion')
  },

  // 获取最近活动记录
  getRecentActivities(limit = 10, offset = 0) {
    return request.get('/stats/recent-activities', { params: { limit, offset } })
  }
}

export default statsApi