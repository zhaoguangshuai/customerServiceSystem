<template>
  <div>
    <!-- Stats cards -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>待质检</span></template>
          <div class="stat-value warning">{{ reviewStats.pending }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>已质检</span></template>
          <div class="stat-value success">{{ reviewStats.reviewed }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>已标记</span></template>
          <div class="stat-value danger">{{ reviewStats.flagged }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>平均评分</span></template>
          <div class="stat-value primary">{{ reviewStats.avg_score || '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Main table -->
    <el-card>
      <template #header>
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
          <span>对话质检</span>
          <el-select v-model="filters.tenant_id" placeholder="租户筛选" clearable style="width: 160px" @change="fetchReviews">
            <el-option v-for="t in tenants" :key="t.tenant_id" :label="t.tenant_name" :value="t.tenant_id" />
          </el-select>
          <el-select v-model="filters.review_status" placeholder="质检状态" clearable style="width: 140px" @change="fetchReviews">
            <el-option label="待质检" value="pending" />
            <el-option label="已质检" value="reviewed" />
            <el-option label="已标记" value="flagged" />
          </el-select>
          <el-button type="primary" @click="fetchReviews">查询</el-button>
        </div>
      </template>

      <el-table :data="reviews" v-loading="loading" stripe @row-click="showDetail">
        <el-table-column prop="tenant_id" label="租户" width="100" />
        <el-table-column prop="user_id" label="用户" width="100" />
        <el-table-column prop="user_query" label="用户提问" show-overflow-tooltip min-width="160" />
        <el-table-column prop="ai_answer" label="AI回答" show-overflow-tooltip min-width="160" />
        <el-table-column prop="intent" label="意图" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="intentTagType(row.intent)">{{ intentLabel(row.intent) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="质检状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.review_status)" size="small">
              {{ statusLabel(row.review_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quality_score" label="评分" width="80">
          <template #default="{ row }">
            <span v-if="row.quality_score">
              <el-icon v-for="i in row.quality_score" :key="i" color="#e6a23c" style="margin-right: 1px"><StarFilled /></el-icon>
            </span>
            <span v-else style="color: #c0c4cc">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.review_status === 'pending'" type="primary" size="small" @click.stop="openReview(row)">质检</el-button>
            <el-button v-if="row.review_status !== 'flagged'" type="danger" size="small" text @click.stop="openFlag(row)">标记</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchReviews"
        />
      </div>
    </el-card>

    <!-- Detail dialog -->
    <el-dialog v-model="showDetailDialog" title="对话详情" width="650px">
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
        <el-descriptions-item label="质检状态">
          <el-tag :type="statusTagType(detail.review_status)" size="small">{{ statusLabel(detail.review_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="质量评分">
          <span v-if="detail.quality_score">
            <el-icon v-for="i in detail.quality_score" :key="i" color="#e6a23c" style="margin-right: 2px"><StarFilled /></el-icon>
            ({{ detail.quality_score }}/5)
          </span>
          <span v-else>未评分</span>
        </el-descriptions-item>
        <el-descriptions-item label="质检备注">{{ detail.review_comment || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button v-if="detail.review_status === 'pending'" type="primary" @click="showDetailDialog = false; openReview(detail)">质检</el-button>
      </template>
    </el-dialog>

    <!-- Review dialog -->
    <el-dialog v-model="showReviewDialog" title="质检评分" width="500px">
      <el-form label-width="80px">
        <el-form-item label="用户提问">
          <div>{{ reviewTarget.user_query }}</div>
        </el-form-item>
        <el-form-item label="AI回答">
          <div>{{ reviewTarget.ai_answer }}</div>
        </el-form-item>
        <el-form-item label="质量评分" required>
          <el-rate v-model="reviewForm.quality_score" :max="5" show-text :texts="['很差', '较差', '一般', '较好', '很好']" />
        </el-form-item>
        <el-form-item label="质检备注">
          <el-input v-model="reviewForm.review_comment" type="textarea" :rows="3" placeholder="填写质检备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="primary" @click="submitReviewAction" :disabled="!reviewForm.quality_score">提交</el-button>
      </template>
    </el-dialog>

    <!-- Flag dialog -->
    <el-dialog v-model="showFlagDialog" title="标记问题" width="500px">
      <el-form label-width="80px">
        <el-form-item label="用户提问">
          <div>{{ flagTarget.user_query }}</div>
        </el-form-item>
        <el-form-item label="AI回答">
          <div>{{ flagTarget.ai_answer }}</div>
        </el-form-item>
        <el-form-item label="标记原因" required>
          <el-input v-model="flagForm.reason" type="textarea" :rows="3" placeholder="请说明标记原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFlagDialog = false">取消</el-button>
        <el-button type="danger" @click="flagReviewAction" :disabled="!flagForm.reason">标记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { StarFilled } from '@element-plus/icons-vue'
import { listReviews, submitReview, flagReview, getReviewStats, listTenants } from '../../api/admin'

const tenants = ref([])
const reviews = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

const reviewStats = reactive({ total: 0, pending: 0, reviewed: 0, flagged: 0, avg_score: 0 })

const filters = reactive({ tenant_id: '', review_status: '' })

// Detail dialog
const showDetailDialog = ref(false)
const detail = ref({})

// Review dialog
const showReviewDialog = ref(false)
const reviewTarget = ref({})
const reviewForm = reactive({ quality_score: 0, review_comment: '' })

// Flag dialog
const showFlagDialog = ref(false)
const flagTarget = ref({})
const flagForm = reactive({ reason: '' })

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

function statusLabel(status) {
  const map = { pending: '待质检', reviewed: '已质检', flagged: '已标记' }
  return map[status] || status
}

function statusTagType(status) {
  const map = { pending: 'warning', reviewed: 'success', flagged: 'danger' }
  return map[status] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function showDetail(row) {
  detail.value = row
  showDetailDialog.value = true
}

function openReview(row) {
  reviewTarget.value = row
  reviewForm.quality_score = 0
  reviewForm.review_comment = ''
  showReviewDialog.value = true
}

function openFlag(row) {
  flagTarget.value = row
  flagForm.reason = ''
  showFlagDialog.value = true
}

async function fetchReviews() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.tenant_id) params.tenant_id = filters.tenant_id
    if (filters.review_status) params.review_status = filters.review_status
    const res = await listReviews(params)
    reviews.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await getReviewStats()
    Object.assign(reviewStats, res.data)
  } catch { /* ignore */ }
}

async function submitReviewAction() {
  try {
    await submitReview(reviewTarget.value.id, {
      quality_score: reviewForm.quality_score,
      review_comment: reviewForm.review_comment,
    })
    ElMessage.success('质检完成')
    showReviewDialog.value = false
    await fetchReviews()
    await fetchStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  }
}

async function flagReviewAction() {
  try {
    await flagReview(flagTarget.value.id, { reason: flagForm.reason })
    ElMessage.success('已标记')
    showFlagDialog.value = false
    await fetchReviews()
    await fetchStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '标记失败')
  }
}

onMounted(async () => {
  try {
    const res = await listTenants()
    tenants.value = res.data || []
  } catch { /* ignore */ }
  await fetchStats()
  await fetchReviews()
})
</script>

<style scoped>
.stat-value {
  font-size: 36px;
  font-weight: bold;
  text-align: center;
}
.stat-value.primary { color: #409eff; }
.stat-value.success { color: #67c23a; }
.stat-value.warning { color: #e6a23c; }
.stat-value.danger { color: #f56c6c; }
</style>
