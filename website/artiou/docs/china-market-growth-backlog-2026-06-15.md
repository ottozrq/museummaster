# Artiou 中国市场增长方向与 backlog（2026-06-15）

## 决策边界

Otto 已明确 Artiou 面向中国市场，后续增长主线从「英文 SEO / Google 索引增长」切换为「中文用户获取与转化」。英文页面不删除，但只保留两类工作：

1. **技术卫生**：sitemap、canonical、404/fallback、结构化数据、基础可访问性、已有页面不回归。
2. **可复用资产**：已经写好的英文 Louvre / Orsay / Monet / Mona Lisa 内容可作为中文页面底稿，不再默认扩张英文内容或把英文 query 当主增长机会。

停止项：新建以 English SEO query/impression 为核心验收的增长卡；批量扩英文 museum guide / artwork guide；用英文 GSC impression 作为默认优先级来源。

## 当前 backlog / 看板盘点

### Artiou 已完成或 REVIEW 的英文 SEO 卡片

这些卡片不作为新增长主线，只作为已完成的技术/内容资产保留：

- `artiou P0：把 sitemap/fallback/canonical smoke test 纳入部署验收`：保留，属于技术卫生。
- `artiou P1：按 “where/location Mona Lisa” query 重写 Mona Lisa 首屏与 FAQ`：不继续作为英文 query 增长主线；可复用为中文「蒙娜丽莎在哪里 / 怎么看」页面底稿。
- `artiou P1：把 Paris guide 改成可传权重的博物馆/作品实体入口`：不继续作为英文 entity SEO 主线；可复用为中文巴黎首次观展入口。
- `artiou P2：清理 Umami 下载事件模型并建立 guide→download funnel`：保留并改口径为按 language / page_path / channel 识别中文转化。

### 当前中文市场卡片

- P0 当前卡：重写增长方向为中文用户获取与转化。
- P1 已在 TODO：建立小红书/抖音「巴黎博物馆艺术小白」内容矩阵。
- P1 已在 TODO：中文落地页与 App 下载漏斗诊断。

## Live 站点入口盘点

验证命令：

```bash
python - <<'PY'
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError
# checked zh/en home + Paris/Louvre/Orsay/Monet/Mona Lisa URLs
PY
```

结果摘要：

| 页面 | live 状态 | 当前承担的中文转化角色 | 判断 |
| --- | --- | --- | --- |
| `https://www.artiou.com/zh/` | 200 | 中文首页，已有「拍照识展 / 中文讲解 / 下载 App」 | 可作为下载入口，但首屏还不够像「中国游客去海外博物馆」场景 |
| `https://www.artiou.com/zh/paris-museum-guide/` | 200 | 中文巴黎选馆指南，已有首次观展、避坑、轻路线 | 可作为中国游客 Paris 入口；需要强化小红书/抖音导流落地和下载 CTA |
| `https://www.artiou.com/zh/louvre-first-time-visitor-guide/` | 404 | 无中文卢浮宫页 | P0 缺口 |
| `https://www.artiou.com/zh/musee-orsay-guide/` | 404 | 无中文奥赛页 | P0 缺口 |
| `https://www.artiou.com/zh/monet-water-lilies-guide/` | 404 | 无中文莫奈/睡莲页 | P1 缺口 |
| `https://www.artiou.com/zh/mona-lisa-guide/` | 404 | 无中文蒙娜丽莎页 | P0 缺口 |
| 英文 Louvre / Orsay / Monet / Mona Lisa | 200 | 现有内容资产 | 翻译/重写为中文用户场景，而不是继续优化英文 query |

## 分析口径调整

后续增长周报和埋点不要只看 `pageviews / English SEO URL impressions`。建议固定四层漏斗：

1. **渠道发现**：小红书、抖音、微信分享、中文搜索 / GEO。
2. **落地页理解**：`/zh/`、`/zh/paris-museum-guide/`、未来中文 Louvre / Mona Lisa / Orsay / Monet 页的停留、滚动、内部点击。
3. **App 下载意图**：`guide_download_click` / `download_click`，必须带 `language=zh-Hans`、`page_path`、`cta_location`、`channel_hint`（如后续加 UTM）。
4. **实际下载/激活代理指标**：App Store click、二维码/分享 click、收藏/识别相关 app 内事件（若可接入）。

现有 `static-site.js` 已给下载/guide CTA 带 `language`、`page_path`、`cta_location`，可作为基础；下一步应增加中文渠道参数和区分 App Store / 页面内锚点点击。

## P0 / P1 / P2 中文市场 backlog

### P0 — 先修中文核心落地与下载漏斗

1. **中文首页首屏改成「中国游客第一次逛海外博物馆」**
   - 用户场景：出境游用户到了卢浮宫/奥赛，看不懂标签、不想租讲解器、希望手机中文讲解。
   - 目标页面/渠道：`/zh/`；来自小红书/抖音 bio、微信转发、中文搜索品牌词。
   - 验收指标：首屏出现「中国游客 / 中文讲解 / 拍照识展 / App Store」语义；顶部 CTA 能直接触发带 `language=zh-Hans` 的下载事件；live 200/canonical/indexable。

