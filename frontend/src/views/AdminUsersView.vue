<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">停用账号不删除数据，历史记录保留；系统至少保留一名启用状态的管理员。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建账号</el-button>
    </div>

    <section class="panel">
      <div class="filter-row">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用户名"
          clearable
          style="width: 200px"
          @keyup.enter="search"
        />
        <el-select v-model="filters.role" placeholder="全部角色" clearable style="width: 150px">
          <el-option label="学生" value="STUDENT" />
          <el-option label="教师" value="TEACHER" />
          <el-option label="管理员" value="ADMIN" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px">
          <el-option label="启用" value="ACTIVE" />
          <el-option label="停用" value="DISABLED" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button text @click="reset">重置</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" empty-text="没有符合条件的账号">
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">{{ ROLE_LABEL[row.role] || row.role }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" effect="light" size="small">
              {{ row.status === 'ACTIVE' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              text
              :type="row.status === 'ACTIVE' ? 'danger' : 'primary'"
              :disabled="row.id === currentUserId"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'ACTIVE' ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="onPage"
        />
      </div>
    </section>

    <el-dialog v-model="dialogVisible" title="新建账号" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="字母开头，3 至 32 位" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位，含字母与数字" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="STUDENT">学生</el-radio>
            <el-radio value="TEACHER">教师</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createUser, listUsers, setUserStatus } from '@/api/admin'
import { authStore } from '@/stores/auth'
import { formatDateTime, ROLE_LABEL } from '@/stores/dict'

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const formRef = ref(null)
const currentUserId = authStore.user?.id

const filters = reactive({ keyword: '', role: null, status: null })
const form = reactive({ username: '', password: '', role: 'STUDENT', email: '' })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/, message: '以字母开头，3 至 32 位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 8, max: 64, message: '长度需在 8 至 64 之间', trigger: 'blur' }
  ]
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.keyword) params.keyword = filters.keyword.trim()
    if (filters.role) params.role = filters.role
    if (filters.status) params.status = filters.status
    const data = await listUsers(params)
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function reset() {
  filters.keyword = ''
  filters.role = null
  filters.status = null
  search()
}

function onPage(value) {
  page.value = value
  load()
}

function openCreate() {
  form.username = ''
  form.password = ''
  form.role = 'STUDENT'
  form.email = ''
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createUser({
      username: form.username.trim(),
      password: form.password,
      role: form.role,
      email: form.email.trim() || null
    })
    ElMessage.success('账号已创建')
    dialogVisible.value = false
    search()
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row) {
  const next = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  const actionText = next === 'ACTIVE' ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}账号 ${row.username} 吗？${next === 'DISABLED' ? '该账号的登录状态会立即失效。' : ''}`,
      `${actionText}账号`,
      { type: 'warning' }
    )
  } catch {
    return
  }
  await setUserStatus(row.id, next)
  ElMessage.success(`已${actionText}`)
  load()
}

onMounted(load)
</script>

<style scoped>
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
