(() => {
  'use strict'

  const STORAGE_KEY = 'lkaya-demo-state-v1'
  const nativeFetch = window.fetch.bind(window)
  let seedPromise = null
  let seedData = null
  let state = null
  let statePromise = null

  const ACTION_LABELS = {
    login: '登录',
    login_failed: '登录失败',
    logout: '退出',
    view_document: '查看文档',
    create_document: '创建文档',
    edit_document: '编辑文档',
    delete_document: '删除文档',
    ask_qa: '智能问答'
  }
  const ACTION_ORDER = ['login', 'login_failed', 'logout', 'view_document', 'create_document', 'edit_document', 'delete_document', 'ask_qa']
  const NODE_COLORS = {
    document: '#3976d9',
    department: '#1d9b83',
    project: '#e9a23b',
    keyword: '#7c5ce5',
    concept: '#e76b67'
  }

  const clone = (value) => JSON.parse(JSON.stringify(value))
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
  const normalizeQuestion = (value) => String(value || '').trim().replace(/\s+/g, ' ')

  function nowText(date = new Date()) {
    const pad = (n) => String(n).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  }

  function dateValue(value) {
    if (!value) return 0
    const parsed = new Date(String(value).replace(' ', 'T'))
    return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime()
  }

  function autoSummary(content, limit = 140) {
    const text = String(content || '').replace(/\s+/g, ' ').trim()
    if (text.length <= limit) return text
    return `${text.slice(0, limit).replace(/[ ,，、]+$/, '')}…`
  }

  function loadSeed() {
    if (!seedPromise) {
      seedPromise = nativeFetch('/data/seed.json', { cache: 'no-store' }).then((response) => {
        if (!response.ok) throw new Error(`演示数据加载失败（${response.status}）`)
        return response.json()
      }).then((data) => {
        seedData = data
        return data
      })
    }
    return seedPromise
  }

  function maxId(items) {
    return items.reduce((max, item) => Math.max(max, Number(item.id) || 0), 0)
  }

  function initialState(seed) {
    const allQa = Object.values(seed.qaHistory || {}).flat()
    return {
      version: seed.version,
      sessionUsername: null,
      users: clone(seed.users),
      categories: clone(seed.categories),
      documents: clone(seed.documents),
      favorites: clone(seed.favorites || {}),
      qaHistory: clone(seed.qaHistory || {}),
      graph: clone(seed.graph),
      graphManage: clone(seed.graphManage),
      audits: clone(seed.audits || []),
      counters: {
        document: Math.max(0, ...seed.documents.map((item) => Number(item.id) || 0)) + 1,
        qa: Math.max(0, ...allQa.map((item) => Number(item.id) || 0)) + 1,
        audit: Math.max(0, ...(seed.audits || []).map((item) => Number(item.id) || 0)) + 1,
        graphNode: Math.max(maxId(seed.graph.nodes), maxId(seed.graphManage.nodes)) + 1,
        graphEdge: Math.max(maxId(seed.graphManage.edges)) + 1
      }
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch (error) {
      console.warn('演示数据无法写入 localStorage，本次操作仅在当前页面有效。', error)
    }
  }

  function ensureState() {
    if (state) return Promise.resolve(state)
    if (statePromise) return statePromise
    statePromise = loadSeed().then((seed) => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY)
        const stored = raw ? JSON.parse(raw) : null
        state = stored && stored.version === seed.version ? stored : initialState(seed)
      } catch {
        state = initialState(seed)
      }
      if (!state) state = initialState(seed)
      saveState()
      return state
    })
    return statePromise
  }

  function currentUser() {
    if (!state?.sessionUsername) return null
    return state.users.find((item) => item.username === state.sessionUsername) || null
  }

  function publicUser(user) {
    if (!user) return null
    return {
      id: user.id,
      username: user.username,
      display_name: user.display_name,
      role: user.role,
      role_label: user.role_label,
      department: user.department,
      is_admin: Boolean(user.is_admin),
      created_at: user.created_at
    }
  }

  function categoryById(id) {
    return state.categories.find((item) => Number(item.id) === Number(id)) || null
  }

  function categoryName(id) {
    return categoryById(id)?.name || '未分类'
  }

  function userFavorites(user) {
    const key = String(user?.id || '')
    if (!state.favorites[key]) state.favorites[key] = []
    return state.favorites[key]
  }

  function isFavorite(doc, user) {
    return userFavorites(user).map(Number).includes(Number(doc.id))
  }

  function canView(doc, user) {
    if (!user || !doc) return false
    if (user.is_admin) return true
    if (doc.visibility === 'secret') return doc.department === user.department || Number(doc.author_id) === Number(user.id)
    return true
  }

  function visibleDocs(user, includeUnpublished = false) {
    return state.documents.filter((doc) => {
      if (!includeUnpublished && doc.status !== 'published') return false
      return canView(doc, user)
    })
  }

  function authorName(authorId) {
    return state.users.find((item) => Number(item.id) === Number(authorId))?.display_name || '未知作者'
  }

  function docPayload(doc, user, includeContent = false) {
    const payload = {
      id: doc.id,
      title: doc.title,
      summary: doc.summary || autoSummary(doc.content),
      department: doc.department,
      visibility: doc.visibility,
      visibility_label: seedData.meta.visibility_labels[doc.visibility] || doc.visibility,
      status: doc.status,
      status_label: seedData.meta.status_labels[doc.status] || doc.status,
      version: doc.version || '1.0',
      tags: Array.isArray(doc.tags) ? doc.tags : String(doc.tags || '').split(',').filter(Boolean),
      category_id: doc.category_id,
      category: categoryName(doc.category_id),
      author_id: doc.author_id,
      author: authorName(doc.author_id),
      created_at: doc.created_at,
      updated_at: doc.updated_at,
      char_count: String(doc.content || '').length,
      chunk_count: Number(doc.chunk_count) || Math.max(1, Math.ceil(String(doc.content || '').length / 400)),
      is_favorite: user ? isFavorite(doc, user) : false
    }
    if (includeContent) payload.content = doc.content || ''
    return payload
  }

  function addAudit(action, detail, user = currentUser(), username = null) {
    const entry = {
      id: state.counters.audit++,
      user_id: user ? user.id : null,
      username: user ? user.username : (username || 'anonymous'),
      action,
      action_label: ACTION_LABELS[action] || action,
      detail,
      created_at: nowText()
    }
    state.audits.unshift(entry)
    state.audits.sort((a, b) => dateValue(b.created_at) - dateValue(a.created_at) || b.id - a.id)
    return entry
  }

  function userQa(user) {
    const key = String(user?.id || '')
    if (!state.qaHistory[key]) state.qaHistory[key] = []
    return state.qaHistory[key]
  }

  function qaPayload(item, includeSources = false) {
    const payload = {
      id: item.id,
      question: item.question,
      answer: item.answer,
      mode: item.mode || 'local',
      mode_label: item.mode_label || '本地检索',
      created_at: item.created_at
    }
    if (includeSources) payload.sources = clone(item.sources || [])
    return payload
  }

  function parseBody(init) {
    if (!init || !init.body) return {}
    if (typeof init.body === 'string') {
      try { return JSON.parse(init.body) } catch { return {} }
    }
    if (init.body instanceof FormData) return Object.fromEntries(init.body.entries())
    return {}
  }

  function json(status, payload) {
    return new Response(JSON.stringify(payload), {
      status,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store'
      }
    })
  }

  function authRequired() {
    return json(401, { error: '请先登录后再访问', code: 'AUTH_REQUIRED' })
  }

  function adminRequired() {
    const user = currentUser()
    if (!user) return authRequired()
    if (!user.is_admin) return json(403, { error: '需要管理员权限', code: 'FORBIDDEN' })
    return null
  }

  function notFound(entity = '资源') {
    return json(404, { error: `${entity}不存在`, code: 'NOT_FOUND' })
  }

  function validation(message) {
    return json(400, { error: message, code: 'VALIDATION_ERROR' })
  }

  function tokenize(text) {
    const lower = String(text || '').toLowerCase().replace(/[，。！？、,.!?；;：:\s]+/g, ' ')
    const parts = lower.split(' ').filter((item) => item.length >= 2)
    const chinese = Array.from(lower.replace(/[^\u4e00-\u9fff]/g, ''))
    for (let i = 0; i < chinese.length - 1; i += 1) parts.push(chinese[i] + chinese[i + 1])
    return Array.from(new Set(parts))
  }

  function rankDocs(docs, question) {
    const q = String(question || '').trim().toLowerCase()
    if (!q) return docs
    const tokens = tokenize(q)
    return docs.map((doc) => {
      const title = String(doc.title || '').toLowerCase()
      const summary = String(doc.summary || '').toLowerCase()
      const tags = (Array.isArray(doc.tags) ? doc.tags.join(' ') : String(doc.tags || '')).toLowerCase()
      const content = String(doc.content || '').toLowerCase()
      let score = 0
      if (title.includes(q)) score += 24
      if (tags.includes(q)) score += 15
      if (summary.includes(q)) score += 10
      if (content.includes(q)) score += 7
      for (const token of tokens) {
        if (title.includes(token)) score += 4
        if (tags.includes(token)) score += 3
        if (summary.includes(token)) score += 2
        if (content.includes(token)) score += 1
      }
      return { doc, score }
    }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score || dateValue(b.doc.updated_at) - dateValue(a.doc.updated_at)).map((item) => item.doc)
  }

  function relatedDocs(doc, user, limit = 4) {
    const tags = new Set(Array.isArray(doc.tags) ? doc.tags : [])
    return visibleDocs(user)
      .filter((item) => Number(item.id) !== Number(doc.id))
      .map((item) => {
        const itemTags = Array.isArray(item.tags) ? item.tags : []
        let score = 0
        if (item.category_id && Number(item.category_id) === Number(doc.category_id)) score += 5
        if (item.department === doc.department) score += 2
        score += itemTags.filter((tag) => tags.has(tag)).length * 3
        return { item, score }
      })
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score || dateValue(b.item.updated_at) - dateValue(a.item.updated_at))
      .slice(0, limit)
      .map((entry) => docPayload(entry.item, user))
  }
  function dashboardPayload(user) {
    const docs = visibleDocs(user)
    const favorites = userFavorites(user)
    const qas = userQa(user)
    const departments = {}
    const categories = {}
    for (const doc of docs) {
      departments[doc.department] = (departments[doc.department] || 0) + 1
      const name = categoryName(doc.category_id)
      categories[name] = (categories[name] || 0) + 1
    }
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
    return {
      stats: {
        visible_documents: docs.length,
        favorites: favorites.length,
        qa_total: qas.length,
        qa_week: qas.filter((item) => dateValue(item.created_at) >= weekAgo).length,
        nodes: state.graph.nodes.length,
        edges: state.graph.links.length
      },
      charts: {
        departments: Object.entries(departments).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'zh-CN')),
        categories: Object.entries(categories).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'zh-CN')).slice(0, 8)
      },
      recent_documents: docs.slice().sort((a, b) => dateValue(b.updated_at) - dateValue(a.updated_at)).slice(0, 6).map((doc) => docPayload(doc, user)),
      recent_qa: qas.slice().sort((a, b) => dateValue(b.created_at) - dateValue(a.created_at)).slice(0, 6).map((item) => qaPayload(item)),
      recent_logs: user.is_admin ? state.audits.slice(0, 8).map((item) => clone(item)) : [],
      quick_questions: clone(seedData.qaQuickQuestions)
    }
  }

  function listDocuments(url, user) {
    const params = url.searchParams
    const q = String(params.get('q') || '').trim()
    const categoryId = params.get('category_id')
    const department = String(params.get('department') || '').trim()
    const visibility = String(params.get('visibility') || '').trim()
    const sort = String(params.get('sort') || 'updated').trim() || 'updated'
    let page = Math.max(Number(params.get('page') || 1), 1)
    const perPage = Math.min(Math.max(Number(params.get('per_page') || 9), 1), 50)
    let docs = visibleDocs(user)
    if (categoryId) docs = docs.filter((doc) => Number(doc.category_id) === Number(categoryId))
    if (department) docs = docs.filter((doc) => doc.department === department)
    if (visibility) docs = docs.filter((doc) => doc.visibility === visibility)
    if (q) docs = rankDocs(docs, q)
    else if (sort === 'title') docs.sort((a, b) => String(a.title).localeCompare(String(b.title), 'zh-CN'))
    else if (sort === 'department') docs.sort((a, b) => String(a.department).localeCompare(String(b.department), 'zh-CN') || dateValue(b.updated_at) - dateValue(a.updated_at))
    else docs.sort((a, b) => dateValue(b.updated_at) - dateValue(a.updated_at))
    const total = docs.length
    const pages = Math.max(Math.ceil(total / perPage), 1)
    page = Math.min(page, pages)
    const start = (page - 1) * perPage
    return {
      items: docs.slice(start, start + perPage).map((doc) => docPayload(doc, user)),
      categories: state.categories.slice().sort((a, b) => a.name.localeCompare(b.name, 'zh-CN')).map((item) => ({ id: item.id, name: item.name, description: item.description || '' })),
      pagination: { page, pages, total, per_page: perPage },
      filters: { q, category_id: categoryId ? Number(categoryId) : null, department, visibility, sort },
      departments: clone(seedData.meta.departments)
    }
  }

  function normalizeTags(value) {
    if (Array.isArray(value)) return value.map((tag) => String(tag).trim()).filter(Boolean)
    return String(value || '').split(/[,，]/).map((tag) => tag.trim()).filter(Boolean)
  }

  function applyDocument(doc, body, user, creating = false) {
    const title = String(body.title || '').trim()
    const content = String(body.content || '').trim()
    if (!title || !content) return '标题与正文不能为空'
    const categoryId = body.category_id ? Number(body.category_id) : null
    if (categoryId && !categoryById(categoryId)) return '所选分类不存在'
    const visibility = ['public', 'internal', 'secret'].includes(body.visibility) ? body.visibility : 'internal'
    const status = ['draft', 'published', 'archived'].includes(body.status) ? body.status : 'published'
    if (creating) {
      doc.id = state.counters.document++
      doc.author_id = user.id
      doc.created_at = nowText()
    }
    doc.title = title
    doc.content = content
    doc.summary = String(body.summary || '').trim().slice(0, 500) || autoSummary(content)
    doc.department = seedData.meta.departments.includes(body.department) ? body.department : (doc.department || user.department)
    doc.visibility = visibility
    doc.status = status
    doc.version = String(body.version || '1.0').trim() || '1.0'
    doc.tags = normalizeTags(body.tags)
    doc.category_id = categoryId
    doc.updated_at = nowText()
    doc.chunk_count = Math.max(1, Math.ceil(content.length / 400))
    return ''
  }
  function syncDocumentGraph(doc) {
    const prefix = '文档:'
    const docName = prefix + doc.title
    const oldNodes = state.graph.nodes.filter((node) => Number(node.document_id) === Number(doc.id))
    const oldIds = new Set(oldNodes.map((node) => node.id))
    state.graph.nodes = state.graph.nodes.filter((node) => !oldIds.has(node.id))
    state.graph.links = state.graph.links.filter((link) => !oldIds.has(link.source) && !oldIds.has(link.target))

    let docNode = state.graph.nodes.find((node) => node.name === docName)
    if (!docNode) {
      docNode = { id: state.counters.graphNode++, name: docName, category: 'document', document_id: doc.id, symbolSize: 24, itemStyle: { color: NODE_COLORS.document } }
      state.graph.nodes.push(docNode)
    } else {
      docNode.document_id = doc.id
    }
    const ensureNode = (name, category) => {
      let node = state.graph.nodes.find((item) => item.name === name)
      if (!node) {
        node = { id: state.counters.graphNode++, name, category, document_id: null, symbolSize: category === 'keyword' ? 14 : 28, itemStyle: { color: NODE_COLORS[category] || '#8996a8' } }
        state.graph.nodes.push(node)
      }
      return node
    }
    const ensureLink = (source, target, relation) => {
      if (!state.graph.links.some((link) => link.source === source && link.target === target && link.relation === relation)) {
        state.graph.links.push({ source, target, relation })
      }
    }
    const department = ensureNode(doc.department, 'department')
    const category = ensureNode(categoryName(doc.category_id), 'concept')
    ensureLink(docNode.id, department.id, '属于')
    ensureLink(docNode.id, category.id, '分类为')
    for (const tag of normalizeTags(doc.tags).slice(0, 8)) {
      const keyword = ensureNode(tag, 'keyword')
      ensureLink(docNode.id, keyword.id, '含有')
    }
  }

  function removeDocumentGraph(docId) {
    const docNodeIds = new Set(state.graph.nodes.filter((node) => Number(node.document_id) === Number(docId)).map((node) => node.id))
    state.graph.nodes = state.graph.nodes.filter((node) => !docNodeIds.has(node.id))
    state.graph.links = state.graph.links.filter((link) => !docNodeIds.has(link.source) && !docNodeIds.has(link.target))
  }

  function visibleGraph(user) {
    const allowedDocIds = new Set(visibleDocs(user).map((doc) => Number(doc.id)))
    const docNodes = state.graph.nodes.filter((node) => node.document_id != null && allowedDocIds.has(Number(node.document_id)))
    const docNodeIds = new Set(docNodes.map((node) => node.id))
    const visibleNodeIds = new Set(docNodeIds)
    const links = state.graph.links.filter((link) => docNodeIds.has(link.source) || docNodeIds.has(link.target))
    for (const link of links) {
      visibleNodeIds.add(link.source)
      visibleNodeIds.add(link.target)
    }
    return {
      nodes: state.graph.nodes.filter((node) => visibleNodeIds.has(node.id)),
      links,
      categories: clone(state.graph.categories)
    }
  }

  function ensureManageNode(name, nodeType = 'concept', description = '') {
    let node = state.graphManage.nodes.find((item) => item.name === name)
    if (!node) {
      node = { id: state.counters.graphNode++, name, node_type: nodeType, description }
      state.graphManage.nodes.unshift(node)
    }
    let graphNode = state.graph.nodes.find((item) => item.name === name)
    if (!graphNode) {
      const category = ['document', 'department', 'project', 'keyword', 'concept'].includes(nodeType) ? nodeType : 'concept'
      state.graph.nodes.push({ id: node.id, name, category, document_id: null, symbolSize: category === 'keyword' ? 14 : 28, itemStyle: { color: NODE_COLORS[category] || '#8996a8' } })
    }
    return node
  }

  function questionSearch(question, user) {
    const docs = rankDocs(visibleDocs(user), question).slice(0, 3)
    if (!docs.length) {
      return {
        answer: '当前账号权限内没有检索到与该问题直接相关的已发布文档。可以换用“年假、差旅、采购、API、合同”等业务关键词，或联系文档所属部门补充知识。',
        sources: [],
        fragments: []
      }
    }
    const fragments = docs.map((doc, index) => {
      const content = String(doc.content || '')
      const compact = content.replace(/\s+/g, ' ').trim()
      return {
        chunk_id: Number(doc.id) * 100 + index + 1,
        document_id: doc.id,
        title: doc.title,
        department: doc.department,
        fragment_no: 1,
        fragment_total: Math.max(Number(doc.chunk_count) || 1, 1),
        score: Math.max(12 - index * 2, 1),
        content: compact.slice(0, 300) + (compact.length > 300 ? '…' : '')
      }
    })
    const sourcesMap = new Map()
    for (const fragment of fragments) {
      if (!sourcesMap.has(fragment.document_id)) {
        sourcesMap.set(fragment.document_id, {
          document_id: fragment.document_id,
          title: fragment.title,
          department: fragment.department,
          score: fragment.score,
          fragments: []
        })
      }
      sourcesMap.get(fragment.document_id).fragments.push(fragment)
    }
    const top = fragments[0]
    const answer = `根据《${top.title}》：${top.content}`
    return { answer, sources: Array.from(sourcesMap.values()), fragments }
  }

  function askQuestion(body, user) {
    const question = normalizeQuestion(body.question)
    if (!question) return validation('问题不能为空')
    const visibleIds = new Set(visibleDocs(user).map((doc) => Number(doc.id)))
    const sampleKey = Object.keys(seedData.qaExamples || {}).find((key) => normalizeQuestion(key) === question)
    let result = null
    if (sampleKey) {
      const sample = clone(seedData.qaExamples[sampleKey])
      sample.sources = (sample.sources || []).filter((source) => visibleIds.has(Number(source.document_id)))
      sample.fragments = (sample.fragments || []).filter((fragment) => visibleIds.has(Number(fragment.document_id)))
      if (sample.sources.length) result = sample
    }
    if (!result) result = questionSearch(question, user)
    const id = state.counters.qa++
    const item = {
      id,
      question,
      answer: result.answer,
      mode: 'local',
      mode_label: '本地检索',
      created_at: nowText(),
      sources: result.sources || [],
      fragments: result.fragments || []
    }
    userQa(user).unshift(item)
    addAudit('ask_qa', `提问：${question.slice(0, 60)}`, user)
    saveState()
    return json(200, {
      answer: item.answer,
      mode: item.mode,
      mode_label: item.mode_label,
      history_id: item.id,
      sources: clone(item.sources),
      fragments: clone(item.fragments)
    })
  }

  function findQaItem(historyId, user) {
    if (user.is_admin) {
      for (const items of Object.values(state.qaHistory)) {
        const found = items.find((item) => Number(item.id) === Number(historyId))
        if (found) return found
      }
      return null
    }
    return userQa(user).find((item) => Number(item.id) === Number(historyId)) || null
  }
  async function handleApi(url, method, body) {
    const path = url.pathname.replace(/^\/api/, '') || '/'
    const user = currentUser()

    if (method === 'GET' && path === '/meta') return json(200, clone(seedData.meta))
    if (method === 'GET' && path === '/auth/session') return json(200, { user: publicUser(user) })
    if (method === 'POST' && path === '/auth/login') {
      const username = String(body.username || '').trim()
      const password = String(body.password || '')
      const account = seedData.meta.demo_accounts.find((item) => item.username === username && item.password === password)
      if (!account) {
        const known = state.users.find((item) => item.username === username)
        addAudit('login_failed', `登录失败：${username || '空账号'}`, known, username)
        saveState()
        return json(401, { error: '账号或密码错误', code: 'INVALID_CREDENTIALS' })
      }
      state.sessionUsername = account.username
      const logged = currentUser()
      addAudit('login', `用户 ${account.username} 登录`, logged)
      saveState()
      return json(200, { message: '登录成功', user: publicUser(logged) })
    }
    if (method === 'POST' && path === '/auth/logout') {
      if (!user) return authRequired()
      addAudit('logout', `用户 ${user.username} 退出`, user)
      state.sessionUsername = null
      saveState()
      return json(200, { message: '已退出登录' })
    }

    if (!user) return authRequired()

    if (method === 'GET' && path === '/dashboard') return json(200, dashboardPayload(user))
    if (method === 'GET' && path === '/documents') return json(200, listDocuments(url, user))
    if (method === 'GET' && path === '/documents/favorites') {
      const docs = userFavorites(user).map((id) => state.documents.find((doc) => Number(doc.id) === Number(id))).filter((doc) => doc && canView(doc, user))
      return json(200, { items: docs.map((doc) => docPayload(doc, user)) })
    }

    let match = path.match(/^\/documents\/(\d+)\/favorite$/)
    if (match && method === 'POST') {
      const doc = state.documents.find((item) => Number(item.id) === Number(match[1]))
      if (!doc) return notFound('文档')
      if (!canView(doc, user)) return json(403, { error: '无权收藏该文档', code: 'FORBIDDEN' })
      const favorites = userFavorites(user)
      const index = favorites.findIndex((id) => Number(id) === Number(doc.id))
      if (index >= 0) favorites.splice(index, 1)
      else favorites.push(Number(doc.id))
      saveState()
      return json(200, { is_favorite: index < 0, message: index < 0 ? '已收藏' : '已取消收藏' })
    }

    match = path.match(/^\/documents\/(\d+)$/)
    if (match) {
      const docId = Number(match[1])
      const doc = state.documents.find((item) => Number(item.id) === docId)
      if (method === 'GET') {
        if (!doc) return notFound('文档')
        if (!canView(doc, user)) return json(403, { error: '无权查看该文档', code: 'FORBIDDEN' })
        if (doc.status !== 'published' && !user.is_admin && Number(doc.author_id) !== Number(user.id)) return json(403, { error: '该文档尚未发布', code: 'FORBIDDEN' })
        addAudit('view_document', `查看文档 #${doc.id} 《${doc.title}》`, user)
        saveState()
        return json(200, { document: docPayload(doc, user, true), related: relatedDocs(doc, user), can_edit: Boolean(user.is_admin || Number(doc.author_id) === Number(user.id)) })
      }
      if (method === 'PUT') {
        if (!doc) return notFound('文档')
        if (!(user.is_admin || Number(doc.author_id) === Number(user.id))) return json(403, { error: '只能编辑自己创建的文档', code: 'FORBIDDEN' })
        const error = applyDocument(doc, body, user, false)
        if (error) return validation(error)
        addAudit('edit_document', `编辑文档 #${doc.id} 《${doc.title}》`, user)
        syncDocumentGraph(doc)
        saveState()
        return json(200, { document: docPayload(doc, user, true), message: '文档已更新' })
      }
      if (method === 'DELETE') {
        if (!doc) return notFound('文档')
        if (!(user.is_admin || Number(doc.author_id) === Number(user.id))) return json(403, { error: '只能删除自己创建的文档', code: 'FORBIDDEN' })
        const title = doc.title
        state.documents = state.documents.filter((item) => Number(item.id) !== docId)
        for (const key of Object.keys(state.favorites)) {
          state.favorites[key] = state.favorites[key].filter((id) => Number(id) !== docId)
        }
        removeDocumentGraph(docId)
        addAudit('delete_document', `删除文档 #${docId} 《${title}》`, user)
        saveState()
        return json(200, { message: '文档已删除' })
      }
    }

    if (method === 'POST' && path === '/documents') {
      const doc = { id: 0, author_id: user.id, content: '' }
      const error = applyDocument(doc, body, user, true)
      if (error) return validation(error)
      state.documents.push(doc)
      addAudit('create_document', `创建文档 #${doc.id} 《${doc.title}》`, user)
      syncDocumentGraph(doc)
      saveState()
      return json(201, { document: docPayload(doc, user, true), message: '文档已创建' })
    }

    if (method === 'GET' && path === '/categories') {
      return json(200, {
        items: state.categories.slice().sort((a, b) => a.id - b.id).map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description || '',
          document_count: state.documents.filter((doc) => Number(doc.category_id) === Number(item.id)).length
        }))
      })
    }

    if (method === 'GET' && path === '/qa') {
      return json(200, {
        suggestions: clone(seedData.qaSuggestions),
        quick_questions: clone(seedData.qaQuickQuestions),
        llm_enabled: false,
        history: userQa(user).slice().sort((a, b) => dateValue(b.created_at) - dateValue(a.created_at)).slice(0, 20).map((item) => qaPayload(item))
      })
    }
    if (method === 'POST' && path === '/qa/ask') return askQuestion(body, user)
    match = path.match(/^\/qa\/history\/(\d+)$/)
    if (match && method === 'GET') {
      const item = findQaItem(Number(match[1]), user)
      if (!item) return notFound('问答记录')
      return json(200, { item: qaPayload(item, true) })
    }
    if (method === 'GET' && path === '/graph') return json(200, visibleGraph(user))
    if (method === 'GET' && path === '/graph/manage') {
      const denied = adminRequired()
      return denied || json(200, clone(state.graphManage))
    }
    if (method === 'POST' && path === '/graph/nodes') {
      const denied = adminRequired()
      if (denied) return denied
      const name = String(body.name || '').trim()
      if (!name) return validation('节点名称不能为空')
      const node = ensureManageNode(name, String(body.node_type || 'concept'), String(body.description || ''))
      saveState()
      return json(201, { id: node.id, name: node.name, message: '节点已添加' })
    }
    if (method === 'POST' && path === '/graph/edges') {
      const denied = adminRequired()
      if (denied) return denied
      const sourceName = String(body.source_name || '').trim()
      const targetName = String(body.target_name || '').trim()
      const relation = String(body.relation || '关联').trim() || '关联'
      if (!sourceName || !targetName) return validation('起点和终点名称不能为空')
      const source = ensureManageNode(sourceName, 'concept')
      const target = ensureManageNode(targetName, 'concept')
      if (!state.graphManage.edges.some((edge) => edge.source === sourceName && edge.target === targetName && edge.relation === relation)) {
        state.graphManage.edges.unshift({ id: state.counters.graphEdge++, source: sourceName, target: targetName, relation })
      }
      const sourceGraph = state.graph.nodes.find((node) => node.name === sourceName)
      const targetGraph = state.graph.nodes.find((node) => node.name === targetName)
      if (sourceGraph && targetGraph && !state.graph.links.some((link) => link.source === sourceGraph.id && link.target === targetGraph.id && link.relation === relation)) {
        state.graph.links.push({ source: sourceGraph.id, target: targetGraph.id, relation })
      }
      saveState()
      return json(201, { message: '关系已添加' })
    }

    if (method === 'GET' && path === '/admin/users') {
      const denied = adminRequired()
      if (denied) return denied
      const items = state.users.map((item) => ({
        ...publicUser(item),
        document_count: state.documents.filter((doc) => Number(doc.author_id) === Number(item.id)).length
      }))
      return json(200, {
        items,
        summary: {
          total: items.length,
          admins: items.filter((item) => item.is_admin).length,
          employees: items.filter((item) => !item.is_admin).length
        }
      })
    }

    if (method === 'GET' && path === '/admin/audits') {
      const denied = adminRequired()
      if (denied) return denied
      const action = String(url.searchParams.get('action') || '').trim()
      const userKeyword = String(url.searchParams.get('user') || '').trim().toLowerCase()
      const detailKeyword = String(url.searchParams.get('detail') || '').trim().toLowerCase()
      const perPage = 25
      let page = Math.max(Number(url.searchParams.get('page') || 1), 1)
      let items = state.audits.slice()
      if (action) items = items.filter((item) => item.action === action)
      if (userKeyword) items = items.filter((item) => String(item.username || '').toLowerCase().includes(userKeyword))
      if (detailKeyword) items = items.filter((item) => String(item.detail || '').toLowerCase().includes(detailKeyword))
      const total = items.length
      const pages = Math.max(Math.ceil(total / perPage), 1)
      page = Math.min(page, pages)
      const actionStats = {}
      for (const item of state.audits) actionStats[item.action] = (actionStats[item.action] || 0) + 1
      return json(200, {
        items: items.slice((page - 1) * perPage, page * perPage).map((item) => clone(item)),
        pagination: { page, pages, total, per_page: perPage },
        action_stats: actionStats,
        actions: ACTION_ORDER.map((value) => ({ value, label: ACTION_LABELS[value] }))
      })
    }

    if (method === 'GET' && path === '/about') {
      const docs = visibleDocs(user)
      return json(200, {
        app: clone(seedData.about.app),
        stats: {
          documents: docs.length,
          chunks: docs.reduce((sum, doc) => sum + (Number(doc.chunk_count) || 1), 0),
          nodes: state.graph.nodes.length,
          edges: state.graph.links.length,
          qa: userQa(user).length
        },
        scope: '本人可见范围'
      })
    }

    if (method === 'POST' && path === '/demo/reset') {
      localStorage.removeItem(STORAGE_KEY)
      return json(200, { message: '演示数据已重置' })
    }

    return json(404, { error: `接口不存在：${method} ${path}`, code: 'NOT_FOUND' })
  }

  const originalFetch = window.fetch
  window.fetch = async function patchedFetch(input, init = {}) {
    let url
    try {
      url = new URL(typeof input === 'string' ? input : input.url, location.origin)
    } catch {
      return originalFetch(input, init)
    }
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return originalFetch(input, init)
    await ensureState()
    await wait(120 + Math.floor(Math.random() * 180))
    const method = String(init.method || (typeof input !== 'string' && input.method) || 'GET').toUpperCase()
    try {
      return await handleApi(url, method, parseBody(init))
    } catch (error) {
      console.error('Mock API error', error)
      return json(500, { error: `演示接口异常：${error.message}`, code: 'DEMO_ERROR' })
    }
  }

  function installBadge() {
    if (document.getElementById('lkaya-demo-badge')) return
    const badge = document.createElement('div')
    badge.id = 'lkaya-demo-badge'
    badge.title = 'lkaya.com 静态演示'
    badge.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;display:flex;align-items:center;gap:7px;padding:6px 9px;border:1px solid rgba(148,163,184,.32);border-radius:999px;background:rgba(255,255,255,.92);color:#64748b;box-shadow:0 5px 18px rgba(15,27,51,.08);backdrop-filter:blur(10px);font:10px/1.4 system-ui,sans-serif;'
    const label = document.createElement('span')
    label.textContent = '静态演示'
    const reset = document.createElement('button')
    reset.type = 'button'
    reset.textContent = '重置数据'
    reset.style.cssText = 'border:0;border-left:1px solid #e2e8f0;background:transparent;color:#147a67;padding:0 0 0 7px;font:inherit;font-weight:700;cursor:pointer;'
    reset.addEventListener('click', () => {
      if (!window.confirm('恢复全部演示数据并退出当前演示账号？')) return
      localStorage.removeItem(STORAGE_KEY)
      location.assign('/login')
    })
    badge.append(label, reset)
    document.body.appendChild(badge)
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installBadge)
  else installBadge()
})()