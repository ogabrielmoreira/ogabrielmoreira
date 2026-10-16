"""Rebuilds the tech-stack icons in README.md from what is actually in my public repos.

Runs on a schedule (see .github/workflows/skills.yml). It looks at each repo's
languages plus its package.json / requirements.txt, maps everything to
https://skillicons.dev ids and rewrites the block between the SKILLS markers.
"""
import base64
import json
import os
import re
import urllib.error
import urllib.request

USER = os.environ.get("GH_USER", "ogabrielmoreira")
TOKEN = os.environ.get("GITHUB_TOKEN")
README = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")

# Always shown, in this order — tools I use that don't show up as repo code.
BASE = ["py", "js", "ts", "react", "nextjs", "html", "css", "tailwind", "nodejs", "figma", "git", "github", "vercel", "vscode"]

LANGUAGES = {
    "Python": "py", "Jupyter Notebook": "py", "JavaScript": "js", "TypeScript": "ts",
    "HTML": "html", "CSS": "css", "SCSS": "sass", "Sass": "sass", "Shell": "bash",
    "Java": "java", "Go": "go", "Rust": "rust", "PHP": "php", "C#": "cs", "C++": "cpp",
    "C": "c", "Kotlin": "kotlin", "Swift": "swift", "Dart": "dart", "Vue": "vue",
    "Svelte": "svelte", "Astro": "astro", "Ruby": "ruby", "Lua": "lua", "Dockerfile": "docker",
}

NPM = {
    "react": "react", "next": "nextjs", "tailwindcss": "tailwind", "vite": "vite",
    "vue": "vue", "svelte": "svelte", "express": "express", "@supabase/supabase-js": "supabase",
    "firebase": "firebase", "prisma": "prisma", "@prisma/client": "prisma", "three": "threejs",
    "redux": "redux", "@reduxjs/toolkit": "redux", "sass": "sass", "jest": "jest",
    "vitest": "vitest", "electron": "electron", "@nestjs/core": "nestjs", "graphql": "graphql",
    "mongoose": "mongodb", "mongodb": "mongodb", "pg": "postgres", "styled-components": "styledcomponents",
}

PIP = {
    "flask": "flask", "django": "django", "fastapi": "fastapi", "tensorflow": "tensorflow",
    "torch": "pytorch", "opencv-python": "opencv", "selenium": "selenium",
}


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def file_text(repo, path):
    data = get(f"https://api.github.com/repos/{USER}/{repo}/contents/{path}")
    if not data or "content" not in data:
        return None
    return base64.b64decode(data["content"]).decode("utf-8", "ignore")


def detect():
    found = {}  # icon id -> weight, used only for ordering extras
    repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner") or []
    for repo in repos:
        if repo["fork"] or repo["name"] == USER:
            continue
        name = repo["name"]
        for lang, size in (get(repo["languages_url"]) or {}).items():
            if lang in LANGUAGES:
                found[LANGUAGES[lang]] = found.get(LANGUAGES[lang], 0) + size

        pkg = file_text(name, "package.json")
        if pkg:
            found["nodejs"] = found.get("nodejs", 0) + 1
            try:
                meta = json.loads(pkg)
            except ValueError:
                meta = {}
            deps = {**meta.get("dependencies", {}), **meta.get("devDependencies", {})}
            for dep in deps:
                if dep in NPM:
                    found[NPM[dep]] = found.get(NPM[dep], 0) + 1

        reqs = file_text(name, "requirements.txt")
        if reqs:
            found["py"] = found.get("py", 0) + 1
            for line in reqs.lower().splitlines():
                dep = re.split(r"[<>=~\[; ]", line.strip(), 1)[0]
                if dep in PIP:
                    found[PIP[dep]] = found.get(PIP[dep], 0) + 1
    return found


def main():
    found = detect()
    extras = sorted((i for i in found if i not in BASE), key=lambda i: -found[i])
    icons = BASE + extras
    line = f'<img src="https://skillicons.dev/icons?i={",".join(icons)}&perline=8&theme=dark" alt="Tech stack" />'

    with open(README, encoding="utf-8") as f:
        text = f.read()
    new = re.sub(
        r"(<!--SKILLS:START-->).*?(<!--SKILLS:END-->)",
        lambda m: f"{m.group(1)}\n{line}\n{m.group(2)}",
        text,
        flags=re.S,
    )
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
    print("icons:", ",".join(icons))


if __name__ == "__main__":
    main()
