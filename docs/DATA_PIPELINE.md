# 数据管道说明

## 1. 总览

首页数据现在走 **Raider.IO**（公开接口，可全自动）；英雄榜那条旧管线保留但需要登录，已暂停：

```
Raider.IO ──fetch──▶ data/guildmember.rio.json ──build──▶ data/page_data.json ──fetch──▶ 首页   ← 当前在用
Blizzard 英雄榜 ──crawl──▶ SQLite ──build──▶ data/page_data.json                              ← 需战网登录，暂停
```

- 成员抓取：`tools/fetch_guild_roster.py`（Raider.IO）
- 页面数据生成：`tools/build_page_data_rio.py`
- 旧链路（英雄榜 → SQLite）：`tools/mounts_crawler.py` + `tools/build_page_data.py`
- 校验脚本：`tools/validate.py`
- 输出文件：`data/page_data.json`（**不要手改**）

两份脚本产出的 `page_data.json` 结构一致，但「活跃」「数据完整率」的口径不同，见 §4。

运行环境：Python 3.9+。第三方依赖见 `requirements.txt`。

## 2. 常用命令

```bash
# 当前链路：Raider.IO → 页面数据
python tools/fetch_guild_roster.py --enrich      # 抓成员 + 逐角色补 ilvl / 本季 M+ 分数
python tools/build_page_data_rio.py              # 生成 data/page_data.json
python tools/validate.py                         # 校验产物（结构与合理性断言）
python tools/validate.py --strict                # 数据过期也失败，适合 CI

# 旧链路（需要登录态的英雄榜导出数据库）
python tools/build_page_data.py

# 调整活跃窗口（默认 30 天）
ACTIVE_DAYS=14 python tools/build_page_data_rio.py

# 爬取坐骑数据（需要令牌与网络）
python tools/mounts_crawler.py

# 数据库巡检
python tools/database_query_tool.py
```

## 3. 数据库（旧链路）

默认位置：`data/guild_database.db`（**不入版本库**）。

主表 `guild_characters` 共 24 列：

```
id, name, rank, level, class, race, sex,
last_online_days, mythic_score, faction, realm, guild, spec,
achievement_points, average_item_level, equipped_item_level,
last_login_timestamp, data_source, created_at, updated_at, crawl_timestamp,
realm_slug, mounts_now, mounts_total
```

关键点：

- `last_login_timestamp` 是**毫秒**（13 位）。直接与秒级阈值比较会恒为真，历史 bug 见 §6。
- 一个角色可能有多行（多次抓取），需按 `(name, realm)` 去重。
- `264` 行的 `last_login_timestamp` 为 `NULL`，这些记录不会进入活跃统计。

## 4. 统计口径

### 当前（Raider.IO，`tools/build_page_data_rio.py`）

| 指标 | 定义 | 计算位置 |
|---|---|---|
| `totalMembers` | 按 `(name, realm)` 去重后的角色数（跨服同名算两个人） | `deduplicate` → `calculate_statistics` |
| `activeMembers` | **本季有大秘境记录**（`mythicScore > 0`）**或** Raider.IO 在「数据集最新更新日往前 N 天」内更新过该角色 | `calculate_statistics` |
| `activeWindow.basis` | `rio_activity`；`label` 是前端直接展示的文案，`note` 是口径说明（挂在 label 的 tooltip 上） | 同上 |
| `activeWindow.mplusActive` | 上述活跃里「本季确实有大秘境记录」的人数，单独暴露便于解释 | 同上 |
| `dataCompleteness` | `achievementPoints > 0` 且 `itemLevel > 0` 的占比 | 同上 |

为什么不按「最后登录天数」：Raider.IO 没有这个字段（只有它自己的抓取时间），
英雄榜才有但要登录。所以活跃改成「有本季 M+ 记录 或 近期被 RIO 更新过」，并在页面上用 `label` 写清楚。

### 旧（英雄榜数据库，`tools/build_page_data.py`，暂停）

| 指标 | 定义 |
|---|---|
| `activeMembers` | 登录时间落在「数据集最新登录时间往前 N 天」内的角色数 |
| `activeWindow.basis` | `dataset_latest`（以数据集内最新登录时间为基准，不用墙上时钟） |
| `dataCompleteness` | `achievement_points > 0` 且 `average_item_level > 0` 的占比 |

**为什么旧口径不用系统时间当基准**：数据若长期未更新，按墙上时钟计算会得到「0 人活跃」，把「数据陈旧」误报成「公会没人」。以数据集最新时间为基准，指标始终描述「这批数据内部的活跃度」，同时通过 `dataAsOf` 字段暴露数据真实截至时间。

## 5. 输出结构

`data/page_data.json`：

