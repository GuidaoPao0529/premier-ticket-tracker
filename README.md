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
