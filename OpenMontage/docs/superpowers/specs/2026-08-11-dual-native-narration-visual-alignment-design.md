# OpenMontage 单入口双原生声画语义对齐设计

日期：2026-08-11

状态：已落地，持续维护

适用范围：OpenMontage 全部视频 pipeline、全部 style package，以及迁入 OpenMontage 的 Vox 原生生产线

## 1. 背景与基线

“白海豚”双样片暴露出一个不能只靠重做镜头解决的流程问题：Vox 的 `beats.json` 已正确描述 8 月 11 日雨区扩展、四个城市节点和 8 月 12 日降温，但后段实际生成画面没有完整表达这些事实；配音时间轴基本落在正确的十秒区间，因此主要问题是语义覆盖失败，不是简单的音频串段。

OpenMontage `clean-professional` 样片通过 Remotion 确定性绘制日期、城市和温度，当前表现更准确，但这些事实主要固化在本片专属 Composition 中，现有 canonical artifacts 和 QA 没有强制记录“哪句旁白由哪个画面证明”。换主题、换 pipeline 或换风格后仍可能复发。

当前执行方法见：

- [`../../HYPERFRAMES_OPTIMIZED_USAGE.md`](../../HYPERFRAMES_OPTIMIZED_USAGE.md)
- [`../../SINGLE_ENTRY_OPERATIONS.md`](../../SINGLE_ENTRY_OPERATIONS.md)

本文是 OpenMontage 单入口全风格融合设计的语义质量补充。它不推翻多 pipeline、多 style package、多 runtime 和专用创作引擎架构，而是补齐所有生产线共同缺少的声画语义合同与证据门。

## 2. 已批准的核心决策

最终架构固定为：

**OpenMontage 单一用户入口 + 两条原生执行线 + 共同声画语义合同 + 共同证据化 QA。**

两条执行线分别是：

1. **Vox 原生线**：保留 beat-driven 叙事、主题预设、生成式纸拼贴关键帧、图生视频、MiMo 旁白和轻量拼接能力。
2. **OpenMontage 原生线**：保留 animated-explainer、cinematic、documentary、animation、character、screen、talking-head、hybrid 等 pipeline，以及 Remotion、HyperFrames、FFmpeg 和其他专用执行器。

两条线共享内容与验收合同，但不共享固定构图模板，也不把所有成片做成同一种风格。

## 3. 目标

### 3.1 生产目标

- 用户只从 OpenMontage 创建、审批、恢复、渲染和发布项目。
- OpenMontage 根据批准的 pipeline、style package、asset strategy、runtime 和 composition mode 路由到正确的原生执行线。
- Vox 不被降级为普通 Remotion 信息卡；OpenMontage 其他风格也不被强制套用纸拼贴语言。
- 每次生产都能回答：每句旁白包含哪些事实、计划如何视觉化、实际由哪个镜头证明、证据帧在哪里。

### 3.2 质量目标

- 所有标记为 `must_show` 的事实必须拥有实际成片证据，覆盖率为 100%。
- 日期、地点、人名、机构名、数量、方向和因果关系等高风险事实准确率为 100%。
- 语义 QA、风格 QA、技术 QA 分开判定，任何一项失败都不能发布。
- 付费图生视频调用之前拦截明显不合格的关键帧，减少无效成本。
- 旁白不因固定镜头长度被不受控加速、截断或跨段。

## 4. 非目标

- 不用单一模板统一全部风格。
- 不要求每句旁白都用文字重复显示；事实可以由地图、图表、对象、动作、来源素材、程序化图形或准确后期文字表达。
- 不禁止电影、纪录片、插画或其他风格使用抽象画面；抽象画面可以承担情绪和过渡，但不能替代已经声明为 `must_show` 的精确信息。
- 不依赖图像模型准确生成关键中文、地名、日期和数字。
- 不在本设计阶段更换 provider、模型、声音或已批准 runtime。

## 5. 根因结论

当前问题由四层缺口共同造成：

1. **脚本层只有段落，没有事实原子。** 一段旁白可以同时包含日期、方向、地点和数值，但 scene plan 只记录一条宽泛描述。
2. **生成层把事实表达交给概率模型。** 提示词虽然写了河南地图、四城节点和雨区方向，实际落图可以只保留云雨和抽象符号。
3. **资产门只验证文件与风格。** 图片能打开、视频能解码、纸张材质符合风格，并不代表旁白事实被表达。
4. **最终验收采样不足。** 每十秒抽一帧无法覆盖两个五秒镜头，也不能发现视频中途的文字变形、物体消失或语义漂移。

