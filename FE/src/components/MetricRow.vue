<template>
  <div class="metric-row">
    <span class="text-gray-300">{{ label }}</span>
    <div class="bar-bg">
      <div
        class="bar-fill"
        :class="barClass"
        :style="{ width: width + '%' }"
      ></div>
    </div>
    <span class="font-bold" :class="valueClass">{{ value }}</span>
    <span v-if="suffix" class="text-[10px] text-gray-500 ml-1">{{
      suffix
    }}</span>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  suffix: { type: String, default: "" },
  width: { type: Number, default: 50 },
  barClass: { type: String, default: "bg-green-400" },
  valueClass: { type: String, default: "text-green-400" },
});
</script>
