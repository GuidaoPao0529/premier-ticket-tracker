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
