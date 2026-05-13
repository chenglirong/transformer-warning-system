<template>
  <div ref="el" class="w-full h-full"></div>
</template>

<script setup>
import { ref } from "vue";
import { useEchart } from "@/composables/useEchart";

const props = defineProps({
  option: { type: Object, required: true },
});

const el = ref(null);
useEchart(el, () => props.option);
</script>
