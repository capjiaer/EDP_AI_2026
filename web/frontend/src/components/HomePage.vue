<template>
  <div class="home-page">
    <!-- Left column -->
    <div class="home-card">
      <!-- Init New Project -->
      <div class="home-section">
        <div class="section-title">Init New Project</div>
        <el-form label-width="120px" class="init-form">
          <el-form-item label="WORK_PATH" required>
            <el-input v-model="workPath" placeholder="/data/work" />
          </el-form-item>
          <el-form-item label="Foundry" required>
            <el-select v-model="formFoundry" placeholder="Foundry" style="width:100%">
              <el-option v-for="f in foundryOptions" :key="f" :label="f" :value="f" />
            </el-select>
          </el-form-item>
          <el-form-item label="Node" required>
            <el-select v-model="formNode" placeholder="Node" style="width:100%" :disabled="!formFoundry">
              <el-option v-for="n in nodeOptions" :key="n" :label="n" :value="n" />
            </el-select>
          </el-form-item>
          <el-form-item label="Project" required>
            <el-select v-model="formProject" filterable allow-create placeholder="Select or type new" style="width:100%">
              <el-option v-for="p in projectNameOptions" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
          <el-form-item label="Version" required>
            <el-select v-model="formVersion" style="width:100%">
              <el-option label="P85" value="P85" />
              <el-option label="P95" value="P95" />
              <el-option label="P100" value="P100" />
            </el-select>
          </el-form-item>
          <el-form-item label="Graph Config">
            <el-select v-model="formGraphConfig" placeholder="Graph Config" style="width:100%" :disabled="formGraphConfigs.length === 0">
              <el-option v-for="gc in formGraphConfigs" :key="gc.name" :label="gc.name" :value="gc.name" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="initLoading" :disabled="!canInit" @click="handleInit">
              Init Project
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-divider />

      <!-- Existing Projects -->
      <div class="home-section">
        <div class="section-header">
          <div class="section-title">Existing Projects</div>
          <div class="section-actions">
            <el-input v-model="search" placeholder="Search..." size="small" clearable style="width:180px" />
            <el-button size="small" text @click="refreshProjects">Refresh</el-button>
          </div>
        </div>

        <div v-if="loadingProjects" class="state-center">
          <span style="color:#909399">Scanning workspace...</span>
        </div>
        <div v-else-if="!workPathDetected" class="state-center">
          <p><strong>WORK_PATH</strong> is not configured.</p>
          <p class="state-hint">Set WORK_PATH above and init a project to get started.</p>
        </div>
        <div v-else-if="filteredProjects.length === 0" class="state-center">
          <p>No projects found in <strong>{{ workPathDetected }}</strong></p>
          <p class="state-hint">Use the form above to create one.</p>
        </div>
        <div v-else class="project-list">
          <div v-for="proj in filteredProjects" :key="proj.name" class="project-group">
            <div class="project-name">{{ proj.name }}</div>
            <div class="version-list">
              <div v-for="ver in proj.versions" :key="ver.version" class="version-row" @click="selectProject(proj, ver)">
                <div class="version-label">{{ ver.version }}</div>
                <div class="version-tech">
                  <el-tag size="small" effect="plain">{{ ver.foundry }}</el-tag>
                  <el-tag size="small" effect="plain" type="info">{{ ver.node }}</el-tag>
                </div>
                <div class="version-meta">
                  <span>{{ ver.block_count }} block(s)</span>
                  <span v-if="ver.created_by" class="meta-light">by {{ ver.created_by }}</span>
                </div>
                <div class="version-action">
                  <el-button size="small" plain @click.stop="selectProject(proj, ver)">Config</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right column -->
    <div class="home-info">
      <!-- Default: how it works -->
      <template v-if="!selectedProject">
        <div class="info-title">How it works</div>
        <div class="info-steps">
          <div class="info-step">
            <div class="info-step-num">1</div>
            <div><strong>Init a project</strong> — set WORK_PATH, pick foundry/node, name your project.</div>
          </div>
          <div class="info-step">
            <div class="info-step-num">2</div>
            <div><strong>Select a project</strong> from the list to configure blocks and users.</div>
          </div>
          <div class="info-step">
            <div class="info-step-num">3</div>
            <div><strong>Enter Graph Mode</strong> to visualize step dependencies and run steps.</div>
          </div>
        </div>
        <div v-if="workPathDetected" class="info-path">
          <div class="info-path-label">WORK_PATH</div>
          <code>{{ workPathDetected }}</code>
        </div>
        <!-- Config file preview -->
        <div v-if="formGraphConfig && formGraphConfigContent" class="info-section">
          <div class="info-section-label">{{ formGraphConfig }}</div>
          <pre class="info-config-code">{{ formGraphConfigContent }}</pre>
        </div>
      </template>

      <!-- Project selected: config panel -->
      <template v-else>
        <div class="info-back">
          <el-button text size="small" @click="selectedProject = null">← Back</el-button>
        </div>
        <div class="info-pj-title">{{ selectedProject.name }}</div>

        <el-descriptions :column="1" border size="small" class="info-pj-desc">
          <el-descriptions-item label="Foundry">{{ selectedProject.foundry }}</el-descriptions-item>
          <el-descriptions-item label="Node">{{ selectedProject.node }}</el-descriptions-item>
          <el-descriptions-item label="Version">{{ selectedProject.version }}</el-descriptions-item>
          <el-descriptions-item label="Graph Config">{{ selectedProject.graphConfig || '(none)' }}</el-descriptions-item>
        </el-descriptions>

        <!-- Existing Blocks -->
        <div v-if="pjExistingBlocks.length" class="info-section">
          <div class="info-section-label">Existing Blocks ({{ pjExistingBlocks.length }})</div>
          <div class="pj-block-row" v-for="blk in pjExistingBlocks" :key="blk.name">
            <span class="pj-block-name">{{ blk.name }}</span>
            <span class="pj-block-users">by {{ blk.created_by }}
              <span v-if="blk.users.length"> · {{ blk.users.join(', ') }}</span>
            </span>
          </div>
        </div>

        <!-- Block Users -->
        <div class="info-section">
          <div class="info-section-label">Block Users</div>
          <div v-if="Object.keys(pjBlockUsers).length">
            <div v-for="(users, block) in pjBlockUsers" :key="block" class="pj-block-row">
              <span class="pj-block-name">{{ block }}</span>
              <span class="pj-block-users">{{ users.join(', ') }}</span>
              <el-button text size="small" @click="pjRemoveBlockUser(block)">✕</el-button>
            </div>
          </div>
          <div class="pj-block-add">
            <el-input v-model="pjNewBlockName" placeholder="Block" size="small" style="width:100%" />
            <el-input v-model="pjNewBlockUsers" placeholder="user1,user2,..." size="small" style="width:100%" />
            <el-button size="small" :disabled="!pjNewBlockName || !pjNewBlockUsers" @click="pjAddBlockUser">Add</el-button>
          </div>
        </div>

        <div class="info-enter-btn">
          <el-button type="primary" size="large" :loading="pjSaving" @click="handleDone">Done</el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['select-project'])

