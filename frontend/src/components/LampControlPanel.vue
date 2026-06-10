<script setup lang="ts">
import type { SceneMode } from '@/types/api'

import { useLampControl } from '@/composables/useLampControl'

const {
  loading,
  applying,
  error,
  success,
  control,
  sceneLabels,
  applyControl,
  applyScene,
} = useLampControl()

const scenes: SceneMode[] = ['eye_care', 'reading', 'focus', 'night']

async function onBrightnessChange(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  await applyControl({ brightness: value })
}

async function onColorTempChange(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  await applyControl({ color_temperature: value })
}
</script>

<template>
  <div class="panel-stack">
    <section class="dashboard-grid dashboard-grid--control">
      <aside class="device-panel device-panel--live">
        <div class="device-panel__header">
          <div>
            <p class="eyebrow">Preview</p>
            <h2>台灯状态预览</h2>
            <span>远程控制指令下发后实时回显</span>
          </div>
          <div
            class="lamp-orb lamp-orb--dynamic"
            :style="{
              filter: `brightness(${0.45 + control.brightness / 180})`,
            }"
          >
            <div
              class="lamp-orb__glow"
              :style="{
                background: `linear-gradient(145deg, #fff6ea, hsl(${40 - control.color_temperature / 220}, 90%, 55%))`,
                boxShadow: `0 0 ${24 + control.brightness / 2}px rgba(255, 105, 0, ${0.25 + control.brightness / 140})`,
              }"
            ></div>
          </div>
        </div>

        <div class="device-panel__metrics">
          <div>
            <span>当前场景</span>
            <strong>{{ sceneLabels[control.scene_mode] }}</strong>
          </div>
          <div>
            <span>亮度</span>
            <strong>{{ control.brightness }}%</strong>
          </div>
          <div>
            <span>色温</span>
            <strong>{{ control.color_temperature }}K</strong>
          </div>
        </div>
      </aside>

      <section class="content-panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">Remote Control</p>
            <h2>台灯远程控制</h2>
          </div>
        </div>

        <section v-if="loading" class="loading-card">正在读取台灯状态...</section>

        <div v-else class="control-stack">
          <div class="control-block">
            <div class="control-block__head">
              <strong>场景模式</strong>
              <span>一键切换护眼、阅读、专注与夜间预设</span>
            </div>
            <div class="scene-grid">
              <button
                v-for="scene in scenes"
                :key="scene"
                type="button"
                class="scene-chip"
                :class="{ 'scene-chip--active': control.scene_mode === scene }"
                :disabled="applying"
                @click="applyScene(scene)"
              >
                {{ sceneLabels[scene] }}
              </button>
            </div>
          </div>

          <div class="control-block">
            <div class="control-block__head">
              <strong>亮度调节</strong>
              <span>{{ control.brightness }}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="1"
              :value="control.brightness"
              :disabled="applying"
              @change="onBrightnessChange"
            />
          </div>

          <div class="control-block">
            <div class="control-block__head">
              <strong>色温调节</strong>
              <span>{{ control.color_temperature }}K</span>
            </div>
            <input
              type="range"
              min="2700"
              max="6500"
              step="100"
              :value="control.color_temperature"
              :disabled="applying"
              @change="onColorTempChange"
            />
          </div>

          <div v-if="error" class="form-message form-message--error">{{ error }}</div>
          <div v-if="success" class="form-message form-message--success">{{ success }}</div>
        </div>
      </section>
    </section>
  </div>
</template>