```jsonc
{
  "lastUpdated": "2026-10-24 02:17:28",  // 生成时间
  "dataAsOf": "2026-10-24",              // 数据截至（名单抓取日）
  "stats": {
    "totalMembers": 724,
    "activeMembers": 319,
    "activeWindow": {
      "days": 30, "since": "2026-09-23", "latest": "2026-10-23",
      "basis": "rio_activity",
      "label": "近 30 天活跃",                    // 前端直接展示
      "note": "本季有大秘境记录，或 Raider.IO 在窗口内更新过该角色",
      "mplusActive": 77                        // 活跃里「本季确实有 M+ 记录」的人数
    },
    "dataCompleteness": { "total": 724, "complete": 703, "incomplete": 21, "percentage": 97.1 }
  },
  "charts": {
    "classDistribution":  [{ "name": "圣骑士", "value": 100 }],
    "factionDistribution":[{ "name": "Horde", "value": 584 }],
    "raceDistribution":   [{ "name": "血精灵", "value": 213 }],
    "realmDistribution":  [{ "name": "阿尔萨斯", "value": 449 }],
    "genderDistribution": [{ "name": "男", "value": 335 }]
  },
  "rankings": {
    "achievementRanking": [{ "rank": 1, "name": "…", "realm": "…", "class": "…",
                            "spec": "…", "achievement_points": 0, "average_item_level": 0,
                            "mythic_score": 0 }],
    "itemLevelRanking":  [],
    "mythicScoreRanking":[]
  },
  "meta": {
    "source": "raider.io", "sourceRows": 724, "uniqueCharacters": 724,
    "duplicatesRemoved": 0, "enriched": 724, "generator": "tools/build_page_data_rio.py"
  }
}
```

`factionDistribution` 的键仍是 `Horde`/`Alliance`（前端按英文键取色，再映射成中文标签）；
其余维度都是中文名。旧链路产的 `page_data.json` 会多一个 `mounts_now` 字段，新链路没有。

下游消费方：`js/modules/GuildStatsLoader.js`（概览）与 `js/components/Chart.js`（图表渲染）。

## 6. 时间戳陷阱（历史 bug 复盘）

旧实现同时存在两个错误，导致日期过滤完全失效：

1. 阈值硬编码为 `1706313600`，注释写「2025-02-27」，实际是 **2024-01-27**（差 397 天）。
2. 数据库存的是毫秒（如 `1754329119000`），与秒级阈值比较恒为真。

结果：`WHERE last_login_timestamp >= ?` 实际只等价于 `IS NOT NULL`。

现在统一由 `tools/timeutil.py` 处理：

```python
to_unix_seconds(1754329119000)  # -> 1754329119
```

## 7. 去重规则

两条链路都按 `(name, realm)` 聚合——**同名但不同服务器是两个人，不合并**。差别在「同一角色多条记录」时怎么取：

- 旧链路（英雄榜）：保留「登录时间更晚 → 更新时间更晚 → 原始顺序靠前」的一条。
- 新链路（Raider.IO）：逐字段取更优值（成就点/装等/M+ 分数取最大、更新时间取最新）。
  RIO 的名单接口与角色接口返回的新旧程度不一致，整条覆盖会丢分。

2025-08 的英雄榜导出：原始 967 行 → 去重后 965，移除 2，264 行没有登录时间。
2026-10 的 RIO 名单：724 条 → 唯一 724（跨服同名 12 组，均在列表里各算一个角色）。

## 8. 校验

`tools/validate.py` 的断言：

- `totalMembers` 在 `(0, 5000]`
- `0 <= activeMembers <= totalMembers`
- `dataCompleteness.percentage` ∈ [0, 100]
- 5 组图表数据非空且 `value >= 0`
- 3 张排行榜非空、无重复 `(name, realm)`、`rank` 连续
- `meta.uniqueCharacters == totalMembers`，`duplicatesRemoved` 自洽
- `dataAsOf` 超过 7 天则告警（`--strict` 时失败）

## 9. 已知数据问题

| 问题 | 现状 | 影响 | 建议 |
|---|---|---|---|
| 数据停滞 | **已解决（2026-10-24）**：改走 Raider.IO，由 `.github/workflows/guild-stats-refresh.yml` 每天自动刷新 | — | 关注 RIO 覆盖率变化 |
| 坐骑数全部相同 | 新链路已不产出坐骑字段（`mounts_now`）；旧库里的 369 是令牌复用所致 | 坐骑维度下线 | 见 `docs/archive/API_ISSUE_ANALYSIS.md` |
| 爬虫令牌未外置 | **已解决（2026-10-23）**：令牌移出仓库，改读 `WOW_ARMORY_TOKEN`；历史提交另行清理 | — | 轮换旧令牌即可 |
| 配置文件重复 | `data/config.json` 与 `data/Database/config.json` 已停止跟踪；统一用 `tools/config.json`（gitignore）+ `tools/config.example.json` | 已收敛 | — |
| 英雄榜需登录 | 角色页/公会页无登录态只发 OAuth 请求、不返回数据；`api/do` 要 `xcxtoken` | 等级/最后在线/坐骑拿不到 | 需要时用登录态浏览器半自动补，见 §12 |
| RIO 覆盖率不完整 | 724 人 vs 旧英雄榜导出 950 个唯一名字，按名字重合 556 | 页面成员数可能少于真实在会人数 | 定期看 `--compare` 的覆盖数字 |

