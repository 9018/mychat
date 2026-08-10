# OpenMontage HyperFrames 优化使用方法

> 当前已验证版本：2026-08-11。适用于 OpenMontage 的竖版信息视频、动效标题和图像/视频蒙太奇。白海豚 60 秒试片按此流程完成。

## 结论

当前推荐的生产链路是：

```text
OpenMontage artifacts
  → HyperFrames 独立 workspace
  → lint
  → validate
  → 原生 1080×1920 / 30fps 渲染
  → FFmpeg 缩放为 720×1280 交付
  → ffprobe + 关键帧人工检查
```

HyperFrames 负责 HTML/CSS/GSAP 合成、标题、画面层、音频挂接和渲染；OpenMontage 的 `artifacts/` 仍是脚本、场景、素材 provenance 和时间轴的事实来源。

## 1. 运行时准备

必须使用公开 npm 包名 `hyperframes`，不要使用不存在的 `@hyperframes/cli`：

```bash
node --version                 # Node 22+
ffmpeg -version
npx --no-install hyperframes --version
```

本机已验证：Node 22、FFmpeg 8、HyperFrames 0.7.105 可以离线运行。npm registry 超时不等于本地 CLI 不可用；优先使用 `npx --no-install`，避免渲染时再次联网解析。

可选环境诊断：

```bash
npx --no-install hyperframes doctor --json
```

`doctor` 可能因可选的 Whisper/Kokoro/MusicGen 未安装而报告 `ok:false`，只要 Node、FFmpeg、Chrome 和本地 HyperFrames CLI 可用，不阻塞本地图像+旁白渲染。

## 2. 项目目录约定

每个 HyperFrames 项目使用独立 workspace，不复用 Remotion 的公共目录：

```text
projects/<project-id>/
├── artifacts/              # OpenMontage canonical artifacts
├── assets/                 # 原始图片、视频、旁白、音乐及 provenance
├── hyperframes/
│   ├── index.html          # 根合成，由 compose 生成或维护
│   ├── hyperframes.json    # registry 和路径配置
│   ├── DESIGN.md           # playbook 派生的设计令牌
│   └── assets/             # workspace 内相对路径素材
└── renders/
    ├── *-1080x1920.mp4     # 原生渲染结果
    └── *-720x1280.mp4      # 最终交付结果
```

已完成的白海豚示例：

```text
projects/white-dolphin-hyperframes-60s/
```

## 3. 时间轴和图层规则

### 3.1 场景分段

先在 `artifacts/script.json`、`scene_plan.json` 和 narration visual contract 中锁定场景时间，再生成 `edit_decisions.cuts[]`。每个画面段必须有：

- `in_seconds` / `out_seconds`
- `asset_id` 或相对素材路径
- `track_index`
- 对应旁白段和画面语义

白海豚试片采用 6 段：`0–8、8–18、18–29、29–39、39–50、50–60`。

### 3.2 视觉层与标题层

- 画面放在 `track_index: 1`。
- 标题/副标题作为覆盖层放在 `track_index: 4`。
- 音频不要占用标题层使用的轨道；当前旁白使用独立音频轨。
- 保留真实 `track_index`，不能在 HTML 生成时全部写死为 1。
- 视觉 cuts 使用 `out_seconds = 场景结束 - 0.02`，留下 20ms 非重叠间隙，避免 HyperFrames 静态时间轴检查把相邻场景判为重叠；音频段仍使用完整场景时间。

### 3.3 标题卡布局

标题卡必须是纵向布局：

```css
.clip.text-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
```

标题和副标题放入面板容器，避免大字号中文挤压、横向错位或与背景对比不足：

```html
<div class="text-card-panel">
  <h1>主标题</h1>
  <div class="subtitle">副标题</div>
</div>
```

建议使用深色半透明面板、左侧强调色线、标题白色、辅助信息使用主题 accent 色；标题字号必须结合竖版安全区检查，不能只按横版比例放大。

## 4. 标准执行顺序

### 4.1 生成 workspace

通过 `HyperFramesCompose` 的 `scaffold_workspace`，把 OpenMontage 的 `edit_decisions`、`asset_manifest`、playbook 和 profile 转换成 `index.html`、CSS、音频引用和 workspace 素材。

