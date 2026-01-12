# RIVET Pro v2 - One Command Build

## RUN THIS IN YOUR TERMINAL:

```bash
claude --dangerously-skip-permissions -p '
## AUTONOMOUS BUILD: RIVET Pro v2

Execute all steps without confirmation. Do not stop. Do not ask questions. Build everything.

### STEP 1: Create project structure
```bash
cd ~
rm -rf rivet-pro-v2 2>/dev/null
mkdir -p rivet-pro-v2/{prompts,evals,test_data/test_images,sidecar,n8n/workflows,scripts,docs}
cd rivet-pro-v2
git init
```

### STEP 2: Create all files

Create these files with exact content:

**CLAUDE.md:**
```
# RIVET Pro v2
## RULES
- NEVER modify STABLE files
- Run evals after AI changes
- Prompts are YAML in /prompts
## Commands
docker-compose up -d
./scripts/run_evals.sh
```

**.gitignore:**
```
.env
__pycache__/
venv/
n8n_data/
eval_results.json
```

**.env.example:**
```
GEMINI_API_KEY=
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TAVILY_API_KEY=
DATABASE_URL=
N8N_ENCRYPTION_KEY=
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=changeme
```

**evals/thresholds.yaml:**
```yaml
ocr:
  manufacturer_accuracy:
    minimum: 0.85
    target: 0.95
  model_accuracy:
    minimum: 0.80
    target: 0.90
  latency_p95_ms:
    minimum: 5000
    target: 3000
retrieval:
  manual_found_rate:
    minimum: 0.60
    target: 0.80
e2e:
  success_rate:
    minimum: 0.70
    target: 0.85
```

**test_data/ocr_test_cases.json:**
```json
{"version":"1.0","test_cases":[{"id":"ocr_001","image_path":"test_data/test_images/test1.jpg","expected":{"manufacturer":"Siemens","model":"6SE6440","equipment_type":"VFD"}},{"id":"ocr_002","image_path":"test_data/test_images/test2.jpg","expected":{"manufacturer":"Allen-Bradley","model":"PowerFlex","equipment_type":"VFD"}},{"id":"ocr_003","image_path":"test_data/test_images/test3.jpg","expected":{"manufacturer":"ABB","model":null,"equipment_type":"motor"}}]}
```

**prompts/ocr_extraction.yaml:**
```yaml
name: ocr_extraction
version: "1.0.0"
model: gemini-1.5-flash
temperature: 0.1
user_prompt: |
  Analyze this equipment nameplate. Return ONLY JSON:
  {"manufacturer":"string or null","model":"string or null","serial":"string or null","equipment_type":"VFD|motor|PLC|HMI|pump|other","error_codes":["array"],"confidence":0-100}
  Common manufacturers: Siemens, ABB, Allen-Bradley, Schneider, Danfoss, Yaskawa, Rockwell
```

**prompts/troubleshooting.yaml:**
```yaml
name: troubleshooting
version: "1.0.0"
model: claude-3-5-sonnet-20241022
temperature: 0.3
user_prompt: |
  Equipment: {manufacturer} {model}
  Issue: {fault_description}
  Provide: 1.DIAGNOSIS 2.SAFETY WARNINGS 3.STEPS 4.WHEN TO ESCALATE
```

**sidecar/requirements.txt:**
```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
python-dotenv==1.0.0
pyyaml==6.0.1
```

**sidecar/Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**sidecar/main.py:**
```python
import os,json,re,httpx,yaml
from pathlib import Path
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from typing import Optional,List
from dotenv import load_dotenv
load_dotenv()
app=FastAPI(title="RIVET Pro",version="2.0.0")

class OCRRequest(BaseModel):
    image_base64:str
class OCRResponse(BaseModel):
    manufacturer:Optional[str]=None
    model:Optional[str]=None
    serial:Optional[str]=None
    equipment_type:Optional[str]=None
    error_codes:Optional[List[str]]=None
    confidence:int=0
    raw_response:Optional[str]=None
class SearchRequest(BaseModel):
    manufacturer:str
    model:str
class SearchResponse(BaseModel):
    found:bool
    manual_url:Optional[str]=None
class HealthResponse(BaseModel):
    status:str
    version:str="2.0.0"
    gemini:bool
    tavily:bool

def load_prompt(name):
    p=Path(__file__).parent.parent/"prompts"/f"{name}.yaml"
    return yaml.safe_load(open(p)) if p.exists() else {}