## 10. 待办

1. ~~**令牌外置**~~ ✅ 2026-10-23：`config.py` 不再内置常量，文档中的明文令牌已替换为占位符；
   仍待做的是**轮换旧令牌**（去 wow.blizzard.cn 重新登录取新令牌）。
2. ~~**配置合一**~~ ✅ 2026-10-23：候选顺序改为 `tools/config.json` → 旧位置回退；仓库只保留 `tools/config.example.json`。
3. ~~**数据出库**~~ ✅ 2026-10-23：`data/guild_database.db`、`data/guildmember.csv`、两份 `config.json` 已 `git rm --cached`（本地文件保留）。
4. ~~**自动化**~~ ✅ 2026-10-24：成员统计（Raider.IO）与职业天梯（Wowhead）各有每日/每周定时任务，有变化才提交。
5. **待定**：RIO 覆盖率与真实在会人数的差额；要补齐只能上登录态英雄榜（§12 末）。

## 11. 职业天梯（独立管道）

天梯数据不走上面的成员数据管道，它是单独一条链路：

```
Wowhead guide 页 ──fetch──▶ tools/fetch_tier_lists.py ──▶ js/data/*-tier-list.js ──import──▶ pages/all-rankings.html
```

- 抓取/生成脚本：`tools/fetch_tier_lists.py`
- 产物：`js/data/` 下 6 份 `*-tier-list.js`（**不要手改**，重跑脚本会覆盖）
- 依赖：`js/data/specs.js`（专精 id ↔ 中文名 ↔ 图标），脚本启动时会校验两边一致

### 为什么需要代理或阅读器

`wowhead.com` 对部分地区出口直接返回 403（CloudFront 地区拦截；实测本机直连、香港出口均为 403；
2026-11-09 的定时任务里 GitHub Runner 直连同样 403，`auto` 全程退回阅读器）。
脚本取页方式三选一：

| 方式 | 适用场景 | 说明 |
|---|---|---|
| `auto`（默认） | CI / 海外出口 | 先直连，非 200 自动退回阅读器 |
| `direct` | 美国出口 | 只直连，失败即报错 |
| `reader` | 本机 | 走 `r.jina.ai` 取正文（本机需能访问 r.jina.ai） |

```bash
# 本机：系统代理 + 阅读器（--proxy 省略时依次取 HTTPS_PROXY、Windows 系统代理）
python tools/fetch_tier_lists.py --reader --proxy http://127.0.0.1:15236

# 只用 .cache/tier-lists/ 里的原文重跑解析（改解析逻辑时不必重新抓）
python tools/fetch_tier_lists.py --offline

# 比对模式：不写文件，有差异退出码 1
python tools/fetch_tier_lists.py --check
```

退出码：`0` 一致；`1` 有差异（`--check`）；`2` `specs.js` 缺专精；`3` 抓取或解析失败。

取页和解析各重试（`PARSE_ATTEMPTS = 3`，间隔 5 秒），全轮失败才返回 3。
阅读器取不到页面时也回 HTTP 200：可能是正文前带一行 `Warning: … not yet fully loaded` 的空壳页，
也可能是 404 页。这类情况按取页失败处理并重试，而不是报“页面结构变了”（判据见
`validate_reader_payload`）。注意 wowhead 每个页面正文里都带隐藏的“举报广告”弹窗，
正常页面也有这段文字，不能按它判死。
失败时抓到的原文存成 `.cache/tier-lists/<key>.failed.md`，CI 作业失败时上传为 artifact
（`tier-list-pages`），用来区分“页面改版”和“根本没抓到正文”。

### 解析口径

- 优先取正文里的编号排名 `1.   Arms Warrior (A Tier)`；没有编号列表时退回
  `### A-Tier Specs …` + `#### 专精名` 的分节结构。两种方式都只在页面的
  “Rankings and Explanations” 之后取，避免把 Disclaimer 里的举例当成数据。
- 层级支持 `S / A+ / A / B / C / D / F`。大秘境 DPS 有 `A+` 档，`TierList.js`
  会把 `A+` 映射成 `tier-a-plus` 类名（CSS 类名里不能出现 `+`）。
