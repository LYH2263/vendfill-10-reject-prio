<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { REJECT_PRIORITY, REJECT_FULL, rejectLabel } from '../rejectCodes'
const lanes = ref<any[]>([])
onMounted(async () => { lanes.value = (await api('/refills/full?location_id=1')).lanes })
</script>
<template>
  <h1>满仓</h1>
  <p class="sub">只收录拒因码为「已满仓 ({{ REJECT_FULL }})」的零补量货道</p>
  <div class="card" style="font-size:0.78rem">
    <div class="muted" style="margin-bottom:0.4rem">零补量行互斥拒因（同一行只命中一码，判定优先级自上而下）：</div>
    <ol style="margin:0;padding-left:1.2rem;line-height:1.7">
      <li v-for="code in REJECT_PRIORITY" :key="code">
        <strong>{{ rejectLabel(code) }}</strong> <code>{{ code }}</code>
        <span v-if="code === REJECT_FULL" class="badge badge-ok" style="margin-left:0.4rem">本页收录</span>
        <span v-else class="badge badge-warn" style="margin-left:0.4rem">本页不收录</span>
      </li>
    </ol>
    <div class="muted" style="margin-top:0.4rem">超占或封锁的货道即使补量为 0 也不会出现在这里，更不会被改写成满仓。</div>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>货道</th><th>商品</th><th>库存</th><th>在途</th><th>容量</th><th>拒因码</th></tr></thead>
      <tbody>
        <tr v-for="l in lanes" :key="l.lane_id">
          <td>{{ l.slot_no }}</td><td>{{ l.sku_name }}</td><td>{{ l.stock }}</td><td>{{ l.in_transit }}</td><td>{{ l.capacity }}</td>
          <td><span class="badge badge-ok">{{ rejectLabel(l.reject_code) }} · {{ l.reject_code }}</span></td>
        </tr>
        <tr v-if="!lanes.length"><td colspan="6" class="muted">当前没有已满仓货道</td></tr>
      </tbody>
    </table>
  </div>
</template>
