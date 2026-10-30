<template>
  <div class="page" style="max-width: 720px">
    <div class="page-head">
      <div>
        <h1 class="page-title">个人设置</h1>
        <p class="page-sub">修改密码后当前登录状态立即失效，需要使用新密码重新登录。</p>
      </div>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h2 class="panel-title">账号信息</h2>
      </div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ ROLE_LABEL[user?.role] || user?.role }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ user?.email || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(user?.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2 class="panel-title">修改密码</h2>
        <span class="panel-hint">8 至 64 位，至少包含字母与数字</span>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 420px">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">保存并重新登录</el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/auth'
import { authStore, clearSession } from '@/stores/auth'
import { formatDateTime, ROLE_LABEL } from '@/stores/dict'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)
const user = authStore.user
const form = reactive({ old_password: '', new_password: '', confirm: '' })

const rules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '长度需在 8 至 64 之间', trigger: 'blur' }
  ],
  confirm: [
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) callback(new Error('两次输入的新密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await changePassword({ old_password: form.old_password, new_password: form.new_password })
    ElMessage.success('密码已修改，请重新登录')
    clearSession()
    router.replace('/login')
  } finally {
    submitting.value = false
  }
}
</script>
