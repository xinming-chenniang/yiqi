# 一起公会网站 · 重构方案 v1

> **已执行完毕，2026-11-26 结项时移入 `docs/archive/`。** 本文件是重构决策的历史记录，
> **不再反映当前代码**；要改代码请按 `docs/ARCHITECTURE.md` / `docs/DATA_PIPELINE.md` / `AGENTS.md`。
> P0 的回归保护仍在 `tests/` 里（密钥外置、成员数据不入库、统计口径与时间过滤均有测试覆盖）。

| 项 | 内容 |
|---|---|
| 状态 | 已执行完毕（2026-11-26 存档） |
| 范围 | 静态站点（HTML/CSS/JS）+ Netlify Functions + Python 数据管道 |
| 基线采集 | 2026-10-18，仓库 `repos/yiqi`，源码 8,583 行 / 资源 21.3 MB / 数据库 967 行 |
| 核心结论 | **做定向重构，不做推倒重写** |

---

## 0. 决策摘要

**不重写的理由**：体量小（JS 3,499 行、CSS 1,955 行、HTML 905 行、Python 2,224 行），无框架、无构建链，整体架构（静态页 + Serverless + 离线取数生成 JSON）与需求匹配。重写的收益主要是"技术观感"，成本约 2–3 周，且会重造当前已经踩过的坑。

**必须重构的理由**：存在 6 个会产生真实后果的缺陷（密钥泄露、越权上传、统计口径错误、时间过滤完全失效、成员数据入库、灯箱崩溃），以及 5 类复制粘贴式重复（341 行死代码、颜色表 5 份、CSS 注入 6 份、图表渲染 5 段、图标 32 处重复引用）。

**执行原则**：

1. **不改 URL、不改目录对外结构**（`index.html` / `pages/` / `css/` / `img/` 全部保持原位），把回归风险压到最低。
2. 只重组内部：`js/` 内部分层、Python 归入 `tools/`、样式回到 `css/`。
3. 每一阶段可独立上线、可独立回滚。
4. P0 未清完之前，不启动 P1 的批量改动。

---

## 1. 现状基线（重构前后对比用）

### 1.1 代码量

| 类型 | 文件数 | 行数 | 主要问题 |
|---|---:|---:|---|
| JS | 26 | 3,499 | 341 行死代码、5 段近似复制、30 条 console.log |
| CSS | 10 | 1,955 | 关键样式（tier list / ranking-nav）不在 CSS 里 |
| HTML | 9 | 905 | 2 个测试页、footer 重复、统计卡片不全 |
| Python | 13 | 2,224 | 2 个空文件、3 个测试脚本、路径约定不一致 |
| **合计** | **58** | **8,583** | |

### 1.2 资源与数据

| 项 | 现状 | 备注 |
|---|---|---|
| 图片资源 | 21.32 MB | 最大两个 GIF 各 3.8 MB；`plan*.png` 5 张各 ~1.4 MB |
| `data/guild_database.db` | 972 KB，967 行 | 含姓名/服务器/阵营，已提交进仓库 |
| `data/guildmember.csv` | 91.9 KB | 同上 |
| `data/page_data.json` | 22.5 KB，703 人 | 与 DB 中非 NULL 记录数一致 |
| 重复图片文件 | 0 | 按 MD5 比对无重复 |

### 1.3 工程化现状

| 项 | 状态 |
|---|---|
| 根 README | 不存在 |
| `netlify.toml` | 不存在（依赖默认 `netlify/functions`） |
| Lint / Format | 无 |
| 测试 | 无 |
| CI | 无（`.github/` 不存在） |
| `package.json` scripts | 无（仅 4 个依赖） |
| `node_modules` | 未安装 |

### 1.4 数据库实测（用于验证 P0-3 / P0-4）

```
总行数                         : 967
last_login_timestamp 非 NULL   : 703
last_login_timestamp 为 NULL   : 264
achievement_points > 0        : 703   ← 当前 activeMembers 取的就是这个
last_login_timestamp 范围      : 1731227374000 ~ 1754329119000（13 位，毫秒）
重名记录（name 重复）          : 12 组
spec 为空的行                  : 264
```

**数据新鲜度**：`data/page_data.json` 的 `lastUpdated` 为 `2025-08-06 22:32:58`，DB 中最新登录时间为 `2025-08-04`（`1754329119000`）。相对当前时间（2026-10）已停滞约 14 个月——这会影响 P0-3 的"活跃"定义，也意味着上线前应重跑一次数据管道。

---

## 2. 问题清单

严重度定义：**P0** = 已产生或即将产生实际损失；**P1** = 显著增加维护成本、易引发回归；**P2** = 工程卫生与长期可维护性。

### 2.1 P0（Phase 0 必须全部关闭）

#### P0-1 访问令牌硬编码进仓库

