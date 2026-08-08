---
name: vox-director
description: >
  Turn ONE topic into a finished Vox-style paper-collage explainer / ad video, end to end
  on a self-hosted OpenAI-compatible aggregator + local ffmpeg — script, collage keyframes,
  motion, voice-over, music, all automated. 触发: "vox 视频"、"拼贴视频"、"motion collage"、
  "纸拼贴讲解"、"做一个拼贴广告"、"把这个话题做成拼贴视频" 等。三选一输入: 选题(B-roll)、
  口播视频(A-roll)、静态照片(C-roll)。注意: 本网关当前只支持 B-roll(选题)。
---

# Vox Director(拼贴动效导演)

把一个一句话选题变成一条成片:旁白讲解式的 **Vox 风纸拼贴视频**——每一拍是一张撕纸拼贴
海报,配动效、旁白与字幕。媒体生成全部跑在 **自托管 OpenAI 兼容网关(newapi)** 上,本地
只用 ffmpeg 合成。

## 本网关模型(2026-08-08 实测验证)

| 用途 | 模型 | 备注 |
|---|---|---|
| 剧本/分镜(chat) | `deepseek-v4-flash-free` / `agnes-2.0-flash` | `mimo-v2.5-free`(结果在 reasoning 字段) |
| 拼贴海报关键帧 | `agnes-image-2.1-flash` | 参数用 `size`;输出**公网可下载 URL** |
| 关键帧(备选) | `gpt-image-2` / `grok-imagine-image` / `-quality` | gpt-image-2 直接返回 b64_json;grok-* 需显式 `GROK2API_BASE`+`GROK2API_KEY` 取回为 base64 data URI |
| 海报动效(图生视频) | `agnes-video-v2.0`(默认)/ `grok-imagine-video` | agnes:`duration` 秒、`image` 支持 base64、跟随输入图比例。grok-imagine-video:**直连 Grok2API** `POST /v1/videos/generations`(v3.1.1:`request_id` 轮询 `pending/done/failed`,`image` 传 `{"url"}` 对象,base64 data URI 实测可用;需显式 `GROK2API_BASE`+`GROK2API_KEY`),显式传 `aspect_ratio`/`resolution` |
| 旁白 TTS | `mimo-v2.5-tts` | chat/completions 音频协议;中文音色用中文名 |
| 音色设计 | `mimo-v2.5-tts-voicedesign` | 自由描述的定制音色 |
| 声音克隆 | `mimo-v2.5-tts-voiceclone` | 参考样本(data URI) |
| 配乐 | ❌ 无 | 用本地 `bgm_file`,或不要 BGM |

**不可用(已验证):** `grok-imagine-image*`(输出 127.0.0.1 内网 URL,取不到)、
`grok-imagine-video`(无 provider)、`gpt-5.5`/`gpt-image-2`(unknown provider)、
`deepseek/deepseek-v4-flash`(403 Cline 专用)。无 STT / 无抠图 / 无 image-edit。

## 前置条件(不要跳过)

- `OPENAI_API_KEY` 已设置(否则停下,让用户配)
- `OPENAI_BASE_URL`(默认 `http://10.0.1.108:18901/v1`)
- `UPSTREAM_PROXY`——本网络必需:10.0.1.108 只能经 `socks5h://192.168.99.3:1080` 显性配置代理访问(后端 `config.json: upstreamProxy` 同款)
- `GROK2API_BASE`——grok-imagine-* 产物由 Grok2API 媒体服务提供(`http://10.0.1.108:8000`,显性配置,无默认)
- `GROK2API_KEY`——Grok2API 控制台签发的 Client Key(显性配置,无默认)
- `ffmpeg` + `ffprobe`(合成必需)
- Python3 + Pillow(字幕/水印)

## 标准流程(选题 → 成片)

每个项目一个 `out/<project>/beats.json` 驱动,按顺序跑:

1. **选题 → 分镜(beats.json)。** 先读 `references/beat-layer.md` 选叙事弧线(`timeline`
   历史、`pas`/`bab` 广告、`how_it_works` 讲解、`man_in_hole` 蜕变…)。beat-1 必须是
   **≤3s 的钩子**;30s→6~8拍,60s→10~12拍;每拍拆 **2 shots**(全景+细节),相邻拍的
   `camera_move` 不要重复(payoff 用 `static`)。每拍写 `narration`、`title_cn/title_en`、
   `scene`、`bg`、`feel`。**这是第一个强制确认点** —— 先给用户看分镜再生成。示例在 `examples/`。

2. **挑风格(关键帧之前)。** 读 `references/prompt-guide.md` §5;从
   `styles.THEME_PRESETS` 挑 3~4 套贴合话题时代/文化/调性的主题(或自组主题),跑一轮试片让
   用户肉眼挑:
   `python3 scripts/style_bakeoff.py out/<project> american-retro,swiss-modern,punk-zine`
   把选中名字写进 beats.json 的 `"theme"`。

