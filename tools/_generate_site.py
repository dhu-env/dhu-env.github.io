# -*- coding: utf-8 -*-
"""
Generate the DHU College of Environmental Science & Engineering course-sharing site
(MkDocs + Material), modeled on ZJUSUEE.github.io.

Course classification & naming rules (per user requirements):
  - Courses are merged ONLY when the course code (课程编号) is identical;
    same-name courses with different codes are NOT merged and get a major suffix,
    e.g. 工程热力学（能环）/ 工程热力学（建环）.
  - Courses shared by 2+ majors  -> public/ (fundamental basics & professional)
  - Courses unique to one major  -> routes/<major>/
  - 双学位 (环境工程与工商管理双学位) is abbreviated as 环管 everywhere.
  - Every course page carries a status bar listing the majors (所属专业).
  - 通识教育 & 综合实践 (common to all 6 majors) -> overview table pages.
"""
import json, io, os, re, shutil

TOOLS = os.path.dirname(os.path.abspath(__file__))   # this tools/ directory
NET = TOOLS                                           # parsed course data lives here
OUT = os.path.dirname(TOOLS)                          # DHU-Env.github.io/
DOCS = os.path.join(OUT, "docs")
PUB = os.path.join(DOCS, "courses", "public")
FUND = os.path.join(PUB, "fundamental")
PROF = os.path.join(PUB, "professional")
ROUTES = os.path.join(DOCS, "courses", "routes")
MANUAL = os.path.join(TOOLS, "_manual_docs")          # hand-written static pages, copied back after rebuild
LOGO_SRC = os.path.join(os.path.dirname(OUT), "logo.jpg")  # net/logo.jpg (院徽)

MAJORS = ["能源与环境系统工程", "环境工程（卓越班）", "环境工程（双学位）",
          "环境科学", "建筑环境与能源应用工程", "土木工程（绿色建造）"]
MJ_SHORT = {"能源与环境系统工程": "能环", "环境工程（卓越班）": "环卓",
            "环境工程（双学位）": "环管", "环境科学": "环科",
            "建筑环境与能源应用工程": "建环", "土木工程（绿色建造）": "土木"}

# ---------- load parsed course data ----------
with io.open(os.path.join(NET, "_all_courses.json"), encoding="utf-8") as f:
    DATA = json.load(f)  # major -> [course dicts]

# 高等数学类：六个专业培养方案均安排在大一学年完成（教学计划仅标注“大一学年”）
for _m in DATA:
    for _c in DATA[_m]:
        if _c["name"] == "高等数学类" and not _c.get("semester"):
            _c["semester"] = "1A;1B"

def find(major, name):
    for c in DATA.get(major, []):
        if c["name"] == name:
            return c
    return None

SEM_LABEL = {"1A": "大一上", "1B": "大一下", "2A": "大二上",
             "2B": "大二下", "3A": "大三上", "3B": "大三下",
             "4A": "大四上", "4B": "大四下"}

# 专业缩写 -> 专业方向页目录名（用于课程页状态栏索引链接）
ROUTE_BY_SHORT = {"能环": "EnergyEnv", "环卓": "EnvEngExcellent", "环管": "EnvEngDual",
                  "环科": "EnvScience", "建环": "BuildingEnv", "土木": "CivilGreen"}

def fmt_sem(sem_raw):
    if not sem_raw:
        return "（教学计划未标明）"
    parts = []
    for seg in sem_raw.split(";"):
        seg = seg.strip()
        if not seg:
            continue
        if ":" not in seg:
            k, v = seg, ""
        else:
            k, v = seg.split(":", 1)
            k = k.strip(); v = v.strip()
        if k in SEM_LABEL:
            parts.append(SEM_LABEL[k] if not v else f"{SEM_LABEL[k]} · {v}学时/周")
    return "；".join(parts) if parts else "（教学计划未标明）"

def fmt_credit(x):
    if x is None:
        return "—"
    return f"{x:g}"

# PAGE_REG[(major, plan_name)] = (containing_dir_abs, page_title)
PAGE_REG = {}

def expand_entry(title, majors, name_map, note, container):
    """按课程编号分组生成页面：课程编号一致的多专业课程合并为**一个页面**
    （标题为课程名本身，不加专业括号备注，如“高等数学类”——它们本质是同一门课）；
    课程编号不一致的同名课程才分设页面并以专业缩写区分（如“流体力学（能环）”“流体力学（建环）”）。
    各专业方向页/导航均链接到对应页面，页面单独显示在各专业目录下。
    返回 (pages, major_to_page)。"""
    groups = {}
    names = {}
    for m in majors:
        nm = (name_map or {}).get(m, title)
        c = find(m, nm)
        if c is None:
            return None, None
        names[m] = nm
        key = c["id"] or ("__NOID__" + m)
        groups.setdefault(key, []).append(m)
    pages = []
    major_to_page = {}
    multi = len(groups) > 1
    for code, ms in groups.items():
        gname = names[ms[0]]
        if multi:
            pt = f"{gname}（{'·'.join(MJ_SHORT[m] for m in ms)}）"
        elif name_map is not None:
            # 多专业课程编号一致合并，且各专业课程名不同时，页面标题使用登记名（title）
            pt = title
        else:
            pt = gname
        infos = [(m, find(m, names[m])) for m in ms]
        ids, credits, hours, sems, cats = [], [], [], [], []
        for m, c in infos:
            if c["id"] and c["id"] not in ids:
                ids.append(c["id"])
            cr = fmt_credit(c["credit"])
            ent = f"{cr}（{MJ_SHORT[m]}）" if len(ms) > 1 else cr
            if ent not in credits:
                credits.append(ent)
            if c["h_total"]:
                ent_h = f"{c['h_total']}（{MJ_SHORT[m]}）" if len(ms) > 1 else c["h_total"]
                if ent_h not in hours:
                    hours.append(ent_h)
            sem = fmt_sem(c["semester"])
            ent_s = f"{sem}（{MJ_SHORT[m]}）" if len(ms) > 1 else sem
            if ent_s not in sems:
                sems.append(ent_s)
            cat = f"{c['cat']}·{c['req']}（{MJ_SHORT[m]}）" if len(ms) > 1 else f"{c['cat']}·{c['req']}"
            if cat not in cats:
                cats.append(cat)
        page = {
            "title": pt, "majors": [MJ_SHORT[m] for m in ms], "majors_full": ms,
            "ids": "、".join(ids), "credits": "；".join(credits),
            "hours": "；".join(hours), "sems": "；".join(sems),
            "cats": "；".join(cats), "note": note, "container": container,
        }
        pages.append(page)
        for m in ms:
            major_to_page[m] = pt
            PAGE_REG[(m, names[m])] = (container, pt)
    return pages, major_to_page

