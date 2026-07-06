<template>
  <span ref="numberRef" class="countup-number">{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';

const props = defineProps({
  endValue: {
    type: [Number, String],
    required: true
  },
  duration: {
    type: Number,
    default: 1500 // 动画时长（毫秒）
  },
  decimals: {
    type: Number,
    default: 0 // 小数位数
  },
  suffix: {
    type: String,
    default: '' // 后缀，如 '%', 'K'
  }
});

const numberRef = ref(null);
const displayValue = ref('0');

const animateNumber = (start, end, duration) => {
  const startTime = Date.now();
  const endNum = typeof end === 'string' ? parseFloat(end) : end;
  
  if (isNaN(endNum)) {
    displayValue.value = end + props.suffix;
    return;
  }
  
  const step = () => {
    const now = Date.now();
    const progress = Math.min((now - startTime) / duration, 1);
    
    // 使用 easeOutQuart 缓动函数
    const easeProgress = 1 - Math.pow(1 - progress, 4);
    
    const currentValue = start + (endNum - start) * easeProgress;
    displayValue.value = currentValue.toFixed(props.decimals) + props.suffix;
    
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      displayValue.value = endNum.toFixed(props.decimals) + props.suffix;
    }
  };
  
  requestAnimationFrame(step);
};

onMounted(() => {
  animateNumber(0, props.endValue, props.duration);
});

watch(() => props.endValue, (newVal, oldVal) => {
  const oldNum = typeof oldVal === 'string' ? parseFloat(oldVal) : oldVal;
  animateNumber(oldNum || 0, newVal, props.duration);
});
</script>

<style scoped>
.countup-number {
  display: inline-block;
  font-variant-numeric: tabular-nums;
}
</style>
