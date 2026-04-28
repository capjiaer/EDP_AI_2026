<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="Init Wizard"
    width="680px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <!-- Mode tabs -->
    <el-tabs v-model="mode" @tab-change="resetSteps">
      <el-tab-pane label="Project Init (PM)" name="project">
        <p class="tab-desc">Create a new project skeleton under WORK_PATH.</p>
        <el-steps :active="pmStep" finish-status="success" align-center>
          <el-step title="Work Path" />
          <el-step title="Project" />
          <el-step title="Graph Config" />
          <el-step title="Confirm" />
        </el-steps>
        <div class="step-content">
          <template v-if="pmStep === 0">
            <el-form label-width="120px">
              <el-form-item label="WORK_PATH" required>
                <el-input v-model="workPath" placeholder="/data/work">
                  <template #prepend>Path</template>
                </el-input>
              </el-form-item>
            </el-form>
            <el-alert v-if="!workPath" type="info" show-icon :closable="false">
              WORK_PATH is where your projects are stored on the server. Set an absolute path
              (e.g., /data/work, /home/user/edp_work).
            </el-alert>
          </template>

          <template v-if="pmStep === 1">
            <el-form label-width="120px">
              <el-form-item label="Foundry" required>
                <el-select v-model="pmFoundry" placeholder="Select foundry" style="width:100%">
                  <el-option v-for="f in foundryOptions" :key="f" :label="f" :value="f" />
                </el-select>
              </el-form-item>
              <el-form-item label="Node" required>
                <el-select v-model="pmNode" placeholder="Select node" style="width:100%"
                  :disabled="!pmFoundry">
                  <el-option v-for="n in nodeOptions" :key="n" :label="n" :value="n" />
                </el-select>
              </el-form-item>
              <el-form-item label="Project" required>
                <el-select v-model="pmProject" placeholder="Select project" style="width:100%"
                  :disabled="!pmNode">
                  <el-option v-for="p in projectOptions" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="Version" required>
                <el-select v-model="pmVersion" placeholder="Select version" style="width:100%">
                  <el-option label="P85" value="P85" />
                  <el-option label="P95" value="P95" />
                  <el-option label="P100" value="P100" />
                  <el-option label="Custom" value="__custom__" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="pmVersion === '__custom__'" label="Custom Ver" required>
                <el-input v-model="pmVersionCustom" placeholder="e.g. P110" />
              </el-form-item>
            </el-form>
          </template>

          <template v-if="pmStep === 2">
            <div v-if="pmGraphConfigsLoading" class="step-loading">Loading...</div>
            <div v-else-if="pmGraphConfigs.length === 0">
              <el-alert type="info" show-icon :closable="false">
                No graph configs found. Project will be created without one.
              </el-alert>
            </div>
            <el-form v-else label-width="120px">
              <el-form-item label="Graph Config">
                <el-radio-group v-model="pmGraphConfig">
                  <el-radio v-for="gc in pmGraphConfigs" :key="gc.name" :value="gc.name">
                    {{ gc.name }}
                  </el-radio>
                </el-radio-group>
              </el-form-item>
            </el-form>
          </template>

          <template v-if="pmStep === 3">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="WORK_PATH">{{ workPath }}</el-descriptions-item>
              <el-descriptions-item label="Foundry">{{ pmFoundry }}</el-descriptions-item>
              <el-descriptions-item label="Node">{{ pmNode }}</el-descriptions-item>
              <el-descriptions-item label="Project">{{ pmProject }}</el-descriptions-item>
              <el-descriptions-item label="Version">{{ pmVersionFinal }}</el-descriptions-item>
              <el-descriptions-item label="Graph Config">
                {{ pmGraphConfig || '(none)' }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Block Init (User)" name="block">
        <p class="tab-desc">Create a new block workspace under an existing project.</p>
        <el-steps :active="blkStep" finish-status="success" align-center>
          <el-step title="Work Path" />
          <el-step title="Project" />
          <el-step title="Block Info" />
          <el-step title="Confirm" />
        </el-steps>
        <div class="step-content">
          <template v-if="blkStep === 0">
            <el-form label-width="120px">
              <el-form-item label="WORK_PATH" required>
                <el-input v-model="workPath" placeholder="/data/work">
                  <template #prepend>Path</template>
                </el-input>
              </el-form-item>
            </el-form>
            <el-alert v-if="!workPath" type="info" show-icon :closable="false">
              WORK_PATH is where your projects are stored on the server.
            </el-alert>
          </template>

          <template v-if="blkStep === 1">
            <el-form label-width="120px">
              <el-form-item label="Foundry" required>
                <el-select v-model="blkFoundry" placeholder="Select foundry" style="width:100%">
                  <el-option v-for="f in foundryOptions" :key="f" :label="f" :value="f" />
                </el-select>
              </el-form-item>
              <el-form-item label="Node" required>
                <el-select v-model="blkNode" placeholder="Select node" style="width:100%"
                  :disabled="!blkFoundry">
                  <el-option v-for="n in nodeOptions" :key="n" :label="n" :value="n" />
                </el-select>
              </el-form-item>
              <el-form-item label="Project" required>
                <el-select v-model="blkProject" placeholder="Select project" style="width:100%"
                  :disabled="!blkNode">
                  <el-option v-for="p in projectOptions" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="Version" required>
                <el-select v-model="blkVersion" placeholder="Select version" style="width:100%">
                  <el-option label="P85" value="P85" />
                  <el-option label="P95" value="P95" />
                  <el-option label="P100" value="P100" />
                  <el-option label="Custom" value="__custom__" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="blkVersion === '__custom__'" label="Custom Ver" required>
                <el-input v-model="blkVersionCustom" placeholder="e.g. P110" />
              </el-form-item>
            </el-form>
          </template>

          <template v-if="blkStep === 2">
            <el-form label-width="120px">
              <el-form-item label="Block Name" required>
                <el-input v-model="blkBlockName" placeholder="e.g. top, pcie, cpu_core" />
              </el-form-item>
              <el-form-item label="User">
                <el-input v-model="blkUserName" placeholder="auto-detect">
                  <template #append>
                    <el-button @click="blkUserName = defaultUser">Reset</el-button>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="Branch">
                <el-input v-model="blkBranchName" placeholder="auto-generate" />
              </el-form-item>
              <el-form-item label="Link Mode">
                <el-switch v-model="blkLinkMode" />
                <span class="switch-hint">Copy (vs symlink) run outputs from source branch</span>
              </el-form-item>
            </el-form>
          </template>

          <template v-if="blkStep === 3">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="WORK_PATH">{{ workPath }}</el-descriptions-item>
              <el-descriptions-item label="Foundry">{{ blkFoundry }}</el-descriptions-item>
              <el-descriptions-item label="Node">{{ blkNode }}</el-descriptions-item>
              <el-descriptions-item label="Project">{{ blkProject }}</el-descriptions-item>
              <el-descriptions-item label="Version">{{ blkVersionFinal }}</el-descriptions-item>
              <el-descriptions-item label="Block">{{ blkBlockName }}</el-descriptions-item>
              <el-descriptions-item label="User">{{ blkUserName || '(auto)' }}</el-descriptions-item>
              <el-descriptions-item label="Branch">{{ blkBranchName || '(auto)' }}</el-descriptions-item>
            </el-descriptions>
          </template>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Error alert -->
    <el-alert v-if="error" type="error" show-icon :closable="true" @close="error = ''"
      class="error-alert">
      {{ error }}
    </el-alert>

    <!-- Footer -->
    <template #footer>
      <el-button @click="prevStep" :disabled="currentStepIndex === 0">Previous</el-button>
      <el-button @click="nextStep" type="primary" :disabled="!canProceed" :loading="submitting">
        {{ isLastStep ? 'Finish' : 'Next' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  visible: Boolean,
  projects: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:visible', 'init-complete'])

// --- Mode ---
const mode = ref('project')
const pmStep = ref(0)
const blkStep = ref(0)
const error = ref('')
const submitting = ref(false)

// --- Work Path (shared) ---
const workPath = ref('')

// --- PM mode state ---
const pmFoundry = ref('')
const pmNode = ref('')
const pmProject = ref('')
const pmVersion = ref('P85')
const pmVersionCustom = ref('')
const pmGraphConfig = ref('')
const pmGraphConfigs = ref([])
const pmGraphConfigsLoading = ref(false)

// --- Block mode state ---
const blkFoundry = ref('')
const blkNode = ref('')
const blkProject = ref('')
const blkVersion = ref('P85')
const blkVersionCustom = ref('')
const blkBlockName = ref('')
const blkUserName = ref('')
const blkBranchName = ref('')
const blkLinkMode = ref(true)

// --- Computed ---
const currentStepIndex = computed(() => mode.value === 'project' ? pmStep.value : blkStep.value)

const maxStep = 3

const isLastStep = computed(() => currentStepIndex.value === maxStep)

const foundryOptions = computed(() => props.projects.map(p => p.foundry))

const nodeOptions = computed(() => {
  const f = props.projects.find(p => p.foundry === (mode.value === 'project' ? pmFoundry.value : blkFoundry.value))
  return f ? f.nodes.map(n => n.node) : []
})

const projectOptions = computed(() => {
  const f = props.projects.find(p => p.foundry === (mode.value === 'project' ? pmFoundry.value : blkFoundry.value))
  if (!f) return []
  const n = f.nodes.find(n => n.node === (mode.value === 'project' ? pmNode.value : blkNode.value))
  return n ? n.projects : []
})

const pmVersionFinal = computed(() =>
  pmVersion.value === '__custom__' ? pmVersionCustom.value : pmVersion.value
)

const blkVersionFinal = computed(() =>
  blkVersion.value === '__custom__' ? blkVersionCustom.value : blkVersion.value
)

// ---- Work path auto-fetch ----
onMounted(async () => {
  try {
    const res = await fetch('/api/init/work-path')
    if (res.ok) {
      const data = await res.json()
      if (data.work_path) workPath.value = data.work_path
    }
  } catch { /* ignore */ }

  try {
    const res = await fetch('/api/init/user-info')
    if (res.ok) {
      const data = await res.json()
      blkUserName.value = data.user_name || ''
      blkBranchName.value = data.default_branch || ''
    }
  } catch { /* ignore */ }
})

// ---- Graph configs load when project selection changes (PM mode) ----
watch([pmFoundry, pmNode, pmProject], async ([f, n, p]) => {
  if (f && n && p) {
    pmGraphConfigsLoading.value = true
    pmGraphConfig.value = ''
    try {
      const params = new URLSearchParams({ foundry: f, node: n, project: p })
      const res = await fetch(`/api/init/graph-configs?${params}`)
      if (res.ok) {
        const data = await res.json()
        pmGraphConfigs.value = data.graph_configs || []
        if (pmGraphConfigs.value.length === 1) {
          pmGraphConfig.value = pmGraphConfigs.value[0].name
        }
      }
    } catch { /* ignore */ }
    pmGraphConfigsLoading.value = false
  } else {
    pmGraphConfigs.value = []
  }
})

// ---- Navigation ----
function resetSteps() {
  pmStep.value = 0
  blkStep.value = 0
  error.value = ''
}

function prevStep() {
  error.value = ''
  if (mode.value === 'project') {
    if (pmStep.value > 0) pmStep.value--
  } else {
    if (blkStep.value > 0) blkStep.value--
  }
}

async function nextStep() {
  error.value = ''
  if (!isLastStep.value) {
    if (mode.value === 'project') pmStep.value++
    else blkStep.value++
    return
  }
  // Last step — submit
  submitting.value = true
  try {
    if (mode.value === 'project') {
      await submitProject()
    } else {
      await submitBlock()
    }
    emit('init-complete')
  } catch (e) {
    error.value = e.message || 'Submission failed'
  } finally {
    submitting.value = false
  }
}

async function submitProject() {
  const res = await fetch('/api/init/project', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      work_path: workPath.value,
      project_name: pmProject.value,
      version: pmVersionFinal.value,
      foundry: pmFoundry.value,
      node: pmNode.value,
      graph_config: pmGraphConfig.value || '',
    }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Project init failed')
}

async function submitBlock() {
  const res = await fetch('/api/init/block', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      work_path: workPath.value,
      project_name: blkProject.value,
      version: blkVersionFinal.value,
      foundry: blkFoundry.value,
      node: blkNode.value,
      block_name: blkBlockName.value,
      user_name: blkUserName.value,
      branch_name: blkBranchName.value,
      link_mode: blkLinkMode.value,
    }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Block init failed')
}

// ---- Validation ----
const canProceed = computed(() => {
  const step = currentStepIndex.value
  if (mode.value === 'project') {
    if (step === 0) return !!workPath.value
    if (step === 1) {
      if (!pmFoundry.value || !pmNode.value || !pmProject.value) return false
      if (pmVersion.value === '__custom__' && !pmVersionCustom.value) return false
      if (pmVersion.value !== '__custom__' && !pmVersion.value) return false
      return true
    }
    if (step === 2) return true  // graph config is optional
    if (step === 3) return true
  } else {
    if (step === 0) return !!workPath.value
    if (step === 1) {
      if (!blkFoundry.value || !blkNode.value || !blkProject.value) return false
      if (blkVersion.value === '__custom__' && !blkVersionCustom.value) return false
      if (blkVersion.value !== '__custom__' && !blkVersion.value) return false
      return true
    }
    if (step === 2) {
      if (!blkBlockName.value) return false
      return true
    }
    if (step === 3) return true
  }
  return false
})
</script>

<style scoped>
.tab-desc {
  font-size: 13px;
  color: #909399;
  margin: 0 0 16px 0;
}
.step-content {
  min-height: 200px;
  padding: 20px 0;
}
.step-loading {
  padding: 40px;
  text-align: center;
  color: #909399;
}
.error-alert {
  margin-top: 12px;
}
.switch-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
</style>