@app.get("/health",response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy",gemini=bool(os.getenv("GEMINI_API_KEY")),tavily=bool(os.getenv("TAVILY_API_KEY")))

@app.post("/ocr",response_model=OCRResponse)
async def ocr(req:OCRRequest):
    key=os.getenv("GEMINI_API_KEY")
    if not key:raise HTTPException(500,"GEMINI_API_KEY not set")
    prompt=load_prompt("ocr_extraction").get("user_prompt","Extract equipment info as JSON")
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",json={"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":req.image_base64}}]}],"generationConfig":{"temperature":0.1}})
        r.raise_for_status()
    txt=r.json()["candidates"][0]["content"]["parts"][0]["text"]
    m=re.search(r"\{[\s\S]*\}",txt)
    d=json.loads(m.group()) if m else {}
    return OCRResponse(manufacturer=d.get("manufacturer"),model=d.get("model"),serial=d.get("serial"),equipment_type=d.get("equipment_type"),error_codes=d.get("error_codes"),confidence=d.get("confidence",50),raw_response=txt)

@app.post("/search",response_model=SearchResponse)
async def search(req:SearchRequest):
    key=os.getenv("TAVILY_API_KEY")
    if not key:return SearchResponse(found=False)
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.post("https://api.tavily.com/search",json={"api_key":key,"query":f"{req.manufacturer} {req.model} manual PDF","max_results":5})
        d=r.json()
    for x in d.get("results",[]):
        if ".pdf" in x.get("url","").lower():return SearchResponse(found=True,manual_url=x["url"])
    return SearchResponse(found=bool(d.get("results")),manual_url=d["results"][0]["url"] if d.get("results") else None)

if __name__=="__main__":
    import uvicorn;uvicorn.run(app,host="0.0.0.0",port=8000)
```

**evals/ocr_eval.py:**
```python
#!/usr/bin/env python3
import json,time,base64,asyncio,sys
from pathlib import Path
from dataclasses import dataclass,asdict
try:
    import httpx,yaml
except:
    import subprocess;subprocess.check_call([sys.executable,"-m","pip","install","httpx","pyyaml","-q"]);import httpx,yaml

@dataclass
class R:
    id:str;mfr_exp:str;mfr_act:str;mfr_ok:bool;model_exp:str;model_act:str;model_ok:bool;ms:int;err:str=None

def norm(s):return (s or"").lower().replace("-","").replace(" ","")
def cmp(e,a):return e is None or norm(e) in norm(a) or norm(a) in norm(e)

async def test1(c,ep):
    p=Path(c.get("image_path",""))
    exp=c["expected"]
    if not p.exists():return R(c["id"],exp.get("manufacturer",""),"",False,exp.get("model",""),"",False,0,f"No image:{p}")
    b64=base64.b64encode(open(p,"rb").read()).decode()
    t=time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r=await cl.post(f"{ep}/ocr",json={"image_base64":b64})
        ms=int((time.time()-t)*1000)
        if r.status_code!=200:return R(c["id"],exp.get("manufacturer",""),"",False,exp.get("model",""),"",False,ms,f"HTTP{r.status_code}")
        d=r.json()
        return R(c["id"],exp.get("manufacturer",""),d.get("manufacturer",""),cmp(exp.get("manufacturer"),d.get("manufacturer")),exp.get("model",""),d.get("model",""),cmp(exp.get("model"),d.get("model")),ms)
    except Exception as e:return R(c["id"],exp.get("manufacturer",""),"",False,exp.get("model",""),"",False,0,str(e))

async def run(ep="http://localhost:8000"):
    f=Path("test_data/ocr_test_cases.json")
    if not f.exists():return{"error":"No test data","passed":False}
    cases=json.load(open(f))["test_cases"]
    res=[await test1(c,ep) for c in cases]
    for r in res:print(f"  {'✓' if r.mfr_ok else '✗'} {r.id}: {r.mfr_act or r.err}")
    v=[r for r in res if not r.err]
    if not v:return{"passed":False,"error":"No valid","results":[asdict(r) for r in res]}
    ma=sum(r.mfr_ok for r in v)/len(v);mo=sum(r.model_ok for r in v)/len(v)
    th=yaml.safe_load(open("evals/thresholds.yaml")).get("ocr",{}) if Path("evals/thresholds.yaml").exists() else {}
    ok=ma>=th.get("manufacturer_accuracy",{}).get("minimum",0.85) and mo>=th.get("model_accuracy",{}).get("minimum",0.8)
    return{"passed":ok,"mfr_acc":round(ma,3),"model_acc":round(mo,3),"total":len(res),"valid":len(v)}

def main():
    ep=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8000"
    print(f"\n{'='*50}\nRIVET OCR Eval\n{'='*50}\nEndpoint:{ep}\n")
    r=asyncio.run(run(ep))
    print(f"\n{'='*50}\nMfr:{r.get('mfr_acc',0):.0%} Model:{r.get('model_acc',0):.0%}\nPASSED:{'✅' if r.get('passed') else '❌'}\n{'='*50}")
    json.dump(r,open("eval_results.json","w"),indent=2)
    sys.exit(0 if r.get("passed") else 1)

if __name__=="__main__":main()
```

**scripts/run_evals.sh:**
```bash
#!/bin/bash
EP=${1:-"http://localhost:8000"}
curl -s "$EP/health">/dev/null 2>&1||{echo "❌ Sidecar not running";exit 1;}
cd "$(dirname "$0")/.."
python3 evals/ocr_eval.py "$EP"
```

**scripts/dev.sh:**
```bash
#!/bin/bash
cd "$(dirname "$0")/../sidecar"
[ -d venv ]||python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q
export $(cat ../.env|grep -v "^#"|xargs) 2>/dev/null
uvicorn main:app --reload --port 8000
```

**scripts/deploy.sh:**
```bash
#!/bin/bash
VPS="root@72.60.175.144"
ssh $VPS "mkdir -p /opt/rivet-pro-v2"
rsync -avz --exclude .env --exclude n8n_data --exclude __pycache__ --exclude .git ./ $VPS:/opt/rivet-pro-v2/
ssh $VPS "cd /opt/rivet-pro-v2 && docker-compose up -d"
echo "✅ Deployed"
```

**docker-compose.yml:**
```yaml
version: "3.8"
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: rivet-n8n
    restart: unless-stopped
    ports: ["5678:5678"]
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD:-changeme}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY:-changeme32chars1234567890123456}
      - SIDECAR_URL=http://sidecar:8000
    volumes: [n8n_data:/home/node/.n8n]
    depends_on: [sidecar]
    networks: [rivet]
  sidecar:
    build: ./sidecar
    container_name: rivet-sidecar
    restart: unless-stopped
    ports: ["8000:8000"]
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    volumes: ["./prompts:/app/prompts:ro"]
    networks: [rivet]
