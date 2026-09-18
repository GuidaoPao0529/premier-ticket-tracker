#!/usr/bin/env python3
import json,re,ssl,urllib.request,hashlib
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"tickets.json"; AUDIT=ROOT/"last-audit.json"
UA="Mozilla/5.0 PremierTicketTracker/2.2"
CTX=ssl.create_default_context()

HEALTH=[
 ("Arsenal","https://www.arsenal.com/tickets/men"),
 ("Arsenal","https://help.arsenal.com/support/solutions/articles/101000578825-home-tickets"),
 ("Chelsea","https://www.chelseafc.com/en/news/article/ticket-application-window-information-for-members"),
 ("Manchester City","https://www.mancity.com/news/mens/ticket-news"),
]

def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
 with urllib.request.urlopen(req,timeout=25,context=CTX) as r:
  return r.read().decode("utf-8","replace")

def plain(h):
 h=re.sub(r"<script\b[^>]*>.*?</script>"," ",h,flags=re.I|re.S)
 h=re.sub(r"<style\b[^>]*>.*?</style>"," ",h,flags=re.I|re.S)
 h=re.sub(r"<[^>]+>"," ",h)
 h=h.replace("&amp;","&").replace("&nbsp;"," ").replace("&#x27;","'")
 return re.sub(r"\s+"," ",h).strip()

def slug(s):
 return re.sub(r"[^a-z0-9]+","-",str(s).lower().replace("&","and")).strip("-")

MONTH={"01":"jan","02":"feb","03":"mar","04":"apr","05":"may","06":"jun",
       "07":"jul","08":"aug","09":"sep","10":"oct","11":"nov","12":"dec"}

# Official City display names differ from our tickets.json opponent names.
DISPLAY_ALIAS={
 "AFC Bournemouth":"bournemouth",
 "Brighton & Hove Albion":"brighton",
 "Tottenham Hotspur":"spurs",
 "Nottingham Forest":"n-forest",
 "Sporting CP":"sporting",
 "Manchester United":"man-united",
 "Crystal Palace":"c-palace",
 "Paris Saint-Germain":"psg",
 "PSG":"psg",
}

def city_candidates(row):
 d=str(row.get("date",""))[:10]
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",d): return []
 y,m,day=d.split("-"); dd=str(int(day)); away=str(row.get("away",""))
 # First try the official short display name used by City's fixture lists.
 names=[]
 if away in DISPLAY_ALIAS: names.append(DISPLAY_ALIAS[away])
 names.append(slug(away))
 # Common safe alternatives; all are still verified by page identity before use.
 if away=="Tottenham Hotspur": names += ["tottenham-hotspur"]
 if away=="Nottingham Forest": names += ["nottingham-forest"]
 if away=="Manchester United": names += ["manchester-united"]
 if away=="Crystal Palace": names += ["crystal-palace"]
 if away=="Brighton & Hove Albion": names += ["brighton-and-hove-albion"]
 seen=[]
 for n in names:
  u=f"https://www.mancity.com/tickets/mens/man-city-v-{n}-{dd}-{MONTH[m]}-{y}"
  if u not in seen: seen.append(u)
 return seen

def opponent_present(text,away):
 tl=text.lower(); a=away.lower()
 aliases={
  "AFC Bournemouth":["bournemouth"],
  "Brighton & Hove Albion":["brighton"],
  "Tottenham Hotspur":["spurs","tottenham"],
  "Nottingham Forest":["n forest","nottingham forest"],
  "Sporting CP":["sporting"],
  "Manchester United":["man united","manchester united"],
  "Crystal Palace":["c palace","crystal palace"],
  "PSG":["psg","paris saint-germain","paris saint germain"],
 }
 return a in tl or any(x in tl for x in aliases.get(away,[]))

def city_status(text):
 low=text.lower(); a=low.find("tickets match ticket")
 if a<0:return None,None
 ends=[x for x in (low.find("bars match ticket",a+1),low.find("hospitality match ticket",a+1)) if x>=0]
 b=min(ends) if ends else min(len(text),a+1100)
 seg=text[a:b]; sl=seg.lower()
 # Notify/off-sale beats sale phrases inside the same Match Ticket block.
 if ("notify me" in sl or "sign up to be notified" in sl or
     "first release of tickets is now off sale" in sl):
  return "COMING SOON",seg[:800]
 # City uses both BUY NOW and BUY TICKETS for general admission.
 if ("buy now" in sl or "buy tickets" in sl) and (
     "tickets on sale" in sl or "on sale to" in sl):
  return "BUY NOW",seg[:800]
 return None,seg[:800]

