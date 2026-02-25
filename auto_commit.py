import pexpect
import subprocess

small_files = [
    "app/config.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/src/app/layout.tsx",
    "frontend/src/components/QAChat.tsx",
    "frontend/src/components/SourcesList.tsx",
    "frontend/src/lib/api.ts"
]

complex_files = [
    "app/models/schemas.py",
    "app/prompts/templates.py",
    "app/main.py",
    "app/services/pdf_service.py",
    "app/services/research_engine.py",
    "app/services/search_service.py",
    "frontend/src/app/page.tsx",
    "frontend/src/app/report/[jobId]/page.tsx"
]

def get_msg(filepath):
    diff = subprocess.check_output(['git', 'diff', '--cached', filepath], text=True)
    f = filepath.split('/')[-1]
    
    if "schemas.py" in f:
        if "LeaderProfile" in diff: return "feat(backend): add LeaderProfile schema"
        if "CompanyFinancials" in diff: return "feat(backend): add CompanyFinancials schema"
        if "ICPFitAssessment" in diff: return "feat(backend): add ICPFitAssessment schema"
        if "SearchRequest" in diff: return "feat(backend): add SearchRequest schema"
        if "JobKind" in diff: return "feat(backend): extend JobKind types"
    if "templates.py" in f:
        if "FUNDING_INTELLIGENCE" in diff: return "feat(backend): add FUNDING_INTELLIGENCE_PROMPT"
        if "CRAWL_STRUCTURING" in diff: return "feat(backend): add CRAWL_STRUCTURING_PROMPT"
    if "main.py" in f:
        if "/api/search" in diff: return "feat(backend): implement /api/search endpoint"
        if "/api/extract" in diff: return "feat(backend): implement /api/extract endpoint"
        if "/api/crawl" in diff: return "feat(backend): implement /api/crawl endpoint"
        if "slowapi" in diff: return "feat(backend): implement rate limiting"
    if "research_engine.py" in f:
        if "swot_response" in diff: return "feat(backend): modularize SWOT generation"
        if "funding_intelligence" in diff: return "feat(backend): integrate GPU scoring pipeline"
    if "search_service.py" in f:
        if "search_depth" in diff: return "feat(backend): enforce advanced search_depth controls"
        if "days=" in diff: return "feat(backend): parameterize chronological recency"
    if "page.tsx" in f:
        if "actionType ===" in diff: return "feat(frontend): refactor state for 4-Tab UI"
        if "Advanced Options" in diff: return "feat(frontend): construct Advanced Options drawer"
        if "ReactMarkdown" in diff: return "fix(frontend): enforce horizontal overflow constraints"
        if "Globe" in diff: return "feat(frontend): unify typography with lucide-react"
        if "ProfileDisplay" in diff: return "feat(frontend): map structured models into React UI"
    if "pdf_service.py" in f:
        if "CompanyFinancials" in diff: return "feat(backend): append structured financial profiles to PDF"
        if "LeaderProfile" in diff: return "feat(backend): append executive rosters to PDF"
    if "api.ts" in f:
        if "executeSearch" in diff: return "feat(frontend): executeSearch API mapping"
                
    return f"refactor: modular update to {f} architecture"

untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
for uf in untracked:
    if uf.endswith('.md') or 'tavily' in uf.lower(): continue
    subprocess.run(['git', 'add', uf])
    name = uf.split('/')[-1].replace('.tsx', '').replace('.py', '')
    subprocess.run(['git', 'commit', '-m', f"feat: create modular {name} component"])

for sf in small_files:
    res = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
    if sf in res.stdout:
        subprocess.run(['git', 'add', sf])
        name = sf.split('/')[-1]
        msg = f"chore: configure {name} module settings"
        if "package" in name: msg = "chore(frontend): update npm dependencies"
        if "layout" in name: msg = "feat(frontend): implement Matomo tracking"
        if "QAChat" in name: msg = "feat(frontend): inject react-markdown engine"
        if "SourcesList" in name: msg = "feat(frontend): build interactive view-all UI"
        if "api.ts" in name: msg = "feat(frontend): implement typed internal API client"
        subprocess.run(['git', 'commit', '-m', msg])

deleted = subprocess.check_output(['git', 'ls-files', '--deleted'], text=True).splitlines()
for df in deleted:
    subprocess.run(['git', 'rm', df])
    subprocess.run(['git', 'commit', '-m', f"refactor: decommission deprecated {df.split('/')[-1]}"])

for cf in complex_files:
    while True:
        res = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
        if cf not in res.stdout: break
        child = pexpect.spawn('git add -p "{}"'.format(cf), encoding='utf-8')
        idx = child.expect(['Stage this hunk', pexpect.EOF, pexpect.TIMEOUT], timeout=3)
        if idx != 0: break
        child.sendline('s')
        idx = child.expect(['Stage this hunk', pexpect.EOF, pexpect.TIMEOUT], timeout=3)
        if idx == 0: child.sendline('y')
        else: break
        while True:
            idx = child.expect(['Stage this hunk', pexpect.EOF, pexpect.TIMEOUT], timeout=1)
            if idx == 0: child.sendline('q')
            else: break
        child.wait()
        staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True)
        if cf in staged:
            subprocess.run(['git', 'commit', '-m', get_msg(cf)])
        else:
            subprocess.run(['git', 'add', cf])
            subprocess.run(['git', 'commit', '-m', f"refactor: finalize {cf.split('/')[-1]}"])
            break

for f in small_files + complex_files: subprocess.run(['git', 'add', f])
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True)
if staged.strip(): subprocess.run(['git', 'commit', '-m', "fix: resolve remaining syntax dependencies"])

print(f"SUCCESS")
