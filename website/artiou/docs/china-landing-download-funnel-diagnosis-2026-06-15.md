# Artiou 中国市场 P1：中文落地页与 App 下载漏斗诊断（2026-06-15）

## 结论

当前中文用户的主转化路径应定义为：

1. 小红书 / 抖音 / 微信 / 中文搜索进入 `https://www.artiou.com/zh/` 或城市 guide（当前最完整的是 `https://www.artiou.com/zh/paris-museum-guide/`）。
2. 首屏理解：Artiou 是「拍照识展 + 中文讲解」的博物馆现场工具。
3. 城市 guide 帮用户先完成选馆 / 路线决策，再引导「把 Artiou 带进展厅」。
4. 点击 `#download` 或 App Store 链接，形成下载意图事件。

不建议把这张卡扩展成英文 SEO 工作；修复项只围绕中文首页、中文 guide、中文渠道和下载事件。

## Live evidence

检查命令：

```bash
python - <<'PY'
import requests
from bs4 import BeautifulSoup
for url in ['https://www.artiou.com/zh/','https://www.artiou.com/zh/paris-museum-guide/','https://www.artiou.com/zh/museum-guide/']:
    r=requests.get(url,timeout=20)
    soup=BeautifulSoup(r.text,'html.parser')
    print(url, r.status_code, soup.title.string if soup.title else None)
    print('lang=', soup.html.get('lang') if soup.html else None)
    print('h1=', [h.get_text(' ',strip=True) for h in soup.find_all('h1')][:2])
PY
```

结果摘要：

| URL | live 状态 | 证据 | 诊断 |
| --- | --- | --- | --- |
| `https://www.artiou.com/zh/` | 200 | `lang=zh-Hans`；H1 `把展厅装进你的口袋`；首屏有「拍照识展 · 即时讲解」「下载 App」；App Store 链接可达 `apps.apple.com/cn/...` | 可作为中文下载入口，但首屏还偏品牌概述；需要更直指「中国游客第一次逛海外博物馆、看不懂标签、手机中文讲解」 |
| `https://www.artiou.com/zh/paris-museum-guide/` | 200 | title `巴黎最佳博物馆：第一次参观路线、选馆和实用建议 | Artiou`；H1 `把巴黎的观展日选对`；有「把 Artiou 带进展厅」和下载区 | 当前最明确的中文 guide→download 路径；适合作为小红书/抖音巴黎内容落地页 |
| `https://www.artiou.com/zh/museum-guide/` | 404 | generic museum guide 不存在 | 不应把中文流量导到 generic `/zh/museum-guide/`；应导到 `/zh/` 或具体城市/作品页 |

Browser accessibility snapshot 也确认：中文首页首屏可见「下载 App」，巴黎 guide 首屏可见「先看短名单」「把 Artiou 带进展厅」。

## Umami / 事件命名诊断

源码检查：`website/artiou/static-site.js`

现状：

- 非 guide 下载点击：`download_click`
- guide 页下载点击：`guide_download_click`
- guide 页 CTA：`guide_cta_click`
- guide 内链：`guide_internal_link_click`
- 路线/FAQ 交互：`route_selector_click`
- 每个事件已有基础上下文：`page` / `path` / `page_path` / `language`

判断：

- **能区分中文/英文**：`language` 来自 `<html lang>`，中文 live 页为 `zh-Hans`，英文页为 `en`。
- **能做 guide→download 漏斗**：`guide_download_click` + `page_path` + `source_page_type=guide` 可过滤具体 guide。
- **原缺口**：下载事件只记录 `href`，不明确区分点击的是页面内 `#download` 还是 App Store / Google Play；中文社媒 UTM 也未进入事件属性。

已做小修复：

- `static-site.js` 增加 `utm_source` / `utm_medium` / `utm_campaign` / `utm_content` / `utm_term`，让小红书/抖音/微信链接可在 Umami 事件属性里分渠道。
- 下载事件增加：
  - `download_target`: `download_section` / `app_store` / `play_store` / `unknown`
  - `store_platform`: `none` / `ios` / `android` / `unknown`

这样中文漏斗推荐查询口径为：

