<template>
  <div class="status-bar">
    <span :class="'ws-dot ws-' + wsStatus"></span>
    <span>WebSocket: {{ wsStatus }}</span>
    <span v-if="runningCount > 0" class="running-info">
      | {{ runningCount }} step(s) running
    </span>
  </div>
</template>

<script setup>
defineProps({
  wsStatus: String,
  runningCount: { type: Number, default: 0 },
})
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 20px;
  background: #fafafa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.ws-connected { background: #67C23A; }
.ws-disconnected { background: #F56C6C; }
.running-info {
  color: #409EFF;
  font-weight: 600;
}
</style>