// --- WORK_PATH ---
const workPath = ref('')
const workPathDetected = ref('')

// --- Init form ---
const formFoundry = ref('')
const formNode = ref('')
const formProject = ref('')
const formVersion = ref('P85')
const formGraphConfig = ref('')
const formGraphConfigs = ref([])
const formGraphConfigContent = ref('')
const initLoading = ref(false)

// --- Project list ---
const projects = ref([])
const loadingProjects = ref(true)
const search = ref('')

// --- Template projects (from EDP_CENTER) for init form ---
const templateProjects = ref([])  // [{foundry, nodes: [{node, projects: [str]}]}]

const foundryOptions = computed(() => templateProjects.value.map(p => p.foundry))

const nodeOptions = computed(() => {
  const f = templateProjects.value.find(p => p.foundry === formFoundry.value)
  return f ? f.nodes.map(n => n.node) : []
})

const projectNameOptions = computed(() => {
  const f = templateProjects.value.find(p => p.foundry === formFoundry.value)
  if (!f) return []
  const n = f.nodes.find(n => n.node === formNode.value)
  return n ? n.projects : []
})

// --- Workspace projects (from WORK_PATH) for existing list ---
const workspaceProjects = ref([])

const filteredProjects = computed(() => {
  if (!search.value) return workspaceProjects.value
  const q = search.value.toLowerCase()
  return workspaceProjects.value.map(p => ({
    ...p,
    versions: p.versions.filter(v =>
      v.version.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)
    ),
  })).filter(p => p.versions.length)
})

