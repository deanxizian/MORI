<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import {
  ui,
  pair,
  restorePairing,
  revokePairing,
  connect,
  api,
  request,
  command,
  claim,
  release,
  startDrive,
  installLifecycle,
  stale,
  prepareAudio,
} from "./client";
import { moods } from "./eyes/engine";
import EyesPreview from "./components/EyesPreview.vue";
const tab = ref("control"),
  code = ref(""),
  busy = ref(false),
  uploadPending = ref<boolean | null>(null),
  support = ref(false),
  local = ref(false),
  yaw = ref(0),
  pitch = ref(0),
  picture = ref(""),
  description = ref(""),
  voice = ref(""),
  query = ref(""),
  memoryText = ref(""),
  confirmed = ref(false),
  memoryOn = ref(true);
const memories = ref<
  Array<{
    id: string;
    text: string;
    category: string;
    source_id: string;
    confirmed: boolean;
    updated_at: string;
    conflicts: unknown[];
  }>
>([]);
const tabs = [
  ["control", "控制台", "⌘"],
  ["vision", "视觉与行为", "◉"],
  ["voice", "语音会话", "◌"],
  ["memory", "长期记忆", "▤"],
  ["settings", "设置与日志", "⚙"],
];
let poll: ReturnType<typeof setInterval> | null = null,
  fetching = false;
