# OpenMontage 单入口融合运行手册

OpenMontage 是唯一生产入口；`vox-director` 只保留为历史参考和已迁移产物目录，不作为运行时依赖。

HyperFrames 当前验证过的竖版视频用法、图层规则、渲染命令和验收步骤见：[HYPERFRAMES_OPTIMIZED_USAGE.md](HYPERFRAMES_OPTIMIZED_USAGE.md)。

## 离线单入口起步

先用单入口命令生成候选风格和锁定的 creative treatment，再进入真实 provider 调用。这个步骤不会产生外部调用，也不会偷偷替换风格、运行时或供应商：

```bash
cd OpenMontage
python scripts/plan_single_entry.py \
  --project-id typhoon-13 \
  --title '第13号台风白海豚' \
  --pipeline cinematic \
  --brief-json /path/to/brief.json \
  --project-root /data/a9017/ai-v2/projects \
  --runtime remotion \
  --provider image --provider video
```

命令会写入：

- `artifacts/style-candidates.json`：当前能力矩阵下所有可执行风格候选及兼容性状态；
- `artifacts/creative_treatment.json`：锁定的风格包版本、构图模式、资产策略、标题系统、运行时和交付承诺；
- `treatments/style-packages/<style-id>/<version>/`：项目级不可变风格快照。

如果需要指定风格，增加 `--style vox-newsprint-editorial`。若该风格在当前运行时或 provider 能力下只能进入 atelier/degraded 状态，命令仍会明确返回状态，后续必须经过人工试片和审批，不得静默降级。

单入口同时生成 `scene_plan.json` 和 `motion_plan.json`。后者会把每个场景的资产来源、运动、转场、标题策略和安全区绑定到 treatment hash；因此后续 provider 或 renderer 不能绕开已批准的创意合同。

如需先验证本机编码、画幅、fps 和 QA 门，可以运行离线闭环命令：

```bash
python scripts/run_single_entry.py \
  --project-id typhoon-13 \
  --title '第13号台风白海豚' \
  --pipeline cinematic \
  --brief-json /path/to/brief.json \
  --project-root /data/a9017/ai-v2/projects \
  --runtime ffmpeg
```

它会生成 10–15 秒本地技术预览和 `artifacts/qa_report.json`。技术项通过不等于创意通过；该报告会明确保持 `blocked`，直到真实风格样片、素材 provenance、创意评分和人工审批补齐。

brief JSON 可以包含 `topic`、`production_family`、`style_family`、`aspect_ratio`、`duration_seconds`、`width`、`height`、`fps`、`language`、`quality_mode`、`references`、`narrative_structure`、`title_font`、`body_font`、`pace`、`narration`、`music`、`sfx` 和 `secondary_families` 等字段。

## 标准路径

```text
vox-collage: research → proposal → script → scene_plan → assets → edit → compose → publish
```

在 `proposal` 中锁定供应商、模型、画幅、标题策略和 `render_runtime`，后续阶段从 checkpoint 读取，不静默切换。

## 配置

根目录 `.env` 是唯一明文密钥来源。支持：

- `AGNES_API_KEY` / `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `GROK2API_KEY` / `XAI_API_KEY`
- `GROK2API_BASE` / `XAI_BASE`

执行 provider preflight 时只输出 `set/missing` 和主机名，不输出密钥。

## 输出与恢复

- 生成视频完成前，将 `request_id` 写入 assets checkpoint；恢复时传回同一 `request_id`，不会重复提交任务。
- compose 默认使用 Remotion 处理图片、标题和动效；纯视频剪辑使用 FFmpeg。
- 本地资源策略上限为单段 10 秒、并发 2。
- publish 的 `output_mirror_root` 只镜像最终视频，不复制中间 MP4。

## 验收命令

```bash
cd OpenMontage
pytest -q
(cd remotion-composer && npx tsc --noEmit)
python scripts/live_provider_smoke.py --confirm-live --output-dir /data/a9017/ai-v2/live-smoke
```

最后一条必须在明确配置网关密钥并确认会产生真实调用时执行；离线验收不依赖它。

离线检查七类代表场景（不会调用 provider）：

```bash
python scripts/run_representative_pilots.py \
  --output-dir /data/a9017/ai-v2/pilot-previews
```

该命令生成每个 family 的短 MP4 技术预览和 JSON 报告，用来先确认编码、画幅、fps 和可播放性；创意通过仍需用真实样片填充 `qa_report` 并完成审批。

## 风格覆盖与验收边界

当前注册表包含 OpenMontage 的 6 个风格包和 vox-director 的 10 个主题包。它们共用同一套 schema、版本锁定、兼容性解析、family QA 和审批证据链；项目可以选择其中任一风格，也可以在同一项目中声明主/辅 family。

“电影感”“纪录片”“拼贴”“AI 生成”不再作为互相排斥的全局规则。是否可用由具体风格包、资产来源、运行时、画幅、provider 能力和项目审批共同决定；若使用重建或生成素材，必须在 provenance 和 QA 报告中明确标注，不能冒充真实档案。
