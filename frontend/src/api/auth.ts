import { api } from "./client"

const TOKEN_KEY = "pdd_token"

export type UserInfo = {
  username: string
  role: "master" | "sub"
  allowed_stores: string[]
}

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

function parseJwt(token: string): Record<string, any> | null {
  try {
    const payload = token.split(".")[1]
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function getCurrentUser(): UserInfo | null {
  const token = getToken()
  if (!token) return null
  const payload = parseJwt(token)
  if (!payload) return null
  return {
    username: payload.sub || "",
    role: payload.role || "sub",
    allowed_stores: payload.allowed_stores || [],
  }
}

export function isMaster(): boolean {
  return getCurrentUser()?.role === "master"
}

export async function login(username: string, password: string) {
  const res = await api.post("/auth/login", { username, password })
  const token = res.data.access_token
  setToken(token)
  return token
}

export async function changePassword(oldPassword: string, newPassword: string) {
  const res = await api.post("/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  })
  return res.data
}

export async function getMe() {
  const res = await api.get<UserInfo>("/auth/me")
  return res.data
}

export function logout() {
  clearToken()
  window.location.href = "/login"
}