- **证据**：`data/config.json:33`、`data/Database/config.py:53`、`data/Database/config.py:62`、`data/Database/quick_test.py:11,13`、`docs/wow-mounts-api.md:77,83,116,145,338`
- **现状**：两个 32 位十六进制令牌共出现 11 处；`.gitignore` 只忽略 `.env`，未覆盖 `data/config.json`。
- **影响**：仓库若公开或曾被 fork，令牌等同泄露；令牌轮换前任何调用方都能冒用。
- **方案**：
  1. `config.py` 删除内置常量，改为环境变量优先：`BLIZZARD_API_TOKEN`（默认）、`BLIZZARD_API_TOKEN_<REALM>`（服务器级）。
  2. 两份重复配置（`data/config.json` 与 `data/Database/config.json`）**合并为一份**，暂落在 `data/Database/config.json`（Python 以 cwd 读取），另提交 `config.example.json`。Phase 1 迁移到 `tools/` 后对应为 `tools/config.json` + `tools/config.example.json`。
  3. `quick_test.py` 改为读 env，或直接删除（它是一次性排查脚本，见 P1-7）。
  4. 文档中令牌替换为 `REDACTED`。
  5. 令牌轮换由项目负责人在暴雪侧完成（见 §6）。
- **验收**：
  - `rg -n "[a-f0-9]{32}" --glob '!*.db' --glob '!*.csv' --glob '!.git/**'` 仅命中 `REDACTED` 或示例占位符。
  - 删除 env 后运行管道，报错信息明确提示"未配置令牌"，而不是静默使用默认值。
  - `data/Database/config.json` 已被 `.gitignore` 覆盖。

#### P0-2 上传接口无鉴权 + 描述丢失 + 画廊被截断

- **证据**：`netlify/functions/handle-upload.js:12`（handler 无任何身份校验）、`netlify/functions/get-images.js:11-14`（`api.resources` 未传 `max_results`）、`get-images.js:18`（描述由文件名反推）、`pages/gallery.html:33`（表单有 `description` 字段，但服务端从未持久化）
- **影响**：任何访问者都可向公会的 Cloudinary 账号上传文件（费用与内容风险）；用户填写的描述永久丢失；`api.resources` 默认只返回 10 条，画廊超过 10 张后只显示前 10 张。
- **方案**：
  1. 引入 `UPLOAD_TOKEN` 环境变量；前端在提交时附带口令，服务端用 `crypto.timingSafeEqual` 做常量时间比较，失败返回 401。**鉴权必须在解析 multipart 之前执行**，否则空 body 会先抛解析异常，401 永远走不到。
  2. 上传时写入 Cloudinary context：`context: "description=" + 描述`，`get-images` 读取 `context.custom.description`。
  3. `get-images` 显式 `max_results: 500`（必要时用 `next_cursor` 分页）。
  4. 补 `allowed_formats` 或沿用现有 contentType 白名单；错误信息不再回传 `error.stack`。
- **验收**：
  - 不带口令 `curl -X POST .../handle-upload` 返回 401。
  - 带口令上传后，刷新页面描述仍在。
  - 上传 12 张后画廊显示 12 张。
  - 上传 11 MB 文件返回 400/413 且无服务端堆栈泄露。

#### P0-3 "活跃玩家"口径错误

- **证据**：`data/Database/generate_page_data.py:71-77`（`complete = achievement_points > 0`，随后 `"activeMembers": complete`）、`index.html:31`（写死文案"11.1活跃玩家"）
- **实测**：`totalMembers = 703`、`activeMembers = 703`，两者恒等，指标失去意义。
- **影响**：首页核心数字是错的；"11.1"写死在 HTML 里，每次版本更新都要改代码。
- **方案**：
  1. 定义三个互相独立的指标：`totalMembers`（去重后角色数）、`activeMembers`（近 N 天有登录，N 写入配置 `crawler.active_days`，默认 30）、`dataCompleteness`（关键字段完整率）。
  2. 生成前按 `(name, realm)` 去重（当前有 12 组重名，会虚增总数与排名）。
  3. HTML 增加 `totalMembers` 卡片，文案改为"近 30 天活跃"，版本号从文案中移除。
  4. **"活跃"的时间基准取数据集内最新时间戳，而不是当前系统时间。** 当前 `page_data.json` 的 `lastUpdated` 是 2025-08-06，DB 中最新登录是 2025-08-04；若按墙上时钟计算，2026 年打开页面会显示"0 人活跃"。同时把真实的"数据更新时间"显示在页面上，避免数据陈旧被误读为"公会没人了"。
- **验收**：
  - 页面上"总成员"与"近 30 天活跃"是两个独立数字，且都能用数据解释。
  - `activeMembers <= totalMembers` 恒成立，并作为生成脚本的断言。
  - 篡改数据库中某角色的登录时间到窗口之外，重新生成后 `activeMembers` 相应变化。
  - 页面明确显示数据时间戳。

#### P0-4 时间过滤完全失效（单位错误 + 硬编码错误叠加）

- **证据**：`data/Database/generate_page_data.py:31`（`cutoff_timestamp = 1706313600`，注释写"2025-02-27"，实际为 **2024-01-27，差 397 天**）、`:37`（`WHERE last_login_timestamp >= ?`）
- **关键发现**：数据库中 `last_login_timestamp` 是**毫秒**（13 位，如 `1754329119000`），而阈值是**秒**。毫秒值恒大于秒值 → 过滤条件恒为真，该过滤实际只等价于 `IS NOT NULL`。
- **影响**：注释、常量、单位三处不一致；任何"只统计最近登录"的意图从未生效。
- **方案**：
  1. 新增 `timeutil.py`（Phase 1 随 1.8 迁入 `tools/`）：`to_unix_seconds(v)`（`v > 1e11` 视为毫秒并除以 1000）、`parse_date("2025-02-27")`。
  2. 截止日期从硬编码改为配置项 `crawler.active_since`（默认 `null` 表示不按日期过滤，只用 `active_days` 窗口）。
  3. 生成前打印实际生效的过滤条件与命中行数，便于核对。
  4. 断言：`0 < len(characters) <= total_rows`。