- 落地页：`page_path starts with /zh/`
- guide 下载：`event = guide_download_click AND language = zh-Hans`
- 首页下载：`event = download_click AND page_path = /zh/`
- 真实商店意图：`download_target = app_store`（iOS）而不是只看 `#download`
- 渠道：`utm_source in (xiaohongshu, douyin, wechat, baidu, ... )`

## 可执行修复任务（中文市场）

### P0 — 文案 / CTA

1. **中文首页首屏重写为中国游客场景**
   - 页面：`/zh/`
   - 建议 H1/副标题方向：`第一次逛海外博物馆，也能听懂每件作品`；副标题强调「拍照识展、中文讲解、不用租讲解器」。
   - 验收：首屏同时出现「中国游客 / 海外博物馆 / 中文讲解 / 拍照识展 / App Store」语义；顶部 CTA 直接可点。

2. **首页顶部 CTA 分成两级**
   - 主 CTA：`去 App Store 下载`
   - 次 CTA：`先看巴黎博物馆路线`
   - 验收：点击主 CTA 触发 `download_click` + `download_target=app_store`；次 CTA 导到 `/zh/paris-museum-guide/`。

3. **巴黎 guide 首屏 CTA 更口语化**
   - 页面：`/zh/paris-museum-guide/`
   - 将「把 Artiou 带进展厅」补成更具体的「到卢浮宫/奥赛后，拍照听中文讲解」。
   - 验收：首屏 CTA 点击触发 `guide_download_click`，并带 `language=zh-Hans`、`page_path=/zh/paris-museum-guide/`。

### P1 — 页面内链 / 分享

4. **不要导向 `/zh/museum-guide/`**
   - 该 URL live 为 404。
   - 所有中文 generic museum guide 链接应改为 `/zh/`、`/zh/paris-museum-guide/` 或具体城市 guide。

5. **中文 guide 增加「转发给同行人」段落**
   - 页面：先做 `/zh/paris-museum-guide/`。
   - 文案方向：`把这条路线发给同行的人：一天别排太满，现场看不懂就用 Artiou 拍照听中文讲解。`
   - 验收：中文 OG title/description 可分享；微信/社群预览不是英文品牌语。

6. **中文社媒 UTM 规范**
   - 小红书：`?utm_source=xiaohongshu&utm_medium=social&utm_campaign=paris_museum_beginner`
   - 抖音：`?utm_source=douyin&utm_medium=video&utm_campaign=paris_museum_beginner`
   - 微信：`?utm_source=wechat&utm_medium=share&utm_campaign=paris_museum_beginner`
   - 验收：Umami 事件属性能按 `utm_source` 聚合下载点击。

### P1 — 新中文页（不是英文 SEO）

7. **中文蒙娜丽莎页**：`/zh/mona-lisa-guide/`
   - 场景：人在卢浮宫，想知道蒙娜丽莎在哪、怎么挤、怎么看懂。
   - CTA：`到了画前，打开 Artiou 拍照听中文讲解`。

8. **中文卢浮宫首次参观页**：`/zh/louvre-first-time-visitor-guide/`
   - 场景：第一次去卢浮宫，只要 2–3 小时轻路线。
   - 内链：巴黎 guide ↔ 蒙娜丽莎页 ↔ 卢浮宫页。

## 本次代码改动

文件：`website/artiou/static-site.js`

- 给所有 Umami 事件补充 UTM 属性。
- 给下载点击事件补充 `download_target` 和 `store_platform`。
- 不创建任何英文 SEO 工作。

验证：

```bash
node --check website/artiou/static-site.js
python - <<'PY'
from pathlib import Path
s=Path('website/artiou/static-site.js').read_text()
for needle in ['utm_source','download_target','store_platform','guide_download_click','language: getLanguage()']:
    assert needle in s, needle
print('static-site tracking fields present')
PY
```

本地浏览器事件验证（`python3 -m http.server` serving `website/artiou`）：

- 访问 `/zh/paris-museum-guide/?utm_source=xiaohongshu&utm_medium=social&utm_campaign=paris_museum_beginner`，mock `window.umami.track` 后点击首屏 `#download`：得到 `guide_download_click`，properties 包含 `language=zh-Hans`、`page_path=/zh/paris-museum-guide/`、`download_target=download_section`、`utm_source=xiaohongshu`。
- 点击底部 `link-app-store`：得到 `guide_download_click`，properties 包含 `download_target=app_store`、`store_platform=ios`、同一组 UTM。
