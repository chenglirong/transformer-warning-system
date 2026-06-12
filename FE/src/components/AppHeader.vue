<template>
  <header
    class="h-14 flex items-center justify-between px-6 border-b border-blue-900/40 relative"
    style="
      background: linear-gradient(
        180deg,
        rgba(30, 58, 138, 0.3),
        rgba(3, 7, 18, 0.8)
      );
    "
  >
    <div class="flex items-center gap-3 w-1/4 text-xs text-gray-400">
      <template v-if="showBack">
        <RouterLink
          to="/dashboard"
          class="text-gray-400 hover:text-cyan-300 text-xs flex items-center gap-1"
        >
          <iconify-icon icon="mdi:arrow-left"></iconify-icon> 返回大屏
        </RouterLink>
      </template>
      <template v-else>
        <iconify-icon
          class="text-cyan-400 text-xl"
          icon="mdi:shield-check"
        ></iconify-icon>
        <span>智能体自动预警中 · 每日 09:00 执行</span>
        <span
          class="bg-green-500/10 text-green-400 px-2 py-0.5 rounded border border-green-500/30"
          >在线</span
        >
      </template>
    </div>

    <h1
      class="font-bold tracking-[0.2em] title-glow text-white flex items-center gap-2"
      :class="titleSize"
    >
      <iconify-icon
        v-if="icon"
        class="text-cyan-400"
        :icon="icon"
      ></iconify-icon>
      <span>{{ title }}</span>
    </h1>

    <div
      class="flex items-center gap-3 text-xs text-gray-400 w-1/4 justify-end"
    >
      <!-- 页面级控件插槽(如 AnalysisView 的日期选择器) -->
      <slot name="actions"></slot>
      <span v-if="subtitle">{{ subtitle }}</span>
      <span class="text-cyan-300 font-mono">{{ clock }}</span>
    </div>
  </header>

  <!-- 规划中横幅:标注该页依赖尚未开发的模块(LSTM/预警/Agent),展示为交互设计稿 -->
  <div
    v-if="planning"
    class="flex items-center justify-center gap-2 py-1.5 text-[12px] font-medium"
    style="
      background: rgba(234, 179, 8, 0.12);
      border-bottom: 1px solid rgba(234, 179, 8, 0.35);
      color: #fcd34d;
    "
  >
    <iconify-icon icon="mdi:hammer-wrench" class="text-sm"></iconify-icon>
    <span>{{ planningText }}</span>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useClock } from "@/composables/useClock";

const props = defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  showBack: { type: Boolean, default: true },
  large: { type: Boolean, default: false },
  // 规划中标注:该页依赖未开发模块时置 true,顶部显示黄色横幅
  planning: { type: Boolean, default: false },
  planningText: {
    type: String,
    default: "本页为规划中功能的交互设计稿,所示数据为示意,非真实计算结果",
  },
});

const clock = useClock();
const titleSize = computed(() =>
  props.large ? "text-xl tracking-[0.3em]" : "text-lg",
);
</script>
