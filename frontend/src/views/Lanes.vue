<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { rejectLabel } from '../rejectCodes'
const rows = ref<any[]>([])
const refill = ref<any>(null)
const busy = ref<number | null>(null)

async function loadAll() {
  rows.value = await api('/lanes')
  // 每次货道变动都重跑，刷新“最新单”：单行码、满仓收录、汇总计数都以它为准，杜绝名单与码分叉
  refill.value = await api('/refills/run?location_id=1', { method: 'POST' })
}

async function patch(id: number, body: Record<string, number | boolean>) {
  busy.value = id
  try {
    await api(`/lanes/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
    await loadAll()
  } finally {
    busy.value = null
  }
}

onMounted(loadAll)
</script>
<template>
  <h1>货道格子</h1>
  <p class="sub">机面货道网格 · 调整库存/在途可改出超占，封锁开关可打开/解除封锁；右侧小票即时跟新码</p>
  <div class="vf-machine-layout">
    <div class="vf-slot-grid">
      <div v-for="r in rows" :key="r.id" class="vf-slot" :class="{ 'vf-locked': r.blocked }">
        <div class="vf-slot-no">{{ r.slot_no }}</div>
        <div class="vf-slot-sku">{{ r.sku_name }}</div>
        <div class="vf-slot-bar">
          <div
            class="vf-slot-fill"
            :class="{ 'vf-need': r.gap > 0, 'vf-over': r.gap < 0 }"
            :style="{ width: Math.min(r.fill_pct, 100) + '%' }"
          />
        </div>
        <div class="vf-slot-meta">{{ r.stock }}/{{ r.capacity }} · 在途 {{ r.in_transit }} · 缺 {{ r.gap }}</div>
        <div class="vf-slot-ctrl">
          <label>库
            <input type="number" min="0" :value="r.stock" :disabled="busy === r.id"
                   @change="(e) => patch(r.id, { stock: Number((e.target as HTMLInputElement).value) })" />
          </label>
          <label>途
            <input type="number" min="0" :value="r.in_transit" :disabled="busy === r.id"
                   @change="(e) => patch(r.id, { in_transit: Number((e.target as HTMLInputElement).value) })" />
          </label>
          <button class="vf-mini-btn" :class="{ 'vf-mini-on': r.blocked }" :disabled="busy === r.id"
                  @click="patch(r.id, { blocked: !r.blocked })">
            {{ r.blocked ? '封锁中·解封' : '封锁' }}
          </button>
        </div>
      </div>
    </div>
    <aside class="vf-receipt" v-if="refill">
      <h2>*** 补货建议单 ***</h2>
      <div class="vf-receipt-line" v-for="l in refill.lines" :key="l.lane_id">
        <span>{{ l.slot_no }} {{ l.sku_name }}
          <small v-if="l.fill_qty === 0 && l.reject_code" style="font-size:0.68rem">
            （{{ rejectLabel(l.reject_code) }}）
          </small>
        </span>
        <span>x{{ l.fill_qty }}</span>
      </div>
      <p class="muted" style="margin:0.75rem 0 0;font-size:0.72rem;color:#6a5e48;text-align:center">
        — 机面打印预览 · 零补量只标一码 —
      </p>
    </aside>
  </div>
</template>