- **验收**：
  - 单元测试：`to_unix_seconds(1754329119000) == 1754329119`。
  - 生成日志中出现 `filter: last_login within 30 days, matched 703/967`。
  - 代码中不再出现裸数字时间戳。

#### P0-5 成员数据已提交进仓库

- **证据**：`data/guild_database.db`（967 行，972 KB）、`data/guildmember.csv`（91.9 KB）。已通过 `.git/index` 条目核实：`data/guild_database.db`、`data/guildmember.csv`、`data/config.json`、`data/Database/config.json` **均处于被跟踪状态**（HEAD 指向 `refs/heads/main`）。
- **影响**：成员姓名、服务器、阵营、公会内部活动记录随仓库分发。
- **方案**：
  1. `.gitignore` 增加 `data/guild_database.db`、`data/guildmember.csv`、`data/config.json`、`data/Database/config.json`、`tools/config.json`、`logs/`。
  2. 用 `git rm --cached` 停止跟踪（**保留本地文件**，不要直接删）。
  3. 若仓库曾公开：用 `git filter-repo` 清理历史并强制推送（由负责人执行，见 §6）。
  4. `data/page_data.json` 保留（前端运行时 fetch，且不含角色姓名以外的敏感字段；如仍担心，改为 CI 构建产物）。
- **验收**：
  - `git ls-files data/` 只列出 `page_data.json`。
  - 全新克隆后 `python tools/build_page_data.py` 给出明确错误："未找到数据库，请先运行爬虫"。

#### P0-6 图片灯箱索引错乱（上传后点旧图崩溃）

- **证据**：`js/modules/ImageModal.js:102-109`（`registerImages` 每次都 `this.images = ...` 整体重置，但点击回调闭包里的 index 是注册时的旧索引）、`js/modules/ImageUploader.js:94-96`（上传后只注册新图）
- **影响**：在画廊上传一张图后，点击任何旧图会以旧索引访问只有 1 个元素的新数组 → `undefined.src` 抛异常，灯箱失灵。
- **方案**：改为事件委托 + 动态索引，注册与索引解耦：

```js
registerImages(images) {
  const list = Array.from(images).filter(img => img.tagName === 'IMG');
  list.forEach(img => {
    if (img.dataset.modalBound) return;      // 防重复绑定
    img.dataset.modalBound = '1';
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => {
      // 每次点击时从 DOM 重新收集，索引永远与当前一致
      this.images = Array.from(document.querySelectorAll('img.zoomable'));
      this.openModal(this.images.indexOf(img));
    });
  });
}
```

- **验收**：
  - 画廊 5 张图 → 上传第 6 张 → 点击第 1 张，显示的是第 1 张（不是第 6 张）。
  - 连续上传 3 张，控制台无异常。
  - 不重复绑定（点击一次只打开一次）。

### 2.2 P1（Phase 1 关闭）