3. **关键帧(拼贴海报)。** `python3 scripts/keyframes.py out/<project>`
   用 `agnes-image-2.1-flash` 每拍生成一张成品拼贴海报(文字直接烧进图里)。提示词用
   `references/prompt-guide.md` 的五段式结构。**动效前先检查海报质量**——图不像拼贴,
   后面救不回来,重roll图比重动效便宜。

4. **动效。** `python3 scripts/clips.py out/<project>`
   用 `agnes-video-v2.0` 让每张海报动起来(「活海报」)。两个独立轴:
   - `camera_move` 每 shot 一个:安全 `{static, push_in, pull_out, pan, tilt, parallax}`;
     大胆 `{orbit, dolly_zoom, roll, whip}` 配 `constraints: loose` 并重roll。
   - `element_motion`:能量所在——**让 AI 每拍按场景写**(别套模板),要丰富;英雄元素
     飞场是亮点,别每拍都用。
   `motion_style` = `calm|punchy|max`,`constraints` = `strict`(默认)|`loose`。
   agnes 动效**跟随输入图比例**,无需额外比例配置。

5. **旁白(+可选音乐)。** `python3 scripts/audio.py out/<project>`
   统一音色旁白,默认 `mimo-v2.5-tts`。**音色要按话题+语种挑**(见 `references/voices.md`):
   `mimo_default`/`冰糖`/`茉莉`/`苏打`/`白桦`(中文),`Mia`/`Chloe`/`Milo`/`Dean`(英文)。
   定制音色:`voice.voice_desc`(如"一位年迈老师傅,北方口音,沙哑慢语速");克隆真人声:
   `voice.clone_ref` 指向本地样本。**网关没有音乐模型**:`bgm_file` 放本地曲子,或者无 BGM。

6. **合成。** `python3 scripts/assemble.py out/<project>`
   ffmpeg:拼接所有镜头、旁白铺底(有 BGM 时自动闪避)、每拍烧字幕、加水印 →
   `out/<project>/final.mp4`。

7. **验收。** `ffmpeg -ss <t> -i final.mp4 -vf "scale=640:-1,format=yuvj420p" -frames:v 1 f.jpg`
   抽帧看,别读 mp4。

### 节奏感——镜头多长

每 **4~6 秒**切一刀:镜头 3~6s,**单镜头别超 7s**;每拍旁白 ~8-10s → 每拍拆 2 个 shots
(带标题的 wide + 不带标题的细节 cut-in),旁白跨两剪接续;60s ≈ 6拍×2 shots×~5s=12 剪。
`keyframes.py` 会跳过已有 `keyframe_url` 的 shot,补细节 shot 只补新的。

## A-roll(口播视频)与 C-roll(单照片)

**当前网关不可用**:无 STT(`asr_beats.py` 报错)、无 video-edit、无抠图/图片编辑模型。
脚本保留,等网关补模型即接通。今天请走 B-roll。

## beats.json 结构要点

```json
{
  "project": "my-film", "topic": "...", "language": "zh", "aspect": "9:16",
  "style": "collage", "provider": "openai",
  "theme": "american-retro", "arc": "timeline",
  "video_model": "agnes-video-v2.0",
  "image_model": "agnes-image-2.1-flash",
  "motion_style": "punchy", "constraints": "strict",
  "voice": {"voice_id": "冰糖", "language": "zh", "speed": 1.0},
  "bgm_file": "bgm.mp3",
  "beats": [
    {"id": 1, "title_en": "BEFORE MONEY", "bg": "earthy tan", "hook": "surprising_stat",
     "narration": "……",
     "shots": [
       {"id": "a", "dur": 5, "title": true,  "camera_move": "push_in",  "scene": "……",
        "element_motion": "……"},
       {"id": "b", "dur": 5, "title": false, "camera_move": "parallax", "scene": "……"}
     ]}
  ]
}
```

## 常见坑(已填平,先读再排错)

`references/models-and-gotchas.md` 记录了全部实测 API/ffmpeg 坑:UA 头必须带;视频
`image` 必须公网 URL 或 base64;`num_frames` 必须 8n+1(用 `duration` 代替);图片参数
`size`(agnes) vs `aspect_ratio`(grok)不同;TTS 同步返回 base64;下载兼容 data URI
与 https;无 libass → 字幕走 Pillow PNG。**大多数失败都能在里边找到答案。**

## 改造标准(2026-08-08)

- 后端 = 自有 OpenAI 兼容网关(`OPENAI_API_KEY`/`OPENAI_BASE_URL`),**不兼容 Atlas**。
- 模型映射:deepseek-v4-flash-free(剧本)、agnes-image-2.1-flash(关键帧)、
  agnes-video-v2.0(动效)、mimo-v2.5-tts 三兄弟(旁白/音设/克隆)。
- 无音乐/无STT/无抠图 → BGM 可选、A/C-roll 关闭,留好接口。
- 完整映射与决策,另见项目根目录 `CLAUDE.md`。