const canInit = computed(() =>
  workPath.value && formFoundry.value && formNode.value && formProject.value && formVersion.value
)

// --- Fetch graph configs when foundry/node/project selected in form ---
watch([formFoundry, formNode, formProject], async ([f, n, p]) => {
  if (f && n && p) {
    formGraphConfig.value = ''
    formGraphConfigs.value = []
    try {
      const params = new URLSearchParams({ foundry: f, node: n, project: p })
      const res = await fetch(`/api/init/graph-configs?${params}`)
      if (res.ok) {
        const data = await res.json()
        formGraphConfigs.value = data.graph_configs || []
        if (formGraphConfigs.value.length === 1) {
          formGraphConfig.value = formGraphConfigs.value[0].name
        }
      }
    } catch { /* ignore */ }
  }
})

// --- Fetch config content when selected ---
watch(formGraphConfig, async (gc) => {
  if (!gc || !formFoundry.value || !formNode.value || !formProject.value) {
    formGraphConfigContent.value = ''
    return
  }
  try {
    const params = new URLSearchParams({
      foundry: formFoundry.value, node: formNode.value, project: formProject.value, graph_config: gc,
    })
    const res = await fetch(`/api/init/graph-config-content?${params}`)
    if (res.ok) {
      const data = await res.json()
      formGraphConfigContent.value = data.content
    }
  } catch { /* ignore */ }
})

// --- Init project ---
async function handleInit() {
  initLoading.value = true
  try {
    const res = await fetch('/api/init/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        work_path: workPath.value,
        project_name: formProject.value,
        version: formVersion.value,
        foundry: formFoundry.value,
        node: formNode.value,
        graph_config: formGraphConfig.value || null,
        block_users: {},
      }),
    })
    if (res.ok) {
      ElMessage.success(`Project ${formProject.value} initialized!`)
      // Reset form
      formFoundry.value = ''
      formNode.value = ''
      formProject.value = ''
      formVersion.value = 'P85'
      formGraphConfig.value = ''
      formGraphConfigs.value = []
      formGraphConfigContent.value = ''
      // Refresh list
      await refreshProjects()
    } else {
      const err = await res.json()
      ElMessage.error(err.error || 'Init failed')
    }
  } catch (e) {
    ElMessage.error('Init failed: ' + e.message)
  } finally {
    initLoading.value = false
  }
}

// --- Project list ---
async function refreshProjects() {
  loadingProjects.value = true
  try {
    const res = await fetch('/api/workspace/projects')
    if (res.ok) {
      const data = await res.json()
      workPathDetected.value = data.work_path || ''
      workspaceProjects.value = data.projects || []
      // Auto-fill workPath from detected
      if (data.work_path && !workPath.value) {
        workPath.value = data.work_path
      }
    }
  } catch { /* ignore */ }
  loadingProjects.value = false
}

// --- Selected project config (right panel) ---
const selectedProject = ref(null)
const pjBlockUsers = ref({})
const pjExistingBlocks = ref([])
const pjNewBlockName = ref('')
const pjNewBlockUsers = ref('')
const pjSaving = ref(false)

function selectProject(proj, ver) {
  selectedProject.value = {
    name: proj.name,
    foundry: ver.foundry,
    node: ver.node,
    version: ver.version,
    graphConfig: ver.graph_config || '',
    blockUsers: { ...(ver.block_users || {}) },
  }
  pjBlockUsers.value = { ...(ver.block_users || {}) }
  pjExistingBlocks.value = []
  fetchExistingBlocks(proj.name, ver.version)
}

