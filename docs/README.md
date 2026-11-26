# 文档索引

| 文档 | 内容 |
|---|---|
| [../README.md](../README.md) | 项目概览、本地运行、环境变量、开发约定 |
| [ONBOARDING.md](ONBOARDING.md) | 上手 / 交接：30 分钟跑起来、改哪儿、发布与回滚、已知坑、决策记录 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 页面与入口、JS 分层、渲染约定、数据流、取舍 |
| [DATA_PIPELINE.md](DATA_PIPELINE.md) | 成员统计（Raider.IO）与职业天梯（Wowhead）两条管道、统计口径、输出契约、已知问题 |
| [wow-mounts-api.md](wow-mounts-api.md) | 暴雪坐骑 API 原始调研笔记（历史，接口现已需登录） |
| [preview/index.html](preview/index.html) | 2026-10 新旧界面对比截图（成员统计 / 排行榜 / 天梯） |

`archive/` 下为重构前的历史文档，内容已被上述文档覆盖，仅供追溯。
2026-11-26 结项时，已执行完毕的 [REFACTOR_PLAN.md](archive/REFACTOR_PLAN.md) 也移入此处（历史决策记录，不要按它改代码）。

主题速查：

- 想改职业颜色 → `css/variables.css` 的 `--class-*`
- 想改天梯图标 → `js/data/specs.js`（新专精另需在 `tools/wow_terms.py` 的 `SPEC_BY_EN` 补一行）
- 想改天梯排名 → 跑 `tools/fetch_tier_lists.py`（数据文件自动生成，不要手改）
- 想改首页统计 → `tools/build_page_data_rio.py`（先跑 `tools/fetch_guild_roster.py --enrich`）
- 想改接口行为 → `netlify/functions/`
