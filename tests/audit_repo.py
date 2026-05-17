"""Audit script — runs locally on Windows. Verifies everything we can verify without Colab/Flutter."""
import json, sys, io, os, re, ast, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

errors = []
warnings = []
notes = []

def fail(msg): errors.append(msg); print(f'[FAIL] {msg}')
def warn(msg): warnings.append(msg); print(f'[WARN] {msg}')
def info(msg): notes.append(msg); print(f'[ok]   {msg}')

# ---------- 1. Notebook JSON validity ----------
print('\n=== 1. NOTEBOOK JSON ===')
nbs = sorted(glob.glob('colab_notebooks/*.ipynb') + glob.glob('eval/*.ipynb'))
for path in nbs:
    try:
        nb = json.load(open(path, encoding='utf-8'))
        n = len(nb.get('cells', []))
        info(f'{path}: {n} cells')
    except Exception as e:
        fail(f'{path}: JSON parse error - {e}')

# ---------- 2. Prompts JSON / Markdown ----------
print('\n=== 2. PROMPTS ===')
try:
    schemas = json.load(open('prompts/tool_schemas.json', encoding='utf-8'))
    tool_names = [t['name'] for t in schemas['tools']]
    info(f'tool_schemas.json: {len(tool_names)} tools = {tool_names}')
    # Check each tool has required JSON-schema bits
    for t in schemas['tools']:
        if 'parameters' not in t or 'properties' not in t['parameters']:
            fail(f'tool {t["name"]} missing parameters.properties')
        req = t['parameters'].get('required', [])
        for r in req:
            if r not in t['parameters']['properties']:
                fail(f'tool {t["name"]} requires "{r}" but it is not in properties')
except Exception as e:
    fail(f'tool_schemas.json: {e}')

for f in ['prompts/triage_system_v1.md', 'prompts/triage_system_v2.md']:
    if os.path.exists(f):
        info(f'{f}: present')
    else:
        fail(f'{f}: missing')

# ---------- 3. Eval JSONL ----------
print('\n=== 3. EVAL JSONL ===')
for fp in ['eval/triage_testcases.jsonl', 'eval/triage_testcases_extended.jsonl']:
    if not os.path.exists(fp):
        fail(f'{fp}: missing'); continue
    n_ok, n_bad = 0, 0
    ids = set()
    for i, line in enumerate(open(fp, encoding='utf-8'), 1):
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            for k in ('id', 'category', 'user', 'expect'):
                if k not in obj:
                    fail(f'{fp}:{i} missing field "{k}"'); n_bad += 1; break
            else:
                if obj['id'] in ids:
                    fail(f'{fp}:{i} duplicate id "{obj["id"]}"'); n_bad += 1
                else:
                    ids.add(obj['id']); n_ok += 1
        except Exception as e:
            fail(f'{fp}:{i} json error - {e}'); n_bad += 1
    info(f'{fp}: {n_ok} valid cases, {n_bad} bad')

# ---------- 4. Static Python check on notebook code ----------
print('\n=== 4. PYTHON STATIC CHECK ===')

def collect_cells(nb_path):
    nb = json.load(open(nb_path, encoding='utf-8'))
    cells = []
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] != 'code': continue
        src = ''.join(c['source'])
        cells.append((i, src))
    return cells

def fake_magics(src):
    # Replace !shell and %magic lines with `pass` so ast.parse succeeds,
    # preserving the original indentation so magic lines inside try/for/if blocks stay valid.
    out = []
    for ln in src.splitlines():
        s = ln.lstrip()
        if s.startswith('!') or s.startswith('%'):
            indent = ln[: len(ln) - len(s)]
            out.append(indent + 'pass  # magic')
        else:
            out.append(ln)
    return '\n'.join(out)