async function handleDone() {
  if (!selectedProject.value) return
  pjSaving.value = true
  try {
    const res = await fetch('/api/workspace/block-users', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: selectedProject.value.name,
        version: selectedProject.value.version,
        block_users: pjBlockUsers.value,
      }),
    })
    if (res.ok) {
      ElMessage.success('Block users saved')
      selectedProject.value = null
      await refreshProjects()
    } else {
      const err = await res.json()
      ElMessage.error(err.error || 'Save failed')
    }
  } catch {
    ElMessage.error('Save failed')
  } finally {
    pjSaving.value = false
  }
}

async function fetchExistingBlocks(pName, pVersion) {
  try {
    const params = new URLSearchParams({ project: pName, version: pVersion })
    const res = await fetch(`/api/blocks?${params}`)
    if (res.ok) {
      const data = await res.json()
      pjExistingBlocks.value = data.blocks || []
    }
  } catch { /* ignore */ }
}

function pjAddBlockUser() {
  const users = pjNewBlockUsers.value.split(',').map(u => u.trim()).filter(Boolean)
  if (pjNewBlockName.value && users.length) {
    pjBlockUsers.value = { ...pjBlockUsers.value, [pjNewBlockName.value]: users }
    pjNewBlockName.value = ''
    pjNewBlockUsers.value = ''
  }
}

function pjRemoveBlockUser(block) {
  const { [block]: _, ...rest } = pjBlockUsers.value
  pjBlockUsers.value = rest
}


onMounted(async () => {
  // Fetch work path
  try {
    const res = await fetch('/api/init/work-path')
    if (res.ok) {
      const data = await res.json()
      if (data.work_path) workPath.value = data.work_path
    }
  } catch { /* ignore */ }

  // Fetch template projects for init form dropdowns
  try {
    const res = await fetch('/api/projects')
    if (res.ok) templateProjects.value = await res.json()
  } catch { /* ignore */ }

  await refreshProjects()
})
</script>

<style scoped>
.home-page {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 24px;
  padding: 40px 20px;
  background: #f0f2f5;
  overflow-y: auto;
}
.home-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  width: 700px;
  max-width: 100%;
  box-shadow: 0 4px 24px rgba(0,0,0,.08);
  flex-shrink: 0;
}
.home-section {
  margin-bottom: 8px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 16px;
}
.section-header .section-title {
  margin-bottom: 0;
}
.init-form {
  margin-top: 8px;
}
.state-center {
  text-align: center;
  padding: 40px 20px;
  color: #606266;
}
.state-hint {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}

/* Project list */
.project-group {
  margin-bottom: 20px;
}
.project-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  padding: 8px 0;
  border-bottom: 2px solid #409eff;
  margin-bottom: 8px;
}
.version-list {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}
.version-row {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: background .15s;
  gap: 12px;
}
.version-row:last-child { border-bottom: none; }
.version-row:hover { background: #f5f7fa; }
.version-label {
  font-weight: 600;
  color: #303133;
  min-width: 60px;
}
.version-tech {
  display: flex;
  gap: 6px;
  align-items: center;
  min-width: 140px;
}
.version-meta {
  flex: 1;
  font-size: 13px;
  color: #606266;
}
.meta-light {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
.version-action {
  min-width: 70px;
  text-align: right;
}

/* Info panel */
.home-info {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  width: 280px;
  flex-shrink: 0;
  box-shadow: 0 4px 24px rgba(0,0,0,.08);
}
.info-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 20px;
}
.info-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
.info-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.info-step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info-path {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}
.info-path-label {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: .5px;
  margin-bottom: 4px;
}
.info-path code {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}
.info-section {
  margin-top: 20px;
}
.info-section-label {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 8px;
  word-break: break-all;
}
.info-config-code {
  margin: 0;
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre;
}
.info-back {
  margin-bottom: 4px;
}
.info-pj-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 12px;
}
.info-pj-desc {
  margin-bottom: 16px;
}
.info-pj-desc :deep(.el-descriptions__label) {
  font-size: 11px;
}
.info-pj-desc :deep(.el-descriptions__content) {
  font-size: 12px;
}
.pj-block-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 0;
}
.pj-block-name {
  font-weight: 600;
  color: #303133;
  min-width: 60px;
}
.pj-block-users {
  flex: 1;
  color: #606266;
  font-size: 11px;
}
.pj-block-add {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.info-enter-btn {
  margin-top: 20px;
  text-align: center;
}
</style>