volumes:
  n8n_data:
networks:
  rivet:
```

### STEP 3: Finalize
```bash
cd ~/rivet-pro-v2
chmod +x scripts/*.sh evals/ocr_eval.py
cp .env.example .env
git add -A
git commit -m "RIVET Pro v2: eval-driven build"
```

### STEP 4: Report
After completing all steps, output:
1. List of files created (find . -type f | head -25)
2. Confirm docker-compose.yml valid
3. Confirm sidecar/main.py has endpoints
4. Print "BUILD COMPLETE" and next steps

DO NOT ASK FOR CONFIRMATION. EXECUTE EVERYTHING.
'
```

---

## AFTER THE BUILD COMPLETES:

### 1. Add your API keys:
```bash
cd ~/rivet-pro-v2
nano .env
# Add: GEMINI_API_KEY, TAVILY_API_KEY, TELEGRAM_BOT_TOKEN
```

### 2. Add your test images:
```bash
# Copy your 20 equipment photos to:
cp ~/your_photos/*.jpg ~/rivet-pro-v2/test_data/test_images/

# Then update test_data/ocr_test_cases.json with correct filenames
```

### 3. Test locally (without Docker):
```bash
cd ~/rivet-pro-v2
./scripts/dev.sh
# In another terminal:
./scripts/run_evals.sh
```

### 4. Or test with Docker:
```bash
cd ~/rivet-pro-v2
docker-compose up -d
./scripts/run_evals.sh
```

### 5. Deploy to VPS:
```bash
./scripts/deploy.sh
```

---

## TROUBLESHOOTING

**"Permission denied":**
```bash
chmod +x scripts/*.sh evals/ocr_eval.py
```

**"Module not found":**
```bash
cd sidecar && pip install -r requirements.txt
```

**"Sidecar not running":**
```bash
docker-compose logs sidecar
# Or run manually:
./scripts/dev.sh
```

**"Gemini API error":**
- Check GEMINI_API_KEY in .env
- Verify key at https://aistudio.google.com/

---

## WHAT YOU GET

```
~/rivet-pro-v2/
├── CLAUDE.md              # Protection rules
├── .env                   # Your API keys
├── docker-compose.yml     # n8n + sidecar
├── prompts/
│   ├── ocr_extraction.yaml
│   └── troubleshooting.yaml
├── evals/
│   ├── thresholds.yaml    # Pass/fail criteria
│   └── ocr_eval.py        # Evaluation script
├── sidecar/
│   ├── main.py            # FastAPI service
│   └── Dockerfile
├── test_data/
│   ├── ocr_test_cases.json
│   └── test_images/       # YOUR PHOTOS HERE
└── scripts/
    ├── run_evals.sh
    ├── dev.sh
    └── deploy.sh
```
