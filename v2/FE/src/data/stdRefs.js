/** DL/T 722 / 1498.2 / 1685 判据说明 + 国标截图（用户提供原图）。 */
import imgTable5 from '@/assets/standards/table5-key-gas.png'
import imgTable67 from '@/assets/standards/table6-7-ratios.png'
import imgDuval from '@/assets/standards/fig-c2-duval.png'
import imgAppB from '@/assets/standards/appendix-b.png'
import imgSec103 from '@/assets/standards/section-10.3-steps.png'
import imgTableA3p1 from '@/assets/standards/table-a3-part1.png'
import imgTableA3p2 from '@/assets/standards/table-a3-part2.png'
import imgTable3p1 from '@/assets/standards/table3-attention-part1.png'
import imgTable3p2 from '@/assets/standards/table3-attention-part2.png'
import imgSec932 from '@/assets/standards/section-9.3.2-rate.png'
import imgSec933 from '@/assets/standards/section-9.3.3.png'
import imgSec1024a from '@/assets/standards/section-10.2.4a.png'
import imgAppD from '@/assets/standards/appendix-d-table-d1.png'
import img1685B2 from '@/assets/standards/1685-table-b2.png'
import img1685B3 from '@/assets/standards/1685-table-b3.png'
import imgAppG1 from '@/assets/standards/appendix-g-table-g1.png'
import imgAppG2 from '@/assets/standards/appendix-g-table-g2.png'
import img1498A31 from '@/assets/standards/1498-a3.1.png'
import img1498545 from '@/assets/standards/1498-5.4.5.png'
import img1498555 from '@/assets/standards/1498-5.5.5.png'
import img72254 from '@/assets/standards/722-5.4-offline.png'

/**
 * @typedef {{ title: string, body: string, image?: string, images?: string[] }} StdEntry
 * @type {Record<string, StdEntry>}
 */
