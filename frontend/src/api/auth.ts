import { api } from "./client"

const TOKEN_KEY = "pdd_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export async function login(username: string, password: string) {
  const res = await api.post("/auth/login", { username, password })
  const token = res.data.access_token
  setToken(token)
  return token
}

export function logout() {
  clearToken()
  window.location.href = "/login"
}
