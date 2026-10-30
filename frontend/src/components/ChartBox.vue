<template>
  <div ref="container" class="chart-box" :style="{ height }"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  option: { type: Object, default: () => ({}) },
  height: { type: String, default: '280px' }
})

const container = ref(null)
let chart = null
let observer = null

function render() {
  if (!container.value) return
  if (!chart) {
    chart = echarts.init(container.value)
  }
  chart.setOption(props.option || {}, true)
}

onMounted(() => {
  render()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart && chart.resize())
    observer.observe(container.value)
  }
  window.addEventListener('resize', render)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', render)
  chart?.dispose()
  chart = null
})
</script>