def resolve_city_fixture(row,audit):
 match=f"Manchester City v {row.get('away')}"
 errors=[]
 for url in city_candidates(row):
  try:
   text=plain(fetch(url))
   if "manchester city" in text.lower() and opponent_present(text,str(row.get("away",""))):
    return url,text
   errors.append({"url":url,"reason":"fixture identity not confirmed"})
  except Exception as e:
   errors.append({"url":url,"reason":str(e)[:180]})
 audit["skipped"].append({"match":match,"reason":"no verified fixture page","attempts":errors})
 return None,None


MONTHNUM={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}

def normalize_uk_datetime(raw,year=2026):
 # Converts Chelsea/Arsenal official English wording to stable UK-local ISO-like storage.
 # DST label is calculated by zoneinfo, not guessed.
 from datetime import datetime
 from zoneinfo import ZoneInfo
 x=re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+","",raw.strip(),flags=re.I)
 x=x.replace(" at "," ")
 m=re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)",x,re.I)
 if not m:return None
 day=int(m.group(1)); mon=MONTHNUM.get(m.group(2).lower())
 if not mon:return None
 hour=int(m.group(3)); minute=int(m.group(4) or 0); ap=m.group(5).lower()
 if ap=="pm" and hour!=12:hour+=12
 if ap=="am" and hour==12:hour=0
 dt=datetime(year,mon,day,hour,minute,tzinfo=ZoneInfo("Europe/London"))
 return dt.strftime("%Y-%m-%d %H:%M ")+dt.tzname()

def search_official_news(query_url):
 # Fetch an explicitly supplied official article URL only; no guessed status writes.
 try:
  return plain(fetch(query_url))
 except Exception:
  return None

def chelsea_application_from_text(text):
 if not text:return None
 # Supports: "Ticket application window opens – Monday 7 September 12pm"
 op=re.search(r"Ticket application window opens?\s*[-–—:]\s*([^.;]+?)(?=Ticket application window closes?|Accessible|$)",text,re.I)
 cl=re.search(r"Ticket application window closes?\s*[-–—:]\s*([^.;]+?)(?=The ticket application|Accessible|Supporters|$)",text,re.I)
 tiers=bool(re.search(r"CFC Blue",text,re.I))
 if not (op and cl and tiers):return None
 return {"openText":op.group(1).strip(),"closeText":cl.group(1).strip(),"cfcBlue":True}

def arsenal_ballot_from_text(text):
 if not text:return None
 # Evidence-only unless the article explicitly contains both opening and closing wording.
 op=re.search(r"(?:Red Member ballot|Red ballot|ballot)[^.;]{0,120}?(?:opens?|open)\s*[-–—:]?\s*([^.;]+)",text,re.I)
 cl=re.search(r"(?:Red Member ballot|Red ballot|ballot)[^.;]{0,120}?(?:closes?|close)\s*[-–—:]?\s*([^.;]+)",text,re.I)
 if not (op and cl):return None
 return {"openText":op.group(1).strip(),"closeText":cl.group(1).strip(),"tier":"Red Member"}

