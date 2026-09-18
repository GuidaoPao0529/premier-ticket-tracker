#!/usr/bin/env python3
import json,re,ssl,urllib.request,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"tickets.json"; AUDIT=ROOT/"last-audit.json"
SOURCES=[
("Arsenal","https://www.arsenal.com/tickets/men"),
("Arsenal","https://help.arsenal.com/support/solutions/articles/101000578825-home-tickets"),
("Chelsea","https://www.chelseafc.com/en/tickets"),
("Manchester United","https://www.manutd.com/en/tickets-and-hospitality"),
("Manchester City","https://www.mancity.com/tickets/mens/all/home")]
def fetch(u):
 r=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0 PremierTicketTracker/2.0","Accept":"text/html"})
 with urllib.request.urlopen(r,timeout=25,context=ssl.create_default_context()) as x:return x.read().decode("utf-8","replace")
def text(h):
 h=re.sub(r"<script\\b[^>]*>.*?</script>"," ",h,flags=re.I|re.S); h=re.sub(r"<style\\b[^>]*>.*?</style>"," ",h,flags=re.I|re.S)
 return re.sub(r"\\s+"," ",re.sub(r"<[^>]+>"," ",h)).lower()
def aliases(n):
 return {"Manchester United":["manchester united","man utd"],"Manchester City":["manchester city","man city"],"Brighton & Hove Albion":["brighton"],"AFC Bournemouth":["bournemouth"],"Tottenham Hotspur":["tottenham","spurs"],"Paris Saint-Germain":["paris saint-germain","psg"]}.get(n,[str(n).lower()])
def main():
 rows=json.loads(DATA.read_text(encoding="utf-8")); pages={}; audit={"checkedAt":datetime.now(timezone.utc).isoformat(),"sources":[],"changes":[]}
 for club,url in SOURCES:
  try:
   h=fetch(url); pages.setdefault(club,[]).append(text(h)); audit["sources"].append({"club":club,"url":url,"ok":True,"sha256":hashlib.sha256(h.encode()).hexdigest()[:16]})
  except Exception as e:audit["sources"].append({"club":club,"url":url,"ok":False,"error":str(e)[:250]})
 for row in rows:
  row.setdefault("matchStatus","UPCOMING"); row.setdefault("windowOpen","待官方公布"); row.setdefault("windowClose","待官方公布"); row.setdefault("resultTime","待官方公布")
  if row.get("home")=="Arsenal":row["membershipTier"]="Red Member"
  if row.get("home")=="Chelsea":row["membershipTier"]="CFC Blue"
  for p in pages.get(row.get("home"),[]):
   if not any(a in p for a in aliases(row.get("away",""))):continue
   new=None
   if "buy now" in p or "buy tickets" in p:new="BUY NOW"
   elif "coming soon" in p:new="COMING SOON"
   if new and row.get("ticketStatus") in ("WAITING FOR TICKET INFO","COMING SOON") and new!=row.get("ticketStatus"):
    old=row.get("ticketStatus"); row["ticketStatus"]=new; audit["changes"].append({"match":f"{row.get('home')} v {row.get('away')}","field":"ticketStatus","old":old,"new":new})
   break
 DATA.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
 AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
 print(json.dumps({"sources":len(audit["sources"]),"changes":len(audit["changes"])},ensure_ascii=False))
if __name__=="__main__":main()
