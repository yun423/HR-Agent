<template>
  <div class="system-page">
    <div class="page-container">
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Setting /></el-icon>
            角色管理
          </h1>
          <p class="page-description">创建、删除角色，并用于用户授权</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" size="large" @click="openCreate">
            <el-icon><Plus /></el-icon>
            新建角色
          </el-button>
        </div>
      </div>

      <div class="main-content">
        <el-card class="list-card">
          <el-table :data="roles" v-loading="loading" border>
            <el-table-column label="角色名" prop="name" min-width="200" />
            <el-table-column label="描述" prop="description" min-width="300" />
            <el-table-column label="内置" width="120">
              <template #default="{ row }">
                <el-tag :type="row.is_builtin ? 'info' : 'success'">{{ row.is_builtin ? '内置' : '自定义' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="danger" :disabled="row.is_builtin" @click="delRole(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <el-dialog v-model="createVisible" title="新建角色" width="480px">
        <el-form :model="form" label-width="100px">
          <el-form-item label="角色名">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createVisible=false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'
import { Setting, Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const roles = ref([])
const createVisible = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '' })

const fetchRoles = async () => {
  try {
    loading.value = true
    const res = await adminApi.listRoles()
    roles.value = Array.isArray(res) ? res : (res.items || res || [])
  } finally {
    loading.value = false
  }
}

const openCreate = () => { createVisible.value = true }

const submitCreate = async () => {
  if (!form.name) { ElMessage.warning('请输入角色名'); return }
  try {
    creating.value = true
    await adminApi.createRole({ name: form.name, description: form.description })
    ElMessage.success('创建成功')
    createVisible.value = false
    Object.assign(form, { name: '', description: '' })
    await fetchRoles()
  } finally {
    creating.value = false
  }
}

const delRole = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除角色“${row.name}”？`, '提示', { type: 'warning' })
    await adminApi.deleteRole(row.id)
    ElMessage.success('删除成功')
    await fetchRoles()
  } catch (e) {}
}

onMounted(() => { fetchRoles() })
</script>

<style lang="scss" scoped>
.system-page { height: 100vh; display: flex; flex-direction: column; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); position: relative; overflow: hidden; }
.system-page::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px); background-size: 50px 50px; animation: float 20s linear infinite; pointer-events: none; }
.page-container { flex: 1; display: flex; flex-direction: column; padding: 20px; max-width: 95%; margin: 0 auto; width: 100%; position: relative; z-index: 1; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); padding: 24px; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
.page-title { margin: 0 0 8px 0; font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; align-items: center; gap: 12px; }
.page-description { margin: 0; color: #64748b; font-size: 16px; }
.header-actions .el-button.el-button--primary { background: linear-gradient(135deg, #667eea, #764ba2); border: none; color: #fff; }
.main-content { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
.list-card { background: rgba(255,255,255,0.95); border-radius: 16px; }
@keyframes float { 0% { transform: translate(0,0) rotate(0deg) } 33% { transform: translate(30px,-30px) rotate(120deg) } 66% { transform: translate(-20px,20px) rotate(240deg) } 100% { transform: translate(0,0) rotate(360deg) } }
</style>