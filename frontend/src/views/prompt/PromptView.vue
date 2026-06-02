<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; gap: 12px; align-items: center">
          <span>提示词配置</span>
          <el-select v-model="selectedTenant" placeholder="选择租户" style="width: 200px" @change="fetchPrompt">
            <el-option v-for="t in tenants" :key="t.tenant_id" :label="t.tenant_name" :value="t.tenant_id" />
          </el-select>
        </div>
      </template>

      <div v-if="!selectedTenant" style="text-align: center; padding: 60px; color: #999">
        请先选择一个租户
      </div>

      <template v-else>
        <el-input
          v-model="systemPrompt"
          type="textarea"
          :rows="16"
          placeholder="输入该租户的系统提示词..."
          style="margin-bottom: 16px"
        />
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="color: #999; font-size: 13px">
            提示词将作为AI客服的系统指令，控制其回答风格和行为
          </span>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listTenants, getPrompt, updatePrompt } from '../../api/admin'

const tenants = ref([])
const selectedTenant = ref('')
const systemPrompt = ref('')
const saving = ref(false)

async function fetchPrompt() {
  if (!selectedTenant.value) return
  try {
    const res = await getPrompt(selectedTenant.value)
    systemPrompt.value = res.data?.system_prompt || ''
  } catch { /* ignore */ }
}

async function handleSave() {
  saving.value = true
  try {
    await updatePrompt(selectedTenant.value, { system_prompt: systemPrompt.value })
    ElMessage.success('保存成功')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
})
</script>
