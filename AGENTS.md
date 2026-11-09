# yiqi（一起公会站点）—— 改它时容易踩的

> 出处 / 是什么 / 状态 / 处置见 `README.md`；架构与数据口径见 `docs/ARCHITECTURE.md`、
> `docs/DATA_PIPELINE.md`。本文件只写**硬约束、自检命令、验证边界**，不重复文档内容。

## 硬约束

1. **生成物不许手改**：`data/page_data.json`（`tools/build_page_data_rio.py` 生成）与
   `js/data/*-tier-list.js`（`tools/fetch_tier_lists.py` 生成）。改口径改脚本再重跑；
   手改会在下次定时任务里被覆盖，还会让 `--check` 与 CI 结果对不上。
2. **数据刷新由 Actions 提交**：`guild-stats-refresh.yml`（每日）与 `tier-list-refresh.yml`（每周），
   提交者是 `github-actions[bot]`。本地动过 `data/` 或 `js/data/` 之后先 `git pull --ff-only`
   再干活 —— 2026-11-10 实测本地落后 12 个数据提交，直接在旧数据上改必然冲突。
3. **`js/data/*-tier-list.js` 必须留在 `.prettierignore` 里**：格式由生成器决定，
   一旦被 prettier 重排，`--check` 会永远报差异。
4. **新增专精要同时改三处**：`js/data/specs.js`（id + 图标）、`tools/wow_terms.py` 的 `SPEC_BY_EN`
   （英文名 → id）、图标文件放 `img/specs/`。天梯里出现未登记专精时脚本**直接失败**
   （宁可报警，不静默少一格）；只有新增档位（如 `A+`）才需要动 `js/components/TierList.js#TIER_ORDER`。
5. **天梯抓取的实际路径是阅读器，不是直连**：wowhead 对数据中心出口 403（本机、香港、
   2026-11-09 的 GitHub runner 实测都 403），`auto` 会逐个退回 `r.jina.ai`。
   阅读器取不到页面时**也回 HTTP 200**：正文前带一行 `Warning: … not yet fully loaded` 的空壳页、
   或 404 页。所以别把它"简化"成只查 `Markdown Content:`；正文里的"举报广告"弹窗是正常页面自带的，
   不能按它判死；取页失败要重试（判据见 `validate_reader_payload` / `fetch_and_parse`，
   来历是 2026-11-09 那次整周天梯没刷新的事故）。
6. **`.cache/tier-lists/` 是离线重跑缓存，别删**：改解析逻辑用 `--offline` 复跑，不联网；
   旁边的 `*.failed.md` 是最近一次失败抓到的原文，CI 作业失败时会作为 artifact 上传。
7. **CSP 白名单在 `netlify.toml`**：新增外部图片 / 脚本 / 字体域名要同时改对应 `*-src`，
   否则线上静默被拦（本地裸开 HTML 没有响应头，看不出来）。
8. **JS 测试零依赖，Python 测试要 requests**：`node --test` 只用标准库，不需要 `npm install`；
   Python 测试会 import 抓取脚本，先 `pip install -r requirements.txt`。
9. **别把 `docs/archive/` 当现状**：旧英雄榜管线（`tools/build_page_data.py`）留作对照，
   现役是 RIO 管线（`build_page_data_rio.py`）；归档文档里提到的 `js/modules/DPSTierList.js`
   早已删除（见 `docs/REFACTOR_PLAN.md` P1-1），别按归档去把它补回来。

## 自检（改完必须能复跑）

```bash
pip install -r requirements.txt                       # 只有 requests
npm run check                                         # = test:js + test:py + data:validate
npm run lint
python tools/fetch_tier_lists.py --offline --check    # 验解析、不联网；退出码 1 = 数据有差异
```

`.github/workflows/ci.yml` 在 push / PR 时跑的就是上面这套。`actions/*` 统一钉在
**Node 24 兼容的最低主版本**（`checkout@v5` / `setup-node@v5` / `setup-python@v6` /
`upload-artifact@v6`）—— GitHub 2025-09 公告弃用 Node 20 后的动作都被自动抬到 Node 24，
钉在最低兼容主版本就不会再刷弃用提示；再升主版本先读它的 breaking changes
（v6 起 checkout 改过凭据持久化方式，v7 起是 ESM 重写）。

## 验证边界

- 天梯解析测试**不联网**（网络那半由定时任务兜）；阅读器产物格式、Wowhead 改版这类事只有
  真实网络能验。抓取失败时先看 CI 的 `tier-list-pages` artifact，不要凭"页面结构可能变了"下结论。
- `tools/validate.py` 只管 `data/page_data.json` 的完整率与新鲜度，**不校验天梯文件**。
- 页面视觉 / 布局改动没有自动化测试，要人工开 `pages/*.html` 看；涉及 CSP 的改动必须在
  **带响应头**的环境里验，否则"本地看着正常"毫无意义。
- 发布：push `main` 后由 Netlify 自动构建（`netlify.toml` 声明发布目录、函数目录、CSP、缓存）。
  本地没有 Netlify 构建的等价物，构建失败只能看 Netlify 那边。
