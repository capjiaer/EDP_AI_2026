<template>
  <div class="app-container" @click="closeContextMenu">
    <!-- Always show top nav -->
    <TopNav
      :foundry="foundry"
      :node="node"
      :project="project"
      :projects="projects"
      :setup-mode="setupMode"
      :preview="isPreview"
      @update:foundry="foundry = $event"
      @update:node="node = $event"
      @update:project="project = $event"
      @change-project="setupMode = true; isPreview = false"
    />

    <!-- Setup mode: select project first -->
    <div v-if="setupMode" class="setup-page">
      <div class="setup-card">
        <div class="setup-title">EDP Workspace Setup</div>
        <p class="setup-desc">Select a project and graph config to get started.</p>

        <div class="setup-form">
          <div class="setup-row">
            <div class="setup-field">
              <label>Foundry</label>
              <el-select v-model="foundry" placeholder="Foundry" style="width:100%">
                <el-option v-for="f in projects" :key="f.foundry" :label="f.foundry" :value="f.foundry" />
              </el-select>
            </div>
            <div class="setup-field">
              <label>Node</label>
              <el-select v-model="node" placeholder="Node" style="width:100%" :disabled="!foundry">
                <el-option v-for="n in availableNodes" :key="n.node" :label="n.node" :value="n.node" />
              </el-select>
            </div>
          </div>
          <div class="setup-row">
            <div class="setup-field">
              <label>Project</label>
              <el-select v-model="project" placeholder="Project" style="width:100%" :disabled="!node">
                <el-option v-for="p in availableProjects" :key="p" :label="p" :value="p" />
              </el-select>
            </div>
            <div class="setup-field">
              <label>Version</label>
              <el-select v-model="version" placeholder="Version" style="width:100%">
                <el-option label="P85" value="P85" />
                <el-option label="P95" value="P95" />
                <el-option label="P100" value="P100" />
              </el-select>
            </div>
          </div>

          <!-- Graph Config Selection -->
          <div class="setup-row">
            <div class="setup-field">
              <label>Graph Config</label>
              <el-select v-model="graphConfig" placeholder="Graph Config" style="width:100%" :disabled="graphConfigs.length === 0">
                <el-option v-for="gc in graphConfigs" :key="gc.name" :label="gc.name" :value="gc.name" />
              </el-select>
            </div>
            <div class="setup-field">
              <label>&nbsp;</label>
              <el-alert v-if="canLoadGraph && graphConfigs.length === 0 && !loadingGraphConfigs" type="info" show-icon :closable="false">
                No graph configs found.
              </el-alert>
            </div>
          </div>

          <!-- Block Users -->
          <div v-if="canLoadGraph" class="setup-section">
            <label class="setup-section-label">Block Users (optional)</label>
            <div v-if="Object.keys(blockUsers).length" class="block-user-table">
              <div v-for="(users, block) in blockUsers" :key="block" class="block-user-row">
                <span class="bu-block">{{ block }}</span>
                <span class="bu-users">{{ users.join(', ') }}</span>
                <el-button text size="small" @click="removeBlockUser(block)">✕</el-button>
              </div>
            </div>
            <div class="block-user-add">
              <el-input v-model="newBlockName" placeholder="Block name" size="small" style="width:140px" />
              <el-input v-model="newBlockUsers" placeholder="user1,user2,..." size="small" style="width:240px" />
              <el-button size="small" :disabled="!newBlockName || !newBlockUsers" @click="addBlockUser">Add</el-button>
            </div>
          </div>
        </div>

        <div class="setup-actions">
          <el-button type="primary" size="large" :disabled="!canLoadGraph" @click="enterGraphMode">
            Enter Graph Mode
          </el-button>
          <el-button size="large" :disabled="!canLoadGraph" @click="handleInit">
            Init New Project
          </el-button>
        </div>

        <div v-if="foundry && node && project" class="setup-preview">
          Viewing: <strong>{{ foundry }}/{{ node }}/{{ project }}</strong>
          <span v-if="graphConfig"> → {{ graphConfig }}</span>
          @ {{ version }}
        </div>
      </div>
    </div>

    <!-- Graph mode -->
    <template v-if="!setupMode">
      <div class="main-content">
        <div class="graph-area">
          <FlowGraph
            :graph-data="graphData"
            :step-statuses="stepStatuses"
            v-on="isPreview ? {} : { 'run-step': handleRunStep, 'node-contextmenu': handleContextMenu }"
          />
        </div>
        <SidePanel
          :step="selectedStep"
          :step-status="selectedStepStatus"
          :tool-name="selectedToolName"
          :step-detail="stepDetail"
          :deps="selectedStepDeps"
          :preview="isPreview"
          @run-step="handleRunStep"
          @select-step="showDetails"
        />
      </div>
      <StatusBar :ws-status="wsStatus" :running-count="runningCount" />
      <ContextMenu
        :visible="contextMenu.visible"
        :x="contextMenu.x"
        :y="contextMenu.y"
        :step-id="contextMenu.stepId"
        @close="closeContextMenu"
        @run="handleRunStep"
        @details="showDetails"
      />
    </template>

  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { io } from 'socket.io-client'
