import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getCurrentUser } from '../api/admin'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.data.token
    localStorage.setItem('token', res.data.token)
    user.value = res.data.user
    return res
  }

  async function fetchUser() {
    try {
      const res = await getCurrentUser()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, login, fetchUser, logout }
})
