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
  platform: string
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

export async function updateFromGithub() {
  const res = await api.post("/system/update")
  return res.data as { success: boolean; up_to_date?: boolean; message?: string; local?: string; remote?: string; steps: any[] }
}

export async function getStores(platform?: string) {
  const res = await api.get<Store[]>("/stores", { params: platform ? { platform } : {} })
  return res.data
}

export async function createStore(name: string, platform: string = "pdd") {
  const res = await api.post<Store>("/stores", { name, platform })
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

export async function getDashboardSummary(startDate: string, endDate: string, storeNames?: string[]) {
  const params: Record<string, any> = { start_date: startDate, end_date: endDate }
  if (storeNames && storeNames.length > 0) {
    params.store_names = storeNames
  }
  const res = await api.get("/dashboard/summary", { params })
  return res.data as { store_count: number; start_date: string; end_date: string; kpis: Kpis; trend: any[] }
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

export async function mapProductToMerchantCode(productId: string, merchantCode: string, styleId?: string, productName?: string) {
  const res = await api.post("/costs/global/map", {
    product_id: productId,
    merchant_code: merchantCode,
    style_id: styleId,
    product_name: productName,
  })
  return res.data
}

export async function exportGlobalCosts(pendingOnly = false) {
  const res = await api.get(`/costs/global/export${pendingOnly ? "?pending_only=true" : ""}`, {
    responseType: "blob",
  })
  return res.data as Blob
}

export async function importGlobalCosts(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  const res = await api.post("/costs/global/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data as { updated: number }
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

// ---------- 抖音 ----------

export type DouyinCost = {
  merchant_code: string
  product_name: string
  product_cost: number
  logistics_cost: number
  updated_at?: string
}

export type DouyinAnalysisData = {
  product_metrics: Record<string, any>[]
  kpis: Record<string, number | null>
  cost_kpis: Record<string, number | null>
}

export async function importDouyinData(formData: FormData) {
  const res = await api.post("/douyin/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data
}

export async function getDouyinDashboardSummary(startDate: string, endDate: string, storeNames?: string[]) {
  const params: Record<string, any> = { start_date: startDate, end_date: endDate }
  if (storeNames && storeNames.length > 0) {
    params.store_names = storeNames
  }
  const res = await api.get("/douyin/dashboard", { params })
  return res.data as { store_count: number; kpis: Record<string, number | null>; cost_kpis: Record<string, number | null>; trend: any[] }
}

export async function getDouyinAnalysis(storeName: string, startDate: string, endDate: string) {
  const res = await api.get<DouyinAnalysisData>("/douyin/analysis", {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getDouyinTrend(storeName: string, startDate: string, endDate: string) {
  const res = await api.get("/douyin/trend", {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getDouyinAiConfig() {
  const res = await api.get("/douyin/ai/config")
  return res.data
}

export async function updateDouyinAiConfig(config: Record<string, any>) {
  const res = await api.post("/douyin/ai/config", config)
  return res.data
}

export async function testDouyinAi(config: Record<string, any>) {
  const res = await api.post("/douyin/ai/test", config)
  return res.data
}

export async function generateDouyinAiReport(
  storeName: string,
  startDate: string,
  endDate: string,
  config: Record<string, any>
) {
  const res = await api.post("/douyin/ai/report", config, {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getDouyinWecomConfig() {
  const res = await api.get("/douyin/wecom/config")
  return res.data
}

export async function updateDouyinWecomConfig(config: Record<string, any>) {
  const res = await api.post("/douyin/wecom/config", config)
  return res.data
}

export async function sendDouyinWecomReport(reportDate: string, config: Record<string, any>) {
  const res = await api.post("/douyin/wecom/send", config, {
    params: { report_date: reportDate },
  })
  return res.data
}

export async function getDouyinOrders(storeName: string, date: string) {
  const res = await api.get("/douyin/orders", { params: { store_name: storeName, date } })
  return res.data
}

export async function getDouyinCosts() {
  const res = await api.get<DouyinCost[]>("/douyin/costs")
  return res.data
}

export async function saveDouyinCosts(costs: DouyinCost[]) {
  const res = await api.post("/douyin/costs", { costs })
  return res.data
}

export async function refreshDouyinCostCodes() {
  const res = await api.post<{ added: number }>("/douyin/costs/refresh")
  return res.data
}

export async function exportDouyinCosts(pendingOnly: boolean = false) {
  const res = await api.get("/douyin/costs/export", {
    params: pendingOnly ? { pending_only: true } : {},
    responseType: "blob",
  })
  return res.data as Blob
}

export async function importDouyinCosts(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  const res = await api.post("/douyin/costs/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data as { updated: number }
}

export interface DouyinUnmappedRow {
  product_id: string
  product_name: string
  style_id: string
  style_name: string
  store_name: string
  order_count: number
  first_date: string
}

export async function getDouyinUnmappedProducts(startDate?: string, endDate?: string, storeName?: string) {
  const params: Record<string, any> = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  if (storeName) params.store_name = storeName
  const res = await api.get<DouyinUnmappedRow[]>("/douyin/costs/unmapped", { params })
  return res.data
}

export async function mapDouyinProductToMerchantCode(
  productId: string,
  merchantCode: string,
  styleId?: string,
  productName?: string
) {
  const res = await api.post("/douyin/costs/map", {
    product_id: productId,
    merchant_code: merchantCode,
    style_id: styleId,
    product_name: productName,
  })
  return res.data
}

export type DouyinImportRecord = {
  date: string
  store_name: string
  promo_file: string
  order_file: string
  product_rows: number
  order_rows: number
  saved_at?: string
}

export async function getDouyinRecords(storeName?: string) {
  const res = await api.get<DouyinImportRecord[]>("/douyin/records", {
    params: storeName ? { store_name: storeName } : {},
  })
  return res.data
}

export async function deleteDouyinRecord(storeName: string, date: string) {
  const res = await api.delete(`/douyin/records/${storeName}/${date}`)
  return res.data
}

// ---------- 天猫 ----------

export type TmallCost = {
  merchant_code: string
  product_name: string
  product_cost: number
  logistics_cost: number
  updated_at?: string
}

export type TmallAnalysisData = {
  product_metrics: Record<string, any>[]
  kpis: Record<string, number | null>
  cost_kpis: Record<string, number | null>
}

export async function importTmallData(formData: FormData) {
  const res = await api.post("/tmall/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data
}

export async function getTmallDashboardSummary(startDate: string, endDate: string, storeNames?: string[]) {
  const params: Record<string, any> = { start_date: startDate, end_date: endDate }
  if (storeNames && storeNames.length > 0) {
    params.store_names = storeNames
  }
  const res = await api.get("/tmall/dashboard", { params })
  return res.data as { store_count: number; kpis: Record<string, number | null>; cost_kpis: Record<string, number | null>; trend: any[] }
}

export async function getTmallAnalysis(storeName: string, startDate: string, endDate: string) {
  const res = await api.get<TmallAnalysisData>("/tmall/analysis", {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getTmallTrend(storeName: string, startDate: string, endDate: string) {
  const res = await api.get("/tmall/trend", {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getTmallOrders(storeName: string, date: string) {
  const res = await api.get("/tmall/orders", { params: { store_name: storeName, date } })
  return res.data
}

export async function getTmallCosts() {
  const res = await api.get<TmallCost[]>("/tmall/costs")
  return res.data
}

export async function saveTmallCosts(costs: TmallCost[]) {
  const res = await api.post("/tmall/costs", { costs })
  return res.data
}

export async function refreshTmallCostCodes() {
  const res = await api.post<{ added: number }>("/tmall/costs/refresh")
  return res.data
}

export async function exportTmallCosts(pendingOnly: boolean = false) {
  const res = await api.get("/tmall/costs/export", {
    params: pendingOnly ? { pending_only: true } : {},
    responseType: "blob",
  })
  return res.data as Blob
}

export async function importTmallCosts(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  const res = await api.post("/tmall/costs/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data as { updated: number }
}

export interface TmallUnmappedRow {
  product_id: string
  product_name: string
  style_id: string
  style_name: string
  store_name: string
  order_count: number
  first_date: string
}

export async function getTmallUnmappedProducts(startDate?: string, endDate?: string, storeName?: string) {
  const params: Record<string, any> = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  if (storeName) params.store_name = storeName
  const res = await api.get<TmallUnmappedRow[]>("/tmall/costs/unmapped", { params })
  return res.data
}

export async function mapTmallProductToMerchantCode(
  productId: string,
  merchantCode: string,
  styleId?: string,
  productName?: string
) {
  const res = await api.post("/tmall/costs/map", {
    product_id: productId,
    merchant_code: merchantCode,
    style_id: styleId,
    product_name: productName,
  })
  return res.data
}

export type TmallImportRecord = {
  date: string
  store_name: string
  promo_file: string
  order_file: string
  product_rows: number
  order_rows: number
  saved_at?: string
}

export async function getTmallRecords(storeName?: string) {
  const res = await api.get<TmallImportRecord[]>("/tmall/records", {
    params: storeName ? { store_name: storeName } : {},
  })
  return res.data
}

export async function deleteTmallRecord(storeName: string, date: string) {
  const res = await api.delete(`/tmall/records/${storeName}/${date}`)
  return res.data
}

export async function getTmallAiConfig() {
  const res = await api.get("/tmall/ai/config")
  return res.data
}

export async function updateTmallAiConfig(config: Record<string, any>) {
  const res = await api.post("/tmall/ai/config", config)
  return res.data
}

export async function testTmallAi(config: Record<string, any>) {
  const res = await api.post("/tmall/ai/test", config)
  return res.data
}

export async function generateTmallAiReport(
  storeName: string,
  startDate: string,
  endDate: string,
  config: Record<string, any>
) {
  const res = await api.post("/tmall/ai/report", config, {
    params: { store_name: storeName, start_date: startDate, end_date: endDate },
  })
  return res.data
}

export async function getTmallWecomConfig() {
  const res = await api.get("/tmall/wecom/config")
  return res.data
}

export async function updateTmallWecomConfig(config: Record<string, any>) {
  const res = await api.post("/tmall/wecom/config", config)
  return res.data
}

export async function sendTmallWecomReport(reportDate: string, config: Record<string, any>) {
  const res = await api.post("/tmall/wecom/send", config, {
    params: { report_date: reportDate },
  })
  return res.data
}
