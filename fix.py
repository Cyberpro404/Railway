import re

with open("frontend/src/dashboard/OverviewTab.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# The regex starts at `useEffect(() => { \n    const generateData = ()` and ends at `return () => clearInterval(interval)\n  }, [])`
pattern = r"useEffect\(\(\) => \{\n\s*const generateData = \(\) => \{.+?return \(\) => clearInterval\(interval\)\n\s*\}, \[\]\)"

new_content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("frontend/src/dashboard/OverviewTab.tsx", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Mock data block removed.")