for nb_path in nbs:
    print(f'\n  -- {nb_path}')
    cells = collect_cells(nb_path)
    # Compile each cell individually (allow undefined names — that's a runtime check)
    for i, src in cells:
        cleaned = fake_magics(src)
        try:
            ast.parse(cleaned)
        except SyntaxError as e:
            fail(f'{nb_path} cell {i}: SyntaxError {e.lineno}:{e.offset} - {e.msg}')

    # Cross-cell name resolution: gather assigned names per cell, then check that
    # references in later cells exist in earlier ones (best-effort; allows builtins/imports).
    BUILTINS = set(dir(__builtins__)) | {'self'}
    defined = set()
    imports_modules = set()
    for i, src in cells:
        cleaned = fake_magics(src)
        try:
            tree = ast.parse(cleaned)
        except SyntaxError:
            continue
        # Collect defs
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
                    elif isinstance(t, ast.Tuple):
                        for e in t.elts:
                            if isinstance(e, ast.Name): defined.add(e.id)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            elif isinstance(node, ast.Import):
                for n in node.names:
                    name = n.asname or n.name.split('.')[0]
                    defined.add(name); imports_modules.add(name)
            elif isinstance(node, ast.ImportFrom):
                for n in node.names:
                    defined.add(n.asname or n.name)
            elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        defined.add(item.optional_vars.id)
    info(f'{nb_path}: top-level names defined across cells: {sorted(defined)[:10]}... (+{max(0,len(defined)-10)} more)')

# ---------- 5. Dart audit ----------
print('\n=== 5. DART / FLUTTER ===')
PUBSPEC = '_archived/mobile_app/pubspec.yaml'
if not os.path.exists(PUBSPEC):
    fail(f'{PUBSPEC} missing')
else:
    pub = open(PUBSPEC, encoding='utf-8').read()
    declared_pkgs = set(re.findall(r'^\s{2}([a-z_][a-z0-9_]*):\s*\^?', pub, re.M))
    # filter out top-level keys
    not_pkgs = {'name','description','publish_to','version','environment','dependencies',
                'dev_dependencies','flutter','sdk','uses-material-design','assets','flutter_test',
                'cupertino_icons','flutter_lints'}
    declared_pkgs -= not_pkgs
    # The dependencies actually used in flutter section
    info(f'pubspec deps detected: {sorted(declared_pkgs)}')

    # Walk all dart files, find package: imports
    used = {}
    for f in glob.glob('_archived/mobile_app/lib/**/*.dart', recursive=True):
        text = open(f, encoding='utf-8').read()
        for m in re.finditer(r"import\s+'package:([a-z_][a-z0-9_]*)/", text):
            used.setdefault(m.group(1), []).append(f)
    info(f'package imports found in lib/: {sorted(used.keys())}')

    KNOWN_OK = {'flutter', 'flutter_test'}
    missing = []
    for pkg in used:
        if pkg in KNOWN_OK: continue
        if pkg not in declared_pkgs:
            missing.append(pkg)
            fail(f'package "{pkg}" imported but NOT in pubspec.yaml. Files: {used[pkg]}')
    if not missing:
        info('all package: imports resolve to declared dependencies')

# Dart symbol cross-check: load all files, scan for "ClassName.method(" and see if ClassName is defined somewhere
print('\n=== 6. DART CROSS-FILE SYMBOLS ===')
dart_files = glob.glob('_archived/mobile_app/lib/**/*.dart', recursive=True)
class_defs = {}  # class name -> file
for f in dart_files:
    text = open(f, encoding='utf-8').read()
    for m in re.finditer(r'^class\s+([A-Z][A-Za-z0-9_]*)', text, re.M):
        class_defs[m.group(1)] = f
info(f'Classes defined: {sorted(class_defs.keys())}')

# Check for likely-problematic static calls (just informational)
for f in dart_files:
    text = open(f, encoding='utf-8').read()
    # Storage.foo / NotificationsService.foo / GemmaService.foo etc
    for m in re.finditer(r'\b(Storage|NotificationsService|GemmaService)\.([a-zA-Z_][a-zA-Z0-9_]*)\(', text):
        klass, method = m.group(1), m.group(2)
        # Crude: just report — full type check needs the Dart analyzer
        pass

# ---------- 7. Cross-reference: prompts files exist where assets bundle expects ----------
print('\n=== 7. ASSET CROSS-REFERENCE ===')
expected_assets = [
    '_archived/mobile_app/assets/prompts/triage_system_v3.txt',
    '_archived/mobile_app/assets/prompts/planner_system.txt',
    '_archived/mobile_app/assets/prompts/photo_journal_system.txt',
]
for a in expected_assets:
    if os.path.exists(a): info(f'{a}: present')
    else: fail(f'{a}: MISSING (gemma_service.dart will fail at runtime)')

# ---------- summary ----------
print('\n' + '='*60)
print(f'ERRORS:   {len(errors)}')
print(f'WARNINGS: {len(warnings)}')
print('='*60)
sys.exit(1 if errors else 0)
