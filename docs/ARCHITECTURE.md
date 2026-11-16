# 架构说明

## 1. 页面与入口

所有页面共用 `js/main.js`：它在 `DOMContentLoaded` 时加载 Header / 导航 / Footer，再按「页面上是否存在某个元素」条件初始化功能模块。

| 页面 | 额外入口 | 初始化的模块 |
|---|---|---|
| `index.html` | `js/pages/home-tier-list.js` | `TierListTabs`（6 份天梯标签切换，默认大秘境 DPS）、`GuildStatsLoader`、`ImageModal`、`ParticleSystem`、`IframeErrorHandler` |
| `pages/all-rankings.html` | `js/pages/all-rankings.js` | `TierList` × 6、`RankingNav` + `main.js` 的通用逻辑 |
| `pages/gallery.html` | — | `ImageUploader`、`ImageModal` |
| `pages/wcl.html` | — | `WCLDataLoader` |
| `pages/class-colors.html` | `js/pages/class-colors.js` | `ClassColorPalette` + `main.js` 的通用逻辑 |
| `pages/H6.html` / `H7.html` | — | `ImageModal`（图片放大） |

> 页面里不要再写静态 `<footer class="footer-container">`：footer 由 `components/footer.js` 统一追加，重复会生成两个节点。

## 2. JS 分层

```
js/
  main.js          入口与页面级装配
  config.js        CONFIG（含 debug 开关）、log()、全局错误处理
  core/            无业务依赖的工具（dom.js: escapeHtml / escapeAttr / byId；icons.js: 内联 SVG 图标）
  data/            纯数据：职业表、专精注册表、天梯排名、图表配色
  components/      可复用 UI：TierList、TierListTabs、Chart、RankingNav、Header、Footer、Nav
  modules/         页面级控制器：统计、WCL、画廊、灯箱、粒子
  pages/           页面入口（首页天梯、排名总览、配色预览），只做装配
```

依赖方向：`modules` → `components` → `data` / `core`；`data` 不得反向依赖其他层。

## 3. 渲染约定

### 3.1 转义

所有把数据拼进 HTML 的位置都走 `escapeHtml` / `escapeAttr`。当前数据源可信度较高，但 `page_data.json` 与 Cloudinary 返回内容属于外部输入，必须转义。

### 3.2 颜色

职业颜色的唯一来源是 `css/variables.css`：

```css
:root { --class-paladin: #F48CBA; /* ... */ }
```

JS 侧需要十六进制值时调用 `js/data/wow-classes.js#resolveClassColor(className)`，它从 CSS 变量解析并按职业缓存。不要再在 JS 里维护 `{'圣骑士': '#F48CBA', ...}` 这类色表——历史上存在过 5 份副本。

### 3.3 样式归属

| 样式 | 位置 |
|---|---|
| 变量与基础 | `variables.css` / `base.css` |
| 布局与卡片 | `layout.css` / `components.css` |
| 导航 | `navigation.css` |
| 统计图表 | `stats.css` |
| 职业天梯 | `tier-list.css` |
| 排名页快捷导航 | `ranking-nav.css` |
| 攻略页（H6/H7） | `strategy.css` |
| 工具类与响应式 | `utilities.css` / `media.css` / `animations.css` |

`main.css` 只做 `@import` 组合。JS 不负责样式注入。

### 3.4 天梯数据

- `js/data/specs.js`：专精注册表，key 形如 `paladin|防护`，值为 `{ class, spec, icon }`
- `js/data/*-tier-list.js`：只保存层级与 id 列表，例如 `S: { specs: ['paladin|防护'] }`
- `js/components/TierList.js`：渲染，颜色取自 `resolveClassColor`
- `js/components/TierListTabs.js`：首页顶部用，六份天梯同一张卡片里按标签切换，一次只渲染一份（总览页仍然六份并列）

新增专精要改三处：`specs.js`（id + 图标）、`tools/wow_terms.py#SPEC_BY_EN`（英文名 → id，天梯抓取与成员统计共用）、`js/components/TierList.js#TIER_ORDER`（只在新增档位时改）。6 份天梯文件共享同一份图标定义，且由脚本生成，不要手改。

## 4. 数据流