| ID | 问题 | 证据 | 方案 | 验收 |
|---|---|---|---|---|
| P1-1 | `DPSTierList.js` 是 `TierList.js` 的复制品（341 行 vs 273 行），且**从未被实例化** | `js/main.js:67-68` 检测的 `dps-tier-list-container` 在全站 HTML 中不存在 | 删除 `js/modules/DPSTierList.js`，删除 `main.js` 对应分支与 import | `rg -n "DPSTierList" .` 无结果；`all-rankings.html` 6 个排行榜正常渲染 |
| P1-2 | 职业颜色表硬编码 5 份 | `js/data/wow-classes.js:139`、`js/modules/TierList.js:88`、`js/modules/DPSTierList.js:93`、`js/modules/GuildStatsLoader.js:115`、`css/variables.css:17-30` | CSS 变量为唯一权威；`wow-classes.js` 提供 `resolveClassColor()` 读 CSS 变量并缓存，其余模块统一调用 | `rg -n "#C69B6D" .` 仅命中 `variables.css`；改 CSS 变量后页面颜色随之变化 |
| P1-3 | 关键样式由 JS 注入 `<head>` | `js/modules/TierList.js:100`、`js/modules/DPSTierList.js:113`、`js/components/ranking-nav.js:87` | 新建 `css/tier-list.css`、`css/ranking-nav.css`，由 `css/main.css` `@import` | `rg -n "createElement\('style'\)" js/` 无结果；`all-rankings.html` 创建 6 个 TierList 后 `document.head.querySelectorAll('style').length === 0` |
| P1-4 | 图表渲染三份条形图 + 两份饼图近乎逐行复制 | `js/modules/GuildStatsLoader.js:87-395`（`renderClassChart` / `renderRaceChart` / `renderRealmChart` / `renderFactionChart` / `renderGenderChart`） | 抽到 `js/components/Chart.js`：`renderBarChart(container, items, opts)`、`renderPieChart(container, items, opts)` | `rg -n "conic-gradient" js/` 仅 1 处；5 个图表数据不变、渲染结果像素级一致 |
| P1-5 | 30 条 `console.log` 留在生产 | `js/modules/GuildStatsLoader.js`（30 条） | 删除调试日志；确需排障时用 `CONFIG.debug` 开关包一层 | `rg -n "console\.log" js/` 无结果 |
| P1-6 | 6 个 tier 数据文件共 70 处专精引用，实际只有 39 个唯一专精（31 处重复），且其中 1 个专精的图标在不同文件里不一致 | `js/data/*tier-list.js` | 新建 `js/data/specs.js` 作为专精注册表，tier 文件只写 id 列表 | tier 文件中不再出现 `specIcon:`；图标 URL 总数 = 39 |
| P1-7 | 死代码与测试残留 | `js/components/ClassIcon.js`（仅被一个未使用的 import 引用）、`data/Database/delete_tables.py`（空）、`data/Database/update_valley_kings_data.py`（空）、`pages/test-class-colors.html`、`pages/test-icons.html`、`data/Database/quick_test.py` | 直接删除。注意当前 `publish = "."`，**仓库内任何文件都会被发布**——下划线开头的目录并不会被 Netlify 跳过（`/_next/` 即为反例），所以"移到 `_dev/`"这种方案无效。确需保留时，用 `netlify.toml` 的 `force = true` + `status = 404` 规则屏蔽 | 上述路径不存在；`/pages/test-icons.html` 返回 404 |
| P1-8 | Python 侧路径约定不一致，且全新克隆必崩 | `database_manager.py:8`（`../guild_database.db`）、`generate_page_data.py:15`（`data/guild_database.db`）、`config.json:23`（`guild_database.db`）、`database_manager.py:20`（直接 `FileHandler('logs/...')`，但 `logs/` 不在仓库中） | 统一以**仓库根为 cwd**，路径集中在 `tools/paths.py`；`setup_logging` 内 `os.makedirs` | 全新克隆执行 `python tools/build_page_data.py` 不抛 `FileNotFoundError` |
| P1-9 | footer 重复 | `pages/gallery.html:47`、`pages/class-colors.html:61` 已有静态 `<footer>`，`js/components/footer.js:18` 又追加一个 | 删除 HTML 里的静态 footer，或 `loadFooter()` 检测已存在则填充 | 任一页面 `document.querySelectorAll('footer').length === 1` |
| P1-10 | 粒子动画在每个页面无条件启动，O(n²) 连线 | `js/main.js:42`（150 粒子 → 每帧约 11,175 次距离计算） | 仅首页启用；`prefers-reduced-motion` 时禁用；数据页跳过 | 打开 `all-rankings.html` 无 canvas 元素；系统开启"减少动态效果"时首页也无动画 |

### 2.3 P2（Phase 2 关闭）

| ID | 问题 | 方案 |
|---|---|---|
| P2-1 | 无 `netlify.toml` | 显式声明 functions 目录、Node 版本、构建命令、安全响应头（CSP、`X-Content-Type-Options`、`Referrer-Policy`）与静态资源缓存策略 |
| P2-2 | 无 lint / format | ESLint flat config + Prettier；`package.json` 增加 `lint` / `format` / `format:check` |
| P2-3 | 无根 README | 一页说明：项目是什么、如何本地起服务、如何跑数据管道、环境变量清单 |
| P2-4 | 数据管道无校验 | `tools/validate.py`：断言行数 > 0、去重后无重名、`active <= total`、关键字段非空率、时间戳量级合理；失败退出码非 0 |
| P2-5 | 文档漂移（10 份 md 散落 5 个目录，且与实际代码不符） | 收敛为 3 份：`README.md`、`docs/ARCHITECTURE.md`、`docs/DATA_PIPELINE.md`；其余归档或删除 |
| P2-6 | 文档中的调用方式已失效 | `js/README.md:91` 写 `new window.ImageModal()`，实际是 `window.GuildApp.ImageModal`；随 P2-5 一并修正 |
| P2-7 | 图片 21.3 MB 未优化 | GIF 转 WebM/MP4（或至少压缩），`plan*.png` 转 WebP；目标总量 < 5 MB |
| P2-8 | `_redirects` 语义隐晦 | 当前 `/*.html → /pages/:splat.html 200` 与 `/index.html → /index.html 200` 叠加，实际依赖 Netlify「已存在静态文件优先于 200 rewrite」的默认行为才不冲突；建议改为显式规则并加注释，或直接删除第二条 |

---

## 3. 目标架构

保持对外结构不变，只重组内部：

