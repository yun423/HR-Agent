import request from '@/utils/request'

export const jdApi = {
  // 获取JD列表
  getJDList: (params) => {
    return request({
      url: '/job-descriptions/',
      method: 'get',
      params
    })
  },

  // 获取JD详情
  getJDDetail: (id) => {
    return request({
      url: `/job-descriptions/${id}`,
      method: 'get'
    })
  },

  // 创建/保存JD
  saveJD: (data) => {
    return request({
      url: '/job-descriptions/save',
      method: 'post',
      data
    })
  },

  // 更新JD
  updateJD: (id, data) => {
    return request({
      url: `/job-descriptions/${id}`,
      method: 'put',
      data
    })
  },

  // 删除JD
  deleteJD: (id) => {
    return request({
      url: `/job-descriptions/${id}`,
      method: 'delete'
    })
  },

  // 生成JD
  generateJD: (data) => {
    return request({
      url: '/hr-workflows/generate-jd',
      method: 'post',
      data
    })
  },

  // 复制JD (暂时使用获取详情然后保存的方式实现)
  copyJD: (id) => {
    return jdApi.getJDDetail(id).then(response => {
      const jdData = { ...response.data }
      delete jdData.id
      delete jdData.created_at
      delete jdData.updated_at
      jdData.title = `${jdData.title} - 副本`
      jdData.status = 'draft'
      return jdApi.saveJD(jdData)
    })
  },

  // 发布JD (更新状态为published)
  publishJD: (id) => {
    return request({
      url: `/job-descriptions/${id}`,
      method: 'put',
      data: { status: 'published' }
    })
  },

  // 归档JD (更新状态为archived)
  archiveJD: (id) => {
    return request({
      url: `/job-descriptions/${id}`,
      method: 'put',
      data: { status: 'archived' }
    })
  }
}

export default jdApi