<template>
  <div class="timeline-container">
    <div v-for="(step, index) in steps" :key="index" class="timeline-item" :class="step.status">
      <div class="timeline-line" v-if="index < steps.length - 1"></div>
      <div class="timeline-dot">
        <iconify-icon :icon="step.icon" class="text-lg"></iconify-icon>
      </div>
      <div class="timeline-content">
        <div class="flex items-center justify-between mb-1">
          <span class="step-title">Step {{ index + 1 }}: {{ step.title }}</span>
          <span class="step-time">{{ step.duration }}</span>
        </div>
        <p class="step-desc">{{ step.description }}</p>
        <div class="step-details" v-if="step.details">
          <span class="detail-tag">{{ step.details }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    required: true,
    // steps format:
    // [{ title, description, icon, duration, status: 'success' | 'running' | 'pending' | 'error', details }]
  }
});
</script>

<style scoped>
.timeline-container {
  position: relative;
  padding: 10px 0;
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 16px;
  padding-bottom: 24px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-line {
  position: absolute;
  left: 14px;
  top: 30px;
  bottom: -24px;
  width: 2px;
  background: rgba(75, 85, 99, 0.4);
}

.timeline-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid rgba(75, 85, 99, 0.4);
  background: rgba(31, 41, 55, 0.8);
  color: #9ca3af;
  position: relative;
  z-index: 1;
}

.timeline-item.success .timeline-dot {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
}

.timeline-item.running .timeline-dot {
  border-color: #06b6d4;
  background: rgba(6, 182, 212, 0.15);
  color: #06b6d4;
  animation: pulse 2s ease-in-out infinite;
}

.timeline-item.error .timeline-dot {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.timeline-item.pending .timeline-dot {
  border-color: rgba(75, 85, 99, 0.4);
  background: rgba(31, 41, 55, 0.6);
  color: #6b7280;
}

.timeline-content {
  flex: 1;
  background: rgba(31, 41, 55, 0.6);
  border: 1px solid rgba(75, 85, 99, 0.4);
  border-radius: 6px;
  padding: 10px 12px;
}

.timeline-item.success .timeline-content {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.05);
}

.timeline-item.running .timeline-content {
  border-color: rgba(6, 182, 212, 0.4);
  background: rgba(6, 182, 212, 0.08);
}

.timeline-item.error .timeline-content {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.step-title {
  font-size: 13px;
  font-weight: 600;
  color: #e5e7eb;
}

.step-time {
  font-size: 10px;
  color: #9ca3af;
  font-family: monospace;
}

.step-desc {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
}

.step-details {
  margin-top: 6px;
}

.detail-tag {
  display: inline-block;
  font-size: 10px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 8px rgba(6, 182, 212, 0.3);
  }
  50% {
    box-shadow: 0 0 16px rgba(6, 182, 212, 0.6);
  }
}
</style>
