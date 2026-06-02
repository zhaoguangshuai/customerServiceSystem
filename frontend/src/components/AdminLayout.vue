<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background: #304156">
      <div class="logo">
        <el-icon :size="24" color="#409eff"><Gem /></el-icon>
        <span>珠宝AI客服</span>
      </div>
      <el-menu
        :default-active="route.path"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/tenants">
          <el-icon><OfficeBuilding /></el-icon>
          <span>租户管理</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Document /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/prompts">
          <el-icon><EditPen /></el-icon>
          <span>提示词配置</span>
        </el-menu-item>
        <el-menu-item index="/chatlogs">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话日志</span>
        </el-menu-item>
        <el-menu-item index="/faqs">
          <el-icon><QuestionFilled /></el-icon>
          <span>FAQ管理</span>
        </el-menu-item>
        <el-menu-item index="/reviews">
          <el-icon><Checked /></el-icon>
          <span>质检中心</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee">
        <h3 style="margin: 0">{{ route.meta.title }}</h3>
        <div style="display: flex; align-items: center; gap: 16px">
          <span>{{ auth.user?.username || '管理员' }}</span>
          <el-button type="danger" text @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main style="background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../utils/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  if (!auth.user) {
    auth.fetchUser()
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