import FlowGraph from './components/FlowGraph.vue'
import TopNav from './components/TopNav.vue'
import SidePanel from './components/SidePanel.vue'
import StatusBar from './components/StatusBar.vue'
import ContextMenu from './components/ContextMenu.vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const foundry = ref('')
const node = ref('')
const project = ref('')
const version = ref('P85')
const projects = ref([])
const graphData = ref({ nodes: [], edges: [] })
const stepStatuses = ref({})
const wsStatus = ref('disconnected')
const selectedStep = ref('')
const stepDetail = ref(null)
const setupMode = ref(true)
let socket = null

const contextMenu = ref({ visible: false, x: 0, y: 0, stepId: '' })
const graphConfig = ref('')
const graphConfigs = ref([])
const loadingGraphConfigs = ref(false)
const workdir = ref('')
const isPreview = ref(false)
const blockUsers = ref({})
const newBlockName = ref('')
const newBlockUsers = ref('')

function addBlockUser() {
  const users = newBlockUsers.value.split(',').map(u => u.trim()).filter(Boolean)
  if (newBlockName.value && users.length) {
    blockUsers.value = { ...blockUsers.value, [newBlockName.value]: users }
    newBlockName.value = ''
    newBlockUsers.value = ''
  }
}
function removeBlockUser(block) {
  const { [block]: _, ...rest } = blockUsers.value
  blockUsers.value = rest
}

const availableNodes = computed(() => {
  const f = projects.value.find(p => p.foundry === foundry.value)
  return f ? f.nodes : []
})

const availableProjects = computed(() => {
  const f = projects.value.find(p => p.foundry === foundry.value)
  if (!f) return []
  const n = f.nodes.find(n => n.node === node.value)
  return n ? n.projects : []
})

const canLoadGraph = computed(() => foundry.value && node.value && project.value)

async function enterGraphMode() {
  setupMode.value = false
  isPreview.value = true
  await loadGraph()
}

async function handleInit() {
  try {
    await ElMessageBox.confirm(
      `Init project <strong>${project.value}</strong> in current directory?<br><small>${workdir.value}</small>`,
      'Confirm Init',
      { confirmButtonText: 'Init', cancelButtonText: 'Cancel', dangerouslyUseHTMLString: true }
    )
    const res = await fetch('/api/init/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        work_path: workdir.value,
        project_name: project.value,
        version: version.value,
        foundry: foundry.value,
        node: node.value,
        graph_config: graphConfig.value || null,
        block_users: blockUsers.value,
      }),
    })
    if (res.ok) {
      ElMessage.success('Project initialized!')
      setTimeout(() => window.location.reload(), 1500)
    } else {
      const err = await res.json()
      ElMessage.error(err.error || 'Init failed')
    }
  } catch {
    // cancelled
  }
}

const runningCount = computed(() => {
  return Object.values(stepStatuses.value).filter(s => s.status === 'running').length
})

const selectedToolName = computed(() => {
  if (!selectedStep.value) return ''
  return (graphData.value.nodes.find(n => n.id === selectedStep.value) || {}).tool || ''
})

const selectedStepStatus = computed(() => {
  if (!selectedStep.value) return null
  return stepStatuses.value[selectedStep.value] || null
})

const selectedStepDeps = computed(() => {
  const step = selectedStep.value
  if (!step) return { upstream: [], downstream: [] }
  const edges = graphData.value.edges || []
  const upstream = edges.filter(e => e.target === step).map(e => e.source)
  const downstream = edges.filter(e => e.source === step).map(e => e.target)
  const nodeMap = {}
  for (const n of graphData.value.nodes || []) {
    nodeMap[n.id] = n.label
  }
  return {
    upstream: upstream.map(id => ({ id, label: nodeMap[id] || id })),
    downstream: downstream.map(id => ({ id, label: nodeMap[id] || id })),
  }
})

const stepTimestamps = ref({})

