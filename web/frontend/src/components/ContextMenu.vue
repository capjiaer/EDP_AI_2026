<template>
  <teleport to="body">
    <div
      v-if="visible"
      class="context-menu-overlay"
      @click="$emit('close')"
      @contextmenu.prevent="$emit('close')"
    >
      <div class="context-menu" :style="menuStyle">
        <div class="context-menu-item" @click="handleRun">
          <span class="menu-icon">&#9654;</span>
          <span>Run</span>
        </div>
        <div class="context-menu-item" @click="handleDetails">
          <span class="menu-icon">&#9432;</span>
          <span>Details</span>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: Boolean,
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  stepId: { type: String, default: '' },
})

const emit = defineEmits(['close', 'run', 'details'])

const menuStyle = computed(() => ({
  left: `${props.x}px`,
  top: `${props.y}px`,
}))

function handleRun() {
  emit('run', props.stepId)
  emit('close')
}

function handleDetails() {
  emit('details', props.stepId)
  emit('close')
}
</script>

<style scoped>
.context-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
}

.context-menu {
  position: fixed;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  min-width: 140px;
  z-index: 10000;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  color: #303133;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

.menu-icon {
  font-size: 12px;
  width: 16px;
  text-align: center;
}
</style>