```
yiqi/
├── README.md                     # 新增
├── netlify.toml                  # 新增
├── package.json                  # 增加 scripts
├── .env.example                  # 新增：环境变量清单
├── .gitignore                    # 补数据与配置
├── index.html                    # 原样
├── pages/                        # 原样（测试页删除，见 P1-7）
├── img/                          # 原样（Phase 2 优化体积）
├── css/
│   ├── main.css                  # 增加两个 @import
│   ├── tier-list.css             # 新增：从 TierList.js 迁出
│   └── ranking-nav.css           # 新增：从 ranking-nav.js 迁出
├── js/
│   ├── main.js                   # 页面引导，按页条件初始化
│   ├── config.js
│   ├── core/
│   │   └── dom.js                # 新增：安全转义 / 元素查询等小工具
│   ├── data/
│   │   ├── wow-classes.js        # 唯一职业数据（颜色解析自 CSS 变量）
│   │   ├── specs.js              # 新增：专精注册表（class + spec + icon）
│   │   └── tier-lists/*.js       # 瘦身后的纯数据（id 列表）
│   ├── components/
│   │   ├── TierList.js           # 唯一实现
│   │   ├── Chart.js              # 新增：条形图 / 饼图
│   │   ├── ranking-nav.js
│   │   ├── header.js / nav.js / footer.js
│   └── modules/                  # 页面级控制器
│       ├── GuildStatsLoader.js
│       ├── WCLDataLoader.js
│       ├── ImageUploader.js
│       ├── ImageModal.js
│       └── ParticleSystem.js
├── netlify/functions/            # 原样（加鉴权）
├── tools/                        # 原 data/Database/ 的 Python（Phase 1 迁入）
│   ├── paths.py / timeutil.py    # 新增
│   ├── build_page_data.py        # 原 generate_page_data.py
│   ├── mounts_crawler.py
│   ├── validate.py               # 新增
│   ├── config.json               # gitignored
│   └── config.example.json       # 入库
└── data/                         # 只保留产物
    └── page_data.json
```

**数据流**（保持不变）：

```
Blizzard API ──crawl──▶ SQLite(guild_characters) ──build──▶ data/page_data.json ──fetch──▶ 首页图表/排行榜
WarcraftLogs ──wcl-proxy──▶ 前端表格
Cloudinary   ──handle-upload / get-images──▶ 画廊
```

---

## 4. 分阶段计划

### Phase 0 · 止血（0.5–1 人天）

| # | 任务 | 产出 |
|---|---|---|
| 0.1 | 令牌外置 + 两份配置合并 + 文档脱敏 | `config.py`、`config.example.json`、脱敏后的文档 |
| 0.2 | 数据/配置从版本控制移出 | `.gitignore`、待执行的 `git rm --cached` 清单 |
| 0.3 | 统计口径重定义 + 去重 | `generate_page_data.py`、`index.html` 卡片 |
| 0.4 | 时间戳统一 + 过滤条件配置化 | `timeutil.py`、生成日志 |
| 0.5 | 上传鉴权 + 描述持久化 + 画廊分页 | 两个 Function、`gallery.html`、`ImageUploader.js` |
| 0.6 | 灯箱索引修复 | `ImageModal.js` |

> 本阶段 Python 文件仍留在 `data/Database/`，目录迁移统一放到 Phase 1（1.8），避免止血期扩大改动面。

**出口条件**：§2.1 六项验收全绿；线上回归一次（首页 / 画廊 / WCL / 排名页）。

### Phase 1 · 去重（1–2 人天）

| # | 任务 | 依赖 |
|---|---|---|
| 1.1 | 删 `DPSTierList.js`、`ClassIcon.js`、空 py、测试页 | 无 |
| 1.2 | 颜色单一来源（`resolveClassColor`） | 1.1 |
| 1.3 | 注入式 CSS 外置到 `css/` | 1.1 |
| 1.4 | 图表渲染合并为 `Chart.js` | 1.3 |
| 1.5 | 清理 console.log，引入 `CONFIG.debug` | 无 |
| 1.6 | tier 数据瘦身（`specs.js` 注册表） | 1.2 |
| 1.7 | footer 去重、粒子系统按页/偏好开关 | 无 |
| 1.8 | Python 从 `data/Database/` 迁入 `tools/`，路径与 `logs/` 目录统一（关闭 P1-8） | 1.1 |

**出口条件**：§2.2 验收全绿；`all-rankings.html` 六个榜单与原来一致。

### Phase 2 · 补基建（1 人天，可与 Phase 1 并行部分）

| # | 任务 |
|---|---|
| 2.1 | `netlify.toml`（functions / Node 版本 / 安全头 / 缓存） |
| 2.2 | ESLint + Prettier + npm scripts |
| 2.3 | 根 README + `docs/ARCHITECTURE.md` + `docs/DATA_PIPELINE.md`，其余文档归档 |
| 2.4 | `tools/validate.py` 数据校验（失败即停） |
| 2.5 | 图片压缩与格式转换 |

---

## 5. 验收清单（可直接执行）

> 命令中的 `rg` 可替换为 `grep -rn`。`--glob '!.git/**'` 用于排除历史对象。

### 5.1 安全与数据

```bash
# P0-1 无明文令牌
rg -n "[a-f0-9]{32}" --glob '!*.db' --glob '!*.csv' --glob '!.git/**'
# 期望：仅命中 example / REDACTED

# P0-5 数据文件未被跟踪
git ls-files data/
# 期望：data/page_data.json

# P0-2 未授权上传
curl -i -X POST https://<site>/.netlify/functions/handle-upload
# 期望：401

# P0-3 / P0-4 数据管道（validate.py 于 Phase 2 交付）
python tools/validate.py
# 期望：退出码 0，并打印 total / active / completeness 与过滤条件

# P0-4 单位换算
python -c "from tools.timeutil import to_unix_seconds as f; assert f(1754329119000)==1754329119; print('ok')"
```

### 5.2 代码质量

