// 补货拒因统一码表：补货单行、满仓页、汇总附注必须共用这一套互斥码，
// 任何页面都不得自行另写判断或标签，以免名单与码分叉。
// 优先级（零补量行三选一）：超占 > 封锁 > 满仓；正补量行拒因为空。
export const REJECT_OVERBOOKED = 'overbooked' // 超占不可补
export const REJECT_BLOCKED = 'blocked' // 货道封锁
export const REJECT_FULL = 'full' // 已满仓
export const NEED_FILL = 'need_fill' // 有待补量（拒因为空）

// 码 → 中文标签（唯一来源）
export const REASON_LABELS: Record<string, string> = {
  [REJECT_OVERBOOKED]: '超占不可补',
  [REJECT_BLOCKED]: '货道封锁',
  [REJECT_FULL]: '已满仓',
}

// 码 → 一行解释（用于小票/满仓页/汇总附注，保持同义）
export const REASON_NOTES: Record<string, string> = {
  [REJECT_OVERBOOKED]: '库存＋在途已超容量，无法补货',
  [REJECT_BLOCKED]: '货道被封锁，暂不补货',
  [REJECT_FULL]: '缺口为 0，已满仓',
}

// 互斥优先级，供汇总附注展示
export const REJECT_PRIORITY = [REJECT_OVERBOOKED, REJECT_BLOCKED, REJECT_FULL]

export function reasonLabel(code: string | null | undefined): string {
  return code ? REASON_LABELS[code] ?? code : ''
}
