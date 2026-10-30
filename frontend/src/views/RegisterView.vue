<template>
  <div class="auth-wrap">
    <section class="auth-brand">
      <div>
        <div class="brand-sub" style="color: #9fc4b9">软件工程实践 · 课程大作业</div>
        <h1>{{ pageTitle }}</h1>
        <p v-if="roleKey === 'TEACHER'">
          教师账号需要课程组发放的邀请码。邀请码由部署方在环境变量中配置，
          未配置时本入口自动关闭。
        </p>
        <p v-else-if="roleKey === 'ADMIN'">
          管理员账号可管理用户、课程与数据导出，注册需要独立的管理员邀请码。
          邀请码未配置时本入口自动关闭，账号只能由初始化脚本创建。
        </p>
        <p v-else>
          注册后即可在教师安排的课堂进行中提交表情反馈，并查看本人的历史记录。
          学生账号只能查看本人数据。
        </p>
      </div>
      <div class="brand-sub" style="color: #7fa79b">口令要求：8 至 64 位，至少包含字母与数字</div>
    </section>

    <section class="auth-form">
      <div class="auth-card">
        <h2>{{ registerTitle }}</h2>
        <p class="sub">用户名以字母开头，可包含字母、数字与下划线。</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" placeholder="例如 stu2021009" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" size="large" show-password />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" size="large" show-password />
          </el-form-item>
          <el-form-item label="邮箱，可选" prop="email">
            <el-input v-model="form.email" size="large" placeholder="仅记录，不用于找回密码" />
          </el-form-item>
          <el-form-item v-if="roleKey !== 'STUDENT'" :label="inviteLabel" prop="inviteCode">
            <el-input v-model="form.inviteCode" size="large" placeholder="向课程组索取" />
          </el-form-item>

          <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
            注册
          </el-button>
        </el-form>

        <div class="auth-foot">
          <router-link to="/login">返回登录</router-link>
          <router-link v-for="item in otherRoles" :key="item.path" :to="item.path">
            {{ item.label }}
          </router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const roleKey = computed(() => {
  if (route.meta.admin) return 'ADMIN'
  if (route.meta.teacher) return 'TEACHER'
  return 'STUDENT'
})

const TITLES = {
  STUDENT: { page: '学生账号注册', card: '学生注册', invite: '' },
  TEACHER: { page: '教师账号开通', card: '教师注册', invite: '教师邀请码' },
  ADMIN: { page: '管理员账号开通', card: '管理员注册', invite: '管理员邀请码' }
}
const pageTitle = computed(() => TITLES[roleKey.value].page)
const registerTitle = computed(() => TITLES[roleKey.value].card)
const inviteLabel = computed(() => TITLES[roleKey.value].invite)

const ROLE_LINKS = [
  { key: 'STUDENT', path: '/register', label: '学生注册' },
  { key: 'TEACHER', path: '/register/teacher', label: '教师注册' },
  { key: 'ADMIN', path: '/register/admin', label: '管理员注册' }
]
const otherRoles = computed(() => ROLE_LINKS.filter((item) => item.key !== roleKey.value))

const form = reactive({
  username: '',
  password: '',
  confirm: '',
  email: '',
  inviteCode: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/, message: '以字母开头，3 至 32 位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '长度需在 8 至 64 个字符之间', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  inviteCode: [{ required: true, message: '请输入邀请码', trigger: 'blur' }]
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const payload = {
      username: form.username.trim(),
      password: form.password,
      email: form.email.trim() || null
    }
    if (roleKey.value !== 'STUDENT') {
      payload.role = roleKey.value
      payload.invite_code = form.inviteCode.trim()
    }
    const user = await register(payload)
    ElMessage.success(`账号 ${user.username} 注册成功，请登录`)
    router.replace('/login')
  } finally {
    loading.value = false
  }
}
</script>
