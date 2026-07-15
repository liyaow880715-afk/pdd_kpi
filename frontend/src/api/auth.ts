import { api } from "./client"

const TOKEN_KEY = "pdd_token"

export type UserInfo = {
  username: string
  role: "master" | "sub"
  allowed_stores: string[]
  allowed_pages: string[]
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
    allowed_pages: payload.allowed_pages || [],
  }
}

export function isMaster(): boolean {
  return getCurrentUser()?.role === "master"
}

export type LoginResult = {
  token: string
  requirePasswordChange: boolean
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const res = await api.post("/auth/login", { username, password })
  const token = res.data.access_token
  setToken(token)
  return {
    token,
    requirePasswordChange: res.data.require_password_change === true,
  }
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<string> {
  const res = await api.post("/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  })
  const token = res.data.access_token
  if (token) {
    setToken(token)
  }
  return token
}

export async function getMe() {
  const res = await api.get<UserInfo & { require_password_change?: boolean }>("/auth/me")
  return res.data
}

export function canAccessPage(page: string): boolean {
  const user = getCurrentUser()
  if (!user) return false
  if (user.role === "master") return true
  return user.allowed_pages.includes(page)
}

export function logout() {
  clearToken()
  window.location.href = "/login"
}
