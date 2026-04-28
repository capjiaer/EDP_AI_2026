<template>
  <div class="top-nav">
    <div class="nav-title">EDP Web UI</div>
    <div class="nav-actions">
      <div class="nav-selects">
        <el-select v-model="localFoundry" placeholder="Foundry" size="small" style="width: 140px">
          <el-option v-for="f in projects" :key="f.foundry" :label="f.foundry" :value="f.foundry" />
        </el-select>
        <el-select v-model="localNode" placeholder="Node" size="small" style="width: 120px">
          <el-option v-for="n in currentNodes" :key="n.node" :label="n.node" :value="n.node" />
        </el-select>
        <el-select v-model="localProject" placeholder="Project" size="small" style="width: 140px">
          <el-option v-for="p in currentProjects" :key="p" :label="p" :value="p" />
        </el-select>
      </div>
      <el-button type="primary" size="small" @click="$emit('open-init')">Init</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  foundry: String,
  node: String,
  project: String,
  projects: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'update:foundry', 'update:node', 'update:project', 'open-init',
])

const localFoundry = computed({
  get: () => props.foundry,
  set: (v) => emit('update:foundry', v),
})
const localNode = computed({
  get: () => props.node,
  set: (v) => emit('update:node', v),
})
const localProject = computed({
  get: () => props.project,
  set: (v) => emit('update:project', v),
})

const currentNodes = computed(() => {
  const f = props.projects.find(p => p.foundry === props.foundry)
  return f ? f.nodes : []
})

const currentProjects = computed(() => {
  const n = currentNodes.value.find(n => n.node === props.node)
  return n ? n.projects : []
})
</script>

<style scoped>
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.nav-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.nav-selects {
  display: flex;
  gap: 12px;
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