因此，修复点必须位于脚本、场景、资产、剪辑和成片五个阶段，不能只加强提示词或只重做当前四段素材。

## 6. 总体架构

```text
用户输入 / 来源材料
        |
        v
OpenMontage Pipeline + Style Director
        |
        v
script.json
        |
        v
narration_visual_contract.json
  - claim 原子
  - 时间目标
  - must_show
  - 表达方式
  - 精确性等级
        |
        v
scene_plan.json（scene/shot 引用 claim_ids）
        |
        +---------------------------+
        |                           |
        v                           v
Vox 原生执行线                 OpenMontage 原生执行线
生成式拼贴底层                 各 pipeline/style 原生资产
+ 确定性事实图层               + 确定性或来源事实图层
        |                           |
        +-------------+-------------+
                      |
                      v
semantic_qa_report.json
  - 资产证据
  - 成片证据
  - 实际 TTS 时间
  - claim 覆盖结果
                      |
                      v
风格 QA + 技术 QA + 人工审批
                      |
                      v
Publish
```

## 7. 新增 canonical artifact：narration_visual_contract.json

该 artifact 在 script 审批后、scene plan 完成前建立，是旁白内容和视觉计划之间的正式合同。

它不要求新增一个用户可见的顶层流水线阶段：实现时由 script 阶段的批准输出或 scene planning 的入口步骤生成，并作为 scene plan 的强制上游依赖。具体归属由实施计划结合现有 checkpoint 和 artifact registry 确定，但不得只保存在临时提示词或运行时内存中。

### 7.1 顶层字段

- `version`
- `project_id`
- `script_hash`
- `delivery_promise`
- `claims`
- `coverage_policy`
- `metadata`

### 7.2 Claim 字段

每个 claim 至少包含：

- `id`：稳定 ID，例如 `claim-05-03`。
- `section_id`：来源 script section。
- `narration_text`：该事实对应的原始旁白片段。
- `claim_type`：`time`、`location`、`quantity`、`direction`、`causal`、`action`、`warning`、`identity`、`summary` 或 `mood`。
- `start_seconds_target`、`end_seconds_target`：计划播报区间。
- `must_show`：是否必须从画面得到明确支持。
- `precision`：`exact`、`literal`、`supporting` 或 `atmospheric`。
- `representation_mode`：`generated_subject`、`source_media`、`deterministic_graphic`、`overlay_text`、`diagram`、`character_action`、`screen_action` 或 `approved_narration_only`。
- `required_visual_tokens`：必须出现或被等价表达的元素。
- `forbidden_substitutions`：不可用来冒充该事实的抽象替代物。
- `source_ref`：事实来源或用户输入引用。

### 7.3 约束

- `must_show=true` 的 claim 不允许使用 `approved_narration_only`。
- `precision=exact` 的日期、地点、名称和数字不得只由生成图中的可读文字承担。
- 每个 `must_show` claim 必须被至少一个 scene/shot 引用。
- 修改 script 后 `script_hash` 失效，合同必须重新生成和审批。
- style package 可以决定如何表达事实，但不能删除事实。

## 8. scene_plan 与 beats.json 扩展

### 8.1 scene_plan

每个 scene 增加或在 `extensions` 中规范保存：

- `claim_ids`
- `must_show`
- `fact_layer_policy`
- `semantic_evidence_points`
- `semantic_risk`

`semantic_risk` 分为：

- `low`：情绪、材质、环境氛围。
- `medium`：对象、动作、一般机制。
- `high`：日期、地点、人物身份、数值、方向、流程关系和因果链。

### 8.2 Vox beats.json

Vox round-trip 必须保留：

- beat 和 shot 的 `claim_ids`。
- `required_visual_tokens`。
- `fact_overlay`。
- `semantic_risk`。
- `semantic_evidence_points`。

未知字段继续进入 `extensions`，不能在 scene plan 与 beats 转换时丢失。

## 9. Vox 原生执行线设计

### 9.1 保留的原生能力

- Vox arc、beat、shot 和节奏方法。
- 全部 Vox 主题和自定义拼贴主题。
- 生成式关键帧及纸张、报纸、网点、撕边、胶带和印刷质感。
- 图生视频形成的 living collage、纸层视差和素材运动。
- MiMo 分段旁白、音乐和轻量拼接。

