<template>
  <div class="step-node" :class="statusClass" @click="handleClick">
    <div class="step-label">{{ data.label }}</div>
    <div v-if="data.tool" class="step-tool">{{ data.tool }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  id: String,
  data: Object,
})

const emit = defineEmits(['run-step'])

const STATUS_CLASSES = {
  idle: 'status-idle',
  running: 'status-running',
  success: 'status-success',
  failed: 'status-failed',
  skipped: 'status-skipped',
}

const statusClass = computed(() => STATUS_CLASSES[props.data?.status] || 'status-idle')

function handleClick() {
  emit('run-step', props.id)
}
</script>

<style scoped>
.step-node {
  padding: 10px 16px;
  border-radius: 8px;
  border: 2px solid #ddd;
  cursor: pointer;
  min-width: 120px;
  text-align: center;
  transition: all 0.3s ease;
  background: white;
}
.step-node:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.step-label {
  font-weight: 600;
  font-size: 14px;
}
.step-tool {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

.status-idle { border-color: #c0c4cc; }
.status-running {
  border-color: #409EFF;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.5);
  animation: pulse 1.5s ease-in-out infinite;
}
.status-success { border-color: #67C23A; background: #f0f9eb; }
.status-failed { border-color: #F56C6C; background: #fef0f0; }
.status-skipped { border-color: #E6A23C; background: #fdf6ec; }

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(64, 158, 255, 0.3); }
  50% { box-shadow: 0 0 16px rgba(64, 158, 255, 0.7); }
}
</style>