```bash
rg -n "DPSTierList" .                 # 期望：无结果
rg -n "createElement\('style'\)" js/  # 期望：无结果
rg -n "conic-gradient" js/            # 期望：1 处（Chart.js）
rg -n "console\.log" js/              # 期望：无结果
rg -n "#C69B6D" --glob '!*.md' .      # 期望：仅 variables.css
rg -n "specIcon:" js/data/            # 期望：仅 specs.js
```

### 5.3 页面冒烟（手动，8 个页面）

| 页面 | 检查点 |
|---|---|
| `index.html` | 统计卡片数值不同且合理；4 个图表渲染；两个排行榜有数据；B 站 iframe 正常；粒子动画可见 |
| `pages/all-rankings.html` | 6 个榜单全部渲染；顶部快捷导航滚动定位正确；`head` 中无动态 `<style>` |
| `pages/gallery.html` | 上传成功→描述保留→刷新后仍在；上传第 11 张后仍可见；灯箱左右切换正常 |
| `pages/wcl.html` | 表格加载；刷新按钮转圈后恢复；错误态有兜底 |
| `pages/class-colors.html` | 13 个职业色块与 `variables.css` 一致；复制按钮可用 |
| `pages/archive/H6.html` / `H7.html` | 图片可点开放大并左右切换 |
| 导航 | 从首页与从子页进入，链接均可达 |
| 移动端 | 375px 宽度下无横向滚动，导航可展开 |

### 5.4 重构前后对比指标

| 指标 | 现状 | 目标 |
|---|---:|---:|
| JS 行数 | 3,499 | ≤ 2,600 |
| 死/重复文件 | 5 | 0 |
| 职业颜色副本 | 5 | 1 |
| 运行时注入的 `<style>` 块（排名页） | 6 | 0 |
| `console.log` | 30 | 0 |
| 仓库体积（含资源） | ~22 MB | < 5 MB |
| 数据文件入库 | 是 | 否 |

---

## 6. 需要项目负责人手工完成（无法代做）

1. **轮换暴雪/网易 API 令牌**：在账号侧重新生成，旧令牌立即失效。
2. **清理 git 历史**：本机当前无 `git` 命令，无法代执行。建议安装 Git 后：
   ```bash
   # 若已完成 Phase 1 的 1.8 迁移，配置路径改为 tools/config.json
   git rm --cached data/guild_database.db data/guildmember.csv data/config.json data/Database/config.json
   git commit -m "chore: 停止跟踪数据与配置文件"
   # 若仓库曾公开，另需（危险，会改写历史，先备份）：
   # git filter-repo --path data/guild_database.db --path data/guildmember.csv --invert-paths
   ```
3. **配置 Netlify 环境变量**：`WCL_CLIENT_ID` / `WCL_CLIENT_SECRET` / `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` / `UPLOAD_TOKEN` / `BLIZZARD_API_TOKEN`。
4. **Cloudinary 侧确认**：上传目录配额、是否开启 unsigned upload（应关闭）。
5. **执行前备份**：在 Phase 0 动手前，对 `repos/yiqi` 整体打一次 zip 或初始化 git 仓库，作为回滚点。

---

## 7. 非目标（明确不做）

- 不引入 React / Vue / Svelte 等框架。
- 不引入 TypeScript（收益不足以覆盖改造面）。
- 不做 SSR / SSG 迁移，不引入 Vite 等构建链。
- 不改 URL 结构、不改页面路由、不改目录对外可见性。
- 不重写爬虫的请求协议与数据源。
- 不做用户系统、权限体系（上传口令是共享口令，不是账号体系）。
- 不为 8 个页面引入组件库。

---

## 8. 风险与回滚

| 风险 | 触发点 | 缓解 |
|---|---|---|
| 无 git 导致改动不可回退 | Phase 0 改文件 | 动手前整目录备份；建议先安装 Git |
| 令牌轮换后本地脚本失效 | P0-1 | 同步更新 `.env` 与 Netlify 环境变量；先改代码再轮换 |
| 上传鉴权导致旧页面 401 | P0-2 | 前后端同一提交上线；先灰度，口令错误时给出明确提示 |
| 统计口径变化导致首页数字大幅变化 | P0-3 | 上线前把新旧 JSON 并排对比，确认差异可解释 |
| 数据文件移出仓库导致其他人无法运行 | P0-5 | README 写明获取方式；`validate.py` 给出明确报错 |
| CSS 外置后样式丢失 | P1-3 | 外置时逐条对照原注入内容；上线后对比截图 |
| tier 数据瘦身引入错配 | P1-6 | 保留一份旧 JSON 快照，渲染结果 diff |

**回滚策略**：每阶段独立提交，回滚 = revert 该阶段的合并提交；Phase 0 的 6 项互相独立，可单项回滚。

---

## 9. 附录：关键改造示例

### 9.1 职业颜色单一来源

```js
// js/data/wow-classes.js
const colorCache = new Map();

/** 从 CSS 变量解析职业 hex 颜色（CSS 为唯一权威） */
export function resolveClassColor(className) {
  if (colorCache.has(className)) return colorCache.get(className);
  const info = getClassInfo(className);
  if (!info) return '#FF6B35';
  const name = info.color.replace('var(', '').replace(')', '').trim();
  const hex = getComputedStyle(document.documentElement)
    .getPropertyValue(name).trim() || '#FF6B35';
  colorCache.set(className, hex);
  return hex;
}
```

