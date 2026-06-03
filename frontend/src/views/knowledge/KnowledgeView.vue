<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; gap: 12px; align-items: center">
            <span>知识库文档</span>
            <el-select v-model="selectedTenant" placeholder="选择租户" clearable style="width: 200px" @change="fetchDocs">
              <el-option v-for="t in tenants" :key="t.tenant_id" :label="t.tenant_name" :value="t.tenant_id" />
            </el-select>
          </div>
          <el-upload
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadData"
            :show-file-list="false"
            :before-upload="beforeUpload"
            :on-success="onUploadSuccess"
            :on-error="onUploadError"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.md,.txt"
          >
            <el-button type="primary" :disabled="!selectedTenant">
              <el-icon><Upload /></el-icon> 上传文档
            </el-button>
          </el-upload>
        </div>
      </template>

      <el-table :data="docs" v-loading="loading" stripe>
        <el-table-column prop="title" label="文档名称" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type?.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '有效' : '已删除' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-popconfirm title="确定删除该文档？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" text size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listKnowledge, deleteKnowledge, listTenants } from '../../api/admin'

const tenants = ref([])
const selectedTenant = ref('')
const docs = ref([])
const loading = ref(false)

const uploadUrl = '/api/v1/jewelry/knowledge/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
}))
const uploadData = computed(() => ({
  tenant_id: selectedTenant.value,
  category: 'general',
}))

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchDocs() {
  if (!selectedTenant.value) {
    docs.value = []
    return
  }
  loading.value = true
  try {
    const res = await listKnowledge(selectedTenant.value)
    docs.value = res.data || []
  } finally {
    loading.value = false
  }
}

function beforeUpload(file) {
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件不能超过10MB')
    return false
  }
  return true
}

function onUploadSuccess(res) {
  ElMessage.success('上传成功')
  fetchDocs()
}

function onUploadError() {
  ElMessage.error('上传失败')
}

async function handleDelete(docId) {
  try {
    await deleteKnowledge(docId, selectedTenant.value)
    ElMessage.success('删除成功')
    await fetchDocs()
  } catch { /* handled by interceptor */ }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
})
</script>
