<template>
  <div class="app-container">
    <TopNav
      :foundry="foundry"
      :node="node"
      :project="project"
      :projects="projects"
      @update:foundry="foundry = $event"
      @update:node="node = $event"
      @update:project="project = $event"
    />
    <div class="main-content">
      <div class="graph-area">
        <FlowGraph
          :graph-data="graphData"
          :step-statuses="stepStatuses"
          @run-step="handleRunStep"
        />
      </div>
      <SidePanel
        :step="selectedStep"
        :status="selectedStep ? stepStatuses[selectedStep] : ''"
      />
    </div>
    <StatusBar :ws-status="wsStatus" :running-count="runningCount" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { io } from 'socket.io-client'
import FlowGraph from './components/FlowGraph.vue'
import TopNav from './components/TopNav.vue'
import SidePanel from './components/SidePanel.vue'
import StatusBar from './components/StatusBar.vue'

const foundry = ref('')
const node = ref('')
const project = ref('')
const projects = ref([])
const graphData = ref({ nodes: [], edges: [] })
const stepStatuses = ref({})
const wsStatus = ref('disconnected')
const selectedStep = ref('')
let socket = null

const runningCount = computed(() => {
  return Object.values(stepStatuses.value).filter(s => s === 'running').length
})

watch([foundry, node, project], async () => {
  if (foundry.value && node.value && project.value) {
    await loadGraph()
  }
})

async function loadGraph() {
  const params = new URLSearchParams({
    foundry: foundry.value,
    node: node.value,
    project: project.value,
  })
  const res = await fetch(`/api/graph?${params}`)
  graphData.value = await res.json()
  const newStatuses = {}
  for (const n of graphData.value.nodes) {
    newStatuses[n.id] = 'idle'
  }
  stepStatuses.value = newStatuses
}

async function handleRunStep(stepId) {
  selectedStep.value = stepId
  stepStatuses.value = { ...stepStatuses.value, [stepId]: 'running' }
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

onMounted(async () => {
  const res = await fetch('/api/projects')
  projects.value = await res.json()
  if (projects.value.length > 0) {
    foundry.value = projects.value[0].foundry
    if (projects.value[0].nodes.length > 0) {
      node.value = projects.value[0].nodes[0].node
      const projs = projects.value[0].nodes[0].projects
      if (projs.length > 0) {
        project.value = projs[0]
      }
    }
  }

  socket = io()
  socket.on('connect', () => { wsStatus.value = 'connected' })
  socket.on('disconnect', () => { wsStatus.value = 'disconnected' })
  socket.on('step_status', (data) => {
    stepStatuses.value = { ...stepStatuses.value, [data.step]: data.status }
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
</style>
