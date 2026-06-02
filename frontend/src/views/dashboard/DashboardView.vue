<template>
  <div>
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>租户数量</span></template>
          <div class="stat-value">{{ stats.tenant_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>知识文档</span></template>
          <div class="stat-value">{{ stats.doc_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>今日对话</span></template>
          <div class="stat-value">{{ stats.today_chats }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>转人工率</span></template>
          <div class="stat-value">{{ stats.handoff_rate }}%</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>总对话数</span></template>
          <div class="stat-value accent">{{ stats.total_chats }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>Token 消耗</span></template>
          <div class="stat-value accent">{{ formatNumber(stats.total_tokens) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>独立用户</span></template>
          <div class="stat-value accent">{{ stats.unique_users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>转人工次数</span></template>
          <div class="stat-value accent">{{ handoffCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="14">
        <el-card>
          <template #header><span>近7天对话趋势</span></template>
          <div ref="trendChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header><span>意图分布</span></template>
          <div ref="pieChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header><span>快速操作</span></template>
          <el-space wrap>
            <el-button type="primary" @click="$router.push('/tenants')">管理租户</el-button>
            <el-button type="success" @click="$router.push('/knowledge')">上传知识库</el-button>
            <el-button type="warning" @click="$router.push('/prompts')">配置提示词</el-button>
            <el-button @click="$router.push('/chatlogs')">查看对话</el-button>
          </el-space>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>最近对话</span></template>
          <el-table :data="recentLogs" size="small" max-height="300">
            <el-table-column prop="user_id" label="用户" width="120" />
            <el-table-column prop="user_query" label="问题" show-overflow-tooltip />
            <el-table-column prop="intent" label="意图" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ intentLabel(row.intent) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="need_manual" label="转人工" width="80">
              <template #default="{ row }">
                <el-tag :type="row.need_manual ? 'danger' : 'success'" size="small">
                  {{ row.need_manual ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getStatistics, listChatLogs } from '../../api/admin'

const stats = reactive({
  tenant_count: 0,
  doc_count: 0,
  today_chats: 0,
  total_chats: 0,
  handoff_rate: 0,
  total_tokens: 0,
  unique_users: 0,
  daily_trend: [],
  intent_distribution: [],
})
const recentLogs = ref([])

const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart = null
let pieChart = null

const handoffCount = computed(() => {
  if (stats.total_chats === 0) return 0
  return Math.round((stats.handoff_rate / 100) * stats.total_chats)
})

const INTENT_LABELS = {
  product_inquiry: '产品咨询',
  complaint: '投诉',
  price_negotiation: '议价',
  custom_order: '定制',
  general: '通用',
}

function intentLabel(intent) {
  return INTENT_LABELS[intent] || intent || '通用'
}

function formatNumber(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function renderTrendChart(data) {
  if (!trendChartRef.value || data.length === 0) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, bottom: 30, top: 20 },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.date),
      axisLabel: { formatter: (v) => v.slice(5) },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'line',
        data: data.map((d) => d.count),
        smooth: true,
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#409eff' },
      },
    ],
  })
}

function renderPieChart(data) {
  if (!pieChartRef.value || data.length === 0) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, orient: 'horizontal' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        data: data.map((d) => ({
          name: intentLabel(d.intent),
          value: d.count,
        })),
        label: { formatter: '{b}\n{d}%' },
      },
    ],
  })
}

onMounted(async () => {
  try {
    const res = await getStatistics()
    Object.assign(stats, res.data)
    await nextTick()
    renderTrendChart(stats.daily_trend)
    renderPieChart(stats.intent_distribution)
  } catch { /* ignore */ }

  try {
    const logRes = await listChatLogs({ page: 1, page_size: 10 })
    recentLogs.value = logRes.data?.items || []
  } catch { /* ignore */ }

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}
</script>

<style scoped>
.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
  text-align: center;
}
.stat-value.accent {
  color: #67c23a;
}
</style>
