# 上手 / 交接手册

> 给第一次接手这个仓库的人，也给三个月后回来改东西的自己。
> 目标：**30 分钟**内能跑起来、改一处东西、发布出去；出问题时知道先看哪里。
> 原理性内容在 [ARCHITECTURE.md](ARCHITECTURE.md) 与 [DATA_PIPELINE.md](DATA_PIPELINE.md)，这里只写「动作」。

## 0. 这是什么

一起公会的静态站点：首页公会统计、职业天梯、WCL 开荒记录、画廊、攻略页。
没有构建链——原生 ES Modules + 多文件 CSS，Netlify 直接发布仓库根目录。

当前数据（2026-10-24）：**724 名成员 / 近 30 天活跃 319 / 数据完整率 97.1%**；
天梯到 Midnight 第二赛季；这两块都由 GitHub Actions 定时自动刷新。

## 1. 跑起来（5 分钟）

```bash
git clone https://github.com/xinming-chenniang/yiqi.git
cd yiqi
pip install -r requirements.txt        # 只有 requests
python -m http.server 8080             # 打开 http://localhost:8080/
npm test                               # JS 58 + Python 60 个测试，不需要 npm install
```

- **只看页面**不需要网络、不需要数据库；`data/page_data.json` 与 `js/data/*-tier-list.js` 都在仓库里。
- 要用 `/.netlify/functions/*`（WCL 拉取、画廊上传）时必须 `netlify dev`，`http.server` 下这些路径 404 属正常。

## 2. 目录地图：想改什么，动哪里

| 想改 | 动这里 | 注意 |
|---|---|---|
| 首页数字 / 图表 / 排行榜 | `data/page_data.json` | **不要手改**，跑 `tools/build_page_data_rio.py` 生成 |
| 职业天梯 | `js/data/*-tier-list.js` | **不要手改**，跑 `tools/fetch_tier_lists.py` 生成 |
| 专精的图标 / 中文名 | `js/data/specs.js` + `tools/wow_terms.py#SPEC_BY_EN` | 两边要同时改，抓取脚本会校验一致性 |
| 服务器中文名 | `tools/wow_terms.py#REALM_SLUG_TO_CN` | 查不到就留空，代码回退英文显示名，**不猜** |
| 职业颜色 | `css/variables.css` 的 `--class-*` | JS 侧只通过 `resolveClassColor()` 取色 |
| 层级颜色 / A+ 档 | `css/variables.css` 的 `--tier-*` + `js/components/TierList.js#TIER_ORDER` | 类名里 `+` 会映射成 `-plus` |
| 页面文案 / 结构 | `index.html`、`pages/*.html` | 页脚与导航由 `js/components/` 注入，别在 HTML 里重复写 |
| 接口行为 | `netlify/functions/` | CommonJS，不能直接复用前端 ESM |
| 定时任务 | `.github/workflows/` | 见第 3 节 |

## 3. 三条流水线：数据是谁在动

| 流水线 | 触发 | 产物 | 失败时 |
|---|---|---|---|
| 成员数据 | 每天 03:00 UTC（北京时间 11:00） | `data/page_data.json` | 作业失败、**不提交**，线上保持上一版 |
| 天梯 | 每周一 02:00 UTC（北京时间 10:00） | `js/data/*-tier-list.js` | 同上 |
| CI | 每次 push / PR | 跑测试 + `validate.py` | PR 变红，阻止合并 |

手动重跑（本机需要能访问对应站点）：

```bash
python tools/fetch_guild_roster.py --enrich      # RIO 名单 + 逐角色 ilvl / M+ 分数（约 20 分钟）
python tools/build_page_data_rio.py              # 生成 page_data.json
python tools/validate.py --strict                # 断言 + 新鲜度检查

python tools/fetch_tier_lists.py                 # 抓 Wowhead 并重写 6 份天梯
python tools/fetch_tier_lists.py --check         # 只比对差异，退出码 1 表示有更新
python tools/fetch_tier_lists.py --offline       # 用 .cache/tier-lists 里的原文重跑解析
```

## 4. 口径差异（最容易误解的地方）