### 9.2 两层画面结构

Vox 镜头分为：

1. **生成式视觉层**：主体、环境、纸张材质、视觉隐喻、云雨、道路、人物、装饰符号和纸层运动。
2. **确定性事实层**：准确日期、城市名、地图节点、方向箭头、数值阈值、时间线、来源标签和必须保持稳定的标题。

确定性事实层必须使用当前 style package 的排版、纸片、颜色、纹理和运动语言，避免变成脱离 Vox 风格的通用 UI。

### 9.3 关键帧门

- 先生成批准数量的候选关键帧，不立即批量调用图生视频。
- 对每个候选按 `required_visual_tokens` 检查主体、构图和事实承载空间。
- 高风险事实如果由后期图层表达，关键帧必须预留安全区域和正确空间关系。
- 未通过的候选记录失败原因，不能进入视频 API。
- Hero 项目按 style package 要求进行人工候选审批；Standard 项目仍必须有证据化自动/代理检查。

### 9.4 图生视频门

- 只动画已经通过关键帧门的画面。
- 视频提示主要描述运动和稳定性，不重新描述需要准确保持的文字。
- 每段视频检查开始、中点和结束三帧，防止主体消失、文字重绘、地图变形或事实图层遮挡。
- 关键事实图层默认在图生视频之后通过批准的 composition runtime 添加。

### 9.5 声音和节奏

- TTS 生成后读取真实时长，再锁定 beat 边界和镜头时长。
- 旁白超过目标区间 0.25 秒以上时，优先修改停顿、重写句子或重新生成 TTS。
- 未经记录和审批，不允许使用超过 3% 的整体语速变更解决时长问题。
- 每个 beat 保留可配置的视觉先导时间，但它必须写入合同，不能只存在于临时 FFmpeg 命令。

## 10. OpenMontage 原生执行线设计

### 10.1 通用原则

OpenMontage 所有 pipeline 使用共同 claim 合同，但按各自 style package 和 production family 选择表达方式。

示例：

- `clean-professional`：地图、节点、时间线、图表、数字和排版动效。
- `cinematic`：来源/生成镜头承担情绪与行动，精确信息通过克制的标题、字幕、地图或插卡表达。
- `documentary`：真实素材、档案、标注、来源说明、地图和解释性图形。
- `illustration` / `character`：角色动作、道具、场景和必要的确定性文字。
- `screen-demo`：真实或合成界面操作与旁白步骤绑定。
- `hybrid`：每种素材明确负责哪些 claim，不能用随机 B-roll 填满时间。

### 10.2 Composition 数据来源

- 事实内容必须来自批准的 contract 和 scene plan，不只写在 Composition 源码中。
- atelier 仍可手写独特构图和动效，但必须读取或显式绑定 canonical artifact 中的 claim 数据。
- 生成图片默认负责氛围、主体或支持视觉；准确文字、数字、地理节点和图表由确定性图层或已核验来源素材承担。
- style package 增加事实表达指导，说明时间、地点、数量、方向、机制和警示如何使用该风格的原生视觉语言表达。

### 10.3 不压平风格

共同合同只规定“必须表达什么”和“如何证明已表达”，不规定所有风格使用同一种地图、卡片、字体或运动组件。

## 11. 新增 canonical artifact：semantic_qa_report.json

该报告由资产阶段开始累积，在 compose 后完成，并进入 publish gate。

它与现有 family/style QA、technical QA 并列，不替代这些报告；最终 `qa_report.json` 必须引用 semantic report 的 artifact ID、hash 和状态，Publish Gate 同时检查各报告，避免产生互不相认的两套 QA 结论。

### 11.1 报告内容

- `project_id`
- `contract_hash`
- `asset_checks`
- `timeline_checks`
- `final_checks`
- `claim_results`
- `coverage_metrics`
- `evidence`
- `status`

### 11.2 每个 claim 的结果

- `claim_id`
- `status`：`pass`、`fail` 或 `blocked`
- `scene_ids`
- `actual_narration_start`、`actual_narration_end`
- `evidence_timestamps`
- `evidence_paths`
- `observed_visual`
- `missing_tokens`
- `unexpected_assertions`
- `reviewer_note`

### 11.3 通过标准

