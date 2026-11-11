<template>
  <div class="activities-page">
    <div class="page-header">
      <h1>活动记录</h1>
      <el-button @click="refreshActivities" :loading="loading">刷新</el-button>
    </div>

    <div class="activities-container">
      <el-timeline>
        <el-timeline-item
          v-for="activity in activities"
          :key="activity.id"
          :timestamp="activity.time"
          :type="getActivityType(activity.type)"
        >
          <div class="activity-item">
            <div class="activity-icon" :class="activity.type">
              <el-icon><component :is="activity.icon" /></el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-title">{{ activity.title }}</div>
              <div class="activity-time">{{ activity.time }}</div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>

      <!-- 分页 -->
      <div class="pagination-container" v-if="total > pageSize">
        <el-pagination
          @current-change="handlePageChange"
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          background
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '@/api/stats'

// 响应式数据
const activities = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 获取活动类型颜色
const getActivityType = (type) => {
  const typeMap = {
    recruitment: 'primary',
    training: 'success',
    interview: 'warning',
    assistant: 'info'
  }
  return typeMap[type] || 'info'
}

// 获取活动记录
const fetchActivities = async (page = 1) => {
  try {
    loading.value = true
    const offset = (page - 1) * pageSize.value
    const response = await statsApi.getRecentActivities(pageSize.value, offset)
    activities.value = response.items || response
    total.value = response.total || (response.items ? response.items.length : response.length)
    currentPage.value = page
  } catch (error) {
    console.error('获取活动记录失败:', error)
  } finally {
    loading.value = false
  }
}

// 刷新活动记录
const refreshActivities = async () => {
  await fetchActivities(currentPage.value)
}

// 处理分页变化
const handlePageChange = (page) => {
  currentPage.value = page
  fetchActivities(page)
}

// 组件挂载时获取数据
onMounted(() => {
  fetchActivities()
})
</script>

<style lang="scss" scoped>
.activities-page {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h1 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }
}

.activities-container {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--border-lighter);
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;

  .activity-icon {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: white;

    &.recruitment { background: var(--primary-color); }
    &.training { background: var(--success-color); }
    &.interview { background: var(--warning-color); }
    &.assistant { background: var(--info-color); }
  }

  .activity-content {
    flex: 1;

    .activity-title {
      font-size: 14px;
      color: var(--text-primary);
      margin-bottom: 2px;
    }

    .activity-time {
      font-size: 12px;
      color: var(--text-secondary);
    }
  }
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>