export const STD_REFS = {
  '722-表3': {
    title: 'DL/T 722-2014 §9.3.1 表3 含量注意值',
    body: '运行中设备油中溶解气体含量注意值(μL/L)。面向 220kV 及以下变压器时：H₂=150、C₂H₂=5、总烃=150。表 A.3 注意值2 与本表同线。',
    images: [imgTable3p1, imgTable3p2],
  },
  '722-10.3': {
    title: 'DL/T 722-2014 §10.3 判断故障的步骤',
    body: '先将气体含量与表3注意值比较；短期内含量迅速增长但尚未超表3，也可判断为内部有异常，再进入故障类型判断。',
    image: imgSec103,
  },
  '722-10.2.4a': {
    title: 'DL/T 722-2014 §10.2.4 a) 比值法应用原则',
    body: '只有根据气体含量注意值或气体增长率注意值有理由判断可能存在故障时，用比值法才有效。含量正常且无增长趋势时比值无意义。',
    image: imgSec1024a,
  },
  '722-表5': {
    title: 'DL/T 722-2014 §10.1 表5 特征气体法',
    body: '不同故障类型的主要/次要特征气体对照；注1~5为定性细则。本系统「偏高」门槛与行加权得分为工程实现（有表3可对齐处贴220kV注意值），非表5原文数值。',
    image: imgTable5,
  },
  '722-表6-7': {
    title: 'DL/T 722-2014 §10.2 表6/表7 三比值法',
    body: '表6：C₂H₂/C₂H₄、CH₄/H₂、C₂H₄/C₂H₆ 编码规则(0/1/2)。表7：编码组合→故障类型。一般在特征气体超注意值后使用。',
    image: imgTable67,
  },
  '722-附录C': {
    title: 'DL/T 722-2014 附录C 图C.2 大卫三角形法',
    body: '以 CH₄、C₂H₄、C₂H₂ 相对百分含量落于等边三角分区：PD / D1 / D2 / T1 / T2 / T3 / D+T。',
    image: imgDuval,
  },
  '722-附录B': {
    title: 'DL/T 722-2014 附录B 表B.1/B.2 解释表',
    body: '援引 IEC 60599 的比值限值分类（PD/D1/D2/T1/T2/T3）及简表，可与表6/7交叉印证。',
    image: imgAppB,
  },
  '1498-表A3': {
    title: 'DL/T 1498.2-2025 表A.3 在线监测阈值（220kV及以下）',
    body: '四档：正常 / 注意值1 / 注意值2 / 告警值。三组判据（绝对浓度、绝对增量、相对增长速率）各算档后取最高档。注意值2 对齐 DL/T 722 表3。',
    images: [imgTableA3p1, imgTableA3p2],
  },
  '722-9.3.2': {
    title: 'DL/T 722-2014 §9.3.2 产气速率',
    body: '相对产气速率（式2）以 %/月计；总烃相对产气速率注意值约 10%/月。与表 A.3 周增率为不同口径。',
    image: imgSec932,
  },
  '722-9.3.3': {
    title: 'DL/T 722-2014 §9.3.3 应用原则',
    body: '超过注意值时结合产气速率判断；超标但长期稳定可继续运行并加强监视。浓度未超但速率超 → 缩短检测周期。',
    image: imgSec933,
  },
  '722-5.4': {
    title: 'DL/T 722-2014 §5.4 b) 缩短检测周期',
    body: '离线检测异常时缩短周期：过热故障可每周、放电故障可每天。在线监测周期另见 1498.2 A.3.1 / §5.4.5 / §5.5.5。',
    image: img72254,
  },
  '722-5.4.5': {
    title: 'DL/T 1498.2-2025 §5.4.5 二次采样验证',
    body: '发现预警后自动二次采样验证，确认后再缩短为快速采样周期。多组分最小检测周期下限见 §5.5.5。',
    image: img1498545,
  },
  '1498-5.4.5': {
    title: 'DL/T 1498.2-2025 §5.4.5 二次采样验证',
    body: '发现预警后自动二次采样验证，确认后再缩短为快速采样周期。多组分最小检测周期下限见 §5.5.5。',
    image: img1498545,
  },
  '1498-A.3.1': {
    title: 'DL/T 1498.2-2025 A.3.1 数据采集周期',
    body: '220kV 及以下在线监测装置采集周期应不大于 12 小时；监测异常增长或判断内部缺陷时，宜缩至最小检测周期。',
    image: img1498A31,
  },
  '1498-5.5.5': {
    title: 'DL/T 1498.2-2025 §5.5.5 最小检测周期',
    body: '多组分在线监测装置最小检测周期不大于 2 小时；少组分不大于 12 小时。',
    image: img1498555,
  },
  '722-附录D': {
    title: 'DL/T 722-2014 附录D 表D.1',
    body: '据 DGA 判断有故障后，推荐结合其它电气试验（绕组直阻、铁芯绝缘、局放、油试验等）进一步核实。',
    image: imgAppD,
  },
  '1685-附录B': {
    title: 'DL/T 1685-2017 附录B 表B.2/B.3',
    body: '过热/放电缺陷：状态量描述与停电测试项目对照，用于补充试验建议。',
    images: [img1685B2, img1685B3],
  },
  '722-附录G': {
    title: 'DL/T 722-2014 附录 G 表 G.1 / G.2',
    body: '油中溶解气体分析档案卡片（资料性附录）。报告版式套表 G.1 / G.2。',
    images: [imgAppG1, imgAppG2],
  },
}

/** 角标展示文案 → 条目 id */
export const STD_LABEL_TO_ID = {
  '§10.3': '722-10.3',
  '§10.3 注意值2起判型': '722-10.3',
  '§10.3 / 速率超进判型': '722-10.3',
  'A.3.1': '1498-A.3.1',
  '§5.5.5': '1498-5.5.5',
  '§5.4.5 / A.3.1': '722-5.4.5',
  'DL/T 722-2014 判断故障的步骤': '722-10.3',
  '§10.1 表5': '722-表5',
  '§10.2 表6/7': '722-表6-7',
  '附录C': '722-附录C',
  '附录C 图C.2': '722-附录C',
  '附录B': '722-附录B',
  '§10.2.4 a': '722-10.2.4a',
  '表A.3': '1498-表A3',
  'DL/T 1498.2 表A.3': '1498-表A3',
  '表3': '722-表3',
  '§9.3.1 表3': '722-表3',
  '§9.3.2': '722-9.3.2',
  '§9.3.3': '722-9.3.3',
  '§5.4 / §5.4.5': '722-5.4',
  '§5.4': '722-5.4',
  '§5.4.5': '722-5.4.5',
  '附录G 表G.1': '722-附录G',
  '附录D': '722-附录D',
  '附录G': '722-附录G',
  '1685 附录B': '1685-附录B',
  '§5.4.5': '1498-5.4.5',
}

export function resolveStd(idOrLabel) {
  if (STD_REFS[idOrLabel]) return { id: idOrLabel, ...STD_REFS[idOrLabel] }
  const id = STD_LABEL_TO_ID[idOrLabel]
  if (id && STD_REFS[id]) return { id, ...STD_REFS[id] }
  return null
}