- `must_show` claim 覆盖率为 100%。
- `precision=exact` claim 准确率为 100%。
- `unexpected_assertions` 为空。
- 所有 evidence path 真实存在并带 SHA-256。
- 音频跨 scene/beat 边界的非计划偏差不超过 0.25 秒。
- 没有因超过 3% 的未批准变速而获得假性时间对齐。

任何一项不满足时，semantic QA 状态为 `fail` 或 `blocked`，不得被风格高分或 ffprobe 通过覆盖。

## 12. 三道强制质量门

### 12.1 Asset Semantic Gate

发生在高成本批量生成前：

- 检查关键帧/场景预览是否具备事实表达能力。
- 检查安全区和确定性图层位置。
- 检查视觉主体是否与旁白相符。
- 生成候选失败时记录原因，不静默替换 provider 或表达方式。

### 12.2 Edit Sync Gate

发生在最终合成前：

- 使用实际 TTS 时长，而不是估算时长。
- 检查旁白、镜头、字幕、标题和事实图层的进入/退出点。
- 检查遗漏、重叠、跨段和不合理变速。
- 合同发生变化时使旧 edit approval 失效。

### 12.3 Final Semantic Gate

发生在发布前：

- 每个生成视频镜头至少抽取开始、中点、结束三帧。
- 程序化/Remotion 场景按 claim 出现时刻抽取证据帧。
- 不能只抽每十秒一帧代替逐镜头检查。
- semantic QA、family/style QA、technical QA 均通过后才能进入 Publish Gate。

## 13. 失败处理和返工路由

失败必须回到产生问题的最早阶段：

- claim 本身不清楚：回 script。
- claim 没有视觉表达方式：回 narration visual contract / scene plan。
- 关键帧主体或空间关系错误：回 assets，重新生成或调整确定性图层方案。
- 视频模型造成变形或语义丢失：回单个 motion asset，不重跑无关镜头。
- TTS 超时：回旁白文本或 TTS，不强行压缩整段。
- Composition 漏画事实：回 edit/compose 数据绑定。
- 成片出现新错误：只返修受影响 claim 对应的镜头和证据。

禁止通过更换标题、添加无关字幕或用抽象图标遮掩事实缺失。

## 14. 对“白海豚”样片的验证要求

完成共同合同和双线接入后，用现有主题做第一组回归。

### 14.1 Vox 回归

优先复用已经合格的前段资产，只重做或重构受影响的 `5a`、`5b`、`6a`、`6b`：

- 第 5 拍必须明确表达雨区由南向北、向东扩展。
- 郑州、开封、商丘、周口必须以准确、可读、风格一致的节点或标签出现。
- 第 6 拍必须表达全省大部分地区、30℃阈值和三日变化总结。
- 精确事实使用后期 Vox 风格图层，不依赖生成图中的中文文字。

### 14.2 OpenMontage 回归

- 现有 clean-professional 表达不得降级。
- 日期、城市、方向、温度和安全提示必须来自 canonical artifacts。
- Composition 不能成为唯一事实来源。
- 每个 scene 生成 claim 证据帧和 semantic QA 结果。

### 14.3 跨题材回归

天气样片通过后，至少再选择一个非天气主题和一个非 `newsprint-editorial` / `clean-professional` 风格，证明合同不依赖固定地图或天气组件。

## 15. 阶段性落地顺序

### 阶段 1：共同合同与 schema

- 新增 narration visual contract 和 semantic QA report schema。
- 扩展 artifact registry、校验器和 checkpoint 绑定。
- 为 script、scene plan 和 Vox beats 建立稳定 claim 引用。

验收：缺失 claim 引用、旧 script hash、空证据路径和不完整 must-show 覆盖均被拒绝。

### 阶段 2：共同 QA 引擎

- 实现 claim 覆盖计算、证据文件校验、时间偏差检查和失败原因聚合。
- 将 semantic QA 与 family QA、technical QA 并列，禁止互相覆盖。
- Backlot 显示 claim、对应镜头、证据和失败原因。

验收：删除证据帧、遗漏 exact claim 或制造跨段偏差都会让 gate 失败。

### 阶段 3：Vox 原生线接入

- 更新 Vox skill、beat layer、关键帧门、视频门、确定性事实图层和实际 TTS 时长锁定。
- scene plan 与 beats round-trip 保留语义字段。
- 把标题、事实图层和音频时间轴从临时命令固化到 canonical edit/compose 决策。

