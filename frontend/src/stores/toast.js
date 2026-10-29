import { reactive } from 'vue'

const state = reactive({ items: [] })
let counter = 0

function push(message, type = 'info', duration = 3600) {
  const id = ++counter
  state.items.push({ id, message, type })
  window.setTimeout(() => remove(id), duration)
}

function remove(id) {
  const index = state.items.findIndex((item) => item.id === id)
  if (index >= 0) state.items.splice(index, 1)
}

export const toast = {
  state,
  info: (message) => push(message, 'info'),
  success: (message) => push(message, 'success'),
  error: (message) => push(message, 'error'),
  warning: (message) => push(message, 'warning'),
  remove
}
