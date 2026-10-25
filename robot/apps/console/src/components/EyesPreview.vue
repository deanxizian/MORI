<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { Eyes, drawEyes, moods, type Mood } from "../eyes/engine";
const props = defineProps<{ state: string; rms: number }>(),
  canvas = ref<HTMLCanvasElement>(),
  eyes = new Eyes();
let request = 0;
onMounted(() => {
  const run = (ms: number) => {
    const state = moods.includes(props.state as Mood)
      ? (props.state as Mood)
      : "idle";
    eyes.setState(state, ms / 1000, props.rms);
    if (canvas.value) drawEyes(canvas.value, eyes.sample(ms / 1000, props.rms));
    request = requestAnimationFrame(run);
  };
  request = requestAnimationFrame(run);
});
onUnmounted(() => cancelAnimationFrame(request));
</script>
<template>
  <canvas
    ref="canvas"
    width="360"
    height="360"
    role="img"
    :aria-label="'MORI 双眼：' + state"
    class="eyes-canvas"
  />
</template>
