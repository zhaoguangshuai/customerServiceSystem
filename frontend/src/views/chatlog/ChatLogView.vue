<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
          <span>对话日志</span>
          <el-select v-model="filters.tenant_id" placeholder="租户筛选" clearable style="width: 160px" @change="fetchLogs">
            <el-option v-for="t in tenants" :key="t.tenant_id" :label="t.tenant_name" :value="t.tenant_id" />
          </el-select>
          <el-input v-model="filters.user_id" placeholder="用户ID" clearable style="width: 140px" @clear="fetchLogs" @keyup.enter="fetchLogs" />
          <el-input v-model="filters.keyword" placeholder="关键词搜索" clearable style="width: 160px" @clear="fetchLogs" @keyup.enter="fetchLogs" />
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="fetchLogs"
          />
          <el-button type="primary" @click="fetchLogs">查询</el-button>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" stripe @row-click="showDetailDialog">
        <el-table-column prop="tenant_id" label="租户" width="100" />
        <el-table-column prop="user_id" label="用户" width="100" />
        <el-table-column prop="user_query" label="用户提问" show-overflow-tooltip min-width="160" />
        <el-table-column prop="ai_answer" label="AI回答" show-overflow-tooltip min-width="160" />
        <el-table-column prop="intent" label="意图" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="intentTagType(row.intent)">{{ intentLabel(row.intent) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="need_manual" label="转人工" width="70">
          <template #default="{ row }">
            <el-tag :type="row.need_manual ? 'danger' : 'success'" size="small">
              {{ row.need_manual ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="used_tokens" label="Token" width="70" />
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <!-- Detail dialog -->
    <el-dialog v-model="showDetail" title="对话详情" width="650px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="租户">{{ detail.tenant_id }}</el-descriptions-item>
        <el-descriptions-item label="用户">{{ detail.user_id }}</el-descriptions-item>
        <el-descriptions-item label="会话">{{ detail.session_id }}</el-descriptions-item>
        <el-descriptions-item label="用户提问">{{ detail.user_query }}</el-descriptions-item>
        <el-descriptions-item label="AI回答">{{ detail.ai_answer }}</el-descriptions-item>
        <el-descriptions-item label="意图">
          <el-tag size="small" :type="intentTagType(detail.intent)">{{ intentLabel(detail.intent) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="转人工">
          <el-tag :type="detail.need_manual ? 'danger' : 'success'" size="small">
            {{ detail.need_manual ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="转人工原因">{{ detail.manual_reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Token消耗">{{ detail.used_tokens }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { listChatLogs, listTenants } from '../../api/admin'

const tenants = ref([])
const logs = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const showDetail = ref(false)
const detail = ref({})

const filters = reactive({ tenant_id: '', user_id: '', keyword: '', dateRange: null })

const INTENT_LABELS = {
  product_inquiry: '产品咨询',
  complaint: '投诉',
  price_negotiation: '议价',
  custom_order: '定制',
  general: '通用',
}

const INTENT_TAG_TYPES = {
  product_inquiry: '',
  complaint: 'danger',
  price_negotiation: 'warning',
  custom_order: 'success',
  general: 'info',
}

function intentLabel(intent) {
  return INTENT_LABELS[intent] || intent || '通用'
}

function intentTagType(intent) {
  return INTENT_TAG_TYPES[intent] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function showDetailDialog(row) {
  detail.value = row
  showDetail.value = true
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.tenant_id) params.tenant_id = filters.tenant_id
    if (filters.user_id) params.user_id = filters.user_id
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    const res = await listChatLogs(params)
    logs.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
  await fetchLogs()
})
</script>