```
Raider.IO ──tools/fetch_guild_roster.py──▶ data/guildmember.rio.json ──tools/build_page_data_rio.py──▶ data/page_data.json
                                                                                                          │
首页 GuildStatsLoader ──fetch──▶ data/page_data.json ◀────────────────────────────────────────────────────┘

Wowhead guide ──tools/fetch_tier_lists.py──▶ js/data/*-tier-list.js ──import──▶ pages/all-rankings.html

WarcraftLogs ──netlify/functions/wcl-proxy.js──▶ pages/wcl.html
Cloudinary   ──handle-upload.js / get-images.js──▶ pages/gallery.html

（旧链路，已暂停：Blizzard 英雄榜 ──mounts_crawler.py──▶ SQLite ──build_page_data.py──▶ page_data.json）
```

`page_data.json` 的字段契约见 [DATA_PIPELINE.md](DATA_PIPELINE.md#输出结构)。

## 5. 取舍与已知限制

| 决策 | 原因 | 代价 |
|---|---|---|
| 不引入框架/构建链 | 站点仅 7 个页面，构建链维护成本高于收益 | 无组件化、无 tree-shaking、依赖靠浏览器原生 ESM |
| Netlify Functions 用 CommonJS | Netlify 默认打包方式，`package.json` 未设 `type: module` | 不能直接复用前端 ESM 模块 |
| `page_data.json` 随仓库分发 | 无需运行时后端，首屏快 | 新鲜度靠两个定时工作流（每天/每周）刷新，失败时页面保持上一版 |
| 静态 HTML 无模板引擎 | 页面少、改动少 | 重复的 `<head>` 需要手工保持一致 |

## 6. 测试与安全策略

### 6.1 测试

零测试框架依赖：JS 用 `node:test`（不需要 npm install），Python 用 `unittest`（需要 `requests`，因为会 import 抓取脚本）。
测试文件在 `tests/`，CI 配置在 `.github/workflows/ci.yml`。详见 [../README.md](../README.md#测试)。

设计上的两个刻意选择：

- **不引入测试框架**（Jest/Vitest）：站点没有构建链，引入框架等于为了测试再造一套构建。
- **图表函数可测**：`Chart.js` 只写 `container.innerHTML`，因此测试用 `{ innerHTML: '' }` 假容器即可断言输出，不需要 jsdom。

### 6.2 CSP

`netlify.toml` 已启用 CSP。style 部分采用**三段式渐进增强**，把「元素级样式」和「属性级样式」分开管：

| 指令 | 值 | 作用 |
|---|---|---|
| `script-src` | `'self'` | 页面内联 `<script>` 已全部外链化（`js/pages/*.js`） |
| `style-src` | `'self'` + cdnjs + `'unsafe-inline'` | **老浏览器兜底**：不认识下面两条时会 fallback 到这里 |
| `style-src-elem` | `'self'` + cdnjs | 现代浏览器：内联 `<style>` 块与外部样式表白名单（当前 `<style>` 块为 0） |
| `style-src-attr` | `'unsafe-inline'` | 现代浏览器：只给 13 处数据驱动的 style 属性开口子 |
| `img-src` | `'self' data:` + 5 个图床域 | netease 职业图标、Cloudinary、raiderio、YY、战网 |
| `frame-src` | bilibili 两个域 | 直播播放器与视频播放器 |
| 其他 | `object-src 'none'`、`base-uri 'self'`、`form-action 'self'` | |

本地验证方法（比"没报错"更强的证据链）：

1. 用带同样响应头 + `report-uri` 的静态服务器加载全部页面 → 零违规；
2. 反向测试：故意收紧到 `default-src 'none'` → 收到多条上报，证明上报链路有效（排除假阴性）；
3. 定向测试：放一个含内联 `<style>` 的探针页 → 只收到 1 条 `style-src-elem` 违规，证明收紧确实生效、且真实页面不受影响。

> 彻底去掉 `'unsafe-inline'` 的路径：把数据驱动的内联 style（天梯 `--class-color`、图表条形宽度）改为
> 预定义 class 或 SVG 属性绘制，然后删掉 `style-src-attr` 与 `style-src` 里的 `'unsafe-inline'`。

## 7. 后续可做

1. **`style-src` 去 `unsafe-inline`**：需要把数据驱动的内联 style 改为预定义 class（天梯 6×39 种组合，可用 CSS 变量 + 少量类实现）。
2. ~~**数据自动化**~~ ✅ 2026-10-24：`guild-stats-refresh.yml`（每日，Raider.IO）与 `tier-list-refresh.yml`（每周，Wowhead），有变化才提交。
3. **视觉回归**：目前改动 CSS 后仍依赖人工核对，可引入截图对比（本项目已用无头 Edge 做过一次性对比）。
4. **lint 进 CI**：需要先同步 `package-lock.json`（当前 devDependencies 未入锁）。
