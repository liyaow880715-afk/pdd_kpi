import axios from "axios"
import { getToken, logout } from "./auth"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  paramsSerializer: (params) => {
    const parts: string[] = []
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined) continue
      if (Array.isArray(value)) {
        value.forEach((v) => parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(v))}`))
      } else {
        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
      }
    }
    return parts.join("&")
  },
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function stringifyDetail(detail: any): string {
  if (detail === null || detail === undefined) return ""
  if (typeof detail === "string") return detail
  if (typeof detail === "object") {
    if (detail.msg) return String(detail.msg)
    if (detail.message) return String(detail.message)
    try {
      return JSON.stringify(detail)
    } catch {
      return String(detail)
    }
  }
  return String(detail)
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      logout()
    }
    const detail = err.response?.data?.detail
    const msg = stringifyDetail(detail) || err.message || "请求失败"
    return Promise.reject(new Error(msg))
  }
)

export type Store = {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export type ImportRecord = {
  date: string
  store_name: string
  store_safe: string
  saved_at: string
  product_rows: number
  style_rows: number
  order_rows: number
  promo_file: string
  order_file: string
}

export type Kpis = Record<string, number | null>

export type AnalysisData = {
  product_metrics: Record<string, any>[]
  style_metrics: Record<string, any>[]
  kpis: Kpis
}

export type Cost = {
  merchant_code: string
  product_name: string
  product_cost: number
  logistics_cost: number
}

export async function getHealth() {
  const res = await api.get("/health")
  return res.data
}

export async function getStores() {
  const res = await api.get<Store[]>("/stores")
  return res.data
}

export async function createStore(name: string) {
  const res = await api.post<Store>("/stores", { name })
  return res.data
}

export async function renameStore(id: string, newName: string) {
  const res = await api.patch<Store>(`/stores/${id}`, { new_name: newName })
  return res.data
}

export async function deleteStore(id: string) {
  const res = await api.delete(`/stores/${id}`)
  return res.data
}

export async function importData(formData: FormData) {
  const res = await api.post("/imports", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data
}

export async function getRecords(storeName?: string) {
  const res = await api.get<ImportRecord[]>("/imports/records", {
    params: storeName ? { store_name: storeName } : {},
  })
  return res.data
}

export async function deleteRecord(storeName: string, date: string) {
  const res = await api.delete(`/imports/records/${storeName}/${date}`)
  return res.data
}

export async function getAnalysis(storeName: string, startDate: string, endDate: string) {
  const res = await api.get<AnalysisData>("/metrics/analysis", {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getTrend(storeNames: string[], startDate: string, endDate: string) {
  const res = await api.get("/metrics/trend", {
    params: { store_names: storeNames, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getOrders(storeName: string, date: string) {
  const res = await api.get("/orders", { params: { store_name: storeName, date } })
  return res.data
}

export async function saveMerchantMapping(storeName: string, productId: string, merchantCode: string) {
  const res = await api.post("/orders/mappings", { store_name: storeName, product_id: productId, merchant_code: merchantCode })
  return res.data
}

export async function getCosts(storeName: string) {
  const res = await api.get<Cost[]>("/costs", { params: { store_name: storeName } })
  return res.data
}

export async function saveCosts(storeName: string, costs: Cost[]) {
  const res = await api.post("/costs", { store_name: storeName, costs })
  return res.data
}

export async function refreshCostCodes(storeName: string) {
  const res = await api.post("/costs/refresh", null, { params: { store_name: storeName } })
  return res.data
}

export async function getGlobalCosts() {
  const res = await api.get<Cost[]>("/costs/global")
  return res.data
}

export async function saveGlobalCosts(costs: Cost[]) {
  const res = await api.post("/costs/global", { costs })
  return res.data
}

export async function refreshGlobalCostCodes() {
  const res = await api.post("/costs/global/refresh")
  return res.data
}

export async function getUnmappedProducts() {
  const res = await api.get("/costs/global/unmapped")
  return res.data
}

export async function mapProductToMerchantCode(productId: string, merchantCode: string, styleId?: string) {
  const res = await api.post("/costs/global/map", { product_id: productId, merchant_code: merchantCode, style_id: styleId })
  return res.data
}

export async function getAiConfig() {
  const res = await api.get("/ai/config")
  return res.data
}

export async function updateAiConfig(config: Record<string, any>) {
  const res = await api.post("/ai/config", config)
  return res.data
}

export async function testAi(config: Record<string, any>) {
  const res = await api.post("/ai/test", config)
  return res.data
}

export async function generateAiReport(storeName: string, startDate: string, endDate: string, config: Record<string, any>) {
  const res = await api.post("/ai/report", { store_name: storeName, start_date: startDate, end_date: endDate, config })
  return res.data
}

export async function getWecomConfig() {
  const res = await api.get("/wecom/config")
  return res.data
}

export async function updateWecomConfig(config: Record<string, any>) {
  const res = await api.post("/wecom/config", config)
  return res.data
}

export async function sendWecomReport(reportDate: string, config: Record<string, any>) {
  const res = await api.post("/wecom/send", { report_date: reportDate, config })
  return res.data
}
