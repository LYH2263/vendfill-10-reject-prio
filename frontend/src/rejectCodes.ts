// 补货零补量行的互斥拒因码——必须与后端 fill_engine 的三个码值完全一致。
// 补货单行、满仓页解释、汇总附注共用这一套码，禁止在任何页面另写一套名单。
export const REJECT_OVERBOOKED = 'overbooked' // 超占不可补（缺口为负）
export const REJECT_BLOCKED = 'blocked' // 货道封锁
export const REJECT_FULL = 'full' // 已满仓（缺口为 0）

// 零补量行唯一判定顺序：超占 > 封锁 > 满仓
export const REJECT_PRIORITY = [REJECT_OVERBOOKED, REJECT_BLOCKED, REJECT_FULL] as const

export const REJECT_LABELS: Record<string, string> = {
  [REJECT_OVERBOOKED]: '超占不可补',
  [REJECT_BLOCKED]: '货道封锁',
  [REJECT_FULL]: '已满仓',
}

export function rejectLabel(code: string | null | undefined): string {
  return (code && REJECT_LABELS[code]) || ''
}
