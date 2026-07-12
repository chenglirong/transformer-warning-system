/** DL/T 722 / 1498.2 判据角标库 —— 悬停展示国标原文/截图(用户提供原图)。 */
import imgTable5 from '@/assets/standards/table5-key-gas.png'
import imgTable67 from '@/assets/standards/table6-7-ratios.png'
import imgDuval from '@/assets/standards/fig-c2-duval.png'
import imgAppB from '@/assets/standards/appendix-b.png'
import imgSec103 from '@/assets/standards/section-10.3-steps.png'
import imgTableA3p1 from '@/assets/standards/table-a3-part1.png'
import imgTableA3p2 from '@/assets/standards/table-a3-part2.png'

/**
 * @typedef {{ title: string, body: string, image?: string, images?: string[] }} StdEntry
 * @type {Record<string, StdEntry>}
 */
export const STD_REFS = {
  '722-10.3': {
    title: 'DL/T 722-2014 §10.3 判断故障的步骤',
    body: '先将气体含量与表3注意值比较，认为设备可能存在故障时，再用表5特征气体法、表6/表7三比值法及附录B/C等方法判断故障类型。本系统注意值2(=表3)及以上才触发判型；正常与注意值1只报档位。',
    image: imgSec103,
  },
  '722-10.2.4a': {
    title: 'DL/T 722-2014 §10.2.4 a) 比值法应用原则',
    body: '气体含量在正常范围内且无增长趋势时，比值可能无意义。故三比值/大卫三角仅在超注意值后使用。',
  },
  '722-表5': {
    title: 'DL/T 722-2014 §10.1 表5 特征气体法',
    body: '不同故障类型的主要/次要特征气体对照。注1~5补充温区、局放几乎无C₂H₂、火花放电总烃不高等细则。',
    image: imgTable5,
  },
  '722-表6-7': {
    title: 'DL/T 722-2014 §10.2 表6/表7 三比值法',
    body: '表6：C₂H₂/C₂H₄、CH₄/H₂、C₂H₄/C₂H₆ 编码规则(0/1/2)。表7：编码组合→故障类型(过热温区/局放/低能放电/电弧及兼过热)。一般在特征气体超注意值后使用。',
    image: imgTable67,
  },
  '722-附录C': {
    title: 'DL/T 722-2014 附录C 图C.2 大卫三角形法',
    body: '以 CH₄、C₂H₄、C₂H₂ 相对百分含量落于等边三角分区：PD / D1 / D2 / T1 / T2 / T3 / D+T。本系统只做三角法，不做图C.1 立体图示法。',
    image: imgDuval,
  },
  '722-附录B': {
    title: 'DL/T 722-2014 附录B 表B.1/B.2 解释表',
    body: '援引 IEC 60599 的六分类比值限值(PD/D1/D2/T1/T2/T3)及简表(PD/D/T)。本系统主判据为表6/7编码法，附录B作交叉印证，不作主输出。',
    image: imgAppB,
  },
  '1498-表A3': {
    title: 'DL/T 1498.2-2025 表A.3 在线监测阈值（220kV及以下）',
    body: '四档：正常 / 注意值1 / 注意值2 / 告警值。三组判据（绝对浓度、绝对增量、相对增长速率）各算档后取最高档。注意值2 对齐 DL/T 722 表3。相对增长仅总烃，且总烃<30 μL/L 不算。参比按 A.3.3：前14~前7天窗口均值并剔奇异值。',
    images: [imgTableA3p1, imgTableA3p2],
  },
  '722-9.3.2': {
    title: 'DL/T 722-2014 §9.3.2 产气速率',
    body: '相对产气速率（式2）注意值约 10%/月（总烃）。本系统用月环比（今 vs 30 天前）直接得 %/月，连续 3 天确认滤噪。与表 A.3 周增率是两套口径，不换算。',
  },
  '722-9.3.3': {
    title: 'DL/T 722-2014 §9.3.3 应用原则',
    body: '超过注意值时结合产气速率判断；超标但长期稳定可继续运行、加强监视。浓度未超但速率超 → 缩短检测周期（「预」）。不改表 A.3 档位。',
  },
  '722-5.4': {
    title: 'DL/T 722-2014 §5.4 b) 缩短检测周期',
    body: '设备有异常时缩短检测周期：过热（疑主磁/漏磁）→ 每周；放电类 → 每天。与 §5.3 表1 正常周期对照使用。',
  },
  '722-5.4.5': {
    title: 'DL/T 1498.2-2025 §5.4.5 二次采样验证',
    body: '发现预警后自动二次采样验证，确认后再缩短为快速采样周期。可信度低/三方分歧时优先建议二次采样。',
  },
  '722-附录G': {
    title: 'DL/T 722-2014 附录 G 表 G.1',
    body: '油中溶解气体分析档案卡片（资料性附录）。本系统报告版式套此表；合成环境无铭牌/油重等字段如实留空，不杜撰。',
  },
}

/** 角标展示文案 → 条目 id */
export const STD_LABEL_TO_ID = {
  '§10.3': '722-10.3',
  '§10.3 注意值2起判型': '722-10.3',
  'DL/T 722-2014 判断故障的步骤': '722-10.3',
  '§10.1 表5': '722-表5',
  '§10.2 表6/7': '722-表6-7',
  '附录C': '722-附录C',
  '附录C 图C.2': '722-附录C',
  '附录B': '722-附录B',
  '§10.2.4 a': '722-10.2.4a',
  '表A.3': '1498-表A3',
  'DL/T 1498.2 表A.3': '1498-表A3',
  '§9.3.2': '722-9.3.2',
  '§9.3.3': '722-9.3.3',
  '§5.4 / §5.4.5': '722-5.4',
  '§5.4': '722-5.4',
  '§5.4.5': '722-5.4.5',
  '附录G 表G.1': '722-附录G',
  '附录G': '722-附录G',
}

export function resolveStd(idOrLabel) {
  if (STD_REFS[idOrLabel]) return { id: idOrLabel, ...STD_REFS[idOrLabel] }
  const id = STD_LABEL_TO_ID[idOrLabel]
  if (id && STD_REFS[id]) return { id, ...STD_REFS[id] }
  return null
}
