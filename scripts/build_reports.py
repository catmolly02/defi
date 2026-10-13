"""Build a public report manifest from reports/**/*.pdf; no handwritten list needed."""
from pathlib import Path
from datetime import datetime, timezone
import re, json, shutil, subprocess, argparse, hashlib
import fitz

def date_for(path, root):
    match=re.search(r"(?<!\d)(20\d{2})[-_.](\d{2})[-_.](\d{2})(?!\d)",path.stem)
    if match:
        try: return datetime(*map(int,match.groups()),tzinfo=timezone.utc), "발행일"
        except ValueError: pass
    try:
        result=subprocess.run(["git","log","--follow","--diff-filter=A","--format=%aI","--",str(path.relative_to(root))],cwd=root,capture_output=True,text=True,check=True)
        if result.stdout.strip(): return datetime.fromisoformat(result.stdout.splitlines()[-1]), "등록일"
    except (subprocess.SubprocessError,ValueError): pass
    return datetime.fromtimestamp(path.stat().st_mtime,timezone.utc), "등록일"

def build(root):
    root=Path(root); source=root/"reports"; output=root/"dist"; dest=output/"reports"
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True); rows=[]
    covers=output/"covers"
    if covers.exists(): shutil.rmtree(covers)
    covers.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower()!=".pdf": continue
        rel=path.relative_to(source); target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        cover=None
        try:
            with fitz.open(path) as pdf:
                if pdf.page_count and not pdf.needs_pass:
                    page=pdf[0]
                    scale=min(480/page.rect.width, 680/page.rect.height)
                    name=hashlib.sha256(rel.as_posix().encode()).hexdigest()[:20]+".jpg"
                    page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(covers/name)
                    cover="covers/"+name
        except Exception:
            print(f"Cover unavailable for {rel.name}; PDF remains readable")
        date,kind=date_for(path,root)
        title=re.sub(r"^20\d{2}[-_.]\d{2}[-_.]\d{2}[_ -]*", "",path.stem).replace("_"," ")
        rows.append({"title":title,"period":date.strftime("%Y.%m.%d"),"date_label":kind,"date":date.isoformat(),"description":"DEFI 바이위클리 · PDF 원문","file":"reports/"+rel.as_posix(),"size":path.stat().st_size,"cover":cover})
    rows.sort(key=lambda r:(r["date"],r["title"]),reverse=True)
    (output/"reports.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Built {len(rows)} PDF report(s)")
    return rows

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=parser.parse_args(); build(args.root)
