/** 分析报告下载（Word / PDF，后端生成） */
import { ElMessage } from 'element-plus'

const MIME = {
  word: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  pdf: 'application/pdf',
}

let inflight = null

function buildDownloadName(g1, format) {
  const no = String(g1?.report_no || 'DGA').replace(/[\\/:*?"<>|]/g, '_')
  const d = String(g1?.day || g1?.sample_dates?.[0] || '').replace(/[\\/:*?"<>|]/g, '_')
  const suffix = d ? `_${d}` : ''
  const ext = format === 'pdf' ? '.pdf' : '.docx'
  return `油中溶解气体分析报告_${no}${suffix}${ext}`
}

function parseFilename(res) {
  const cd = res.headers.get('Content-Disposition') || ''
  const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i)
  if (m) {
    try {
      return decodeURIComponent(m[1] || m[2])
    } catch {
      return m[1] || m[2]
    }
  }
  return null
}

function saveBuffer(buffer, filename, mime) {
  const blob = new Blob([buffer], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  window.setTimeout(() => {
    a.remove()
    URL.revokeObjectURL(url)
  }, 5000)
}

function validateBuffer(buffer, format) {
  if (!buffer || buffer.byteLength === 0) throw new Error('下载文件为空')
  const head = new Uint8Array(buffer.slice(0, 8))
  if (head[0] === 0x7b) {
    try {
      const j = JSON.parse(new TextDecoder().decode(buffer))
      throw new Error(j.message || j.detail || '下载失败')
    } catch (e) {
      if (e instanceof Error && !['下载失败'].includes(e.message)) throw e
      throw new Error('下载失败')
    }
  }
  if (format === 'pdf') {
    const sig = String.fromCharCode(head[0], head[1], head[2], head[3])
    if (sig !== '%PDF') throw new Error('PDF 文件无效，请重试')
  } else if (head[0] !== 0x50 || head[1] !== 0x4b) {
    throw new Error('Word 文件无效，请确认后端已启动后重试')
  }
}

async function fetchReportBuffer(format, payload) {
  const { g1, g2 = null } = payload || {}
  if (!g1) throw new Error('报告数据未就绪')
  const path = format === 'pdf' ? '/agent/report/export/pdf' : '/agent/report/export/word'
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/octet-stream',
    },
    body: JSON.stringify({
      g1: JSON.parse(JSON.stringify(g1)),
      g2: g2 ? JSON.parse(JSON.stringify(g2)) : null,
    }),
  })
  const buffer = await res.arrayBuffer()
  if (!res.ok) validateBuffer(buffer, format)
  validateBuffer(buffer, format)
  const filename = parseFilename(res) || buildDownloadName(g1, format)
  return { buffer, filename }
}

/**
 * @param {'word'|'pdf'} format
 * @param {{ g1: object, g2?: object|null }} payload
 */
export async function downloadReportFile(format, payload) {
  const task = (async () => {
    const { buffer, filename } = await fetchReportBuffer(format, payload)
    saveBuffer(buffer, filename, MIME[format])
    ElMessage.success('报告已下载，可用 WPS 或 Word 打开')
  })()
  inflight = task.finally(() => {
    if (inflight === task) inflight = null
  })
  return inflight
}

export function isReportDownloadBusy() {
  return Boolean(inflight)
}

export function buildReportFilename(g1, date) {
  return buildDownloadName({ ...g1, day: date || g1?.day }, 'word').replace(/\.docx$/, '')
}
