import re
with open("frontend/src/dashboard/OverviewTab.tsx", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"useEffect\(\(\) => \{\s*// Simulate data\s*const generateData.+?return \(\) => clearInterval\(interval\)\s*\}, \[\]\)"
new_content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("frontend/src/dashboard/OverviewTab.tsx", "w", encoding="utf-8") as f:
    f.write(new_content)
print("Removed fake data generated interval!")
