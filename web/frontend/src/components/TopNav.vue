<template>
  <div class="top-nav">
    <span class="nav-title">EDP Web UI</span>
    <span>{{ foundry }} / {{ node }} / {{ project }}</span>
  </div>
</template>

<script setup>
defineProps({ foundry: String, node: String, project: String, projects: Array })
</script>

<style scoped>
.top-nav { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.nav-title { font-weight: 600; font-size: 18px; }
</style>
