<template>
  <div class="auth-wrap">
    <section class="auth-brand">
      <div>
        <div class="brand-sub" style="color: #9fc4b9">软件工程实践 · 课程大作业</div>
        <h1>表情符号课堂情绪检查器</h1>
        <p>
          学生在课堂上主动记录当下感受，摄像头侧的分析进程仅上报匿名表情分类结果，
          教师据此观察课堂反馈的分布与变化，管理员完成排课、统计与导出。
        </p>
        <ul>
          <li>手动反馈与 AI 观察分区呈现，不合并为单一情绪得分</li>
          <li>权限按角色与数据归属双重校验</li>
          <li>默认不保存原始人脸图像与视频</li>
        </ul>
      </div>
      <div class="brand-sub" style="color: #7fa79b">2026 年秋季学期</div>
    </section>

    <section class="auth-form">
      <div class="auth-card">
        <h2>登录</h2>
        <p class="sub">使用课程账号进入系统，登录后按角色进入对应工作台。</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              size="large"
              show-password
              placeholder="请输入密码"
              autocomplete="current-password"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
            登录
          </el-button>
        </el-form>

        <div class="auth-foot">
          <router-link to="/register">学生注册</router-link>
          <router-link to="/register/teacher">教师注册</router-link>
        </div>

        <div class="demo-accounts">
          演示账号：管理员 admin / Admin@2026；教师 teacher_zhang / Emoji@2026；
          学生 stu2021001 / Emoji@2026。首次部署请执行初始化脚本修改默认口令。
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { homeFor, setSession } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const data = await login({ username: form.username.trim(), password: form.password })
    setSession(data.access_token, data.user)
    ElMessage.success(`欢迎，${data.user.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.replace(redirect || homeFor(data.user.role))
  } finally {
    loading.value = false
  }
}
</script>
