# -*- coding: utf-8 -*-
"""Parse the 6 teaching-plan docx files into structured course data per major.

Usage:
    python _parse_plans.py                # regenerate _all_courses.json next to this script
Requires the 6 docx files in the same directory as the script.
"""
import re, json, io, os, ast, zipfile
import xml.etree.ElementTree as ET
import _extract_docx as ex

TOOLS = os.path.dirname(os.path.abspath(__file__))
NETROOT = os.path.dirname(os.path.dirname(TOOLS))  # net/ folder containing the original teaching-plan docx files
FILES = {
    "能源与环境系统工程": "2023a能源与环境系统工程_教学计划总揽.docx",
    "环境工程（卓越班）": "2023a环境工程（卓越班）_教学计划总揽.docx",
    "环境工程（双学位）": "2023a环境工程（环境工程与工商管理双学位）_教学计划总揽.docx",
    "环境科学": "2023a环境科学_教学计划总揽.docx",
    "建筑环境与能源应用工程": "2023a建筑环境与能源应用工程_教学计划总揽.docx",
    "土木工程（绿色建造）": "2024a土木工程（绿色建造）_教学计划总揽.docx",
}

def load_table(path):
    text = ex.extract(path)
    for line in text.splitlines():
        if line.startswith('__TABLE__:'):
            return ast.literal_eval(line[len('__TABLE__:'):])
    raise ValueError('no table found')

REQ_MARKERS = {'必修'} | {'选修（至少选修%s学分）' % n for n in ('4.0','5.0','6.0','8.0','9.0','11.0','16.0','23.0')}

def parse_plan(path):
    """Return list of course dicts: {id, name, credit, hours, semester, cat, req}"""
    rows = load_table(path)
    courses = []
    current_cat = ''
    current_req = ''
    for r in rows:
        if len(r) < 6:
            continue
        # r: [课程类别, 课程编号, 课程名称, 学分, 共计, 课内, 课外, 上机, 实验, 1A..4B]
        cat_cell = (r[0] or '').strip()
        id_cell = (r[1] or '').strip()
        name_cell = (r[2] or '').strip()
        if cat_cell in ('通识教育', '学科基础', '专业方向', '综合实践', '实践教学'):
            current_cat = cat_cell
        if id_cell in REQ_MARKERS:
            current_req = '必修' if id_cell == '必修' else '选修'
            continue
        if cat_cell in ('通识教育', '学科基础', '专业方向', '综合实践', '实践教学'):
            continue
        if not name_cell or '小计' in name_cell or '模块' in name_cell:
            continue
        # skip header rows
        if name_cell == '课程名称':
            continue
        try:
            credit = float(r[3])
        except Exception:
            credit = None
        semester = ''
        sem_cells = r[9:17] if len(r) >= 17 else []
        for i, s in enumerate(sem_cells):
            if s:
                labels = ['1A', '1B', '2A', '2B', '3A', '3B', '4A', '4B']
                semester += f"{labels[i]}:{s}; "
        courses.append({
            'id': id_cell, 'name': name_cell, 'credit': credit,
            'h_total': r[4] if len(r) > 4 else '',
            'h_in': r[5] if len(r) > 5 else '',
            'h_out': r[6] if len(r) > 6 else '',
            'h_pc': r[7] if len(r) > 7 else '',
            'h_lab': r[8] if len(r) > 8 else '',
            'semester': semester.strip(),
            'cat': current_cat, 'req': current_req,
        })
    return courses

if __name__ == '__main__':
    out = {}
    for major, fn in FILES.items():
        out[major] = parse_plan(os.path.join(NETROOT, fn))
        print(f"== {major} ({len(out[major])} courses) ==")
    with io.open(os.path.join(TOOLS, '_all_courses.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # print compact inventory
    for major, cs in out.items():
        print('\n###', major)
        for c in cs:
            print(f"  [{c['cat']}|{c['req']}] {c['id']} {c['name']} ({c['credit']})")
