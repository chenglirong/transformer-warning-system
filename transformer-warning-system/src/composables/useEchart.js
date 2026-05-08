import { onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const instances = new Set()
let globalHandler = null

function ensureHandler() {
  if (globalHandler) return
  globalHandler = () => {
    instances.forEach((chart) => {
      if (chart && !chart.isDisposed()) chart.resize()
    })
  }
  window.addEventListener('resize', globalHandler)
}

function teardownHandlerIfEmpty() {
  if (instances.size === 0 && globalHandler) {
    window.removeEventListener('resize', globalHandler)
    globalHandler = null
  }
}

export function useEchart(elRef, getOption) {
  let chart = null

  onMounted(() => {
    const el = elRef.value
    if (!el) return
    chart = echarts.init(el)
    chart.setOption(getOption())
    instances.add(chart)
    ensureHandler()

    watch(getOption, (opt) => {
      if (chart && !chart.isDisposed()) chart.setOption(opt, true)
    }, { deep: true })
  })

  onBeforeUnmount(() => {
    if (chart) {
      instances.delete(chart)
      chart.dispose()
      chart = null
    }
    teardownHandlerIfEmpty()
  })

  return () => chart
}