def main():
 rows=json.loads(DATA.read_text(encoding="utf-8"))
 audit={"checkedAt":datetime.now(timezone.utc).isoformat(),"mode":"V2.3 CALENDAR SAFE",
        "sources":[],"evidence":[],"changes":[],"skipped":[]}
 for club,url in HEALTH:
  try:
   h=fetch(url); audit["sources"].append({"club":club,"url":url,"ok":True,
    "sha256":hashlib.sha256(h.encode()).hexdigest()[:16]})
  except Exception as e:
   audit["sources"].append({"club":club,"url":url,"ok":False,"error":str(e)[:250]})

 for row in rows:
  row.setdefault("matchStatus","UPCOMING")
  row.setdefault("windowOpen","待官方公布"); row.setdefault("windowClose","待官方公布"); row.setdefault("resultTime","待官方公布")
  if row.get("home")=="Arsenal": row["membershipTier"]="Red Member"
  if row.get("home")=="Chelsea": row["membershipTier"]="CFC Blue"
  # Finished matches are deliberately not queried or modified.
  if row.get("matchStatus")=="FINISHED": continue
  if row.get("home")!="Manchester City": continue

  url,text=resolve_city_fixture(row,audit)
  if not url: continue
  st,ev=city_status(text)
  audit["evidence"].append({"match":f"Manchester City v {row.get('away')}",
    "url":url,"matchTicketStatus":st,"excerpt":ev})
  if st and st!=row.get("ticketStatus"):
   old=row.get("ticketStatus"); row["ticketStatus"]=st
   audit["changes"].append({"match":f"Manchester City v {row.get('away')}",
    "field":"ticketStatus","old":old,"new":st,"url":url})


 # V2.2 official, match-level seed articles already present in known data / current official season.
 # Chelsea: exact official article pages. We write only when CFC Blue is explicitly named.
 chelsea_articles={
  "Hull City":"https://www.chelseafc.com/en/news/article/premier-league-ticket-news-hull-at-home",
   "AFC Bournemouth":"https://www.chelseafc.com/en/news/article/premier-league-ticket-news-bournemouth-at-home-2026-27",
  "Tottenham Hotspur":"https://www.chelseafc.com/en/news/article/premier-league-ticket-news-tottenham-at-home-2026-27",
 }
 for row in rows:
  if row.get("matchStatus")=="FINISHED":continue
  if row.get("home")=="Chelsea" and row.get("away") in chelsea_articles:
   url=chelsea_articles[row["away"]]; txt=search_official_news(url); ev=chelsea_application_from_text(txt)
   audit["evidence"].append({"match":f"Chelsea v {row.get('away')}","type":"Application","url":url,"parsed":ev})
   if ev:
    # Store exact official wording, avoiding timezone/date-parser mistakes in this first safe release.
    open_norm=normalize_uk_datetime(ev["openText"],2026)
    close_norm=normalize_uk_datetime(ev["closeText"],2026)
    if not (open_norm and close_norm):
     audit["skipped"].append({"match":f"Chelsea v {row.get('away')}","reason":"application time could not be normalized","url":url})
     continue
    for field,val in [("windowType","Application"),("windowOpen",open_norm),("windowClose",close_norm),("membershipTier","CFC Blue")]:
     if row.get(field)!=val:
      old=row.get(field);row[field]=val
      audit["changes"].append({"match":f"Chelsea v {row.get('away')}","field":field,"old":old,"new":val,"url":url})
 # Arsenal UCL eligibility evidence: exact embargo dates from Arsenal Help.
 arsenal_embargo={
  "Real Madrid":"2026-08-26",
  "Lille":"2026-08-26",
  "Sabah":"2026-08-26",
  "Borussia Dortmund":"2026-06-24",
 }
 for row in rows:
  if row.get("matchStatus")=="FINISHED" or row.get("home")!="Arsenal":continue
  row["membershipTier"]="Red Member"
  if row.get("away") in arsenal_embargo:
   audit["evidence"].append({"match":f"Arsenal v {row.get('away')}","type":"UCL membership embargo",
    "membershipTier":"Red Member","membershipMustBePurchasedOnOrBefore":arsenal_embargo[row["away"]],
    "source":"https://help.arsenal.com/support/solutions/articles/101000593989-ticketing-embargo-champions-league-group-phase"})

 # Arsenal: current release remains evidence-only. Generic help pages confirm process but are NOT enough
 # to invent a specific fixture's dates. Exact match pages/ECAL will be added only when discoverable.
 for row in rows:
  if row.get("matchStatus")=="FINISHED" or row.get("home")!="Arsenal":continue
  row["membershipTier"]="Red Member"

 DATA.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"mode":"V2.3 CALENDAR SAFE","sources":len(audit["sources"]),
  "evidence":len(audit["evidence"]),"changes":len(audit["changes"]),
  "skipped":len(audit["skipped"])},ensure_ascii=False))

if __name__=="__main__": main()
