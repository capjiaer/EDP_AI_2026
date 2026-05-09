<template>
  <div class="config-page">
    <div class="config-card">
      <!-- Header -->
      <div class="config-header">
        <el-button text size="small" @click="$emit('back')">← Back</el-button>
        <div class="config-title">Project Configuration</div>
      </div>

      <!-- Project info -->
      <el-descriptions :column="3" border size="small" class="config-info">
        <el-descriptions-item label="Foundry">{{ foundry }}</el-descriptions-item>
        <el-descriptions-item label="Node">{{ node }}</el-descriptions-item>
        <el-descriptions-item label="Project">{{ project }}</el-descriptions-item>
        <el-descriptions-item label="Version">{{ version }}</el-descriptions-item>
        <el-descriptions-item label="Graph Config">{{ graphConfig || '(none)' }}</el-descriptions-item>
      </el-descriptions>

      <!-- Existing Blocks -->
      <div v-if="existingBlocks.length" class="config-section">
        <label class="config-section-label">Existing Blocks ({{ existingBlocks.length }})</label>
        <div class="block-table">
          <div v-for="blk in existingBlocks" :key="blk.name" class="block-row">
            <span class="block-name">{{ blk.name }}</span>
            <span class="block-users">
              by {{ blk.created_by }}
              <span v-if="blk.user_count > 0"> · {{ blk.user_count }} user(s)</span>
              <span v-if="blk.users.length" class="block-user-list"> · {{ blk.users.join(', ') }}</span>
            </span>
            <el-tag v-if="blk.created_at" size="small" type="info" effect="plain">
              {{ blk.created_at.slice(0, 10) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- Block Users -->
      <div class="config-section">
        <label class="config-section-label">Block Users</label>
        <div v-if="Object.keys(localBlockUsers).length" class="block-table">
          <div v-for="(users, block) in localBlockUsers" :key="block" class="block-row">
            <span class="block-name">{{ block }}</span>
            <span class="block-users">{{ users.join(', ') }}</span>
            <el-button text size="small" @click="removeBlockUser(block)">✕</el-button>
          </div>
        </div>
        <div class="block-add">
          <el-input v-model="newBlockName" placeholder="Block name" size="small" style="width:140px" />
          <el-input v-model="newBlockUsers" placeholder="user1,user2,..." size="small" style="width:240px" />
          <el-button size="small" :disabled="!newBlockName || !newBlockUsers" @click="addBlockUser">Add</el-button>
        </div>
      </div>

      <!-- Actions -->
      <div class="config-actions">
        <el-button type="primary" size="large" @click="$emit('enter-graph', { ...localBlockUsers })">
          Enter Graph Mode
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  foundry: { type: String, default: '' },
  node: { type: String, default: '' },
  project: { type: String, default: '' },
  version: { type: String, default: '' },
  graphConfig: { type: String, default: '' },
  blockUsers: { type: Object, default: () => ({}) },
})

defineEmits(['back', 'enter-graph'])

const localBlockUsers = ref({})
const newBlockName = ref('')
const newBlockUsers = ref('')
const existingBlocks = ref([])

// Sync from parent
watch(() => props.blockUsers, (bu) => {
  localBlockUsers.value = { ...bu }
}, { immediate: true, deep: true })

function addBlockUser() {
  const users = newBlockUsers.value.split(',').map(u => u.trim()).filter(Boolean)
  if (newBlockName.value && users.length) {
    localBlockUsers.value = { ...localBlockUsers.value, [newBlockName.value]: users }
    newBlockName.value = ''
    newBlockUsers.value = ''
  }
}

function removeBlockUser(block) {
  const { [block]: _, ...rest } = localBlockUsers.value
  localBlockUsers.value = rest
}

async function fetchBlocks() {
  if (!props.project || !props.version) return
  try {
    const params = new URLSearchParams({ project: props.project, version: props.version })
    const res = await fetch(`/api/blocks?${params}`)
    if (res.ok) {
      const data = await res.json()
      existingBlocks.value = data.blocks || []
    }
  } catch { /* ignore */ }
}

onMounted(fetchBlocks)

// Re-fetch when props change
watch([() => props.project, () => props.version], fetchBlocks)
</script>

<style scoped>
.config-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  padding: 40px 20px;
}
.config-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  width: 700px;
  box-shadow: 0 4px 24px rgba(0,0,0,.08);
}
.config-header {
  margin-bottom: 20px;
}
.config-title {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  margin-top: 8px;
}
.config-info {
  margin-bottom: 20px;
}
.config-section {
  margin-top: 20px;
}
.config-section-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}
.block-table {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
}
.block-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid #f0f2f5;
  font-size: 13px;
}
.block-row:last-child { border-bottom: none; }
.block-name {
  font-weight: 600;
  color: #303133;
  min-width: 100px;
}
.block-users {
  flex: 1;
  color: #606266;
}
.block-user-list {
  font-size: 12px;
  color: #909399;
}
.block-add {
  display: flex;
  gap: 8px;
  align-items: center;
}
.config-actions {
  margin-top: 24px;
  text-align: right;
}
</style>
