<template>
  <div class="flex items-center gap-1.5 text-[10px] text-gray-500">
    <iconify-icon icon="mdi:clock-outline" class="text-cyan-400"></iconify-icon>
    <span>数据更新时间：</span>
    <span class="text-cyan-300 font-mono">{{ currentTime }}</span>
    <span class="mx-1">|</span>
    <span>下次更新：</span>
    <span class="text-gray-400 font-mono">{{ nextUpdateTime }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const currentTime = ref('');
const nextUpdateTime = ref('');

const updateTime = () => {
  const now = new Date();
  
  // 格式化当前时间
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  
  currentTime.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  
  // 计算下次更新时间（明天 08:00）
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(8, 0, 0, 0);
  
  const tomorrowMonth = String(tomorrow.getMonth() + 1).padStart(2, '0');
  const tomorrowDay = String(tomorrow.getDate()).padStart(2, '0');
  
  nextUpdateTime.value = `明天 08:00`;
};

let timer = null;

onMounted(() => {
  updateTime();
  // 每秒更新一次时间
  timer = setInterval(updateTime, 1000);
});

onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
  }
});
</script>
