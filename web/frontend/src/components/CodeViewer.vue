<template>
  <div class="expandable-item" @click="toggle">
    <div class="expandable-header">
      <span class="expand-arrow" :class="{ rotated: isOpen }">&#9654;</span>
      <span class="item-name">{{ name }}</span>
      <span v-if="tag" :class="['file-tag', tagClass]">{{ tag }}</span>
    </div>
    <div v-if="isOpen" class="code-block">
      <div v-if="loading" class="code-loading">Loading...</div>
      <pre v-else-if="content">{{ content }}</pre>
      <div v-else class="code-empty">No content</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  name: String,
  tag: String,
  tagClass: String,
  filePath: String,
})

const isOpen = ref(false)
const content = ref('')
const loading = ref(false)

function toggle() {
  isOpen.value = !isOpen.value
  if (isOpen.value && !content.value && !loading.value && props.filePath) {
    loadCode()
  }
}

async function loadCode() {
  loading.value = true
  try {
    const res = await fetch(`/api/file-content?path=${encodeURIComponent(props.filePath)}`)
    if (res.ok) {
      const data = await res.json()
      content.value = data.content
    }
  } catch {
    content.value = '// Failed to load'
  }
  loading.value = false
}

watch(() => props.filePath, () => {
  isOpen.value = false
  content.value = ''
  loading.value = false
})
</script>

<style scoped>
.expandable-item {
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}
.expandable-item:hover {
  background: #f5f7fa;
}
.expandable-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
}
.expand-arrow {
  font-size: 10px;
  color: #c0c4cc;
  transition: transform 0.15s;
  width: 12px;
  flex-shrink: 0;
}
.expand-arrow.rotated {
  transform: rotate(90deg);
}
.item-name {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  color: #606266;
}
.file-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #ecf5ff;
  color: #409EFF;
  margin-left: auto;
}
.file-tag.hook-tag {
  background: #fdf6ec;
  color: #E6A23C;
}
.code-block {
  margin: 0 8px 8px 26px;
  background: #1e1e1e;
  border-radius: 4px;
  overflow-x: auto;
}
.code-block pre {
  margin: 0;
  padding: 10px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  line-height: 1.5;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}
.code-loading, .code-empty {
  padding: 8px 10px;
  font-size: 12px;
  color: #888;
}
</style>
