<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { reasonLabel, REJECT_FULL, REASON_NOTES } from '../codes'

const rows = ref<any[]>([])
const refill = ref<any>(null)
const savingId = ref<number | null>(null)
const msg = ref('')

// 行内编辑草稿：stock / in_transit / blocked（'' = 未配置 → null）
const drafts = ref<Record<number, { stock: number; in_transit: number; blocked: string }>>({})

function draftOf(r: any) {
  if (!drafts.value[r.id]) {
    drafts.value[r.id] = {
      stock: r.stock,
      in_transit: r.in_transit,
      blocked: r.blocked === true ? 'true' : r.blocked === false ? 'false' : '',
    }
  }
  return drafts.value[r.id]
}

// 用最新单据构造 lane_id → 行 的映射，页面所有结论都取自该码，不自行另判
const lineByLane = () => {
  const m: Record<number, any> = {}
  for (const l of refill.value?.lines ?? []) m[l.lane_id] = l
  return m
}

async function load() {
  rows.value = await api('/lanes?location_id=1')
  refill.value = await api('/refills/run?location_id=1', { method: 'POST' })
}

async function save(r: any) {
  savingId.value = r.id
  msg.value = ''
  try {
    const d = draftOf(r)
    const body: any = { stock: Number(d.stock), in_transit: Number(d.in_transit) }
    // 封锁三态：'' 未配置（不冒封锁码）/ false 正常 / true 封锁
    body.blocked = d.blocked === '' ? null : d.blocked === 'true'
    const res = await api(`/lanes/${r.id}`, { method: 'PATCH', body: JSON.stringify(body) })
    Object.assign(rows.value.find((x) => x.id === r.id) ?? {}, res.lane)
    // 最新单行码、满仓收录、汇总计数全部跟随服务端按新码重算的单据
    refill.value = res.refill
    msg.value = `已保存 ${r.slot_no}，单据按新状态重算`
  } catch (e: any) {
    msg.value = '保存失败：' + e.message
  } finally {
    savingId.value = null
  }
}

onMounted(load)
</script>
<template>
  <h1>货道格子</h1>
  <p class="sub">机面货道网格 · 可改库存/在途制造超占、切换封锁；右侧小票与下方计数实时跟随新码</p>
  <div class="vf-machine-layout">
    <div>
      <div class="vf-slot-grid">
        <div v-for="r in rows" :key="r.id" class="vf-slot" :class="{ 'vf-slot-blocked': r.blocked === true }">
          <div class="vf-slot-no">{{ r.slot_no }}</div>
          <div class="vf-slot-sku">{{ r.sku_name }}</div>
          <div class="vf-slot-bar">
            <div
              class="vf-slot-fill"
              :class="{ 'vf-need': r.gap > 0 }"
              :style="{ width: Math.min(r.fill_pct, 100) + '%' }"
            />
          </div>
          <div class="vf-slot-meta">{{ r.stock }}/{{ r.capacity }} · 缺 {{ r.gap }}</div>
          <!-- 该行在最新单据中的互斥结论（直接取单据码，不另判） -->
          <div class="vf-slot-meta" v-if="lineByLane()[r.id]?.reject_reason">
            <small :title="REASON_NOTES[lineByLane()[r.id].reject_reason]">
              拒因：{{ reasonLabel(lineByLane()[r.id].reject_reason) }}<template
                v-if="lineByLane()[r.id].reject_reason === REJECT_FULL"> · 收录满仓页</template>
            </small>
          </div>
          <div class="vf-edit" style="display:flex;gap:.35rem;align-items:center;flex-wrap:wrap;margin-top:.4rem">
            <label style="font-size:.7rem">库存
              <input type="number" v-model.number="draftOf(r).stock" style="width:3.4rem" />
            </label>
            <label style="font-size:.7rem">在途
              <input type="number" v-model.number="draftOf(r).in_transit" style="width:3.4rem" />
            </label>
            <label style="font-size:.7rem">封锁
              <select v-model="draftOf(r).blocked" style="width:4.6rem">
                <option value="">未配置</option>
                <option value="false">正常</option>
                <option value="true">封锁</option>
              </select>
            </label>
            <button class="btn" style="padding:.15rem .5rem;font-size:.72rem" :disabled="savingId === r.id" @click="save(r)">
              {{ savingId === r.id ? '…' : '保存' }}
            </button>
          </div>
        </div>
      </div>
      <p class="muted" role="status" style="margin-top:.6rem;font-size:.78rem">{{ msg }}</p>
      <!-- 与满仓页、汇总同源的计数，保存后即时跟随新码 -->
      <div class="card" v-if="refill" style="margin-top:.5rem;display:flex;gap:1.2rem;flex-wrap:wrap;font-size:.82rem">
        <span>待补 <strong>{{ refill.need_fill_count }}</strong></span>
        <span>满仓 <strong>{{ refill.full_count }}</strong></span>
        <span>封锁 <strong>{{ refill.blocked_count }}</strong></span>
        <span>超占 <strong>{{ refill.overbooked_count }}</strong></span>
        <span>总补量 <strong>{{ refill.total_fill }}</strong></span>
      </div>
    </div>
    <aside class="vf-receipt" v-if="refill">
      <h2>*** 补货建议单 ***</h2>
      <div class="vf-receipt-line" v-for="l in refill.lines" :key="l.lane_id">
        <span>{{ l.slot_no }} {{ l.sku_name }}
          <small v-if="l.reject_reason">（{{ reasonLabel(l.reject_reason) }}）</small>
        </span>
        <span>x{{ l.fill_qty }}</span>
      </div>
      <p class="muted" style="margin:0.75rem 0 0;font-size:0.72rem;color:#6a5e48;text-align:center">
        — 机面打印预览 —
      </p>
    </aside>
  </div>
</template>