`TierList.js` 改为：

```js
import { resolveClassColor } from '../data/wow-classes.js';
const hex = resolveClassColor(spec.class);
// 半透明背景：用 color-mix 或 rgba 转换，避免拼 8 位 hex
style="background: color-mix(in srgb, ${hex} 12%, transparent); border-left: 4px solid ${hex};"
```

### 9.2 专精注册表（P1-6）

```js
// js/data/specs.js
export const SPECS = {
  'paladin:protection': { class: '圣骑士', spec: '防护', icon: 'https://.../2adb89.jpg' },
  'death-knight:blood': { class: '死亡骑士', spec: '鲜血', icon: 'https://.../93e144.jpg' },
  // ... 共 38 条
};
export function resolveSpec(id) {
  const s = SPECS[id];
  if (!s) throw new Error(`未知专精: ${id}`);
  return { ...s, name: `${s.spec} ${s.class}` };
}
```

tier 数据瘦身为：

```js
tiers: {
  S: { name: 'S', description: '', specs: ['paladin:protection', 'death-knight:blood'] },
  A: { name: 'A', description: '', specs: ['warrior:protection', 'druid:guardian', 'demon-hunter:vengeance'] },
}
```

### 9.3 统一图表组件（P1-4）

```js
// js/components/Chart.js
export function renderBarChart(container, items, { colorOf = () => '#9C27B0', emptyText = '暂无数据' } = {}) {
  if (!container) return;
  const max = Math.max(...items.map(i => i.value), 0);
  if (!items.length || max === 0) { container.innerHTML = `<p class="chart-empty">${emptyText}</p>`; return; }
  container.innerHTML = items.map(({ name, value }) => {
    const color = colorOf(name);
    const pct = (value / max * 100).toFixed(1);
    return `<div class="chart-bar">
      <span class="chart-bar-label" style="color:${color}">${escapeHtml(name)}</span>
      <div class="chart-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${color} 0%,${color}80 100%)"></div>
      <span class="chart-bar-value">${value}</span>
    </div>`;
  }).join('');
}

export function renderPieChart(container, items, { colorOf, labelOf = i => i.name, emptyText = '暂无数据' } = {}) {
  if (!container) return;
  const total = items.reduce((s, i) => s + i.value, 0);
  if (!items.length || total === 0) { container.innerHTML = `<p class="chart-empty">${emptyText}</p>`; return; }
  let angle = 0;
  const stops = items.map(i => {
    const from = angle, to = angle + (i.value / total) * 360;
    angle = to;
    return `${colorOf(i.name)} ${from}deg ${to}deg`;
  });
  container.innerHTML = `
    <div class="chart-pie" style="background: conic-gradient(${stops.join(', ')})">
      <div class="chart-pie-center">${total}</div>
    </div>
    <ul class="chart-legend">
      ${items.map(i => `<li><span style="background:${colorOf(i.name)}"></span>
        <b style="color:${colorOf(i.name)}">${escapeHtml(labelOf(i))}</b>
        ${i.value} (${(i.value / total * 100).toFixed(1)}%)</li>`).join('')}
    </ul>`;
}
```

> 注意：现有代码把 `item.name` 直接拼进 HTML，存在注入面（虽然数据源可控）。外置模板时统一用 `escapeHtml` 收敛。

### 9.4 时间工具（P0-4）

```python
# tools/timeutil.py
from datetime import datetime, timezone

def to_unix_seconds(value):
    """把秒或毫秒时间戳统一为秒。"""
    if value is None:
        return None
    v = int(value)
    return v // 1000 if v > 10_000_000_000 else v

def parse_date(text):
    """'2025-02-27' -> unix 秒（UTC）。"""
    return int(datetime.strptime(text, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
```

### 9.5 `netlify.toml` 参考

```toml
[build]
  publish = "."
  functions = "netlify/functions"

[build.environment]
  NODE_VERSION = "20"

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    X-Frame-Options = "SAMEORIGIN"

[[headers]]
  for = "/css/*"
  [headers.values]
    Cache-Control = "public, max-age=3600"

[[headers]]
  for = "/img/*"
  [headers.values]
    Cache-Control = "public, max-age=604800"
```

### 9.6 数据校验（P2-4）

```python
# tools/validate.py —— 任一断言失败即退出码 1
import json, sys
from datetime import datetime, timedelta

def main():
    data = json.load(open('data/page_data.json', encoding='utf-8'))
    stats = data['stats']
    total, active = stats['totalMembers'], stats['activeMembers']
    assert 0 < total <= 5000, f'totalMembers 异常: {total}'
    assert 0 <= active <= total, f'active({active}) > total({total})'
    ages = {r['name'] for r in data['rankings']['achievementRanking']}
    assert len(ages) == len(data['rankings']['achievementRanking']), '排行榜存在重名'
    ts = datetime.strptime(data['lastUpdated'], '%Y-%m-%d %H:%M:%S')
    age = datetime.now() - ts
    if age > timedelta(days=7):
        # 默认只告警；CI 中可用 --strict 提升为失败
        print(f'WARN 数据已过期 {age.days} 天: {data["lastUpdated"]}', file=sys.stderr)
    print(f'OK total={total} active={active} pct={stats["dataCompleteness"]["percentage"]}%')

if __name__ == '__main__':
    main()
```

