# Premier Ticket Tracker

四队主场票务追踪 + iPhone 可订阅日历。

## Production
- Website: `https://premier-ticket-tracker.vercel.app/`
- Calendar HTTP: `https://premier-ticket-tracker.vercel.app/premier-ticket-tracker.ics`
- iPhone webcal: `webcal://premier-ticket-tracker.vercel.app/premier-ticket-tracker.ics`

## Auto update
`.github/workflows/update-ticket-data.yml` 每小时运行 `scripts/update_tickets.py`。
脚本只读取俱乐部官方来源，采用保守策略：读不到或无法明确确认时不修改现有数据，也不推测精确 Ballot/Application 时间。

详细步骤见 `部署说明.txt`。

## Membership profile
- Arsenal: Red Member
- Chelsea: CFC Blue

## Calendar timezone
所有比赛、Ballot/Application/Member Sale 时间均从英国当地时间自动换算为北京时间（Asia/Shanghai），并自动处理英国夏令时/冬令时差异。

## Weekly fixtures in iPhone Calendar
日历同时包含 Arsenal、Chelsea、Manchester United、Manchester City 的网站内未开赛主场比赛。
比赛事件标题直接显示北京时间和对阵，例如：
`⚽ 10/14 03:00｜Manchester City vs PSG`
比赛默认提前 1 天及 2 小时提醒。

## iPhone 日历标题格式
- `【比赛】阿森纳-切尔西 09/06 23:30`
- `【Ballot】阿森纳-里尔 开`
- `【申请】切尔西-伯恩茅斯 截止`
- `【会员购票】曼城-巴黎圣日耳曼 开`
- `【Exchange】阿森纳-埃弗顿 开`

队名优先中文显示，所有时间继续使用北京时间。

## V2 iPhone subscription
Use the new feed to bypass old iOS Calendar cache:

- HTTPS: `https://premier-ticket-tracker.vercel.app/iphone-cn.ics`
- webcal: `webcal://premier-ticket-tracker.vercel.app/iphone-cn.ics`
- Calendar name: `四队票务｜北京时间`

## UCL update
已补充四队已由俱乐部官方确认的 2026/27 欧冠主场 league phase 赛程，共新增 10 条缺失记录（若原数据已存在则不重复）。
iPhone 日历会随 `tickets.json` 自动包含这些欧冠主场比赛。

## Match event display
比赛事件只显示开球时间，不再写入比赛结束时间；Ballot/Application 等票务事件仍保留各自的事件时段。

## 2026/27 UCL clean audit
This build removes all previously imported UCL rows and re-adds only fixtures explicitly verified as 2026/27 from official club pages.
Chelsea men's UCL fixtures are intentionally omitted until a current-season official page is verified, preventing 2025/26 data from leaking into the 2026/27 calendar.
