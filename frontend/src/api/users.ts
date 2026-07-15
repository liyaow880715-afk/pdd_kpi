import { api } from "./client"

export type User = {
  username: string
  role: "master" | "sub"
  allowed_stores: string[]
}

export type CreateUserRequest = {
  username: string
  password: string
  role: "master" | "sub"
  allowed_stores: string[]
}

export type UpdateUserRequest = {
  password?: string
  allowed_stores?: string[]
}

export async function getUsers() {
  const res = await api.get<User[]>("/users")
  return res.data
}

export async function createUser(req: CreateUserRequest) {
  const res = await api.post<User>("/users", req)
  return res.data
}

export async function updateUser(username: string, req: UpdateUserRequest) {
  const res = await api.patch<User>(`/users/${username}`, req)
  return res.data
}

export async function deleteUser(username: string) {
  const res = await api.delete(`/users/${username}`)
  return res.data
}