验收：Vox 保留纸拼贴与图生视频特征，同时精确事实不依赖生成文字；失败镜头不会进入批量视频调用。

### 阶段 4：OpenMontage 全 pipeline 接入

- 先接 `animated-explainer` 和 `vox-collage`，再扩展到其他 pipeline。
- atelier、templated、Remotion、HyperFrames 和 FFmpeg 路径均绑定 claim 合同。
- style package 增加事实表达指导，但不引入全局构图模板。

验收：同一 contract 可由不同风格原生表达，且 claim 结果一致可追溯。

### 阶段 5：回归样片与切换

- 运行白海豚双线回归。
- 运行一个非天气、非现有两种风格的回归。
- 更新操作文档和唯一入口说明。

验收：所有 must-show 和 exact claim 通过；两条成片仍具有明显不同的原生风格；用户不需要直接操作 vox-director。

## 16. 实施计划拆分

本设计后续拆成三个可独立验收的实施计划，避免把多个子系统一次性混改：

1. **共同语义合同与 QA 核心**：schema、artifact 校验、checkpoint、semantic QA 和 Backlot 证据展示。
2. **Vox 原生线接入**：skill、beats round-trip、资产门、确定性事实图层、TTS 时间锁定和 Vox 回归。
3. **OpenMontage 全 pipeline 接入**：先 animated-explainer，再按生产家族扩展，并完成跨风格回归。

每个计划必须使用测试先行、独立提交和阶段性验收。计划 1 完成后，计划 2 与计划 3 才能在同一合同上分别推进。

## 17. 预计修改范围

共同核心预计涉及：

- `schemas/artifacts/`
- `schemas/artifacts/__init__.py`
- `lib/checkpoint.py`
- `lib/family_qa.py`
- 新增独立 semantic QA 模块
- `backlot/` 的 artifact/证据展示
- 对应 contract、integration、QA 测试

Vox 预计涉及：

- `pipeline_defs/vox-collage.yaml`
- `skills/pipelines/vox-collage/`
- `styles/packages/vox-paper-collage/`
- `lib/vox_collage_artifacts.py`
- `vox-director/SKILL.md`、`SKILL.zh.md` 和 `references/`
- Vox 的关键帧、视频、标题和音频合成脚本或 OpenMontage adapter

OpenMontage 其他生产线预计涉及：

- `pipeline_defs/animated-explainer.yaml` 及后续 pipeline manifests
- 各 pipeline 的 script、scene、asset、edit、compose director skills
- style package 的事实表达指导
- atelier/templated composition 的 canonical data binding

准确文件和函数级步骤在用户审阅本文后写入实施计划。

## 18. 最终验收标准

### 18.1 单入口

- 用户只使用 OpenMontage 完成项目生命周期。
- 路由记录实际使用的原生执行线、style package、provider、runtime 和 composition mode。
- 不静默降级或替换已批准生产方法。

### 18.2 双原生质量

- Vox 结果保持生成式纸拼贴、纸层运动和主题差异。
- OpenMontage 各生产家族保持自己的原生视觉与 runtime 优势。
- 共同合同不会把两条线压成同一种信息卡样式。

### 18.3 声画语义

- must-show 覆盖率 100%。
- exact claim 准确率 100%。
- unsupported/unexpected assertions 为 0。
- 每个 claim 有真实证据文件和时间戳。
- 旁白非计划跨段偏差不超过 0.25 秒。

### 18.4 证据和恢复

- contract、scene、asset、edit、render 和 QA hash 可追溯。
- 删除证据或修改上游合同会使旧审批失效。
- 单个失败镜头可恢复和返工，不必重跑整个项目。

### 18.5 回归

- 白海豚 Vox 与 OpenMontage 两条 60 秒成片通过新合同。
- 至少一个非天气、非现有两风格的样片通过。
- 旧的技术、风格、安全和 provider 测试不回退。

## 19. 结论

最优方案不是继续为每条片人工判断“画面大概对不对”，也不是把 Vox 和 OpenMontage 合成一个模板渲染器，而是让 OpenMontage 成为唯一编排入口，在共享的事实、时间和证据合同之下调用两条原生生产线。

这样可以同时获得：Vox 的生成式视觉能力、OpenMontage 的全风格与确定性合成能力，以及可重复、可拦截、可追溯的声画语义质量。
