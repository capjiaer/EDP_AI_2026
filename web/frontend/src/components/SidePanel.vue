<template>
  <div class="side-panel">
    <template v-if="step">
      <h3>{{ step }}</h3>
      <span :class="'status-badge status-' + status">{{ status || 'idle' }}</span>
    </template>
    <p v-else class="hint">Click a step to see details</p>
  </div>
</template>

<script setup>
defineProps({ step: String, status: String })
</script>

<style scoped>
.side-panel { width: 280px; background: #fff; border-left: 1px solid #e4e7ed; padding: 20px; }
.hint { color: #c0c4cc; text-align: center; margin-top: 40px; }
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.status-idle { background: #f4f4f5; color: #909399; }
.status-running { background: #ecf5ff; color: #409EFF; }
.status-success { background: #f0f9eb; color: #67C23A; }
.status-failed { background: #fef0f0; color: #F56C6C; }
.status-skipped { background: #fdf6ec; color: #E6A23C; }
</style>
