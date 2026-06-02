<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>租户列表</span>
          <el-button type="primary" @click="showCreate = true">
            <el-icon><Plus /></el-icon> 新增租户
          </el-button>
        </div>
      </template>

      <el-table :data="tenants" v-loading="loading" stripe>
        <el-table-column prop="tenant_id" label="租户ID" width="150" />
        <el-table-column prop="tenant_name" label="租户名称" />
        <el-table-column prop="contact" label="联系人" width="120" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreate" title="新增租户" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="租户ID" prop="tenant_id">
          <el-input v-model="form.tenant_id" placeholder="唯一标识，如 shop_001" />
        </el-form-item>
        <el-form-item label="租户名称" prop="tenant_name">
          <el-input v-model="form.tenant_name" placeholder="如：周大福深圳店" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
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
import { listTenants, createTenant } from '../../api/admin'

const tenants = ref([])
const loading = ref(false)
const showCreate = ref(false)
const submitting = ref(false)
const formRef = ref()

const form = reactive({ tenant_id: '', tenant_name: '', contact: '', phone: '' })
const rules = {
  tenant_id: [{ required: true, message: '请输入租户ID', trigger: 'blur' }],
  tenant_name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
}

async function fetchTenants() {
  loading.value = true
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createTenant(form)
    ElMessage.success('创建成功')
    showCreate.value = false
    form.tenant_id = ''
    form.tenant_name = ''
    form.contact = ''
    form.phone = ''
    await fetchTenants()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchTenants)
</script>
