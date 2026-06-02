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
          <el-button type="primary" :disabled="!selectedTenant" @click="openCreate">
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
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除该FAQ？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" text size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create dialog -->
    <el-dialog v-model="showCreate" title="新增FAQ" width="600px">
      <el-form ref="createFormRef" :model="form" :rules="rules" label-width="80px">
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

    <!-- Edit dialog -->
    <el-dialog v-model="showEdit" title="编辑FAQ" width="600px">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="80px">
        <el-form-item label="问题" prop="title">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="回答" prop="answer">
          <el-input v-model="editForm.answer" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="editForm.category" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort" :min="0" :max="9999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listTenants, listFaqs, createFaq, updateFaq, deleteFaq } from '../../api/admin'

const tenants = ref([])
const selectedTenant = ref('')
const faqs = ref([])
const loading = ref(false)
const showCreate = ref(false)
const showEdit = ref(false)
const submitting = ref(false)
const createFormRef = ref()
const editFormRef = ref()

const form = reactive({ title: '', answer: '', category: '', sort: 0 })
const editForm = reactive({ id: 0, title: '', answer: '', category: '', sort: 0 })

const rules = {
  title: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  answer: [{ required: true, message: '请输入回答', trigger: 'blur' }],
}
const editRules = {
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

function openCreate() {
  form.title = ''
  form.answer = ''
  form.category = ''
  form.sort = 0
  showCreate.value = true
}

function openEdit(row) {
  editForm.id = row.id
  editForm.title = row.title
  editForm.answer = row.answer
  editForm.category = row.category || ''
  editForm.sort = row.sort || 0
  showEdit.value = true
}

async function handleCreate() {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createFaq({ ...form, tenant_id: selectedTenant.value })
    ElMessage.success('创建成功')
    showCreate.value = false
    await fetchFaqs()
  } finally {
    submitting.value = false
  }
}

async function handleEdit() {
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await updateFaq(editForm.id, {
      title: editForm.title,
      answer: editForm.answer,
      category: editForm.category,
      sort: editForm.sort,
    })
    ElMessage.success('更新成功')
    showEdit.value = false
    await fetchFaqs()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(faqId) {
  try {
    await deleteFaq(faqId)
    ElMessage.success('删除成功')
    await fetchFaqs()
  } catch { /* handled by interceptor */ }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
})
</script>
