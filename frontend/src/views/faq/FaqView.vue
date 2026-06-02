<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; gap: 12px; align-items: center">
            <span>FAQ管理</span>
            <el-select v-model="selectedTenant" placeholder="选择租户" style="width: 200px" @change="fetchFaqs">
              <el-option v-for="t in tenants" :key="t.tenant_id" :label="t.tenant_name" :value="t.tenant_id" />
            </el-select>
          </div>
          <el-button type="primary" :disabled="!selectedTenant" @click="showCreate = true">
            <el-icon><Plus /></el-icon> 新增FAQ
          </el-button>
        </div>
      </template>

      <div v-if="!selectedTenant" style="text-align: center; padding: 60px; color: #999">
        请先选择一个租户
      </div>

      <el-table v-else :data="faqs" v-loading="loading" stripe>
        <el-table-column prop="title" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="300" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="sort" label="排序" width="80" />
      </el-table>
    </el-card>

    <el-dialog v-model="showCreate" title="新增FAQ" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="问题" prop="title">
          <el-input v-model="form.title" placeholder="常见问题标题" />
        </el-form-item>
        <el-form-item label="回答" prop="answer">
          <el-input v-model="form.answer" type="textarea" :rows="4" placeholder="标准回答内容" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="如：售后、价格、产品" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listTenants, listFaqs, createFaq } from '../../api/admin'

const tenants = ref([])
const selectedTenant = ref('')
const faqs = ref([])
const loading = ref(false)
const showCreate = ref(false)
const submitting = ref(false)
const formRef = ref()

const form = reactive({ title: '', answer: '', category: '', sort: 0 })
const rules = {
  title: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  answer: [{ required: true, message: '请输入回答', trigger: 'blur' }],
}

async function fetchFaqs() {
  if (!selectedTenant.value) {
    faqs.value = []
    return
  }
  loading.value = true
  try {
    const res = await listFaqs(selectedTenant.value)
    faqs.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createFaq({ ...form, tenant_id: selectedTenant.value })
    ElMessage.success('创建成功')
    showCreate.value = false
    form.title = ''
    form.answer = ''
    form.category = ''
    form.sort = 0
    await fetchFaqs()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
})
</script>
