import { reactive } from 'vue'
import { api } from '../api/client'

const store = reactive({
  user: null,
  meta: null,
  ready: false,
  loading: false
})

let bootstrapPromise = null

async function bootstrap(force = false) {
  if (store.ready && !force) return store
  if (bootstrapPromise) return bootstrapPromise
  bootstrapPromise = (async () => {
    store.loading = true
    try {
      store.meta = await api.get('/meta')
      const result = await api.get('/auth/session')
      store.user = result.user
    } finally {
      store.ready = true
      store.loading = false
      bootstrapPromise = null
    }
    return store
  })()
  return bootstrapPromise
}

async function login(username, password) {
  const result = await api.post('/auth/login', { username, password })
  store.user = result.user
  return result
}

async function logout() {
  await api.post('/auth/logout')
  store.user = null
}

export const session = {
  store,
  bootstrap,
  login,
  logout
}
