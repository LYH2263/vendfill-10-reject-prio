<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { REJECT_FULL, REASON_NOTES, reasonLabel } from '../codes'
const lanes = ref<any[]>([])
onMounted(async () => { lanes.value = (await api('/refills/full?location_id=1')).lanes })
</script>
<template>
  <h1>满仓</h1>
  <!-- 本页只收录互斥码 full（缺口为 0）；超占/封锁即使补量为 0 也不收录 -->
  <p class="sub">仅收录「{{ reasonLabel(REJECT_FULL) }}」：{{ REASON_NOTES[REJECT_FULL] }}；超占、封锁不进本页</p>
  <div class="card">
    <table>
      <thead><tr><th>货道</th><th>商品</th><th>库存</th><th>在途</th><th>容量</th><th>结论</th></tr></thead>
      <tbody>
        <tr v-for="l in lanes" :key="l.lane_id">
          <td>{{ l.slot_no }}</td><td>{{ l.sku_name }}</td><td>{{ l.stock }}</td><td>{{ l.in_transit }}</td><td>{{ l.capacity }}</td>
          <td>{{ reasonLabel(l.reject_reason) }}</td>
        </tr>
        <tr v-if="!lanes.length"><td colspan="6" class="muted" style="text-align:center">暂无已满仓货道</td></tr>
      </tbody>
    </table>
  </div>
</template>
