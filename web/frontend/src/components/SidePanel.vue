<template>
  <div class="side-panel">
    <template v-if="step">
      <h3>{{ step }}</h3>
      <div class="status-row">
        <span class="label">Status:</span>
        <span :class="'status-badge status-' + status">{{ status || 'idle' }}</span>
      </div>
      <div v-if="toolName" class="info-row">
        <span class="label">Tool:</span>
        <span class="info-value">{{ toolName }}</span>
      </div>
      <div v-if="status === 'failed'" class="error-section">
        <h4>Error</h4>
        <p class="error-text">{{ lastError }}</p>
      </div>
    </template>
    <template v-else>
      <p class="hint">Click a step node to see details</p>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  step: String,
  status: String,
  toolName: String,
})

const lastError = ref('')

watch(() => props.status, (newStatus) => {
  if (newStatus === 'failed') {
    lastError.value = 'Execution failed. Check logs for details.'
  }
})
</script>

<style scoped>
.side-panel {
  width: 280px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  padding: 20px;
  overflow-y: auto;
}
h3 {
  margin: 0 0 16px 0;
  color: #303133;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.label {
  color: #909399;
  font-size: 14px;
}
.info-value {
  font-size: 14px;
  color: #606266;
}
.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.status-idle { background: #f4f4f5; color: #909399; }
.status-running { background: #ecf5ff; color: #409EFF; }
.status-success { background: #f0f9eb; color: #67C23A; }
.status-failed { background: #fef0f0; color: #F56C6C; }
.status-skipped { background: #fdf6ec; color: #E6A23C; }
.hint {
  color: #c0c4cc;
  text-align: center;
  margin-top: 40px;
}
.error-section {
  margin-top: 12px;
}
.error-section h4 {
  color: #F56C6C;
  margin: 0 0 8px 0;
}
.error-text {
  font-size: 13px;
  color: #606266;
  background: #fef0f0;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
}
</style>
