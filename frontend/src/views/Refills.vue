<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { reasonLabel, REASON_NOTES } from '../codes'
const data = ref<any>(null)
async function run() { data.value = await api('/refills/run?location_id=1', { method: 'POST' }) }
onMounted(run)
</script>
<template>
  <h1>补货小票</h1>
  <p class="sub">gap = 容量 − 库存 − 在途 · 收据纸样式</p>
  <button class="btn" @click="run">生成补货单</button>
  <div style="margin-top:1rem" v-if="data">
    <div class="vf-receipt">
      <h2>*** VendFill 补货单 ***</h2>
      <div class="vf-receipt-line" style="font-weight:700;border-bottom:2px dashed #8a7e64">
        <span>货道 / 商品</span><span>补量</span>
      </div>
      <div class="vf-receipt-line" v-for="l in data.lines" :key="l.lane_id">
        <span>{{ l.slot_no }} {{ l.sku_name }}
          <!-- 正补量行无拒因；零补量行按统一码显示互斥结论 -->
          <small v-if="l.reject_reason" :title="REASON_NOTES[l.reject_reason]">
            （{{ reasonLabel(l.reject_reason) }}）
          </small>
        </span>
        <span>{{ l.fill_qty }} / 缺{{ l.gap }}</span>
      </div>
      <p style="text-align:center;margin:1rem 0 0;font-size:0.72rem;color:#6a5e48">谢谢使用 · 请核对后装机</p>
    </div>
  </div>
</template>