2. **建立中文蒙娜丽莎页：`/zh/mona-lisa-guide/`**
   - 用户场景：中国游客在卢浮宫想知道「蒙娜丽莎在哪、怎么看、值不值得排队」。
   - 目标页面/渠道：小红书/抖音短内容「蒙娜丽莎 60 秒看懂」→ 中文页 → App 下载。
   - 验收指标：页面 200；H1/首屏回答位置、排队、人群、看点；至少 1 个 App 下载 CTA；Umami 能看到 `guide_download_click` with `language=zh-Hans`。

3. **建立中文卢浮宫艺术小白路线页：`/zh/louvre-first-time-visitor-guide/`**
   - 用户场景：第一次去卢浮宫，只想 2–3 小时看懂重点，不做打卡马拉松。
   - 目标页面/渠道：小红书「第一次去卢浮宫路线」/ 抖音「卢浮宫别乱逛」。
   - 验收指标：路线分 1h/2h/3h；明确可用 Artiou 拍照听中文讲解；链接蒙娜丽莎页与巴黎页；live 200/canonical/indexable。

4. **中文下载漏斗诊断与修复**
   - 用户场景：中文用户从 `/zh/` 或中文 guide 进站后，知道为什么下载、点哪里下载、点完能追踪。
   - 目标页面/渠道：`/zh/`、`/zh/paris-museum-guide/`、未来中文 guide。
   - 验收指标：App Store 链接可用；每个核心页面至少 1 个可见下载 CTA；事件能按 language/page_path/cta_location 聚合；不重复触发。

### P1 — 建立中文获客内容与页面扩展

5. **小红书/抖音内容矩阵：巴黎博物馆艺术小白**
   - 用户场景：准备巴黎自由行，对艺术不熟但想拍照、看懂、少踩坑。
   - 目标渠道：小红书图文/视频、抖音短视频。
   - 验收指标：4 个栏目，每栏目 10 个选题；每条有标题钩子、脚本结构、CTA 和目标 URL；优先导到 `/zh/`、`/zh/paris-museum-guide/`、中文 Louvre/Mona Lisa 页。

6. **中文奥赛页：`/zh/musee-orsay-guide/`**
   - 用户场景：想看梵高/莫奈/印象派，不确定奥赛和卢浮宫怎么选。
   - 目标页面/渠道：小红书「奥赛比卢浮宫更适合艺术小白吗」。
   - 验收指标：页面 200；首屏明确奥赛适合艺术小白；包含 2h 路线、必看作品、下载 CTA。

7. **中文莫奈/睡莲页：`/zh/monet-water-lilies-guide/`**
   - 用户场景：去橘园看莫奈《睡莲》，想知道为什么值得看、怎么看。
   - 目标渠道：小红书/抖音「莫奈睡莲 60 秒看懂」。
   - 验收指标：页面 200；能从巴黎页/奥赛页互链；包含「60 秒看懂」段落和 App 下载 CTA。

8. **中文 SEO / GEO 基础包**
   - 用户场景：用户在百度/微信搜一搜/AI 问答中问「巴黎博物馆怎么选」「卢浮宫路线」。
   - 目标页面/渠道：中文首页和中文 guide 页；结构化 FAQ/HowTo 只服务中文问题，不为了英文 query 扩写。
   - 验收指标：每页 title/meta/H1 是中文问题；FAQ 使用中文自然问法；sitemap 包含中文核心页；无英文 SEO brief 泄漏。

### P2 — 分享、微信与留存

9. **微信分享卡与中文 OG 优化**
   - 用户场景：用户把巴黎观展路线发给同行朋友或微信群。
   - 目标页面/渠道：`/zh/` 和中文 guide 页。
   - 验收指标：每页 `og:title` / `og:description` 是中文可分享标题；分享图不只服务英文品牌；可用浏览器/HTML 检查。

10. **中文社媒落地 UTM / channel_hint 规范**
    - 用户场景：不同小红书/抖音/微信内容导流后需要判断哪类内容带来下载意图。
    - 目标页面/渠道：所有中文 CTA URL。
    - 验收指标：链接规范包含 `utm_source` / `utm_campaign`；Umami properties 或后端日志能区分渠道；周报能按渠道聚合下载点击。

11. **App 内中文新手任务/收藏引导**
    - 用户场景：下载后第一次打开，不知道该拍哪件作品、不知道讲解如何收藏。
    - 目标渠道：App 内 onboarding（若代码/权限可改）。
    - 验收指标：新用户首次识别/收藏率有可观察事件；未接入前先用下载点击作为代理指标。

## 下一步执行建议

优先顺序：先做 P0 的中文 Mona Lisa + Louvre + 首页首屏与下载事件验证，再执行 P1 内容矩阵。这样社媒内容有明确落地页，不会继续把流量导到英文 guide 或仅泛泛导到首页。
