<template>
  <div class="system-page">
    <div class="page-container">
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><User /></el-icon>
            用户管理
          </h1>
          <p class="page-description">查看、创建用户，并为用户分配角色</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" size="large" @click="openCreate">
            <el-icon><Plus /></el-icon>
            新建用户
          </el-button>
        </div>
      </div>

      <div class="main-content">
        <el-card class="list-card">
          <template #header>
            <div class="list-header">
              <span class="list-title">
                <el-icon><List /></el-icon>
                用户列表 ({{ pagination.total }})
              </span>
              <div class="list-actions">
                <el-input v-model="keyword" placeholder="搜索用户名/邮箱" clearable size="small" style="width: 240px" @input="fetchUsers">
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </div>
            </div>
          </template>

          <el-table :data="users" v-loading="loading" border>
            <el-table-column label="用户名" prop="username" min-width="140" />
            <el-table-column label="邮箱" prop="email" min-width="200" />
            <el-table-column label="姓名" prop="full_name" min-width="140" />
            <el-table-column label="角色" min-width="220">
              <template #default="{ row }">
                <template v-if="row.roles && row.roles.length > 0">
                  <el-tag v-for="r in row.roles" :key="r.id" type="success" class="mr8">{{ r.name }}</el-tag>
                </template>
                <template v-else>
                  <el-tag type="info" class="mr8">普通用户</el-tag>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="400" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEdit(row)">编辑</el-button>
                <el-button size="small" @click="openAssign(row)">分配角色</el-button>
                <el-button v-if="row.is_active" size="small" type="danger" @click="disableUser(row)">停用</el-button>
                <el-button v-else size="small" type="success" @click="enableUser(row)">启用</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container" v-if="pagination.total > 0">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.size"
              :total="pagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              small
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </div>

      <el-dialog v-model="createVisible" title="新建用户" width="520px">
        <el-form :model="form" label-width="100px">
          <el-form-item label="用户名">
            <el-input v-model="form.username" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="form.full_name" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="form.department" />
          </el-form-item>
          <el-form-item label="职位">
            <el-input v-model="form.position" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createVisible=false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="editVisible" title="编辑用户" width="520px">
        <el-form :model="editForm" label-width="100px">
          <el-form-item label="用户名">
            <el-input v-model="editForm.username" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="editForm.email" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="editForm.full_name" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="editForm.department" />
          </el-form-item>
          <el-form-item label="职位">
            <el-input v-model="editForm.position" />
          </el-form-item>
          <el-form-item label="头像">
            <el-input v-model="editForm.avatar_url" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="editForm.password" type="password" placeholder="留空则不修改密码" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible=false">取消</el-button>
          <el-button type="primary" :loading="editing" @click="submitEdit">保存</el-button>
        </template>
      </el-dialog>

      <el-drawer v-model="assignVisible" title="分配角色" :with-header="true" size="30%">
        <div class="assign-body">
          <div class="assign-user">{{ currentUser?.username }} ({{ currentUser?.email }})</div>
          <el-checkbox-group v-model="selectedRoleIds">
            <el-checkbox v-for="r in roles" :key="r.id" :label="r.id">{{ r.name }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <template #footer>
          <el-button @click="assignVisible=false">取消</el-button>
          <el-button type="primary" :loading="assigning" @click="submitAssign">保存</el-button>
        </template>
      </el-drawer>
    </div>
  </div>
  
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'
import { request } from '@/api'
import { User, Plus, List, Search } from '@element-plus/icons-vue'

const loading = ref(false)
const users = ref([])
const keyword = ref('')
const pagination = reactive({ page: 1, size: 10, total: 0 })

const createVisible = ref(false)
const creating = ref(false)
const form = reactive({ username: '', email: '', full_name: '', password: '', department: '', position: '' })

const editVisible = ref(false)
const editing = ref(false)
const editForm = reactive({ id: '', username: '', email: '', full_name: '', department: '', position: '', avatar_url: '', password: '' })

const assignVisible = ref(false)
const assigning = ref(false)
const roles = ref([])
const selectedRoleIds = ref([])
const currentUser = ref(null)

const mapEnumRole = (role) => {
  const map = { admin: '管理员', hr_manager: 'HR经理', hr_specialist: 'HR专家', employee: '员工' }
  return map[role] || role
}

const fetchUsers = async () => {
  try {
    loading.value = true
    const res = await adminApi.listUsers({ skip: (pagination.page-1)*pagination.size, limit: pagination.size, search: keyword.value })
    users.value = Array.isArray(res) ? res : (res.items || [])
    pagination.total = res?.total || users.value.length
  } catch (e) {
  } finally {
    loading.value = false
  }
}

const fetchRoles = async () => {
  const res = await adminApi.listRoles()
  roles.value = Array.isArray(res) ? res : (res.items || res || [])
}

const openCreate = () => {
  createVisible.value = true
}

const submitCreate = async () => {
  if (!form.username || !form.email || !form.full_name || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    creating.value = true
    await adminApi.createUser({
      username: form.username,
      email: form.email,
      full_name: form.full_name,
      password: form.password,
      department: form.department,
      position: form.position
    })
    ElMessage.success('创建成功')
    createVisible.value = false
    Object.assign(form, { username: '', email: '', full_name: '', password: '', department: '', position: '' })
    await fetchUsers()
  } finally {
    creating.value = false
  }
}

const openAssign = async (row) => {
  currentUser.value = row
  await fetchRoles()
  const res = await adminApi.getUserRoles(row.id)
  selectedRoleIds.value = (res || []).map(r => r.id)
  assignVisible.value = true
}

const openEdit = (row) => {
  editForm.id = row.id
  editForm.username = row.username
  editForm.email = row.email
  editForm.full_name = row.full_name
  editForm.department = row.department
  editForm.position = row.position
  editForm.avatar_url = row.avatar_url
  editForm.password = ''
  editVisible.value = true
}

const submitEdit = async () => {
  try {
    editing.value = true
    const payload = { username: editForm.username, email: editForm.email, full_name: editForm.full_name, department: editForm.department, position: editForm.position, avatar_url: editForm.avatar_url }
    if (editForm.password) payload.password = editForm.password
    if (adminApi && typeof adminApi.updateUser === 'function') {
      await adminApi.updateUser(editForm.id, payload)
    } else {
      await request.put(`/users/${editForm.id}`, payload)
    }
    ElMessage.success('保存成功')
    editVisible.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    editing.value = false
  }
}

const disableUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定停用用户“${row.username}”？`, '确认', { type: 'warning' })
    if (adminApi && typeof adminApi.disableUser === 'function') {
      await adminApi.disableUser(row.id)
    } else {
      await request.delete(`/users/${row.id}`)
    }
    ElMessage.success('已停用')
    await fetchUsers()
  } catch (e) {
    const msg = e?.message || '停用失败'
    ElMessage.error(msg)
  }
}

const enableUser = async (row) => {
  try {
    if (adminApi && typeof adminApi.enableUser === 'function') {
      await adminApi.enableUser(row.id)
    } else {
      await request.put(`/users/${row.id}`, { is_active: true })
    }
    ElMessage.success('已启用')
    await fetchUsers()
  } catch (e) {
    ElMessage.error('启用失败')
  }
}

const submitAssign = async () => {
  try {
    assigning.value = true
    await adminApi.assignUserRoles(currentUser.value.id, selectedRoleIds.value)
    ElMessage.success('分配成功')
    assignVisible.value = false
    await fetchUsers()
  } finally {
    assigning.value = false
  }
}

const handleSizeChange = (size) => { pagination.size = size; pagination.page = 1; fetchUsers() }
const handlePageChange = (page) => { pagination.page = page; fetchUsers() }

onMounted(() => { fetchUsers() })
</script>

<style lang="scss" scoped>
.system-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: float 20s linear infinite;
    pointer-events: none;
  }

  .page-container { flex: 1; display: flex; flex-direction: column; padding: 20px; max-width: 95%; margin: 0 auto; width: 100%; position: relative; z-index: 1; }

  .page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); padding: 24px; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
  .page-title { margin: 0 0 8px 0; font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; align-items: center; gap: 12px; }
  .page-description { margin: 0; color: #64748b; font-size: 16px; }
  .header-actions .el-button.el-button--primary { background: linear-gradient(135deg, #667eea, #764ba2); border: none; color: #fff; }

  .main-content { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }

  .list-card { background: rgba(255,255,255,0.95); border-radius: 16px; }
  .list-header { display: flex; justify-content: space-between; align-items: center; }
  .list-title { display: flex; align-items: center; gap: 6px; font-weight: 600; }
  .mr8 { margin-right: 8px; }
}

@keyframes float { 0% { transform: translate(0,0) rotate(0deg) } 33% { transform: translate(30px,-30px) rotate(120deg) } 66% { transform: translate(-20px,20px) rotate(240deg) } 100% { transform: translate(0,0) rotate(360deg) } }
</style>