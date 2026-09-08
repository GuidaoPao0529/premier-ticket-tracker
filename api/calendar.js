
const fs = require('fs');
const path = require('path');

function esc(s='') {
  return String(s).replace(/\\/g,'\\\\').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\n/g,'\\n');
}
function pad(n){ return String(n).padStart(2,'0'); }
function ymdhms(d){
  return d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+pad(d.getUTCMinutes())+pad(d.getUTCSeconds())+'Z';
}
function parseDateTimeUK(dateStr, timeStr){
  if(!dateStr || !timeStr || !/^\d{1,2}:\d{2}$/.test(timeStr)) return null;
  const [y,m,d] = dateStr.split('-').map(Number);
  const [hh,mm] = timeStr.split(':').map(Number);
  // Approximate UTC from Europe/London using Intl-derived offset.
  const guess = new Date(Date.UTC(y,m-1,d,hh,mm,0));
  const parts = new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(guess);
  const vals={}; for(const p of parts) vals[p.type]=p.value;
  const localAsUTC = Date.UTC(+vals.year,+vals.month-1,+vals.day,+vals.hour,+vals.minute,0);
  const offsetMs = localAsUTC - guess.getTime();
  return new Date(Date.UTC(y,m-1,d,hh,mm,0) - offsetMs);
}
function parseWindow(s){
  const m = String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
  if(!m) return null;
  return parseDateTimeUK(`${m[1]}-${m[2]}-${m[3]}`,`${m[4]}:${m[5]}`);
}

module.exports = async (req,res) => {
  const file = path.join(process.cwd(),'tickets.json');
  const data = JSON.parse(fs.readFileSync(file,'utf8'));
  const now = new Date();
  const out = [
    'BEGIN:VCALENDAR','VERSION:2.0',
    'PRODID:-//Premier Ticket Tracker//Calendar//ZH-CN',
    'CALSCALE:GREGORIAN','METHOD:PUBLISH',
    'X-WR-CALNAME:Premier Ticket Tracker'
  ];

  for(const x of data){
    if(!x.date) continue;
    const match = parseDateTimeUK(x.date, x.time || '');
    if(match && match.getTime() < now.getTime()-4*3600*1000) continue;

    // Match event
    out.push('BEGIN:VEVENT');
    out.push(`UID:match-${x.home}-${x.away}-${x.date}@premier-ticket-tracker`);
    out.push(`DTSTAMP:${ymdhms(now)}`);
    out.push(`SUMMARY:${esc(`${x.home} vs ${x.away}`)}`);
    if(match){
      out.push(`DTSTART:${ymdhms(match)}`);
      out.push(`DTEND:${ymdhms(new Date(match.getTime()+2*3600*1000))}`);
    }else{
      const ymd = x.date.replace(/-/g,'');
      out.push(`DTSTART;VALUE=DATE:${ymd}`);
    }
    out.push(`DESCRIPTION:${esc(`赛事：${x.competition||''}\n票务状态：${x.ticketStatus||'待官方公布'}\n票务类型：${x.windowType||''}\n说明：${x.windowNote||''}\n官方票务：${x.officialUrl||''}`)}`);
    if(x.officialUrl) out.push(`URL:${esc(x.officialUrl)}`);
    out.push('END:VEVENT');

    // Ticket window open/close events
    for(const [field,label] of [['windowOpen','票务开放'],['windowClose','票务截止']]){
      const t = parseWindow(x[field]);
      if(!t) continue;
      out.push('BEGIN:VEVENT');
      out.push(`UID:${field}-${x.home}-${x.away}-${x.date}@premier-ticket-tracker`);
      out.push(`DTSTAMP:${ymdhms(now)}`);
      out.push(`SUMMARY:${esc(`${label}｜${x.home} vs ${x.away}`)}`);
      out.push(`DTSTART:${ymdhms(t)}`);
      out.push(`DTEND:${ymdhms(new Date(t.getTime()+30*60*1000))}`);
      out.push(`DESCRIPTION:${esc(`${x.windowType||'票务'}：${label}\n状态：${x.ticketStatus||''}\n说明：${x.windowNote||''}\n官方链接：${x.officialUrl||''}`)}`);
      if(x.officialUrl) out.push(`URL:${esc(x.officialUrl)}`);
      out.push('BEGIN:VALARM','TRIGGER:-P1D','ACTION:DISPLAY',`DESCRIPTION:${esc(`${label}｜${x.home} vs ${x.away}`)}`,'END:VALARM');
      out.push('BEGIN:VALARM','TRIGGER:-PT2H','ACTION:DISPLAY',`DESCRIPTION:${esc(`${label}｜${x.home} vs ${x.away}`)}`,'END:VALARM');
      out.push('END:VEVENT');
    }
  }
  out.push('END:VCALENDAR');
  res.setHeader('Content-Type','text/calendar; charset=utf-8');
  res.setHeader('Content-Disposition','inline; filename="premier-ticket-tracker.ics"');
  res.setHeader('Cache-Control','public, max-age=300');
  res.status(200).send(out.join('\r\n')+'\r\n');
};