async function run(fn: () => Promise<unknown>) {
  busy.value = true;
  try {
    await fn();
  } catch (e) {
    ui.notice = String(e);
  } finally {
    busy.value = false;
  }
}
async function camera(mode: string) {
  await command("CAMERA_MODE", {
    mode,
    upload_allowed: ui.status?.camera.upload_allowed ?? false,
  });
  if (mode === "OFF") {
    if (picture.value) URL.revokeObjectURL(picture.value);
    picture.value = "";
  } else await frame();
}
async function setUploadConsent(event: Event) {
  const allowed = (event.target as HTMLInputElement).checked;
  uploadPending.value = allowed;
  await run(async () => {
    const result = await command("CAMERA_MODE", {
      mode: ui.status?.camera.mode ?? "OFF",
      upload_allowed: allowed,
    });
    // The result can arrive before the next telemetry frame. Keep the accepted
    // value visible instead of resetting the checkbox to the previous frame.
    if (result?.status === "COMPLETED" && ui.status)
      ui.status.camera.upload_allowed = allowed;
  });
  uploadPending.value = null;
}
async function frame() {
  if (!ui.identity || fetching) return;
  fetching = true;
  try {
    const r = await request("/api/camera/frame");
    if (!r.ok || r.status === 204) return;
    const url = URL.createObjectURL(await r.blob());
    if (picture.value) URL.revokeObjectURL(picture.value);
    picture.value = url;
  } catch {
    // Polls can race camera shutdown, revocation or a transport disconnect.
    // Discard the old frame and wait for the next authenticated telemetry.
    if (picture.value) URL.revokeObjectURL(picture.value);
    picture.value = "";
  } finally {
    fetching = false;
  }
}
async function search() {
  const r = await command("MEMORY_QUERY", { query: query.value });
  if (r?.status === "COMPLETED")
    memories.value = r.data as typeof memories.value;
}
async function remember() {
  const r = await command("MEMORY_REMEMBER", {
    text: memoryText.value,
    category: "preference",
    confirmed: confirmed.value,
    sensitive: false,
    source_id: "console-explicit-" + Date.now(),
  });
  if (r?.status === "COMPLETED") {
    memoryText.value = "";
    await search();
  }
}
async function correct(m: (typeof memories.value)[number]) {
  await command("MEMORY_CORRECT", {
    id: m.id,
    text: m.text,
    confirmed: true,
    source_id: "console-correction-" + Date.now(),
  });
  await search();
}
async function exportMemory() {
  const r = await command("MEMORY_EXPORT", {});
  if (r?.status === "COMPLETED") {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" }),
    );
    a.download = "MORI-memory-export.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }
}
async function talk() {
  await prepareAudio();
  await command("VOICE_SESSION", { action: "text", text: voice.value });
  voice.value = "";
}
async function audioFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (file.size > 640044) {
    ui.notice = "最多 20 秒，16 kHz 单声道 WAV";
    return;
  }
  const b = new Uint8Array(await file.arrayBuffer());
  let str = "";
  for (const x of b) str += String.fromCharCode(x);
  const r = await api("/api/voice/asr", { audio_base64: btoa(str) });
  voice.value = r.text;
  ui.notice = r.source + " ASR；请确认文字再发送";
}
function chooseTab(value: string) {
  release();
  tab.value = value;
  if (value === "memory") void search();
}
onMounted(() => {
  installLifecycle();
  restorePairing();
  poll = setInterval(() => {
    if (
      tab.value === "vision" &&
      ui.connected &&
      ui.status?.camera.mode === "TRACKING"
    )
      void frame();
  }, 250);
});
onUnmounted(() => {
  if (poll) clearInterval(poll);
});
</script>
<template>
  <div class="shell">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="chooseTab('control')"
        >MORI<span>V1.2 / DEVELOPMENT</span></a
      >
      <nav aria-label="主导航">
        <button
          v-for="[value, label, icon] in tabs"
          :key="value"
          :class="{ selected: tab === value }"
          @click="chooseTab(value)"
        >
          <span class="nav-icon">{{ icon }}</span
          >{{ label }}
        </button>
      </nav>
      <div class="sidebar-foot">
        <span class="connection-dot" :class="{ live: ui.connected }"></span
        >{{ ui.connected ? "本地设备连接" : "尚未连接"
        }}<small>协议 MORI/2<br />软件原型 · 实机能力锁定</small>
      </div>
    </aside>
    <main>
      <header class="topbar">
        <div>
          <p class="eyebrow">MORI / WORKSPACE</p>
          <h1>{{ tabs.find((x) => x[0] === tab)?.[1] }}</h1>
        </div>
        <div class="top-status">
          <span class="pill simulation">{{
            ui.status?.source ?? "未连接"
          }}</span
          ><span class="pill" :class="{ danger: ui.connected && stale() }">{{
            !ui.connected ? "OFFLINE" : stale() ? "STALE · 状态陈旧" : "● 在线"
          }}</span
          ><span class="desktop-only">MORI V1.2</span>
        </div>
      </header>
      <section v-if="!ui.connected" class="pair card">
        <div>
          <h2>连接开发设备</h2>
          <p>
            模拟设备使用本机一次性凭证。读取
            <code>.state/pairing.txt</code>，有效期 10
            分钟。实机配网与绑定尚未验证。
          </p>
        </div>
        <form @submit.prevent="run(() => pair(code))">
          <label
            >服务地址<input
              v-model="ui.base"
              aria-label="服务地址"
              placeholder="https://mori.example.com" /></label
          ><label
            >一次性配对码<input
              v-model="code"
              aria-label="一次性配对码"
              autocomplete="off"
              maxlength="8"
              placeholder="8 位配对码" /></label
          ><button class="primary" :disabled="busy">配对并连接</button
          ><button v-if="ui.identity" type="button" @click="connect">
            重新连接
          </button>
        </form>
      </section>
      <div class="safety-strip">
        <span>ⓘ</span>
        <p>
          模拟数据，不代表实机测量。自主运动仅限人工看护、清场、无台阶地面；无避障或防跌落能力。
        </p>
      </div>
      <div class="toolbar">
        <div>
          <span class="caption">当前控制权</span
          ><strong>{{
            ui.status?.owner === ui.identity?.client_id && ui.status?.owner
              ? "此客户端"
              : ui.status?.owner
                ? "其他客户端"
                : "未持有"
          }}</strong
          ><small
            >{{ ui.status?.state ?? "DISCONNECTED" }} ·
            {{ ui.status?.lease_remaining_ms ?? 0 }} ms</small
          >
        </div>
        <div class="actions">
          <button @click="claim" :disabled="!ui.connected">
            取得控制权 / 续租</button
          ><button class="stop" @click="release" :disabled="!ui.connected">
            ■ 停止移动
          </button>
        </div>
      </div>
      <div v-if="ui.notice" class="notice" role="status">{{ ui.notice }}</div>
      <template v-if="tab === 'control'">
        <div class="control-grid">
          <section class="card face-panel">
            <div class="card-title">
              <h2>双眼预览</h2>
              <span class="caption">EYES ONLY / 360 × 360</span>
            </div>
            <EyesPreview
              :state="ui.status?.expression ?? 'idle'"
              :rms="ui.playbackRms"
            />
            <div class="expression-list">
              <button
                v-for="m in moods"
                :key="m"
                :class="{ active: ui.status?.expression === m }"
                @click="command('SET_EXPRESSION', { state: m })"
              >
                {{ m }}
              </button>
            </div>
            <p class="muted center">闭眼只改变表情 · 不改变平衡状态</p>
          </section>
          <section class="card motion-panel">
            <div class="card-title">
              <h2>手动控制</h2>
              <span class="pill">遥控</span>
            </div>
            <div class="arming">
              <label class="check"
                ><input
                  v-model="local"
                  type="checkbox"
                />明确解锁此模拟设备</label
              ><button
                @click="command('ARM', { local_confirmation: local })"
                :disabled="!local"
              >
                解锁模拟运动
              </button>
            </div>
            <div
              class="dpad"
              @pointerup="release"
              @pointercancel="release"
              @lostpointercapture="release"
            >
              <button
                class="up"
                aria-label="向前"
                @pointerdown.prevent="
                  ($event.currentTarget as HTMLElement).setPointerCapture(
                    $event.pointerId,
                  );
                  startDrive(0.08, 0);
                "
              >
                ↑</button
              ><button
                class="left"
                aria-label="向左"
                @pointerdown.prevent="
                  ($event.currentTarget as HTMLElement).setPointerCapture(
                    $event.pointerId,
                  );
                  startDrive(0, 0.35);
                "
              >
                ←
              </button>
              <div class="dpad-center">
                {{ ((ui.status?.v_m_s ?? 0) * 1000).toFixed(0)
                }}<small>mm/s · 模拟</small>
              </div>
              <button
                class="right"
                aria-label="向右"
                @pointerdown.prevent="
                  ($event.currentTarget as HTMLElement).setPointerCapture(
                    $event.pointerId,
                  );
                  startDrive(0, -0.35);
                "
              >
                →</button
              ><button
                class="down"
                aria-label="向后"
                @pointerdown.prevent="
                  ($event.currentTarget as HTMLElement).setPointerCapture(
                    $event.pointerId,
                  );
                  startDrive(-0.08, 0);
                "
              >
                ↓
              </button>
            </div>
            <p class="muted center">
              按住移动，松开即停止续租。上限 100 mm/s。
            </p>
            <div class="divider"></div>
            <h3>双轴头部 <span class="caption">角度估计</span></h3>
            <label class="range-label"
              >Yaw <output>{{ yaw }}°</output
              ><input
                v-model.number="yaw"
                aria-label="头部 Yaw"
                type="range"
                min="-60"
                max="60"
              /><span>−60° <span>+60°</span></span></label
            ><label class="range-label"
              >Pitch <output>{{ pitch }}°</output
              ><input
                v-model.number="pitch"
                aria-label="头部 Pitch"
                type="range"
                min="-20"
                max="25"
              /><span>−20° <span>+25°</span></span></label
            ><button
              class="wide"
              @click="
                command('HEAD_TARGET', {
                  yaw_rad: (yaw * Math.PI) / 180,
                  pitch_rad: (pitch * Math.PI) / 180,
                })
              "
            >
              发送有界头部目标
            </button>
          </section>
        </div>
        <div class="bottom-grid">
          <section class="card">
            <div class="card-title">
              <h2>有界动作</h2>
              <span class="caption">SIMULATION</span>
            </div>
            <div class="button-grid">
              <button @click="command('MOVE_DISTANCE', { distance_m: 0.1 })">
                前进 100 mm</button
              ><button
                @click="command('TURN_ANGLE', { angle_rad: Math.PI / 6 })"
              >
                左转 30°</button
              ><button
                @click="
                  command('ACTIVE_ACTION', { pattern: 'nod', supervised: true })
                "
              >
                点头</button
              ><button
                @click="
                  command('ACTIVE_ACTION', {
                    pattern: 'shake',
                    supervised: true,
                  })
                "
              >
                摇头
              </button>
            </div>
            <p class="muted">动作由本机状态机执行，300 ms 失联撤销目标。</p>
          </section>
          <section class="card">
            <h2>设备状态</h2>
            <dl class="metrics">
              <div>
                <dt>驱动</dt>
                <dd>{{ ui.status?.enabled ? "模拟使能" : "禁止" }}</dd>
              </div>
              <div>
                <dt>电压 / 电流 / 温度</dt>
                <dd>NOT_TESTED</dd>
              </div>
              <div>
                <dt>硬件最大控制时延</dt>
                <dd>NOT_TESTED</dd>
              </div>
              <div>
                <dt>故障</dt>
                <dd>{{ ui.status?.fault ?? "无模拟故障" }}</dd>
              </div>
            </dl>
          </section>
        </div>
      </template>
      <template v-else-if="tab === 'vision'"
        ><div class="bottom-grid">
          <section class="card">
            <h2>相机与目标</h2>
            <p class="muted">
              像素模拟源 → OpenCV 色标检测。没有随机检测框；不识别身份。
            </p>
            <div class="actions">
              <button
                v-for="m in ['OFF', 'SNAPSHOT', 'TRACKING']"
                :key="m"
                :class="{ active: ui.status?.camera.mode === m }"
                @click="camera(m)"
              >
                {{ m }}
              </button>
            </div>
            <label class="check"
              ><input
                :checked="
                  uploadPending ?? ui.status?.camera.upload_allowed ?? false
                "
                :disabled="!ui.connected || busy"
                @change="setUploadConsent"
                type="checkbox"
              />允许本次按需抓拍上传语义服务（跟踪默认本地）</label
            ><img
              v-if="picture"
              class="camera-preview"
              :src="picture"
              alt="SIMULATED 像素输入"
            />
            <div v-else class="camera-empty">相机关闭 / 尚无画面</div>
            <div class="actions">
              <button
                @click="frame"
                :disabled="ui.status?.camera.mode === 'OFF'"
              >
                抓拍</button
              ><button
                @click="
                  run(async () => {
                    description = JSON.stringify(
                      await api('/api/camera/describe', {}),
                    );
                  })
                "
              >
                按需识物
              </button>
            </div>
            <p>{{ description }}</p>
            <p class="muted">
              观测年龄 {{ ui.status?.camera.age_ms ?? "—" }} ms · 超过 250 ms
              停止跟随
            </p>
          </section>
          <section class="card">
            <h2>跟踪与有限巡游</h2>
            <p>
              先在托架中验证头部跟踪，再验证底盘。画面大小仅为相对线索，没有米级测距。
            </p>
            <button
              class="wide"
              @click="
                command('SELECT_TARGET', {
                  target_id: ui.status?.camera.observation?.target_id ?? '',
                  confirmed: true,
                })
              "
              :disabled="
                !ui.status?.camera.observation ||
                ui.status.camera.observation.uncertain
              "
            >
              确认当前目标 {{ ui.status?.camera.observation?.target_id ?? "—" }}
            </button>
            <div class="button-grid">
              <button
                @click="command('FOLLOW', { mode: 'HEAD', supervised: true })"
              >
                头部跟踪</button
              ><button
                @click="command('FOLLOW', { mode: 'BODY', supervised: true })"
              >
                模拟底盘跟随</button
              ><button
                @click="
                  command('PATROL', {
                    duration_s: 20,
                    segment_m: 0.1,
                    supervised: true,
                  })
                "
              >
                巡游 20 秒</button
              ><button
                @click="
                  command('ACTIVE_ACTION', {
                    pattern: 'short_forward',
                    supervised: true,
                  })
                "
              >
                主动短距离活动</button
              ><button
                @click="
                  command('CANCEL', { command_id: ui.status?.active ?? 'none' })
                "
              >
                取消当前动作
              </button>
            </div>
            <h3>可复现视觉场景</h3>
            <div class="button-grid">
              <button
                v-for="[s, l] in [
                  ['single', '单目标'],
                  ['multiple', '多人 / 遮挡'],
                  ['lost', '目标丢失'],
                  ['dark', '曝光不足'],
                ]"
                :key="s"
                @click="
                  run(() => api('/api/simulation/scenario', { scenario: s }))
                "
              >
                {{ l }}
              </button>
            </div>
            <p class="muted">
              丢失或歧义后必须重新确认目标，不会自动换人。实机自主模式 BLOCKED。
            </p>
          </section>
        </div></template
      >
      <template v-else-if="tab === 'voice'"
        ><section class="card readable">
          <h2>中文语音会话</h2>
          <span class="pill simulation"
            >{{ ui.voiceSource }} · 半双工开发链路</span
          >
          <p>
            无密钥时播放测试音，不冒充中文 TTS。文本和 WAV 可进入独立 ASR / LLM
            / TTS 适配器。
          </p>
          <form @submit.prevent="run(talk)">
            <label
              >中文输入<textarea
                v-model="voice"
                aria-label="中文输入"
                placeholder="例如：停下"
                maxlength="2000"
              ></textarea>
            </label>
            <div class="actions">
              <button class="primary">发送并播放</button
              ><button
                type="button"
                @click="
                  command('VOICE_SESSION', { action: 'interrupt', text: '' })
                "
              >
                打断
              </button>
            </div>
          </form>
          <label class="file-input"
            >上传测试 WAV（16 kHz / 单声道 / ≤20 秒）<input
              type="file"
              accept=".wav,audio/wav"
              @change="run(() => audioFile($event))"
          /></label>
          <p class="voice-response">{{ ui.voiceText || "等待会话输入" }}</p>
          <div class="actions">
            <button @click="command('BUTTON', { gesture: 'short' })">
              模拟短按</button
            ><button @click="command('BUTTON', { gesture: 'double' })">
              模拟双击停止
            </button>
          </div>
          <p class="muted">
            “停下”走
            STOP_MOTION；语音不能替代硬件急停。自定义“你好，莫里”模型未提供，唤醒准确率与设备打断尚未实测。
          </p>
          <pre>{{ ui.voiceMetrics }}</pre>
        </section></template
      >
      <template v-else-if="tab === 'memory'"
        ><section class="card">
          <div class="card-title">
            <h2>个人长期记忆</h2>
            <label class="check"
              ><input
                v-model="memoryOn"
                type="checkbox"
                @change="
                  command('MEMORY_ENABLED', { enabled: memoryOn });
                  search();
                "
              />启用</label
            >
          </div>
          <p>
            SQLite
            持久保存，按用户与设备隔离。推断、已确认事实和纠正记录分别保留。不会自动保存音视频或身份模板。
          </p>
          <div class="memory-add">
            <textarea
              v-model="memoryText"
              aria-label="新增记忆"
              placeholder="明确希望记住的偏好"
              maxlength="2000"
            ></textarea
            ><label class="check"
              ><input
                v-model="confirmed"
                type="checkbox"
              />我确认保存这条内容</label
            ><button @click="remember" :disabled="!confirmed || !memoryText">
              记住
            </button>
          </div>
          <form class="actions" @submit.prevent="search">
            <input
              v-model="query"
              aria-label="搜索记忆"
              placeholder="搜索来源明确的记忆"
            /><button>检索</button
            ><button type="button" @click="exportMemory">导出</button>
          </form>
          <p v-if="!memories.length" class="empty">尚无匹配记忆</p>
          <article v-for="m in memories" :key="m.id" class="memory-entry">
            <textarea v-model="m.text" :aria-label="'记忆 ' + m.id"></textarea
            ><small
              >{{ m.category }} ·
              {{ m.confirmed ? "已确认" : "推断 / 未确认" }} ·
              {{ m.source_id }} · {{ m.updated_at }}</small
            >
            <div class="actions">
              <button @click="correct(m)">确认纠正</button
              ><button
                @click="command('MEMORY_DELETE', { id: m.id }).then(search)"
              >
                删除
              </button>
            </div>
            <details v-if="m.conflicts.length">
              <summary>纠正历史 {{ m.conflicts.length }}</summary>
              <pre>{{ m.conflicts }}</pre>
            </details>
          </article>
          <p class="muted">
            删除清理正文、索引与冲突记录；备份默认最多保留 7
            天，恢复必须重放独立删除清单。
          </p>
        </section></template
      >
      <template v-else
        ><div class="bottom-grid">
          <section class="card">
            <h2>维护与故障</h2>
            <p>
              禁驱后可能倒下。维护、刷机、关机之前必须有可靠外部支撑；下方仅为人工确认。
            </p>
            <label class="check"
              ><input
                v-model="support"
                type="checkbox"
              />已放入托架或可靠人工支撑</label
            >
            <div class="button-grid">
              <button
                @click="command('DISARM', { support_confirmed: support })"
              >
                禁驱 DISARM</button
              ><button
                @click="command('ACK_FAULT', { support_confirmed: support })"
              >
                人工确认故障</button
              ><button
                @click="
                  command('ENTER_MAINTENANCE', {
                    support_confirmed: support,
                    cabled: true,
                  })
                "
              >
                进入维护态</button
              ><button @click="command('BUTTON', { gesture: 'long' })">
                模拟长按</button
              ><button
                class="danger"
                @click="
                  command('FAULT_STOP', { reason: 'OPERATOR_FAULT_INJECTION' })
                "
              >
                模拟严重故障
              </button>
            </div>
            <h3>音量与唤醒</h3>
            <label
              >音量
              <input
                aria-label="音量"
                type="range"
                min="0"
                max="1"
                step=".05"
                :value="ui.status?.volume ?? 0.55"
                @change="
                  command('VOLUME', {
                    level: Number(($event.target as HTMLInputElement).value),
                  })
                "
            /></label>
            <p class="muted">你好，莫里：BLOCKED · 缺少离线模型与许可核验</p>
            <button
              @click="
                command('WAKE_CONFIG', {
                  enabled: true,
                  requested_phrase: '你好，莫里',
                })
              "
            >
              检查自定义唤醒配置
            </button>
          </section>
          <section class="card">
            <h2>版本与额度</h2>
            <dl class="metrics">
              <div>
                <dt>控制台</dt>
                <dd>{{ ui.status?.software_version ?? "1.2.0-dev.1" }}</dd>
              </div>
              <div>
                <dt>协议</dt>
                <dd>MORI/2</dd>
              </div>
              <div>
                <dt>通道</dt>
                <dd>本地模拟 / HTTPS 云适配</dd>
              </div>
              <div>
                <dt>设备</dt>
                <dd>{{ ui.status?.device_id ?? "—" }}</dd>
              </div>
              <div>
                <dt>1.2 主选</dt>
                <dd>
                  STM32 · S288 · SCS0009<br />CAM-OV3660 · ST77916 360×360
                </dd>
              </div>
              <div>
                <dt>参数 / 实机解锁</dt>
                <dd>
                  {{ ui.status?.parameter_version ?? "V1.2-UNMEASURED-1"
                  }}<br />BLOCKED · 校准与安全链待测
                </dd>
              </div>
            </dl>
            <button
              @click="
                run(async () => {
                  ui.costs = await api('/api/budget');
                })
              "
            >
              查看 API 额度
            </button>
            <pre>{{ ui.costs }}</pre>
            <h3>本机通信统计（非 MCU 实测时延）</h3>
            <pre>{{ ui.statistics }}</pre>
            <button @click="run(revokePairing)">撤销此客户端凭证</button>
            <p class="muted">
              当前仅开发网页；App 暂停。模拟绑定不代表实机 Wi-Fi 配网完成。
            </p>
          </section>
        </div></template
      >
      <section class="card event-panel">
        <div class="card-title">
          <h2>命令记录</h2>
          <span class="caption">接收 ≠ 完成</span>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>命令</th>
                <th>状态</th>
                <th>说明</th>
                <th>ID</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!ui.results.length">
                <td colspan="4" class="empty">
                  尚无命令。连接不会自动解锁或发送运动目标。
                </td>
              </tr>
              <tr
                v-for="r in ui.results.slice(0, 8)"
                :key="r.command_id + r.status"
              >
                <td>{{ r.type }}</td>
                <td>
                  <span
                    class="result-state"
                    :class="{
                      danger: r.status === 'REJECTED' || r.status === 'FAULT',
                    }"
                    >{{ r.status }}</span
                  >
                </td>
                <td>{{ r.reason || "—" }}</td>
                <td class="mono">{{ r.command_id?.slice(0, 8) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <footer>
        软件验证工作区 <span>硬件 / 自由平衡 / 60 分钟续航：NOT_TESTED</span>
      </footer>
    </main>
  </div>
</template>