# ---------- classification ----------
# Entry: (title, [majors], name_map_or_None, note)
FUND_SECTIONS = [
    ("数理类", [
        ("高等数学类", MAJORS, None, ""),
        ("线性代数A或B", ["能源与环境系统工程", "环境科学", "建筑环境与能源应用工程", "土木工程（绿色建造）"], None, "环工（卓越班、双学位）以“工程数学”替代"),
        ("概率论与数理统计A或B", ["能源与环境系统工程", "环境科学", "建筑环境与能源应用工程", "土木工程（绿色建造）"], None, "环工（卓越班、双学位）以“工程数学”替代"),
        ("工程数学(1)", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
        ("工程数学(2)", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
        ("大学物理A(1)", MAJORS, None, ""),
        ("大学物理A(2)", MAJORS, None, ""),
        ("大学物理实验(1)", MAJORS, None, ""),
        ("大学物理实验(2)", MAJORS, None, ""),
        ("高等数学实验", ["环境科学"], None, ""),
    ]),
    ("化学类", [
        ("工程化学基础", ["能源与环境系统工程", "建筑环境与能源应用工程", "土木工程（绿色建造）"], None, "环工（卓越班、双学位）、环境科学以“无机化学”替代"),
        ("无机化学", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("无机化学实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("有机化学", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("有机化学实验(1)", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("物理化学", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("物理化学实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ]),
    ("力学类", [
        ("理论力学(1)", ["能源与环境系统工程", "土木工程（绿色建造）"], None, ""),
        ("理论力学(2)", ["能源与环境系统工程", "土木工程（绿色建造）"], None, ""),
        ("材料力学", ["能源与环境系统工程", "土木工程（绿色建造）"], None, ""),
        ("工程力学", ["建筑环境与能源应用工程"], None, ""),
        ("工程力学与土建基础", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
    ]),
    ("机械与制图类", [
        ("画法几何及工程制图（1）", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("画法几何及工程制图（2）", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("工程制图", ["环境工程（卓越班）", "环境工程（双学位）", "土木工程（绿色建造）"], None, ""),
        ("机械设计基础", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, "两专业课程编号不同（080421 / 080069），按课程代码分设页面"),
        ("工程训练", ["能源与环境系统工程", "环境工程（卓越班）", "环境工程（双学位）", "建筑环境与能源应用工程", "土木工程（绿色建造）"],
         {"能源与环境系统工程": "工程训练(1)", "建筑环境与能源应用工程": "工程训练(1)",
          "环境工程（卓越班）": "工程训练", "环境工程（双学位）": "工程训练", "土木工程（绿色建造）": "工程训练"}, "能环/建环分(1)(2)两个阶段"),
        ("工程训练(2)", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, "能环/建环第二阶段（课程编号一致，合并为同一页面）"),
        ("制图大作业", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("机械设计课程设计", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("工程制图课程设计", ["环境工程（卓越班）", "环境工程（双学位）", "土木工程（绿色建造）"], None, ""),
        ("工程Auto CAD", ["能源与环境系统工程", "建筑环境与能源应用工程", "土木工程（绿色建造）"],
         {"建筑环境与能源应用工程": "工程Auto CAD实践"}, "建环专业名为“工程Auto CAD实践”"),
    ]),
    ("电学及控制类", [
        ("电工电子技术B", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("电工电子技术C", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
        ("电工电子技术实验B", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, ""),
        ("电工电子技术实验C", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ]),
    ("计算机类", [
        ("计算思维与人工智能（Python语言程序设计）", MAJORS,
         {m: "计算机类" for m in MAJORS}, "六个专业课程编号一致（150001），合并为同一页面；教学计划课程名为“计算机类”"),
    ]),
]

PROF_COURSES = [
    ("流体力学", ["能源与环境系统工程", "环境工程（卓越班）", "环境工程（双学位）", "建筑环境与能源应用工程"], None, "各专业课程编号不同，按课程代码分设页面"),
    ("工程热力学", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, "两专业课程编号不同，按课程代码分设页面"),
    ("传热学", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, "两专业课程编号不同，按课程代码分设页面"),
    ("化工原理", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, "环工与环科课程编号不同，按课程代码分设页面"),
    ("化工原理实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ("化工原理课程设计", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, "环科为2学分，环工为1学分"),
    ("环境学", ["环境工程（卓越班）", "环境科学"], None, "两专业课程编号一致（140031），合并为同一页面"),
    ("环境监测", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, "环工与环科课程编号不同，按课程代码分设页面"),
    ("环境监测实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ("环境监测大实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"],
     {"环境科学": "环境监测大型实验"}, "实践环节，环科专业名为“环境监测大型实验”"),
    ("环境分析化学", ["环境工程（卓越班）", "环境工程（双学位）"], None, "环科以“环境分析化学(双语)”单列"),
    ("环境分析化学实验", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, "三专业课程编号一致（141381），合并为同一页面"),
    ("环境仪器分析", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ("环境评价学", ["环境工程（卓越班）", "环境工程（双学位）", "环境科学"], None, ""),
    ("环境经济学", ["环境工程（双学位）", "环境科学"], None, ""),
    ("信息检索与资源利用", ["能源与环境系统工程", "环境工程（卓越班）", "环境工程（双学位）", "环境科学", "建筑环境与能源应用工程"], None, "土木工程（绿色建造）培养方案未列"),
    ("工程伦理", ["能源与环境系统工程", "建筑环境与能源应用工程", "土木工程（绿色建造）"], None, "各专业课程编号不同，按课程代码分设页面"),
    ("专业英语", ["能源与环境系统工程", "环境科学", "建筑环境与能源应用工程", "土木工程（绿色建造）"],
     {"能源与环境系统工程": "能环专业英语", "环境科学": "专业外语"}, "各专业课程名称与编号均不同，分设页面"),
    ("泵与风机", ["能源与环境系统工程", "建筑环境与能源应用工程"], None, "两专业课程编号不同，按课程代码分设页面"),
]

ROUTE_SECTIONS = [
    ("EnergyEnv", "能源与环境系统工程", "能环",
     "能源与环境系统工程", [
        ("专业核心课程（学科基础必修）", [
            ("热交换器原理与设计", ["能源与环境系统工程"], None, ""),
            ("大气污染控制技术", ["能源与环境系统工程"], None, ""),
            ("燃烧学基础", ["能源与环境系统工程"], None, ""),
            ("热工控制及自动化", ["能源与环境系统工程"], None, ""),
            ("能源转化（含锅炉原理）", ["能源与环境系统工程"], None, ""),
            ("制冷技术", ["能源与环境系统工程"], None, ""),
            ("热力系统工程", ["能源与环境系统工程"], None, ""),
        ]),
        ("专业方向课程（选修）", [
            ("工程材料及机械制造基础", ["能源与环境系统工程"], None, ""),
            ("能源与环境系统工程专业导论", ["能源与环境系统工程"], None, ""),
            ("专业前沿课程", ["能源与环境系统工程"], None, ""),
            ("余热利用", ["能源与环境系统工程"], None, ""),
            ("废弃物能源资源化技术", ["能源与环境系统工程"], None, ""),
            ("生物质能利用技术", ["能源与环境系统工程"], None, ""),
            ("能源审计", ["能源与环境系统工程"], None, ""),
            ("太阳能利用技术", ["能源与环境系统工程"], None, ""),
            ("氢能及燃料电池基础", ["能源与环境系统工程"], None, ""),
        ]),
        ("实践教学环节", [
            ("制冷课程设计", ["能源与环境系统工程"], None, ""),
            ("热工测试技术与实验（一）", ["能源与环境系统工程"], None, ""),
            ("热工测试技术与实验（二）", ["能源与环境系统工程"], None, ""),
            ("热工基础实验（一）", ["能源与环境系统工程"], None, ""),
            ("热工基础实验（二）", ["能源与环境系统工程"], None, ""),
            ("热力系统工程课程设计", ["能源与环境系统工程"], None, ""),
            ("热交换器课程设计", ["能源与环境系统工程"], None, ""),
            ("锅炉课程设计", ["能源与环境系统工程"], None, ""),
            ("认识实习", ["能源与环境系统工程"], None, ""),
            ("生产实习", ["能源与环境系统工程"], None, ""),
            ("毕业实习", ["能源与环境系统工程"], None, ""),
            ("毕业论文", ["能源与环境系统工程"], None, ""),
        ]),
    ]),
    ("EnvEngExcellent", "环境工程（卓越班）", "环卓",
     "环境工程（卓越班）", [
        ("专业核心课程（专业方向必修）", [
            ("水污染控制工程(上)", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("水污染控制工程(下)", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("大气污染控制工程", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("固体废物处理与处置", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环境管理与规划", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("物理性污染控制", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环保设备基础与智能控制", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环境微生物学", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环境微生物学实验", ["环境工程（卓越班）", "环境工程（双学位）"], None, "实践环节"),
            ("工程项目管理", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
        ]),
        ("学科基础及专业方向（必修/选修）", [
            ("环境问题分析与研讨", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("智慧环保技术", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("工程概预算", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环境工程CAD", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("建筑概论及制图", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("工业污染和排放管理", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("清洁生产工艺学", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("排水管网", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("工业废水处理", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("建筑给水排水工程", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("土壤和地下水污染修复", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("生态工程", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("创新思维与方法", ["环境工程（卓越班）"], None, ""),
            ("环境系统分析", ["环境工程（卓越班）"], None, ""),
            ("环境工程专业前沿课程", ["环境工程（卓越班）"], None, ""),
            ("微机上机与环境大数据分析", ["环境工程（卓越班）"], None, "实践环节"),
        ]),
        ("实践教学环节", [
            ("水污染控制工程课程设计", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("固体废物处理与处置课程设计", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("环境评价课程设计", ["环境工程（卓越班）", "环境工程（双学位）"], None, "环卓/环管课程编号不同，按课程代码分设页面"),
            ("大气污染控制工程课程设计", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("固体废物处理与处置实验", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("大气污染控制工程实验", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("水污染控制工程实验(1)", ["环境工程（卓越班）", "环境工程（双学位）"], None, ""),
            ("水污染控制工程实验(2)", ["环境工程（卓越班）", "环境工程（双学位）"],
             {"环境工程（双学位）": "水污染控制工程实验（2）"}, "环卓/环管课程编号不同，按课程代码分设页面"),
            ("生产实习", ["环境工程（卓越班）"], None, ""),
            ("认识实习", ["环境工程（卓越班）"], None, ""),
            ("毕业实习", ["环境工程（卓越班）"], None, ""),
            ("毕业设计", ["环境工程（卓越班）"], None, ""),
        ]),
    ]),
    ("EnvEngDual", "环境工程（双学位）", "环管",
     "环境工程（环境工程与工商管理双学位）", [
        ("学科基础（必修）", [
            ("工程数学(1)", ["环境工程（双学位）"], None, ""),
            ("工程数学(2)", ["环境工程（双学位）"], None, ""),
            ("工程制图", ["环境工程（双学位）"], None, ""),
            ("电工电子技术C", ["环境工程（双学位）"], None, ""),
            ("电工电子技术实验C", ["环境工程（双学位）"], None, ""),
            ("有机化学", ["环境工程（双学位）"], None, ""),
            ("有机化学实验(1)", ["环境工程（双学位）"], None, ""),
            ("物理化学", ["环境工程（双学位）"], None, ""),
            ("物理化学实验", ["环境工程（双学位）"], None, ""),
            ("工程力学与土建基础", ["环境工程（双学位）"], None, ""),
            ("化工原理", ["环境工程（双学位）"], None, ""),
            ("化工原理实验", ["环境工程（双学位）"], None, ""),
            ("流体力学", ["环境工程（双学位）"], None, ""),
            ("环境微生物学", ["环境工程（双学位）"], None, ""),
            ("环境分析化学", ["环境工程（双学位）"], None, ""),
            ("环境分析化学实验", ["环境工程（双学位）"], None, ""),
            ("环境监测", ["环境工程（双学位）"], None, ""),
            ("环境监测实验", ["环境工程（双学位）"], None, ""),
            ("工程项目管理", ["环境工程（双学位）"], None, ""),
            ("管理学", ["环境工程（双学位）"], None, ""),
            ("宏观经济学", ["环境工程（双学位）"], None, ""),
            ("微观经济学", ["环境工程（双学位）"], None, ""),
            ("环管融合创新思维与方法", ["环境工程（双学位）"], None, ""),
            ("环管融合专业导论", ["环境工程（双学位）"], None, ""),
        ]),
        ("学科基础（选修）", [
            ("环境问题分析与研讨", ["环境工程（双学位）"], None, ""),
            ("智慧环保技术", ["环境工程（双学位）"], None, ""),
            ("工程概预算", ["环境工程（双学位）"], None, ""),
            ("环境工程CAD", ["环境工程（双学位）"], None, ""),
            ("建筑概论及制图", ["环境工程（双学位）"], None, ""),
            ("环境仪器分析", ["环境工程（双学位）"], None, ""),
            ("信息检索与资源利用", ["环境工程（双学位）"], None, ""),
            ("会计学", ["环境工程（双学位）"], None, ""),
            ("环境系统分析与管理", ["环境工程（双学位）"], None, ""),
            ("环境与经济法基础", ["环境工程（双学位）"], None, ""),
            ("组织行为学", ["环境工程（双学位）"], None, ""),
        ]),
        ("专业方向（必修）", [
            ("管理信息系统", ["环境工程（双学位）"], None, ""),
            ("环境经济学", ["环境工程（双学位）"], None, ""),
            ("大气污染控制工程", ["环境工程（双学位）"], None, ""),
            ("固体废物处理与处置", ["环境工程（双学位）"], None, ""),
            ("环境评价学", ["环境工程（双学位）"], None, ""),
            ("环境管理与规划", ["环境工程（双学位）"], None, ""),
            ("物理性污染控制", ["环境工程（双学位）"], None, ""),
            ("水污染控制工程(上)", ["环境工程（双学位）"], None, ""),
            ("水污染控制工程(下)", ["环境工程（双学位）"], None, ""),
            ("环保设备基础与智能控制", ["环境工程（双学位）"], None, ""),
        ]),
        ("专业方向（选修）", [
            ("企业经营管理", ["环境工程（双学位）"], None, ""),
            ("环管融合专业前沿课程", ["环境工程（双学位）"], None, ""),
            ("数据库系统及应用", ["环境工程（双学位）"], None, ""),
            ("工业污染和排放管理", ["环境工程（双学位）"], None, ""),
            ("清洁生产工艺学", ["环境工程（双学位）"], None, ""),
            ("排水管网", ["环境工程（双学位）"], None, ""),
            ("工业废水处理", ["环境工程（双学位）"], None, ""),
            ("建筑给水排水工程", ["环境工程（双学位）"], None, ""),
            ("土壤和地下水污染修复", ["环境工程（双学位）"], None, ""),
            ("生态工程", ["环境工程（双学位）"], None, ""),
        ]),
        ("实践教学环节", [
            ("工程制图课程设计", ["环境工程（双学位）"], None, ""),
            ("工程训练", ["环境工程（双学位）"], None, ""),
            ("环管融合认识实习", ["环境工程（双学位）"], None, ""),
            ("环管融合生产实习", ["环境工程（双学位）"], None, ""),
            ("环管融合毕业实习", ["环境工程（双学位）"], None, ""),
            ("水污染控制工程课程设计", ["环境工程（双学位）"], None, ""),
            ("创业决策", ["环境工程（双学位）"], None, ""),
            ("微机上机和管理系统", ["环境工程（双学位）"], None, ""),
            ("环境微生物学实验", ["环境工程（双学位）"], None, ""),
            ("环境监测大实验", ["环境工程（双学位）"], None, ""),
            ("固体废物处理与处置课程设计", ["环境工程（双学位）"], None, ""),
            ("环境评价课程设计", ["环境工程（双学位）"], None, ""),
            ("大气污染控制工程课程设计", ["环境工程（双学位）"], None, ""),
            ("固体废物处理与处置实验", ["环境工程（双学位）"], None, ""),
            ("大气污染控制工程实验", ["环境工程（双学位）"], None, ""),
            ("水污染控制工程实验(1)", ["环境工程（双学位）"], None, ""),
            ("水污染控制工程实验（2）", ["环境工程（双学位）"], None, ""),
            ("化工原理课程设计", ["环境工程（双学位）"], None, ""),
            ("毕业设计", ["环境工程（双学位）"], None, ""),
        ]),
    ]),
    ("EnvScience", "环境科学", "环科",
     "环境科学", [
        ("学科基础必修", [
            ("生物化学", ["环境科学"], None, ""),
            ("生物化学实验", ["环境科学"], None, ""),
            ("环境化学", ["环境科学"], None, ""),
            ("环境化学实验", ["环境科学"], None, ""),
            ("环境生物学", ["环境科学"], None, ""),
            ("环境生物学实验", ["环境科学"], None, ""),
            ("生态学", ["环境科学"], None, ""),
            ("环境工程制图", ["环境科学"], None, ""),
            ("环境工程学", ["环境科学"], None, ""),
            ("环境工程学实验", ["环境科学"], None, ""),
            ("环境分析化学(双语)", ["环境科学"], None, ""),
            ("环境仪器分析实验", ["环境科学"], None, ""),
        ]),
        ("专业方向选修 · 环境管理与规划模块", [
            ("环境法学", ["环境科学"], None, ""),
            ("环境信息系统", ["环境科学"], None, ""),
            ("大气环境学", ["环境科学"], None, ""),
            ("环境地学", ["环境科学"], None, ""),
            ("环境水文学", ["环境科学"], None, ""),
            ("环境管理学", ["环境科学"], None, ""),
            ("环境规划学", ["环境科学"], None, ""),
            ("清洁生产审核与EHS", ["环境科学"], None, ""),
            ("环境科学前沿", ["环境科学"], None, ""),
        ]),
        ("专业方向选修 · 环境治理与修复模块", [
            ("基因工程", ["环境科学"], None, ""),
            ("生物工程", ["环境科学"], None, ""),
            ("环境材料", ["环境科学"], None, ""),
            ("环境生物技术", ["环境科学"], None, ""),
            ("水污染控制原理", ["环境科学"], None, ""),
            ("地表水环境修复", ["环境科学"], None, ""),
            ("地表水环境修复（全英文）", ["环境科学"], None, ""),
            ("环境土壤学", ["环境科学"], None, ""),
            ("环境土壤学（全英文）", ["环境科学"], None, ""),
            ("场地污染修复技术", ["环境科学"], None, ""),
            ("固废与资源化利用技术", ["环境科学"], None, ""),
            ("物理污染控制技术", ["环境科学"], None, ""),
        ]),
        ("实践教学环节", [
            ("环境数据分析上机", ["环境科学"], None, ""),
            ("环境工程制图课程设计", ["环境科学"], None, ""),
            ("环境生物技术综合实验", ["环境科学"], None, ""),
            ("生态实习", ["环境科学"], None, ""),
            ("环境材料综合实验", ["环境科学"], None, ""),
            ("认识实习", ["环境科学"], None, ""),
            ("环境评价", ["环境科学"], None, ""),
            ("毕业实习", ["环境科学"], None, ""),
            ("毕业论文", ["环境科学"], None, ""),
        ]),
    ]),
    ("BuildingEnv", "建筑环境与能源应用工程", "建环",
     "建筑环境与能源应用工程", [
        ("专业核心课程（学科基础必修）", [
            ("工业通风", ["建筑环境与能源应用工程"], None, ""),
            ("自动控制原理", ["建筑环境与能源应用工程"], None, ""),
            ("工程管理", ["建筑环境与能源应用工程"], None, ""),
            ("建筑环境学", ["建筑环境与能源应用工程"], None, ""),
            ("流体输配管网", ["建筑环境与能源应用工程"], None, ""),
            ("热质交换原理与设备", ["建筑环境与能源应用工程"], None, ""),
            ("空气调节", ["建筑环境与能源应用工程"], None, ""),
            ("建筑环境与能源系统测量技术", ["建筑环境与能源应用工程"], None, ""),
            ("供热工程", ["建筑环境与能源应用工程"], None, ""),
            ("空调用制冷技术", ["建筑环境与能源应用工程"], None, ""),
            ("燃气供应", ["建筑环境与能源应用工程"], None, ""),
            ("锅炉及锅炉房设备", ["建筑环境与能源应用工程"], None, ""),
            ("建筑设备自动化与智能建筑", ["建筑环境与能源应用工程"], None, ""),
            ("环境保护概论", ["建筑环境与能源应用工程"], None, ""),
            ("建筑工程基础", ["建筑环境与能源应用工程"], None, ""),
        ]),
        ("专业方向课程（选修）", [
            ("建筑专业导论", ["建筑环境与能源应用工程"], None, ""),
            ("空气洁净技术", ["建筑环境与能源应用工程"], None, ""),
            ("专业前沿", ["建筑环境与能源应用工程"], None, ""),
            ("施工组织技术与工程经济", ["建筑环境与能源应用工程"], None, ""),
            ("建筑给排水", ["建筑环境与能源应用工程"], None, ""),
            ("高层建筑空调与防排烟", ["建筑环境与能源应用工程"], None, ""),
            ("建筑节能技术与能耗模拟", ["建筑环境与能源应用工程"], None, ""),
            ("专业报告写作与表达", ["建筑环境与能源应用工程"], None, ""),
            ("BIM技术与应用实践", ["建筑环境与能源应用工程"], None, ""),
        ]),
        ("实践教学环节", [
            ("通风课程设计", ["建筑环境与能源应用工程"], None, ""),
            ("制冷课程设计", ["建筑环境与能源应用工程"], None, ""),
            ("专业基础实验（一）", ["建筑环境与能源应用工程"], None, ""),
            ("专业基础实验（二）", ["建筑环境与能源应用工程"], None, ""),
            ("专业综合实验（一）", ["建筑环境与能源应用工程"], None, ""),
            ("专业综合实验（二）", ["建筑环境与能源应用工程"], None, ""),
            ("空调课程设计", ["建筑环境与能源应用工程"], None, ""),
            ("供热课程设计", ["建筑环境与能源应用工程"], None, ""),
            ("锅炉课程设计", ["建筑环境与能源应用工程"], None, ""),
            ("生产实习", ["建筑环境与能源应用工程"], None, ""),
            ("认识实习", ["建筑环境与能源应用工程"], None, ""),
            ("毕业实习", ["建筑环境与能源应用工程"], None, ""),
            ("毕业论文", ["建筑环境与能源应用工程"], None, ""),
        ]),
    ]),
    ("CivilGreen", "土木工程（绿色建造）", "土木",
     "土木工程（绿色建造）", [
        ("学科基础必修", [
            ("土木工程概论", ["土木工程（绿色建造）"], None, ""),
            ("土木工程材料", ["土木工程（绿色建造）"], None, ""),
            ("荷载与可靠度设计原理", ["土木工程（绿色建造）"], None, ""),
            ("水力学", ["土木工程（绿色建造）"], None, ""),
        ]),
        ("专业方向必修", [
            ("土力学", ["土木工程（绿色建造）"], None, ""),
            ("结构力学", ["土木工程（绿色建造）"], None, ""),
            ("混凝土结构设计原理", ["土木工程（绿色建造）"], None, ""),
            ("基础工程", ["土木工程（绿色建造）"], None, ""),
            ("工程地质", ["土木工程（绿色建造）"], None, ""),
            ("房屋建筑学", ["土木工程（绿色建造）"], None, ""),
            ("土木工程测量", ["土木工程（绿色建造）"], None, ""),
            ("钢结构设计原理", ["土木工程（绿色建造）"], None, ""),
            ("建筑结构抗震设计原理", ["土木工程（绿色建造）"], None, ""),
            ("土木工程施工与工程经济", ["土木工程（绿色建造）"], None, ""),
        ]),
        ("专业方向课程（选修）", [
            ("特殊土地基处理", ["土木工程（绿色建造）"], None, ""),
            ("地下综合管廊工程", ["土木工程（绿色建造）"], None, ""),
            ("土工合成材料", ["土木工程（绿色建造）"], None, ""),
            ("工程地下水", ["土木工程（绿色建造）"], None, ""),
            ("海绵城市建设理念与工程应用", ["土木工程（绿色建造）"], None, ""),
            ("建筑业碳排放", ["土木工程（绿色建造）"], None, ""),
            ("给排水工程", ["土木工程（绿色建造）"], None, ""),
            ("BIM与虚拟现实", ["土木工程（绿色建造）"], None, ""),
            ("地下空间规划与利用", ["土木工程（绿色建造）"], None, ""),
            ("弹性力学", ["土木工程（绿色建造）"], None, ""),
            ("环境岩土工程", ["土木工程（绿色建造）"], None, ""),
        ]),
        ("实践教学环节", [
            ("绿色低碳地基处理设计", ["土木工程（绿色建造）"], None, ""),
            ("土木工程信息化设计", ["土木工程（绿色建造）"], None, ""),
            ("工程地质实习", ["土木工程（绿色建造）"], None, ""),
            ("测量实习", ["土木工程（绿色建造）"], None, ""),
            ("混凝土结构课程设计", ["土木工程（绿色建造）"], None, ""),
            ("基础工程课程设计", ["土木工程（绿色建造）"], None, ""),
            ("地下建筑结构设计", ["土木工程（绿色建造）"], None, ""),
            ("钢结构课程设计", ["土木工程（绿色建造）"], None, ""),
            ("生产实习", ["土木工程（绿色建造）"], None, ""),
            ("认识实习", ["土木工程（绿色建造）"], None, ""),
            ("毕业实习", ["土木工程（绿色建造）"], None, ""),
            ("毕业设计", ["土木工程（绿色建造）"], None, ""),
        ]),
    ]),
]

# ---------- page templates ----------
def page_tags(major_shorts):
    return "\n".join(f"  - {t}" for t in dict.fromkeys(major_shorts))

def status_bar(c):
    tags = []
    for t in dict.fromkeys(c["majors"]):
        route = ROUTE_BY_SHORT.get(t)
        if route:
            rel = os.path.relpath(
                os.path.join(ROUTES, route, "index.md"),
                c.get("container", ROUTES)).replace(os.sep, "/")
            tags.append(f'<a class="dhu-tag" href="{rel}">{t}</a>')
        else:
            tags.append(f'<span class="dhu-tag">{t}</span>')
    return f'<div class="dhu-bar"><strong>所属专业</strong>{"".join(tags)}</div>'

def course_page(c):
    tags = page_tags(c["majors"])
    note_line = f"\n\n!!! note \"课程说明\"\n\n    {c['note']}" if c["note"] else ""
    bar = status_bar(c)
    return f"""---
tags:
{tags}
---

# {c['title']}

{bar}

> 本页为课程信息页，当前仅包含培养方案中的基本信息，其余内容待完善。

## 课程内容

### 课程基本信息

| 项目 | 内容 |
| ---- | ---- |
| 适用专业 | {'、'.join(c['majors_full'])} |
| 课程性质 | {c['cats']} |
| 课程编号 | {c['ids'] or '—'} |
| 学分 | {c['credits']} |
| 总学时 | {c['hours'] or '—'} |
| 建议修读学期 | {c['sems']}{note_line} |

## 课程资源

### 推荐教材 / 网课

> 该部分待完善

### 资源文件

> 该部分待完善

### 学习笔记

> 该部分待完善

## 学习建议

> 该部分待完善
"""

# 环境科学专业方向（选修）在教学计划中分为两个模块，其余专业无模块结构
ENVSCI_MODULES = {
    "环境管理与规划模块": [
        "环境法学", "环境信息系统", "大气环境学", "环境地学", "环境水文学",
        "环境管理学", "环境规划学", "清洁生产审核与EHS", "环境科学前沿",
    ],
    "环境治理与修复模块": [
        "基因工程", "生物工程", "环境材料", "环境生物技术", "水污染控制原理",
        "地表水环境修复", "地表水环境修复（全英文）", "环境土壤学",
        "环境土壤学（全英文）", "场地污染修复技术", "固废与资源化利用技术",
        "物理污染控制技术",
    ],
}

# 不进方向页/导航目录的公共环节课程（劳动教育类在教学计划中属实践教学，
# 其余公共环节课程如军训、学术讲座、安全教育、社会实践等已因属通识教育/综合实践被过滤）
EXCLUDE_COURSES = {"劳动教育类"}

def route_full_index(dirname, major, title, short):
    """按教学计划原始分类（课程类别·必修/选修，环境科学专业方向选修含模块）
    全量列出本专业培养方案中的课程；重叠课程同样列出并跳转到对应课程页面，
    不重复建设页面。返回 (页面文本, 分组数据, 缺失课程列表)。"""
    out = [f"# {title}", "",
           f'<div class="dhu-bar"><strong>专业方向</strong><span class="dhu-tag">{short}</span></div>', "",
           '!!! info "专业简介"', '',
           '该部分待完善。建议从学院官网、专业介绍手册或《本科培养方案》中摘录本专业的定位、主干学科、就业方向后补充。',
           ""]
    groups = {}   # (cat, req[, module]) -> [(pt, rel, rel_docs, cr, sem)]
    order = []
    missing_courses = []
    for c in DATA[major]:
        if c["cat"] in ("通识教育", "综合实践"):
            continue  # 通识教育与综合实践为全校性环节，见「通识教育与公共环节总览」
        if c["name"] in EXCLUDE_COURSES:
            continue  # 指定公共环节课程不进入方向目录
        nm = c["name"]
        key = (c["cat"], c["req"])
        if major == "环境科学" and c["cat"] == "专业方向" and c["req"] == "选修":
            mod = next((m for m, lst in ENVSCI_MODULES.items() if nm in lst), None)
            key = (c["cat"], c["req"], mod)
        if key not in groups:
            groups[key] = []
            order.append(key)
        reg = PAGE_REG.get((major, nm))
        if reg is None:
            missing_courses.append(nm)
            continue
        container, pt = reg
        rel = os.path.relpath(os.path.join(container, f"{pt}.md"), os.path.join(ROUTES, dirname)).replace(os.sep, "/")
        rel_docs = os.path.relpath(os.path.join(container, f"{pt}.md"), DOCS).replace(os.sep, "/")
        groups[key].append((pt, rel, rel_docs, fmt_credit(c["credit"]), fmt_sem(c["semester"])))
    for key in order:
        cat, req = key[0], key[1]
        mod = key[2] if len(key) > 2 else None
        sec = f"{cat}（{'必修' if req == '必修' else '选修'}）"
        if mod:
            sec = f"{sec} · {mod}"
        out.append(f"### {sec}")
        out.append("")
        out.append("| 课程名称 | 学分 | 建议学期 | 资料情况 |")
        out.append("| ------- | ---- | ---- | ---- |")
        for pt, rel, rel_docs, cr, sem in groups[key]:
            out.append(f"| [**{pt}**]({rel}) | {cr} | {sem} | :x: 待完善 |")
        out.append("")
    return "\n".join(out), groups, missing_courses

# ---------- build ----------
os.chdir(TOOLS)  # avoid locking OUT as cwd

def wipe_dir(d):
    """Remove directory; if the root is locked (WinError 32), remove its contents instead."""
    if not os.path.exists(d):
        return
    try:
        shutil.rmtree(d)
        return
    except OSError:
        pass
    for name in os.listdir(d):
        p = os.path.join(d, name)
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except OSError:
            pass

wipe_dir(DOCS)
for d in [DOCS, PUB, FUND, PROF, ROUTES, os.path.join(DOCS, "stylesheets"), os.path.join(DOCS, "js")]:
    os.makedirs(d, exist_ok=True)

missing = []
all_fund = {}      # section -> [pages]
for sec_name, entries in FUND_SECTIONS:
    all_fund.setdefault(sec_name, [])
    for (t, majors, nm, note) in entries:
        pages, _ = expand_entry(t, majors, nm, note, FUND)
        if pages is None:
            missing.append(("FUND", t))
            continue
        all_fund[sec_name].extend(pages)
        for p in pages:
            with io.open(os.path.join(FUND, f"{p['title']}.md"), "w", encoding="utf-8") as f:
                f.write(course_page(p))

prof_pages = []
for (t, majors, nm, note) in PROF_COURSES:
    pages, _ = expand_entry(t, majors, nm, note, PROF)
    if pages is None:
        missing.append(("PROF", t))
        continue
    prof_pages.extend(pages)
    for p in pages:
        with io.open(os.path.join(PROF, f"{p['title']}.md"), "w", encoding="utf-8") as f:
            f.write(course_page(p))

# 通识教育总览
gen_table = """| 课程名称 | 学分 | 课程性质 | 适用专业 | 备注 |
| ---- | ---- | ---- | ---- | ---- |
| 马克思主义基本原理 | 3.0 | 通识教育·必修 | 全部6个专业 | — |
| 形势与政策（1）～（4） | 0.5×4 | 通识教育·必修 | 全部6个专业 | 能环、土木总学时28，其余专业12 |
| 毛泽东思想和中国特色社会主义理论体系概论 | 3.0 | 通识教育·必修 | 全部6个专业 | — |
| 习近平新时代中国特色社会主义思想概论 | 3.0 | 通识教育·必修 | 全部6个专业 | — |
| 中国近现代史纲要 | 3.0 | 通识教育·必修 | 全部6个专业 | — |
| 思想道德与法治 | 3.0 | 通识教育·必修 | 全部6个专业 | — |
| 四史教育类 | 1.0 | 通识教育·必修 | 全部6个专业 | — |
| 体育类 | 4.0 | 通识教育·必修 | 全部6个专业 | — |
| 军事理论 | 2.0 | 通识教育·必修 | 全部6个专业 | — |
| 大学外语类 | 8.0 | 通识教育·必修 | 全部6个专业 | — |
| 创新创业类 | 2.0 | 通识教育·必修 | 全部6个专业 | — |
| 大学新生心理导航 | 2.0 | 通识教育·必修 | 全部6个专业 | — |
| 文化素质类 | 6.0 | 通识教育·选修 | 全部6个专业 | 至少选修 |
| 计算机类 | 5.0 | 通识教育·选修 | 全部6个专业 | 至少选修 |
| 学术讲座（12次分散） | 1.0 | 综合实践·必修 | 全部6个专业 | — |
| 社会实践 | 2.0 | 综合实践·必修 | 全部6个专业 | — |
| 军训 | 2.0 | 综合实践·必修 | 全部6个专业 | — |
| 安全教育 | 0.5 | 综合实践·必修 | 全部6个专业 | — |
| 劳动教育类 | 2.0 | 实践教学·必修 | 全部6个专业 | — |
"""
gen_page = """# 通识教育与公共环节总览

!!! info "说明"

    以下课程为东华大学环境学院**六个专业（能环、环卓、环管、环科、建环、土木）均需修读**的通识教育课程与公共实践环节。
    其中自然科学类课程（高等数学、线性代数、概率论与数理统计、大学物理、工程数学及化学类课程）已在「公共基础课程」中单列课程页面，此处不再重复。

## 通识教育课程（六个专业共有）

""" + gen_table + """
## 需要补充的内容

- **各课程的考核方式、教材信息**：该部分待完善，可从教务系统课程简介或任课老师处获取。
- **各课程学习笔记与攻略**：该部分待完善，欢迎投稿（见[平台贡献指南](../../../guideline.md)）。
"""

with io.open(os.path.join(FUND, "通识教育.md"), "w", encoding="utf-8") as f:
    f.write(gen_page)

# public/index.md
pub_idx = ["# 公共基础课程", "",
"""!!! info "分类说明"

    本站将六个专业的课程按以下方式归类：
    1. **公共基础课程**：两个及以上专业共同修读的基础学科课程（数理、化学、力学、机械制图、电学等），按学科模块整理；
    2. **专业方向课程**：各专业开设的课程见各专业方向页面，专业间重叠的课程不重复建设页面，跳转后仍为同一课程界面。

    同名课程仅当**课程编号一致**时合并为同一页面（页面标题为课程名本身，不加专业括号）；课程编号不一致的同名课程分设页面并以专业缩写区分（如“工程热力学（能环）”“工程热力学（建环）”）。各课程页面顶部状态栏标注该课程所属专业（可点击跳转至对应专业方向页），便于按专业索引。
"""]
for sec_name, items in all_fund.items():
    pub_idx.append(f"### {sec_name}")
    pub_idx.append("")
    pub_idx.append("| 课程名称 | 学分 | 适用专业 | 资料情况 |")
    pub_idx.append("| ------- | ---- | ---- | ---- |")
    for p in items:
        rel = f"./fundamental/{p['title']}.md"
        pub_idx.append(f"| [**{p['title']}**]({rel}) | {p['credits']} | {'、'.join(p['majors'])} | :x: 待完善 |")
    pub_idx.append("")
pub_idx.append("### 通识教育与公共环节")
pub_idx.append("")
pub_idx.append("| 课程 | 说明 |")
pub_idx.append("| ---- | ---- |")
pub_idx.append("| [**通识教育与公共环节总览**](./fundamental/通识教育.md) | 六个专业共有的思政、体育、外语、军事、实践等课程 |")
pub_idx.append("")
with io.open(os.path.join(PUB, "index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(pub_idx))

# public/professional/index.md
pro_idx = ["# 公共专业课程", "",
"""!!! info "说明"

    以下为**两个及以上专业共同修读**的专业性质课程。同名课程按课程编号一致与否决定合并或分设页面（如“流体力学（能环）”“流体力学（建环）”等）；仅单个专业开设的课程请前往对应专业方向页面查看。
""",
"| 课程名称 | 学分 | 适用专业 | 资料情况 |",
"| ------- | ---- | ---- | ---- |"]
for p in prof_pages:
    rel = f"./{p['title']}.md"
    pro_idx.append(f"| [**{p['title']}**]({rel}) | {p['credits']} | {'、'.join(p['majors'])} | :x: 待完善 |")
pro_idx.append("")
with io.open(os.path.join(PROF, "index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(pro_idx))

# routes
route_nav_data = {}  # dirname -> [(sec_title, [(page_title, rel_docs)])]
for dirname, major, short, title, sections in ROUTE_SECTIONS:
    rdir = os.path.join(ROUTES, dirname)
    os.makedirs(rdir, exist_ok=True)
    # 1) 课程页注册：仅生成尚未在公共区或其他方向生成的课程页面（重叠课程仅跳转）
    for sec_name, courses in sections:
        for (t, majors, nm, note) in courses:
            keys = [(m, (nm or {}).get(m, t)) for m in majors]
            if all(k in PAGE_REG for k in keys):
                # 该课程页面已在公共区或其他专业方向生成（重叠课程）：
                # 不重复生成页面，仅保留超链接跳转
                continue
            pages, _ = expand_entry(t, majors, nm, note, rdir)
            if pages is None:
                missing.append((dirname, t))
                continue
            for p in pages:
                with io.open(os.path.join(rdir, f"{p['title']}.md"), "w", encoding="utf-8") as f:
                    f.write(course_page(p))
    # 2) 方向导航页：按教学计划分类全量列出本专业培养方案课程（重叠课程同样列出并跳转）
    text, groups, miss = route_full_index(dirname, major, title, short)
    for nm in miss:
        missing.append((dirname, nm))
    with io.open(os.path.join(rdir, "index.md"), "w", encoding="utf-8") as f:
        f.write(text)
    nav_rows = []
    for key, items in groups.items():
        cat, req = key[0], key[1]
        mod = key[2] if len(key) > 2 else None
        sec = f"{cat}（{'必修' if req == '必修' else '选修'}）"
        if mod:
            sec = f"{sec} · {mod}"
        nav_rows.append((sec, [(pt, rel_docs) for pt, rel, rel_docs, cr, sem in items]))
    route_nav_data[dirname] = nav_rows

# courses.md
courses_md = """# 本科课程大纲

本页汇总东华大学环境科学与工程学院六个本科专业的课程导航。

#### 公共课程

- [**公共基础课程**](./courses/public/index.md)（数理、化学、力学、机械制图、电学等基础学科课程）
- [**通识教育与公共环节总览**](./courses/public/fundamental/通识教育.md)

#### 专业方向课程

- [**能源与环境系统工程**](./courses/routes/EnergyEnv/index.md)
- [**环境工程（卓越班）**](./courses/routes/EnvEngExcellent/index.md)
- [**环境工程（环境工程与工商管理双学位）**](./courses/routes/EnvEngDual/index.md)
- [**环境科学**](./courses/routes/EnvScience/index.md)
- [**建筑环境与能源应用工程**](./courses/routes/BuildingEnv/index.md)
- [**土木工程（绿色建造）**](./courses/routes/CivilGreen/index.md)

#### 待完善内容

- 各课程页面的「教材 / 资源 / 笔记 / 学习建议」均为待完善状态，欢迎投稿补充（见[平台贡献指南](./guideline.md)）。
"""
with io.open(os.path.join(DOCS, "courses.md"), "w", encoding="utf-8") as f:
    f.write(courses_md)

# extra.css for the status bar
extra_css = """.dhu-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  background: linear-gradient(135deg, rgba(46,125,50,.10), rgba(0,137,123,.08));
  border: 1px solid rgba(46,125,50,.30);
  border-radius: 8px;
  padding: 8px 14px;
  margin: 6px 0 14px;
  font-size: .88rem;
}
.dhu-bar strong {
  color: #1b5e20;
  margin-right: 4px;
}
.dhu-tag {
  display: inline-block;
  background: #2e7d32;
  color: #fff !important;
  border-radius: 4px;
  padding: 1px 10px;
  font-size: .78rem;
  font-weight: 600;
  line-height: 1.6;
}
a.dhu-tag {
  text-decoration: none;
  transition: background .15s ease;
}
a.dhu-tag:hover {
  background: #1b5e20;
}
"""
with io.open(os.path.join(DOCS, "stylesheets", "extra.css"), "w", encoding="utf-8") as f:
    f.write(extra_css)

# dhu_nav.js：侧边导航「专业上下文保持」——同一课程被多个专业引用时，
# 从某专业点入后侧边栏保持停留在该专业目录（见 mkdocs.yml extra_javascript）
nav_js = r"""/* 东华环院课程攻略 · 侧边导航"专业上下文保持"脚本
 * 目标：同一门课程（课程代码相同、合并为单一页面）被多个专业引用时，
 * 从某个专业方向页/该专业侧边栏点入后，侧边导航保持停留在该专业目录，
 * 不再跳到其他专业的目录下。
 * 机制：进入方向页（routes/<专业>/ 下）点击课程链接时，把当前专业目录名
 * 记入 sessionStorage；课程页面加载时读取该记录，展开对应专业的侧边导航
 * 并收起其他专业。该记录会一直保留到用户进入全校性列表页（公共基础课程等）。 */
(function () {
  "use strict";
  var KEY = "dhu-major-dir";

  function currentRouteDir() {
    var m = location.pathname.match(/\/courses\/routes\/([^\/]+)\//);
    return m ? m[1] : null;
  }

  function isPublicListPage() {
    return /\/courses\/public\//.test(location.pathname) &&
           (location.pathname.indexOf("index.html") !== -1 ||
            /\/courses\/public\/[^\/]+\/$/.test(location.pathname));
  }

  /* 把相对 href 解析为绝对路径（用于与 location.pathname 比对） */
  function absPath(href) {
    var a = document.createElement("a");
    a.href = href;
    return a.pathname;
  }

  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href === "#" || href.indexOf("#") === 0 || href.indexOf("http") === 0) return;
    var dir = currentRouteDir();
    if (dir) {
      /* 在专业上下文内：点击课程页链接（排除导航页/文档页）时记录来源专业 */
      if (href.indexOf("index.html") !== -1 || href.indexOf(".md") !== -1) return;
      sessionStorage.setItem(KEY, dir);
    } else if (isPublicListPage()) {
      /* 从全校性列表页进入：清除专业上下文 */
      sessionStorage.removeItem(KEY);
    }
  });

  /* 展开目标链接所属分区，收起其他根级分区；返回顶层分区项 */
  function expandTo(link, root) {
    var foundItem = link.closest(".md-nav__item");
    if (!foundItem) return null;
    var node = foundItem;
    while (node && node !== root) {
      var toggle = node.querySelector(":scope > .md-nav__toggle");
      if (toggle && !toggle.checked) toggle.checked = true;
      node = node.parentElement;
    }
    var topList = root.querySelector(":scope > .md-nav__list");
    if (topList) {
      var topItem = foundItem;
      while (topItem && topItem.parentElement !== topList) topItem = topItem.parentElement;
      var tops = topList.children;
      for (var j = 0; j < tops.length; j++) {
        var item = tops[j];
        if (item && item !== topItem && item.classList.contains("md-nav__item--nested")) {
          var t = item.querySelector(":scope > .md-nav__toggle");
          if (t && t.checked) t.checked = false;
        }
      }
    }
    return foundItem;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var dir = sessionStorage.getItem(KEY);
    /* 方向页自身的导航由 MkDocs Material 按当前页自动高亮，无需应用记录 */
    if (currentRouteDir()) return;
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    if (!root) return;
    var curPath = location.pathname.replace(/\/+$/, "");
    var needle = dir ? "routes/" + dir + "/" : null;
    var found = null;
    var links = root.querySelectorAll(".md-nav__link");
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute("href") || "";
      if (needle) {
        if (href.indexOf(needle) !== -1) { found = links[i]; break; }
      } else {
        var abs = absPath(href).replace(/\/+$/, "");
        if (abs === curPath) { found = links[i]; break; }
      }
    }
    if (!found) return;
    var foundItem = expandTo(found, root);
    if (!foundItem) return;
    /* 高亮本分区内匹配当前 URL 的课程链接，并清除其他位置的高亮 */
    var curLink = null;
    var itemLinks = foundItem.querySelectorAll(".md-nav__link");
    for (var k = 0; k < itemLinks.length; k++) {
      var abs2 = absPath(itemLinks[k].getAttribute("href") || "").replace(/\/+$/, "");
      if (abs2 === curPath) { curLink = itemLinks[k]; break; }
    }
    document.querySelectorAll(".md-nav__item--active").forEach(function (it) {
      if (!foundItem.contains(it)) it.classList.remove("md-nav__item--active");
    });
    if (curLink) {
      var cli = curLink.closest(".md-nav__item");
      if (cli) cli.classList.add("md-nav__item--active");
    }
    foundItem.classList.add("md-nav__item--active");
  });
})();
"""
# 文件名带内容哈希：JS 内容变更时文件名随之变化，避免浏览器缓存旧版脚本
import hashlib as _hashlib
nav_js_name = "dhu_nav." + _hashlib.md5(nav_js.encode("utf-8")).hexdigest()[:8] + ".js"
with io.open(os.path.join(DOCS, "js", nav_js_name), "w", encoding="utf-8") as f:
    f.write(nav_js)

# ---------- copy hand-written static pages back ----------
if os.path.isdir(MANUAL):
    for name in os.listdir(MANUAL):
        src = os.path.join(MANUAL, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(DOCS, name))
    print("manual pages copied:", os.listdir(MANUAL))
img_dir = os.path.join(DOCS, "images")
os.makedirs(img_dir, exist_ok=True)
if os.path.isfile(LOGO_SRC):
    shutil.copy2(LOGO_SRC, os.path.join(img_dir, "logo.jpg"))
    print("logo copied")

# ---------- mkdocs.yml ----------
def nav_course_list(titles, base):
    return [f"      - {t}: {base}/{t}.md" for t in titles]

nav = ["nav:",
       "  - 主页:",
       "    - 首页: index.md",
       "    - 平台贡献指南: guideline.md",
       "    - 本科课程大纲: courses.md",
       "  - 公共基础课程:",
       "    - 导航页: courses/public/index.md",
       "    - 通识教育与公共环节总览: courses/public/fundamental/通识教育.md"]
for sec_name, entries in FUND_SECTIONS:
    titles = [p["title"] for p in all_fund[sec_name]]
    nav.append(f"    - {sec_name}:")
    nav.extend(nav_course_list(titles, "courses/public/fundamental"))
for dirname, major, short, title, sections in ROUTE_SECTIONS:
    # 顶部导航与侧边导航一级标题采用专业缩写（方向页内标题仍为专业全称）
    nav.append(f"  - {short}:")
    nav.append(f"    - 导航页: courses/routes/{dirname}/index.md")
    for sec, rows in route_nav_data[dirname]:
        nav.append(f"    - {sec}:")
        for pt, rel_docs in rows:
            nav.append(f"      - {pt}: {rel_docs}")
nav.append("  - 平台资料:")
nav.append("    - 本科课程大纲: courses.md")

mkdocs_head = f"""site_name: 东华环院课程攻略
site_url: https://dhu-env.github.io/
# 部署到自己的 GitHub Pages 后请将上面的 site_url 改为实际网址（如 https://<用户名>.github.io/<仓库名>/）
exclude_docs: |
  /courses/load.md
  /完善指南.md
extra_css:
  - stylesheets/extra.css
extra_javascript:
  - js/{nav_js_name}
markdown_extensions:
  - pymdownx.pathconverter:
      base_path: ''
      relative_path: ''
      absolute: true
      tags: 'a script img link object embed'
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - attr_list
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - md_in_html
  - pymdownx.blocks.caption
  - tables
theme:
  name: material
  palette:
    - scheme: default
      primary: green
      toggle:
        icon: material/brightness-7
        name: 切换到深色模式
    - scheme: slate
      primary: teal
      toggle:
        icon: material/brightness-4
        name: 切换到浅色模式
  font:
    text: Noto Serif SC
  logo: images/logo.jpg
  favicon: images/logo.jpg
  icon:
    admonition:
      note: fontawesome/solid/note-sticky
      abstract: fontawesome/solid/book
      info: fontawesome/solid/circle-info
      tip: fontawesome/solid/bullhorn
      success: fontawesome/solid/check
      question: fontawesome/solid/circle-question
      warning: fontawesome/solid/triangle-exclamation
      failure: fontawesome/solid/bomb
      danger: fontawesome/solid/skull
      bug: fontawesome/solid/robot
      example: fontawesome/solid/flask
      quote: fontawesome/solid/quote-left
  features:
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.indexes
    - content.tabs.link
plugins:
  - tags
  - search
"""
with io.open(os.path.join(OUT, "mkdocs.yml"), "w", encoding="utf-8") as f:
    f.write(mkdocs_head + "\n" + "\n".join(nav) + "\n")

print("Missing courses:", missing)
print("fund pages:", sum(len(v) for v in all_fund.values()))
print("prof pages:", len(prof_pages))
print("routes:", [(d, sum(len(s) for _, s in route_nav_data[d])) for d, *_ in [(r[0], r) for r in ROUTE_SECTIONS]])
print("splits:", sorted({p['title'] for sec in all_fund.values() for p in sec if '（' in p['title']} |
                        {p['title'] for p in prof_pages if '（' in p['title']}))