- **活跃** = 本季有大秘境记录 **或** RIO 近 30 天更新过该角色。不是「最后登录」——英雄榜才提供最后登录，而它现在要求战网登录。
- **数据完整率** = 成就点数 > 0 且装备等级 > 0 的占比。
- **坐骑**维度已下线（RIO 没有该字段；旧的坐骑数据本身也是错的，全部同值）。
- **成员数偏少是正常的**：RIO 724 人 vs 旧英雄榜导出 950 个唯一名字，按名字重合 556。RIO 只收录它抓过的角色。
  详细口径与这三个数字见 [DATA_PIPELINE.md](DATA_PIPELINE.md) §4 与 §12。

## 5. 发布与回滚

```bash
git push origin main        # Netlify 自动部署；Actions 之后可能回写 page_data.json
```

回滚：

```bash
git revert <sha>                     # 推荐：保历史
git show <旧 sha>:data/page_data.json > data/page_data.json   # 只回数据
git show <旧 sha>:requirements.txt  > requirements.txt        # 只回依赖
```

回滚后跑一遍 `npm test && python tools/validate.py --strict` 再推。

## 6. 已知坑（按踩到的概率排）

1. **wowhead 部分地区 403**（CloudFront 地区拦截）：本机直连、香港出口都被拦，用 `--route reader`（走 r.jina.ai）或挂代理。
2. **RIO 会限速**：`--enrich` 724 人实测约 20 分钟，别以为卡死了；`--limit 20` 可以小批量先试。
3. **`requirements.txt` 必须是纯 ASCII**：pip 在中文 Windows 上按 cp936 解码该文件，中文注释会让 `pip install -r` 直接崩。
4. **`.cache/` 是缓存，别删**：`tier-lists/`（抓下来的原始页面）与 `guild-roster/`（名单快照）能让重跑不联网。截图不放这里了，去 `docs/preview/`。
5. **H6/H7 攻略是 11.1「解放安德麦」的内容**，已从导航收起、挪到 `pages/archive/`（只从「其他」页 `pages/other.html` 进），版本仍是旧的 —— 见第 8 节待办。
6. **两条服务器名存疑**：`holy-chanter=神圣之歌`、`dreamwalker=踏梦者`，已在代码里标 `# 待游戏内核实`。
7. **CSP 白名单**：新增图片/字体域名要同步改 `netlify.toml` 的 `img-src` / `font-src`，否则线上静默不显示。
8. **不要让 prettier 碰 `js/data/*-tier-list.js`**：已加入 `.prettierignore`，否则生成器会一直被格式化差异打回。

## 7. 决策记录（为什么长这样）

| 决策 | 原因 | 代价 |
|---|---|---|
| 成员数据走 Raider.IO | 公开接口、可全自动；英雄榜现在必须战网登录 | 没有等级/最后在线/坐骑；覆盖不全 |
| 天梯抓 Wowhead 而不是自己算 | 编辑给的层级就是产品口径，自己算要定一堆加权 | 依赖第三方页面结构，改版会断 |
| 天梯保留 A+ 档 | 大秘境 DPS 榜单确实有 A+，压成 A 会失真 | 多一层级样式与测试 |
| 新专精图标自托管 `img/specs/` | CSP 只放行白名单域名，zamimg 不在其中 | 仓库多两个小图 |
| `page_data.json` 随仓库分发 | 首屏不需要后端 | 由 Actions 定时回写 |
| 旧英雄榜链路保留但标「旧链路」 | 将来有登录态时还能取全字段 | 两套口径并存，文档要说清 |

## 8. 交接 checklist（离开前 5 分钟）

```bash
git status -sb                     # 有没有未提交/未推的东西
npm test                           # JS + Python
python tools/validate.py --strict  # 产物与新鲜度
```

- 有没有**只在本机**的文件（截图、抓取缓存、临时脚本）？该入库的入库，该删的删。
- 没做完的事写进「未决」——具体到文件与动作，不写「继续完善」。
- 本机收尾报告（如果还在）：`C:\Users\28402\.dsh\closeouts\`，不在仓库里。

## 9. 当前待办（2026-10-24）

1. ~~H6/H7 攻略加版本横幅、导航改名~~ ✅ 2026-11-16：挪到 `pages/archive/`，从导航收起，入口收进「其他」页。剩下 RaidPlan 链接的 `raid=wow.undermine` 参数待更新。
2. WCL 页显示「最后一条报告日期」，过期时提示。
3. `holy-chanter` / `dreamwalker` 两条服务器名游戏内核实后摘掉标记。
4. RIO 覆盖率与真实在会人数的差额——需要登录态英雄榜或游戏内名单对照。