- 英文专精名 → id 的映射写在脚本的 `SPEC_BY_EN`。页面出现未登记的专精时**脚本直接失败**，
  不会静默少一格。新增专精要同时改 `specs.js` 与 `SPEC_BY_EN`，图标放 `img/specs/`
  （CSP 的 `img-src` 只放行白名单域名，自托管最省事）。
- `lastUpdated` 取页面自带的“已更新：YYYY/MM/DD”；页面没写时用抓取当天。
  `fetchedAt` 恒为抓取当天（北京时间）。

### 自动刷新

`.github/workflows/tier-list-refresh.yml`：每周一 UTC 02:00（北京时间 10:00）执行一次。
一次运行只抓一遍：脚本先抓全 6 个页面、全部解析成功才写文件（两段式），一个页面抓坏就整批不写，
作业失败且不提交（宁可报警，不写坏数据）。写盘后再跑 `node --test`（兜住“新专精没登记”），
最后有差异才提交到 `main`。

### 注意

- `js/data/*-tier-list.js` 已加入 `.prettierignore`：格式由生成器决定，
  一旦被 prettier 重排，`--check` 就会永远报差异。

## 12. 公会成员（Raider.IO）

英雄榜这条路现在要登录：实测无登录态访问 `wow.blizzard.cn/character/#/…` 与 `/guild/#/…`
只会发出一个 OAuth `authorize` 请求、不加载任何成员数据；侧信道接口
`webapi.blizzard.cn/wow-armory-server/api/do` 需要 `xcxtoken`（账号令牌，旧 cookie 的过期时间是签发后约 7 天）。
这也是「数据停滞在 2025-08」的直接原因。

成员名单改走 Raider.IO 公开 API（无需鉴权，覆盖国服）：

```bash
python tools/fetch_guild_roster.py                 # 抓名单 → data/guildmember.rio.json
python tools/fetch_guild_roster.py --compare       # 与旧 CSV 比覆盖率
python tools/fetch_guild_roster.py --enrich --limit 50   # 逐角色补装备等级 + 本季大秘境分数
```

| 项 | 说明 |
|---|---|
| 产物 | `data/guildmember.rio.json`（已 gitignore：成员数据不入库，与 `guildmember.csv` 同规则） |
| 能拿到 | 名字、服务器（含 slug）、会阶、职业/专精、种族、性别、阵营、成就点数；`--enrich` 再加装备等级与本季 M+ 分数 |
| 拿不到 | **角色等级、最后在线天数、坐骑数量**——只有登录英雄榜才有 |
| 速率 | `--enrich` 是每角色一次请求；实测 724 人按 0.25s 间隔约 **20 分钟**（RIO 会限速，失败会退避重试），`--limit` 可先小批量验证 |
| 覆盖率 | 2026-10-24 实测 724 人；与旧 CSV（965 行 / 950 个名字）按名字重合 556，只在旧 CSV 394，只在 RIO 156 |

覆盖率这组数字的含义：**RIO 只收录它爬到过的角色**，离会的、从没打过 M+ 的小号都可能不在里面；
反过来「只在 RIO」的 156 个多半是旧导出之后的新人。要判断某批名字到底是「离会」还是「RIO 没爬到」，
只能拿登录态英雄榜对照——这也是目前唯一没自动化的部分。

### 生成页面数据

```bash
python tools/fetch_guild_roster.py --enrich      # 名单 + ilvl + 本季 M+ 分数
python tools/build_page_data_rio.py              # → data/page_data.json
python tools/validate.py                         # 结构断言
```

2026-10-24 首次实跑：724 名成员、319 人在「近 30 天」口径内活跃（其中 77 人本季有 M+ 记录）、
数据完整率 97.1%（21 个老角色 RIO 没有装等）。中文名映射在 `tools/wow_terms.py`：
职业 13 条、专精 40 条、种族 26 条、服务器 69 条（2026-10-24 补齐，当前 61 个服务器全部有中文名）。
**查不到的新服务器回退英文显示名**，不猜中文名——需要时补 `REALM_SLUG_TO_CN` 一行即可。

### 自动刷新

`.github/workflows/guild-stats-refresh.yml`：每天北京时间 11:00 抓一次 → 生成 → `validate.py` → `node --test`，
有变化才提交 `data/page_data.json`。抓取失败则作业失败、不提交。

### 为什么不直接改旧脚本

`tools/build_page_data.py` 读的是英雄榜导出的 SQLite，字段（等级、最后在线、坐骑）在 RIO 里没有，
硬改成 RIO 会静默把「活跃」算成 0。所以新脚本单独一份、口径显式写进 `stats.activeWindow`，
旧脚本保留给将来有登录态时使用。

