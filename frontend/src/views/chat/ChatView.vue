<template>
  <div class="chat-container">
    <!-- Top Bar -->
    <el-card class="chat-config" shadow="never">
      <el-form :inline="true" size="default">
        <el-form-item label="租户">
          <el-select
            v-model="tenantId"
            placeholder="选择租户"
            style="width: 200px"
            @change="onTenantChange"
          >
            <el-option
              v-for="t in tenants"
              :key="t.tenant_id"
              :label="t.tenant_name"
              :value="t.tenant_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用户ID">
          <el-input v-model="userId" placeholder="user_id" style="width: 160px" />
        </el-form-item>
        <el-form-item label="会话ID">
          <el-tag>{{ sessionId }}</el-tag>
        </el-form-item>
        <el-form-item>
          <el-button type="warning" @click="clearChat">清空对话</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Message Area -->
    <div class="message-area" ref="messageAreaRef">
      <div v-if="messages.length === 0" class="empty-hint">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>选择租户后输入消息开始对话测试</p>
      </div>
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message-row"
        :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'"
      >
        <div class="message-bubble">
          <div class="message-role">{{ msg.role === 'user' ? '用户' : 'AI客服' }}</div>
          <div class="message-text" v-html="formatMessage(msg.content)"></div>
          <div v-if="msg.role === 'ai' && msg.sources && msg.sources.length" class="message-sources">
            <el-tag v-for="s in msg.sources" :key="s" size="small" type="info">{{ s }}</el-tag>
          </div>
          <div v-if="msg.role === 'ai' && msg.need_manual" class="message-handoff">
            <el-tag size="small" type="danger">转人工: {{ msg.manual_reason }}</el-tag>
          </div>
        </div>
      </div>
      <div v-if="loading" class="message-row msg-ai">
        <div class="message-bubble">
          <div class="message-role">AI客服</div>
          <div class="message-text typing">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        placeholder="输入消息，按 Enter 发送（Shift+Enter 换行）"
        :disabled="!tenantId || loading"
        @keydown="handleKeydown"
      />
      <el-button
        type="primary"
        :disabled="!tenantId || !inputText.trim() || loading"
        :loading="loading"
        @click="sendMessage"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { listTenants, sendChatMessage } from '../../api/admin'

const tenants = ref([])
const tenantId = ref('')
const userId = ref('admin_test_user')
const sessionId = ref('')
const inputText = ref('')
const messages = ref([])
const loading = ref(false)
const messageAreaRef = ref(null)

function generateSessionId() {
  return `admin_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

onMounted(async () => {
  sessionId.value = generateSessionId()
  try {
    const res = await listTenants()
    tenants.value = res?.data || res || []
    if (tenants.value.length > 0) {
      tenantId.value = tenants.value[0].tenant_id
    }
  } catch (e) {
    console.error('Failed to load tenants:', e)
  }
})

function onTenantChange() {
  clearChat()
}

function clearChat() {
  messages.value = []
  sessionId.value = generateSessionId()
}

function scrollToBottom() {
  nextTick(() => {
    if (messageAreaRef.value) {
      messageAreaRef.value.scrollTop = messageAreaRef.value.scrollHeight
    }
  })
}

function formatMessage(text) {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || !tenantId.value || loading.value) return

  messages.value.push({ role: 'user', content: query })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await sendChatMessage(tenantId.value, userId.value, sessionId.value, query)
    const data = res?.data || res
    messages.value.push({
      role: 'ai',
      content: data.answer || '抱歉，暂时无法回答。',
      sources: data.sources || [],
      need_manual: data.need_manual || false,
      manual_reason: data.manual_reason || '',
    })
  } catch (e) {
    messages.value.push({
      role: 'ai',
      content: '请求失败：' + (e.message || '未知错误'),
      sources: [],
      need_manual: true,
      manual_reason: '系统异常',
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 160px);
}

.chat-config {
  margin-bottom: 12px;
}

.chat-config :deep(.el-card__body) {
  padding: 12px 16px;
}

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  margin-bottom: 12px;
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
}

.message-row {
  display: flex;
  margin-bottom: 16px;
}

.msg-user {
  justify-content: flex-end;
}

.msg-ai {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 8px;
  word-break: break-word;
  line-height: 1.6;
}

.msg-user .message-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 2px;
}

.msg-ai .message-bubble {
  background: #f4f4f5;
  color: #303133;
  border-bottom-left-radius: 2px;
}

.message-role {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 4px;
}

.msg-user .message-role {
  text-align: right;
}

.message-text {
  font-size: 14px;
}

.message-sources {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.message-handoff {
  margin-top: 6px;
}

.typing {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 20px;
}

.dot {
  width: 6px;
  height: 6px;
  background: #909399;
  border-radius: 50%;
  animation: blink 1.4s infinite both;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

.input-area {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-area .el-textarea {
  flex: 1;
}

.input-area .el-button {
  height: 56px;
}
</style>
