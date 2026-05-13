import { ref, onMounted, onUnmounted } from 'vue'

const pad = (n) => String(n).padStart(2, '0')

function format(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function useClock() {
  const now = ref(format(new Date()))
  let timer = null

  onMounted(() => {
    now.value = format(new Date())
    timer = setInterval(() => {
      now.value = format(new Date())
    }, 1000)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return now
}