使用工具时，关键输入保持如下关系：

```json
{
  "operation": "scaffold_workspace",
  "workspace_path": "projects/<project-id>/hyperframes",
  "profile": "tiktok",
  "fps": 30,
  "edit_decisions": "<已锁定的 cuts + audio>",
  "asset_manifest": "<带 provenance 的素材清单>",
  "playbook": "<已锁定风格包>"
}
```

### 4.2 静态检查

```bash
cd projects/<project-id>/hyperframes
npx --no-install hyperframes lint --json > /tmp/<project-id>-lint.json
```

必须满足：`ok: true`、`errorCount: 0`。警告需要记录原因；时间轴密度或 composition selector 警告可以保留，但不能有错误。

### 4.3 浏览器验证

```bash
npx --no-install hyperframes validate --json > /tmp/<project-id>-validate.json
```

必须满足：`ok: true`、`errors: 0`、`contrastFailures: 0`。最终交付不能使用 `--no-contrast` 绕过对比度检查。

### 4.4 原生渲染

```bash
npx --no-install hyperframes render \
  --output renders/<project-id>-1080x1920.mp4 \
  --fps 30 \
  --quality standard
```

原生渲染保留 1080×1920，便于检查标题安全区和画面细节；不要直接把低分辨率作为唯一母版。

### 4.5 生成 720p 交付文件

```bash
mkdir -p ../renders
ffmpeg -y \
  -i renders/<project-id>-1080x1920.mp4 \
  -vf scale=720:1280:flags=lanczos \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 160k \
  ../renders/<project-id>-720x1280.mp4
```

交付文件必须保留旁白和背景音乐，不能在缩放时使用 `-an`。

## 5. 交付验收

### 5.1 技术验收

```bash
ffprobe -v error \
  -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,channels \
  -of default=nw=1 \
  ../renders/<project-id>-720x1280.mp4
```

目标结果：

- 时长约 60 秒；
- `width=720`、`height=1280`；
- `r_frame_rate=30/1`；
- 视频 `h264`；
- 音频 `aac`，通常为双声道；
- 文件可正常播放，不能只有画面没有音频。

### 5.2 关键帧验收

至少抽查开头、转场后、中后段和结尾：

```bash
ffmpeg -y -ss 2  -i ../renders/<project-id>-720x1280.mp4 -frames:v 1 -q:v 2 -update 1 ../renders/frame-2s.png
ffmpeg -y -ss 42 -i ../renders/<project-id>-720x1280.mp4 -frames:v 1 -q:v 2 -update 1 ../renders/frame-42s.png
```

检查：

- 第一幕不是测试色块或空白；
- 标题没有被裁切，主副标题纵向排列；
- 标题没有遮住主体信息；
- 每幕标题、画面和旁白语义一致；
- 片尾没有突然黑屏或音频截断。

### 5.3 代码回归

修改 HyperFrames 生成器后执行：

```bash
cd OpenMontage
python3 -m pytest tests/tools/test_hyperframes_compose.py -q
git diff --check
```

当前优化后的回归结果：`49 passed`。

## 6. 当前已知事项

1. HyperFrames 的渲染链路已可用，但属于动态 HTML/CSS/GSAP 合成；60 秒 1080×1920 渲染时间可能明显长于 FFmpeg 拼接。
2. 旁白源文件如果短于预定场景槽位，HyperFrames 会按媒体实际长度缩短音频，剩余时间由背景音乐填充。正式交付前应把旁白槽位改为实际音频时长，或在脚本阶段重新生成与画面节拍一致的旁白。
3. HyperFrames 适合动效标题、宣传片、信息图和 UI/网页风格合成；逐字字幕、口型头像和已有 Remotion 专用组件仍应继续使用 Remotion。
4. 不允许把生成图像冒充真实纪录素材；所有图片、视频、旁白和音乐必须保留 provider/provenance 记录。

## 7. 白海豚当前产物

```text
projects/white-dolphin-hyperframes-60s/renders/white-dolphin-hyperframes-60s-720x1280.mp4
```

该文件已按本方法完成渲染、缩放、`ffprobe` 检查和关键帧抽查。
