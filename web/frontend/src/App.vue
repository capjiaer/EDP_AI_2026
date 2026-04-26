<template>
  <div class="app-container">
    <h1>EDP Web UI</h1>
    <p>Foundry: {{ foundry }} / Node: {{ node }} / Project: {{ project }}</p>
    <p>WebSocket: {{ wsStatus }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { io } from 'socket.io-client'

const foundry = ref('')
const node = ref('')
const project = ref('')
const wsStatus = ref('disconnected')

let socket = null

onMounted(async () => {
  const res = await fetch('/api/projects')
  const data = await res.json()
  if (data.length > 0) {
    foundry.value = data[0].foundry
    if (data[0].nodes.length > 0) {
      node.value = data[0].nodes[0].node
      const projs = data[0].nodes[0].projects
      if (projs.length > 0) {
        project.value = projs[0]
      }
    }
  }

  socket = io()
  socket.on('connect', () => { wsStatus.value = 'connected' })
  socket.on('disconnect', () => { wsStatus.value = 'disconnected' })
  socket.on('step_status', (data) => {
    console.log('Step status:', data)
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
}
.app-container {
  padding: 20px;
}
</style>