// Auto-reload graph in graph mode; fetch available configs in setup mode
watch([foundry, node, project], async () => {
  const f = foundry.value, n = node.value, p = project.value
  if (!f || !n || !p) return

  if (setupMode.value) {
    loadingGraphConfigs.value = true
    graphConfig.value = ''
    graphConfigs.value = []
    try {
      const params = new URLSearchParams({ foundry: f, node: n, project: p })
      const res = await fetch(`/api/init/graph-configs?${params}`)
      if (res.ok) {
        const data = await res.json()
        graphConfigs.value = data.graph_configs || []
        if (graphConfigs.value.length === 1) {
          graphConfig.value = graphConfigs.value[0].name
        }
      }
    } catch (e) { /* ignore */ }
    loadingGraphConfigs.value = false
  } else {
    await loadGraph()
  }
})

async function loadGraph() {
  const params = new URLSearchParams({
    foundry: foundry.value,
    node: node.value,
    project: project.value,
  })
  if (graphConfig.value) {
    params.append('graph_config', graphConfig.value)
  }
  const res = await fetch(`/api/graph?${params}`)
  graphData.value = await res.json()
  const newStatuses = {}
  for (const n of graphData.value.nodes) {
    newStatuses[n.id] = { status: 'idle' }
  }
  stepStatuses.value = newStatuses
}

async function handleRunStep(stepId) {
  selectedStep.value = stepId
  showDetails(stepId)
  stepTimestamps.value = { ...stepTimestamps.value, [stepId]: Date.now() }
  stepStatuses.value = { ...stepStatuses.value, [stepId]: { status: 'running' } }
  await fetch(`/api/run/${stepId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      foundry: foundry.value,
      node: node.value,
      project: project.value,
    }),
  })
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return ''
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

async function showDetails(stepId) {
  selectedStep.value = stepId
  stepDetail.value = null
  try {
    const params = new URLSearchParams({
      foundry: foundry.value,
      node: node.value,
      project: project.value,
      step: stepId,
    })
    const res = await fetch(`/api/step-detail?${params}`)
    if (res.ok) {
      stepDetail.value = await res.json()
    }
  } catch (e) {
    // ignore
  }
}

function handleContextMenu({ stepId, x, y }) {
  contextMenu.value = { visible: true, x, y, stepId }
}

function closeContextMenu() {
  contextMenu.value = { ...contextMenu.value, visible: false }
}

onMounted(async () => {
  const [projectsRes, contextRes] = await Promise.all([
    fetch('/api/projects'),
    fetch('/api/context'),
  ])
  projects.value = await projectsRes.json()
  const ctx = contextRes.ok ? await contextRes.json() : {}
  workdir.value = ctx.workdir || ''

  if (ctx?.has_context && projects.value.length > 0) {
    // Has workspace context → go straight to graph mode
    foundry.value = ctx.foundry
    node.value = ctx.node
    project.value = ctx.project
    setupMode.value = false
    isPreview.value = false
    await loadGraph()
  }
  // No context → stay in setup mode, let user pick

  socket = io()
  socket.on('connect', () => { wsStatus.value = 'connected' })
  socket.on('disconnect', () => { wsStatus.value = 'disconnected' })
  socket.on('step_status', (data) => {
    const entry = { status: data.status }
    if (data.execution_time) {
      entry.execution_time = data.execution_time
      entry.formatted_time = formatTime(data.execution_time)
    }
    stepStatuses.value = { ...stepStatuses.value, [data.step]: entry }
  })
})

onUnmounted(() => {
  if (socket) socket.disconnect()
})
</script>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.graph-area {
  flex: 1;
  padding: 16px;
}

/* Setup mode */
.setup-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.setup-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  width: 520px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}
.setup-title {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}
.setup-desc {
  font-size: 13px;
  color: #909399;
  margin: 0 0 28px 0;
}
.setup-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}
.setup-row {
  display: flex;
  gap: 16px;
}
.setup-field {
  flex: 1;
}
.setup-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
}
.setup-actions {
  display: flex;
  gap: 12px;
}
.setup-preview {
  margin-top: 16px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
.setup-section {
  margin-top: 8px;
}
.setup-section-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}
.block-user-table {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
}
.block-user-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid #f0f2f5;
  font-size: 13px;
}
.block-user-row:last-child {
  border-bottom: none;
}
.bu-block {
  font-weight: 600;
  color: #303133;
  min-width: 100px;
}
.bu-users {
  flex: 1;
  color: #606266;
}
.block-user-add {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
