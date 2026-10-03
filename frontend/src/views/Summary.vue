<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { REASON_NOTES, reasonLabel, REJECT_PRIORITY } from '../codes'
const s = ref<any>({})
onMounted(async () => { s.value = await api('/refills/summary?location_id=1') })
</script>
<template>
  <h1>汇总</h1>
  <p class="sub">本点位补货建议合计 · 计数与补货单行同一套互斥码</p>
  <div class="card grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem">
    <div><div class="muted">建议补货总量</div><div class="stat">{{ s.total_fill }}</div></div>
    <div><div class="muted">待补货道</div><div class="stat">{{ s.need_fill_count }}</div></div>
    <div><div class="muted">满仓货道</div><div class="stat">{{ s.full_count }}</div></div>
    <div><div class="muted">封锁货道</div><div class="stat">{{ s.blocked_count ?? 0 }}</div></div>
    <div><div class="muted">超占货道</div><div class="stat">{{ s.overbooked_count }}</div></div>
  </div>
  <!-- 零补量行三码互斥，优先级：超占 > 封锁 > 满仓；正补量行不计入任一拒因 -->
  <div class="card" style="margin-top:1rem">
    <div class="muted" style="margin-bottom:0.5rem">零补量拒因（互斥，每行至多一个；优先级自高到低）</div>
    <ol style="margin:0;padding-left:1.2rem;line-height:1.8">
      <li v-for="code in REJECT_PRIORITY" :key="code">
        <strong>{{ reasonLabel(code) }}</strong> · {{ REASON_NOTES[code] }}
        · <span class="muted">{{ s.reject_counts?.[code] ?? 0 }} 道</span>
      </li>
    </ol>
  </div>
</template>