---

## 10. 待评审确认的问题

1. **`active_days` 取多少**：30 天（推荐）／14 天／7 天？
2. **`totalMembers` 是否只统计当前公会成员**：DB 里含历史成员记录，需要确认是否按 `guild` 字段过滤。
3. **上传口令的使用者范围**：仅管理员（写进 `.env` 分发）还是全员（需要更轻量的方案）？
4. **测试页与 `class-colors.html` 的去留**：直接删除，还是保留并在 `netlify.toml` 中强制 404？（当前 `publish = "."`，保留即等于公开发布）
5. **是否接受"数据文件移出仓库"**：若坚持保留，至少要接受"仓库内含成员数据"这一事实并限制仓库可见性。
6. **数据是否重跑**：现有数据停在 2025-08，重构上线前是否重跑一次爬虫？（涉及令牌额度与耗时）

---

## 11. 执行记录（2026-10-18）

> 约束：本次执行环境无 `git`、无 `ffmpeg/ImageMagick`；项目负责人要求**暂不处理密钥/令牌**。
> 执行前已生成整目录备份：`_backup_yiqi_20261018-015656.zip`（21.6 MB / 107 项）。

### 11.1 已完成

| 阶段 | 条目 | 结果 |
|---|---|---|
| Phase 0 | 0.3 统计口径 + 去重 | 967 行 → 965 角色；`totalMembers=965`、`activeMembers=356`、完整率 72.7% |
| Phase 0 | 0.4 时间戳统一 | `tools/timeutil.py`；去除硬编码 cut-off 与毫秒/秒误用 |
| Phase 0 | 0.5 画廊函数（不含鉴权） | 描述写入 Cloudinary context 并在读取时还原；`max_results=500`；错误不再泄露堆栈 |
| Phase 0 | 0.6 灯箱索引 | 改为点击时重算索引 + 防重复绑定 + 越界防御 |
| Phase 0 | 0.2 数据隔离（部分） | `.gitignore` 已覆盖数据库/CSV/配置；`git rm --cached` 待有 git 环境时执行 |
| Phase 1 | 1.1–1.7 | 删除 `DPSTierList.js`(341 行)、`ClassIcon.js`、2 个空 py、2 个测试页；颜色收敛为 1 处；CSS 外置 2 个文件；图表合并为 `Chart.js`；`console.log` 仅保留在 `log()` 内部；天梯数据从 70 处引用收敛为 39 条注册表；footer 去重；粒子按页面/偏好开关 |
| Phase 1 | 1.8 Python 迁移 | `data/Database/` → `tools/`；`generate_page_data.py` → `tools/build_page_data.py`；路径统一走 `tools/paths.py`；`logs/` 自动创建 |
| Phase 2 | 2.1–2.4 | `netlify.toml`；ESLint(flat) + Prettier + npm scripts；根 README + ARCHITECTURE + DATA_PIPELINE + docs 索引；`tools/validate.py` |

### 11.2 未完成 / 跳过

| 条目 | 原因 | 后续 |
|---|---|---|
| P0-1 令牌外置与轮换 | 负责人要求暂不处理密钥 | 见 DATA_PIPELINE §10 |
| P0-5 `git rm --cached` | 环境无 git 命令 | 安装 git 后执行（命令见 §6） |
| P0-2 上传鉴权 | 依赖 `UPLOAD_TOKEN` 环境变量 | 已实现「设置后才启用」的可选鉴权，未配置时行为不变 |
| P2-5 图片压缩 | 无 `ffmpeg` / `ImageMagick` | 建议转 WebM/WebP |
| `package-lock.json` 同步 | 未安装依赖（公用电脑，不联网安装） | 本地执行 `npm install` 后提交 |

### 11.3 执行中发现的新问题

1. **增强萨满图标冲突**：`dps-tier-list.js` 与 `mplus-dps-tier-list.js` 对 `shaman|增强` 使用了不同图标，后者误用了元素萨满的图标。注册表按「首见优先」保留了正确图标，等价于顺带修复。
2. **`lastUpdated` 会掩盖数据老化**：生成时间总是"现在"。已新增 `dataAsOf`（数据截至日 = 2025-08-04），页面展示改为"数据更新: 2025-08-04 · 页面生成于 {生成时间}"，`validate.py` 也改为按 `dataAsOf` 判断新鲜度。
3. **坐骑数据无区分度**：277 个有坐骑记录的角色 `mounts_now` 全部为 369，疑为爬虫对所有角色复用了同一令牌（与归档的 `API_ISSUE_ANALYSIS.md` 描述一致）。属数据源问题，未在本次范围内修复。
4. **`class-colors.html` 未加载 `main.js`**：页面此前没有 Header/导航/Footer 内容，已补上入口脚本。

### 11.4 与计划的偏差

- 测试页采取**直接删除**而非移入 `_dev/`（复核后确认 Netlify 会发布下划线目录）。
- 文档收敛为 4 份（README / ARCHITECTURE / DATA_PIPELINE / docs 索引）+ `archive/`，未删除任何历史文档。
- Python 迁移提前到 Phase 1 一次完成，避免同一批文件改两遍。
