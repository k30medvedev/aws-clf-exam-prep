def get_version():
    with open("version.txt", "r") as f:
        return f.read().strip()

def update_readme(version):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    import re
    updated = re.sub(r"📦\s*Version:\s*[0-9.]+", f"📦 Version: {version}", content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated)

if __name__ == "__main__":
    version = get_version()
    update_readme(version)
