w
<template>
  <footer class="footer-standard">
    <div class="flex items-center gap-4">
      <DataUpdateTime />
      <div class="flex items-center gap-1.5">
        <iconify-icon icon="mdi:database" class="text-cyan-400"></iconify-icon>
        <span>数据集：IEC TC 10 公开数据集 + SMOTE 扩增</span>
      </div>
      <div class="flex items-center gap-1.5">
        <iconify-icon
          icon="mdi:chart-box"
          class="text-orange-400"
        ></iconify-icon>
        <span>当前展示：历史数据回测结果（5000+ 样本）</span>
      </div>
      <div class="flex items-center gap-1.5">
        <iconify-icon icon="mdi:flask" class="text-purple-400"></iconify-icon>
        <span>预处理：缺失值清洗 · MinMaxScaler 归一化</span>
      </div>
    </div>
    <div class="text-gray-600">
      电力设备健康管控智能体预警系统 v1.0 · 毕业设计演示
    </div>
  </footer>
</template>

<script setup>
import DataUpdateTime from "./DataUpdateTime.vue";
</script>

<style scoped>
.footer-standard {
  @apply px-3 pb-2 flex items-center justify-between text-[10px] text-gray-500;
}
</style>
