<template>
  <div class="app-container" @click="closeContextMenu">
    <!-- Top bar -->
    <div class="top-bar">
      <div class="top-bar-title">EDP Web UI</div>
    </div>

    <!-- HomePage: project list + init -->
    <HomePage
      v-if="appMode === 'home'"
      @select-project="handleSelectProject"
    />

    <!-- Graph mode -->
    <template v-if="appMode === 'graph'">
      <div class="main-content">
        <div class="graph-area">
          <FlowGraph
            :graph-data="graphData"
            :step-statuses="stepStatuses"
            @run-step="handleRunStep"
            @node-contextmenu="handleContextMenu"
          />
        </div>
        <SidePanel
          :step="selectedStep"
          :step-status="selectedStepStatus"
          :tool-name="selectedToolName"
          :step-detail="stepDetail"
          :deps="selectedStepDeps"
          :preview="false"
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { io } from 'socket.io-client'

import FlowGraph from './components/FlowGraph.vue'
import SidePanel from './components/SidePanel.vue'
import StatusBar from './components/StatusBar.vue'
import ContextMenu from './components/ContextMenu.vue'
import HomePage from './components/HomePage.vue'
// --- State machine ---
const appMode = ref('home')  // 'home' | 'graph'

// --- Project context ---
const foundry = ref('')
const node = ref('')
const project = ref('')
const version = ref('')
const graphConfig = ref('')
const blockUsers = ref({})

// --- Graph state ---
const graphData = ref({ nodes: [], edges: [] })
const stepStatuses = ref({})
const selectedStep = ref('')
const stepDetail = ref(null)
const wsStatus = ref('disconnected')
const contextMenu = ref({ visible: false, x: 0, y: 0, stepId: '' })
const stepTimestamps = ref({})
let socket = null

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

// --- Navigation ---
async function handleSelectProject(ctx) {
  foundry.value = ctx.foundry
  node.value = ctx.node
  project.value = ctx.name
  version.value = ctx.version
  graphConfig.value = ctx.graphConfig || ''
  blockUsers.value = { ...(ctx.blockUsers || {}) }
  appMode.value = 'graph'
  await loadGraph()
}

// --- Graph ops ---
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
      foundry: foundry.value, node: node.value, project: project.value, step: stepId,
    })
    const res = await fetch(`/api/step-detail?${params}`)
    if (res.ok) stepDetail.value = await res.json()
  } catch { /* ignore */ }
}

function handleContextMenu({ stepId, x, y }) {
  contextMenu.value = { visible: true, x, y, stepId }
}

function closeContextMenu() {
  contextMenu.value = { ...contextMenu.value, visible: false }
}

// --- WebSocket ---
onMounted(() => {
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
.top-bar {
  display: flex;
  align-items: center;
  padding: 8px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.top-bar-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
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
</style>
