import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSession } from '@/api/catalog'
import { submitEmoji } from '@/api/emoji'

/**
 * 学生反馈页的状态与提交逻辑。
 *
 * 学生端按 MVVM 组织：本组合式函数是 ViewModel，View 只绑定模板。
 * sessionId 接受数字或返回数字的函数，便于路由参数变化时复用。
 */
export function useFeedback(sessionId) {
  const session = ref(null)
  const emotion = ref('')
  const submitting = ref(false)
  const lastResult = ref(null)

  const hint = computed(() =>
    emotion.value ? '提交后会立即出现在教师的课堂看板中' : '请先选择一个表情'
  )

  const resolveId = () => Number(typeof sessionId === 'function' ? sessionId() : sessionId)

  function newEventId() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID().replace(/-/g, '')
    return `${Date.now()}${Math.random().toString(16).slice(2, 10)}`
  }

  async function load() {
    session.value = await getSession(resolveId())
  }

  async function submit() {
    if (!emotion.value || submitting.value) return
    submitting.value = true
    try {
      lastResult.value = await submitEmoji({
        event_id: newEventId(),
        session_id: resolveId(),
        emotion: emotion.value
      })
      ElMessage.success('提交成功')
    } finally {
      submitting.value = false
    }
  }

  async function reset() {
    lastResult.value = null
    emotion.value = ''
    await load()
  }

  return { session, emotion, submitting, lastResult, hint, load, submit, reset }
}
