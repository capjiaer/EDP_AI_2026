<template>
  <div class="flow-graph" @contextmenu.prevent="onContainerContextMenu">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :node-types="nodeTypes"
      :default-edge-options="defaultEdgeOptions"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :edges-updatable="false"
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

import { layoutGraph } from '../utils/layout.js'
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

const emit = defineEmits(['run-step', 'node-contextmenu'])

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
  const positions = layoutGraph(rawNodes, edges)

  return rawNodes.map(n => ({
    id: n.id,
    type: 'step',
    position: positions.get(n.id) || { x: 0, y: 0 },
    data: {
      label: n.label,
      tool: n.tool,
      status: (props.stepStatuses[n.id] || {}).status || 'idle',
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

function onContainerContextMenu(e) {
  const nodeEl = e.target.closest('[data-step-id]')
  if (!nodeEl) return
  const stepId = nodeEl.getAttribute('data-step-id')
  if (stepId) {
    emit('node-contextmenu', { stepId, x: e.clientX, y: e.clientY })
  }
}
</script>

<style scoped>
.flow-graph {
  width: 100%;
  height: 100%;
  min-height: 500px;
}
</style>
