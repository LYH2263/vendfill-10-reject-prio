<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { REJECT_PRIORITY, rejectLabel } from '../rejectCodes'
const s = ref<any>({})
onMounted(async () => { s.value = await api('/refills/summary?location_id=1') })
</script>
<template>
  <h1>汇总</h1>
  <p class="sub">本点位补货建议合计 · 零补量行按同一套互斥码计数，每行只计入一项</p>
  <div class="card grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem">
    <div><div class="muted">建议补货总量</div><div class="stat">{{ s.total_fill }}</div></div>
    <div><div class="muted">待补货道（正补量，拒因为空）</div><div class="stat">{{ s.need_fill_count }}</div></div>
    <div><div class="muted">满仓货道</div><div class="stat">{{ s.full_count }}</div></div>
    <div><div class="muted">封锁货道</div><div class="stat" style="color:var(--vf-amber)">{{ s.blocked_count ?? 0 }}</div></div>
    <div><div class="muted">超占货道</div><div class="stat" style="color:var(--vf-red)">{{ s.overbooked_count }}</div></div>
  </div>
  <div class="card" style="font-size:0.78rem">
    <div class="muted" style="margin-bottom:0.35rem">附注 · 补量为 0 的行只能命中以下一个拒因码，判定优先级自上而下，不并写两码：</div>
    <ol style="margin:0;padding-left:1.2rem;line-height:1.7">
      <li v-for="code in REJECT_PRIORITY" :key="code">
        <strong>{{ rejectLabel(code) }}</strong> <code>{{ code }}</code>
        <span class="muted">——
          <template v-if="code === 'overbooked'">缺口为负，超占优先于封锁与满仓</template>
          <template v-else-if="code === 'blocked'">货道被封锁且未超占；未配置封锁字段的点位不会出现此码</template>
          <template v-else>缺口为 0 且未封锁，才计入满仓</template>
        </span>
      </li>
    </ol>
  </div>
</template>
