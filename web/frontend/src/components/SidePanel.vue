<template>
  <div class="side-panel-wrapper" :style="{ width: panelWidth + 'px' }">
    <div class="resize-handle" @mousedown="startResize"></div>
    <div class="side-panel">
      <template v-if="step">
        <!-- Header -->
        <div class="panel-header">
          <h3>{{ step }}</h3>
          <span :class="'status-badge status-' + (status || 'idle')">{{ status || 'idle' }}</span>
        </div>

        <!-- Basic Info -->
        <div class="section">
          <div class="section-title">Basic Info</div>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Tool</span>
              <span class="info-value">{{ toolName || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Step</span>
              <span class="info-value">{{ step }}</span>
            </div>
          </div>
        </div>

        <!-- Sub-steps -->
        <div v-if="stepDetail && stepDetail.sub_steps && stepDetail.sub_steps.length" class="section">
          <div class="section-title">Sub-steps ({{ stepDetail.sub_steps.length }})</div>
          <div class="substep-list">
            <CodeViewer
              v-for="sub in stepDetail.sub_steps"
              :key="sub"
              :name="sub"
              :tag="subStepFile(sub) ? '.tcl' : ''"
              :file-path="subStepFile(sub)"
            />
          </div>
        </div>

        <!-- Hooks -->
        <div v-if="stepDetail && stepDetail.hooks && stepDetail.hooks.length" class="section">
          <div class="section-title">Hooks ({{ stepDetail.hooks.length }})</div>
          <div class="substep-list">
            <CodeViewer
              v-for="hook in stepDetail.hooks"
              :key="hook.name"
              :name="hook.name"
              tag="hook"
              tag-class="hook-tag"
              :file-path="hook.path"
            />
          </div>
        </div>

        <!-- Invoke Command -->
        <div v-if="stepDetail && stepDetail.invoke && stepDetail.invoke.length" class="section">
          <div class="section-title">Invoke</div>
          <div class="invoke-block">
            <div v-for="(seg, idx) in stepDetail.invoke" :key="idx" class="invoke-line">
              <span class="invoke-seg">{{ seg }}</span>
            </div>
          </div>
        </div>

        <!-- File Paths -->
        <div v-if="allFilePaths.length" class="section">
          <div class="section-title">File Paths</div>
          <div class="path-list">
            <div v-for="f in allFilePaths" :key="f.label" class="path-item">
              <div class="path-top-row">
                <span class="path-label">{{ f.label }}</span>
                <button class="copy-btn" @click="copyPath(f.path, $event)">{{ copiedPath === f.path ? '&#10003;' : 'Copy' }}</button>
              </div>
              <span class="path-value">{{ f.path }}</span>
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-if="status === 'failed'" class="section">
          <div class="section-title error-title">Error</div>
          <div class="error-block">
            Execution failed. Check logs for details.
          </div>
        </div>
      </template>
      <template v-else>
        <div class="empty-state">
          <div class="empty-icon">&#9656;</div>
          <p>Right-click a node and select <strong>Details</strong></p>
          <p class="empty-sub">to see step information</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import CodeViewer from './CodeViewer.vue'

const props = defineProps({
  step: String,
  status: String,
  toolName: String,
  stepDetail: Object,
})

const panelWidth = ref(380)
const copiedPath = ref('')
let resizing = false

const allFilePaths = computed(() => {
  const files = props.stepDetail?.files || {}
  const result = []
  // Generated cmd files (workspace)
  const cmdLabels = {
    config_tcl: 'config.tcl',
    step_tcl: 'step.tcl',
    debug_tcl: 'debug.tcl',
    launcher: 'launcher (.sh)',
  }
  for (const [key, label] of Object.entries(cmdLabels)) {
    if (files[key]) result.push({ label, path: files[key] })
  }
  // Sub-step source files (resources)
  if (files.sub_step_files) {
    for (const [sub, path] of Object.entries(files.sub_step_files)) {
      result.push({ label: `${sub}.tcl`, path })
    }
  }
  return result
})

function subStepFile(sub) {
  return props.stepDetail?.files?.sub_step_files?.[sub] || ''
}

function copyPath(path, event) {
  navigator.clipboard.writeText(path)
  copiedPath.value = path
  setTimeout(() => { copiedPath.value = '' }, 1500)
}

function startResize(e) {
  e.preventDefault()
  resizing = true
  const startX = e.clientX
  const startWidth = panelWidth.value

  function onMouseMove(e) {
    if (!resizing) return
    const delta = startX - e.clientX
    panelWidth.value = Math.max(280, Math.min(800, startWidth + delta))
  }

  function onMouseUp() {
    resizing = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.side-panel-wrapper {
  position: relative;
  min-width: 280px;
  max-width: 800px;
}

.resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  width: 4px;
  height: 100%;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;
  z-index: 10;
}

.resize-handle:hover {
  background: #409EFF;
}

.side-panel {
  background: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.section {
  padding: 14px 20px;
  border-bottom: 1px solid #f5f5f5;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 13px;
  color: #909399;
}

.info-value {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.substep-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.invoke-block {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 10px 12px;
  overflow-x: auto;
}

.invoke-line {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.invoke-seg {
  color: #d4d4d4;
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.path-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background 0.15s;
}

.path-item:hover {
  background: #f5f7fa;
}

.path-top-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.path-label {
  font-size: 11px;
  font-weight: 600;
  color: #409EFF;
}

.copy-btn {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 3px;
  background: #fff;
  color: #909399;
  cursor: pointer;
  transition: all 0.15s;
}

.copy-btn:hover {
  border-color: #409EFF;
  color: #409EFF;
}

.path-value {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 10px;
  color: #909399;
  word-break: break-all;
}

.status-badge {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.status-idle { background: #f4f4f5; color: #909399; }
.status-running { background: #ecf5ff; color: #409EFF; }
.status-success { background: #f0f9eb; color: #67C23A; }
.status-failed { background: #fef0f0; color: #F56C6C; }
.status-skipped { background: #fdf6ec; color: #E6A23C; }

.error-title { color: #F56C6C; }

.error-block {
  font-size: 13px;
  color: #606266;
  background: #fef0f0;
  padding: 10px 12px;
  border-radius: 4px;
  border-left: 3px solid #F56C6C;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 12px;
  color: #dcdfe6;
}

.empty-state p {
  margin: 4px 0;
  font-size: 13px;
}

.empty-sub {
  color: #dcdfe6;
  font-size: 12px;
}
</style>
