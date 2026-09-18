const fs=require('fs'), path=require('path');
function esc(s=''){return String(s).replace(/\\/g,'\\\\').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\n/g,'\\n');}
function pad(n){return String(n).padStart(2,'0');}
const TEAM_CN={'Arsenal':'阿森纳','Chelsea':'切尔西','Manchester United':'曼联','Manchester City':'曼城','Leeds United':'利兹联','Everton':'埃弗顿','Lille':'里尔','Hull City':'赫尔城','Brighton & Hove Albion':'布莱顿','Brighton':'布莱顿','AFC Bournemouth':'伯恩茅斯','Bournemouth':'伯恩茅斯','Paris Saint-Germain':'巴黎圣日耳曼','PSG':'巴黎圣日耳曼','AEK Athens':'雅典AEK','Napoli':'那不勒斯','Sporting CP':'葡萄牙体育','Tottenham Hotspur':'热刺','Tottenham':'热刺','AS Roma':'罗马','RB Leipzig':'RB莱比锡','Bayern Munich':'拜仁慕尼黑','Real Madrid':'皇马','Borussia Dortmund':'多特蒙德','Sabah':'萨巴','Benfica':'本菲卡','Ajax':'阿贾克斯','Barcelona':'巴塞罗那','Pafos':'帕福斯','Norwich City':'诺维奇','Sunderland':'桑德兰','Ipswich Town':'伊普斯维奇','Ipswich':'伊普斯维奇','Coventry City':'考文垂'};
const cnTeam=n=>TEAM_CN[n]||n;

function ukToBeijing(dateStr,timeStr){
  if(!dateStr||!timeStr||!/^\d{1,2}:\d{2}$/.test(timeStr)) return null;
  const [y,m,d]=dateStr.split('-').map(Number), [hh,mm]=timeStr.split(':').map(Number);
  let guess=new Date(Date.UTC(y,m-1,d,hh,mm,0));
  for(let i=0;i<2;i++){
    const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(guess);
    const v={}; for(const p of parts)v[p.type]=p.value;
    const represented=Date.UTC(+v.year,+v.month-1,+v.day,+v.hour,+v.minute,0);
    const wanted=Date.UTC(y,m-1,d,hh,mm,0);
    guess=new Date(guess.getTime()+(wanted-represented));
  }
  return new Date(guess.getTime()+8*3600*1000);
}
function fmtBJ(d){return d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+pad(d.getUTCMinutes())+pad(d.getUTCSeconds());}
function parseWindow(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
  return m?ukToBeijing(`${m[1]}-${m[2]}-${m[3]}`,`${m[4]}:${m[5]}`):null;
}
function todayBJ(){
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const v={}; for(const p of parts)v[p.type]=p.value;
  return `${v.year}-${v.month}-${v.day}`;
}

module.exports=async(req,res)=>{
  const data=JSON.parse(fs.readFileSync(path.join(process.cwd(),'tickets.json'),'utf8'));
  const now=new Date(), today=todayBJ();
  const out=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Premier Ticket Tracker//Beijing Calendar//ZH-CN','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:四队票务｜北京时间','X-WR-TIMEZONE:Asia/Shanghai','REFRESH-INTERVAL;VALUE=DURATION:PT1H','X-PUBLISHED-TTL:PT1H'];

  for(const x of data){
    if(!x.date||x.date<today||x.matchStatus==='FINISHED') continue;
    const match=ukToBeijing(x.date,x.time||'');

    out.push('BEGIN:VEVENT');
    out.push(`UID:match-${x.home}-${x.away}-${x.date}-v3@premier-ticket-tracker`);
    out.push(`DTSTAMP:${now.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z')}`);
    const title=match?`【比赛】${cnTeam(x.home)}-${cnTeam(x.away)} ${pad(match.getUTCMonth()+1)}/${pad(match.getUTCDate())} ${pad(match.getUTCHours())}:${pad(match.getUTCMinutes())}`:`【比赛】${cnTeam(x.home)}-${cnTeam(x.away)} 时间待定`;
    out.push(`SUMMARY:${esc(title)}`);
    if(match){out.push(`DTSTART;TZID=Asia/Shanghai:${fmtBJ(match)}`);out.push('DURATION:PT0S');}
    else out.push(`DTSTART;VALUE=DATE:${x.date.replace(/-/g,'')}`);
    out.push(`DESCRIPTION:${esc(`赛事：${x.competition||''}\n票务状态：${x.ticketStatus||'待官方公布'}\n会员资格：${x.membershipTier||''}\n说明：${x.windowNote||''}\n官方票务：${x.officialUrl||''}`)}`);
    if(x.officialUrl) out.push(`URL:${esc(x.officialUrl)}`);
    if(match){
      out.push('BEGIN:VALARM','TRIGGER:-P1D','ACTION:DISPLAY',`DESCRIPTION:${esc(`【比赛】明天 ${cnTeam(x.home)}-${cnTeam(x.away)}`)}`,'END:VALARM');
      out.push('BEGIN:VALARM','TRIGGER:-PT2H','ACTION:DISPLAY',`DESCRIPTION:${esc(`【比赛】2小时后 ${cnTeam(x.home)}-${cnTeam(x.away)}`)}`,'END:VALARM');
    }
    out.push('END:VEVENT');

    for(const [field,label] of [['windowOpen','开放'],['windowClose','截止']]){
      const t=parseWindow(x[field]); if(!t) continue;
      let tag='票务', wt=String(x.windowType||'').toLowerCase();
      if(wt.includes('ballot'))tag='Ballot'; else if(wt.includes('application'))tag='申请'; else if(wt.includes('member'))tag='会员购票'; else if(wt.includes('exchange')||wt.includes('resale'))tag='Exchange';
      out.push('BEGIN:VEVENT');
      out.push(`UID:${field}-${x.home}-${x.away}-${x.date}-v3@premier-ticket-tracker`);
      out.push(`DTSTAMP:${now.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z')}`);
      out.push(`SUMMARY:${esc(`【${tag}】${cnTeam(x.home)}-${cnTeam(x.away)} ${label}`)}`);
      out.push(`DTSTART;TZID=Asia/Shanghai:${fmtBJ(t)}`);
      out.push('DURATION:PT0S');
      out.push(`DESCRIPTION:${esc(`${x.windowType||'票务'}：${label}\n状态：${x.ticketStatus||''}\n会员资格：${x.membershipTier||''}\n说明：${x.windowNote||''}\n官方链接：${x.officialUrl||''}`)}`);
      if(x.officialUrl)out.push(`URL:${esc(x.officialUrl)}`);
      out.push('BEGIN:VALARM','TRIGGER:-P1D','ACTION:DISPLAY',`DESCRIPTION:${esc(`【${tag}】${cnTeam(x.home)}-${cnTeam(x.away)} ${label}`)}`,'END:VALARM');
      out.push('BEGIN:VALARM','TRIGGER:-PT2H','ACTION:DISPLAY',`DESCRIPTION:${esc(`【${tag}】${cnTeam(x.home)}-${cnTeam(x.away)} ${label}`)}`,'END:VALARM');
      out.push('END:VEVENT');
    }
  }

  out.push('END:VCALENDAR');
  res.setHeader('Content-Type','text/calendar; charset=utf-8');
  res.setHeader('Content-Disposition','inline; filename="iphone-cn.ics"');
  res.setHeader('Cache-Control','no-store, max-age=0');
  res.status(200).send(out.join('\r\n')+'\r\n');
};
