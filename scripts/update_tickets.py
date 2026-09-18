#!/usr/bin/env python3
import json,re,ssl,urllib.request,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"tickets.json"; AUDIT=ROOT/"last-audit.json"
UA="Mozilla/5.0 PremierTicketTracker/2.1"; CTX=ssl.create_default_context()
HEALTH=[
("Arsenal","https://www.arsenal.com/tickets/men"),
("Arsenal","https://help.arsenal.com/support/solutions/articles/101000578825-home-tickets"),
("Chelsea","https://www.chelseafc.com/en/news/article/ticket-application-window-information-for-members"),
("Manchester City","https://www.mancity.com/news/mens/ticket-news")]
def fetch(u):
 r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
 with urllib.request.urlopen(r,timeout=25,context=CTX) as x:return x.read().decode("utf-8","replace")
def plain(h):
 h=re.sub(r"<script\\b[^>]*>.*?</script>"," ",h,flags=re.I|re.S); h=re.sub(r"<style\\b[^>]*>.*?</style>"," ",h,flags=re.I|re.S)
 h=re.sub(r"<[^>]+>"," ",h); return re.sub(r"\\s+"," ",h.replace("&amp;","&").replace("&nbsp;"," ")).strip()
def slug(s): return re.sub(r"[^a-z0-9]+","-",str(s).lower().replace("&","and")).strip("-")
def city_url(row):
 d=str(row.get("date",""))[:10]
 if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}",d):return None
 y,m,day=d.split("-"); mon={"01":"jan","02":"feb","03":"mar","04":"apr","05":"may","06":"jun","07":"jul","08":"aug","09":"sep","10":"oct","11":"nov","12":"dec"}
 opp={"PSG":"psg","Paris Saint-Germain":"psg","AEK Athens":"aek-athens","Sporting CP":"sporting-cp"}.get(row.get("away"),slug(row.get("away","")))
 return f"https://www.mancity.com/tickets/mens/man-city-v-{opp}-{int(day)}-{mon[m]}-{y}"
def city_status(t):
 low=t.lower(); a=low.find("tickets match ticket")
 if a<0:return None,None
 ends=[x for x in [low.find("bars match ticket",a+1),low.find("hospitality match ticket",a+1)] if x>=0]
 b=min(ends) if ends else min(len(t),a+1000); seg=t[a:b]; sl=seg.lower()
 if "notify me" in sl or "sign up to be notified" in sl:return "COMING SOON",seg[:700]
 if "buy now" in sl and "on sale" in sl:return "BUY NOW",seg[:700]
 return None,seg[:700]
def main():
 rows=json.loads(DATA.read_text(encoding="utf-8"))
 audit={"checkedAt":datetime.now(timezone.utc).isoformat(),"mode":"V2.1 SAFE","sources":[],"evidence":[],"changes":[],"skipped":[]}
 for club,url in HEALTH:
  try:
   h=fetch(url); audit["sources"].append({"club":club,"url":url,"ok":True,"sha256":hashlib.sha256(h.encode()).hexdigest()[:16]})
  except Exception as e:audit["sources"].append({"club":club,"url":url,"ok":False,"error":str(e)[:250]})
 for row in rows:
  row.setdefault("matchStatus","UPCOMING"); row.setdefault("windowOpen","待官方公布"); row.setdefault("windowClose","待官方公布"); row.setdefault("resultTime","待官方公布")
  if row.get("home")=="Arsenal":row["membershipTier"]="Red Member"
  if row.get("home")=="Chelsea":row["membershipTier"]="CFC Blue"
  if row.get("home")!="Manchester City":continue
  url=city_url(row)
  if not url:continue
  try:
   t=plain(fetch(url)); tl=t.lower(); away=str(row.get("away",""))
   aliases={"PSG":["psg","paris saint-germain","paris saint germain"],"Sporting CP":["sporting"],"AEK Athens":["aek athens"]}
   ok=away.lower() in tl or any(x in tl for x in aliases.get(away,[]))
   if "manchester city" not in tl or not ok:
    audit["skipped"].append({"match":f"Manchester City v {away}","url":url,"reason":"fixture identity not confirmed"});continue
   st,ev=city_status(t); audit["evidence"].append({"match":f"Manchester City v {away}","url":url,"matchTicketStatus":st,"excerpt":ev})
   if st and st!=row.get("ticketStatus"):
    old=row.get("ticketStatus");row["ticketStatus"]=st
    audit["changes"].append({"match":f"Manchester City v {away}","field":"ticketStatus","old":old,"new":st,"url":url})
  except Exception as e:audit["skipped"].append({"match":f"Manchester City v {row.get('away')}","url":url,"reason":str(e)[:200]})
 DATA.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"mode":"V2.1 SAFE","sources":len(audit["sources"]),"evidence":len(audit["evidence"]),"changes":len(audit["changes"]),"skipped":len(audit["skipped"])},ensure_ascii=False))
if __name__=="__main__":main()
