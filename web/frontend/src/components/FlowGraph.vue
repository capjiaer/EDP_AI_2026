<template>
  <div class="flow-graph">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :node-types="nodeTypes"
      :default-edge-options="defaultEdgeOptions"
      fit-view-on-init
      @node-click="onNodeClick"
    >
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import StepNode from './StepNode.vue'

const props = defineProps({
  graphData: {
    type: Object,
    default: () => ({ nodes: [], edges: [] }),
  },
  stepStatuses: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['run-step'])

const nodeTypes = {
  step: markRaw(StepNode),
}

const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: false,
  style: { stroke: '#999', strokeWidth: 2 },
}

const nodes = computed(() => {
  const rawNodes = props.graphData.nodes || []
  const edges = props.graphData.edges || []

  // Build downstream map and in-degree
  const downstream = {}
  const inDegree = {}
  for (const n of rawNodes) {
    downstream[n.id] = []
    inDegree[n.id] = 0
  }
  for (const e of edges) {
    if (downstream[e.source]) {
      downstream[e.source].push(e.target)
    }
    inDegree[e.target] = (inDegree[e.target] || 0) + 1
  }

  // BFS to assign levels
  const levels = {}
  const queue = rawNodes.filter(n => inDegree[n.id] === 0).map(n => n.id)
  for (const id of queue) {
    levels[id] = 0
  }
  let idx = 0
  while (idx < queue.length) {
    const current = queue[idx++]
    for (const child of (downstream[current] || [])) {
      levels[child] = Math.max(levels[child] || 0, (levels[current] || 0) + 1)
      inDegree[child]--
      if (inDegree[child] === 0) {
        queue.push(child)
      }
    }
  }

  // Group by level for positioning
  const levelGroups = {}
  for (const [id, lvl] of Object.entries(levels)) {
    if (!levelGroups[lvl]) levelGroups[lvl] = []
    levelGroups[lvl].push(id)
  }
  const nodePositions = {}
  for (const [lvl, ids] of Object.entries(levelGroups)) {
    ids.forEach((id, i) => {
      nodePositions[id] = { x: i * 180, y: Number(lvl) * 120 }
    })
  }

  return rawNodes.map(n => ({
    id: n.id,
    type: 'step',
    position: nodePositions[n.id] || { x: 0, y: 0 },
    data: {
      label: n.label,
      tool: n.tool,
      status: props.stepStatuses[n.id] || 'idle',
    },
  }))
})

const edges = computed(() => {
  const rawEdges = props.graphData.edges || []
  return rawEdges.map(e => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    style: e.weak ? { strokeDasharray: '5,5', stroke: '#bbb' } : {},
    animated: false,
  }))
})

function onNodeClick(event) {
  emit('run-step', event.node.id)
}
</script>

<style scoped>
.flow-graph {
  width: 100%;
  height: 100%;
  min-height: 500px;
}
</style>
