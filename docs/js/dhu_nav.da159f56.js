/* 东华环院课程攻略 · 侧边导航"展开状态保持"脚本
 * 目标：点击课程进入对应页面后，侧边导航保持点击时的展开状态——不自动收起、
 *       不跳转到其他专业。例如在"公共基础课程 → 力学类"展开状态下点击"理论力学(1)"，
 *       打开课程页后侧边栏仍保持"公共基础课程"展开（含力学类）。
 * 机制：点击链接时记录"当前所在顶层分区"（公共基础课程或某专业缩写，点击顶部 tab
 *       时按目标 URL 记录目标分区），存入 sessionStorage；课程页加载时展开该顶层
 *       及全部子分区。列表/导航页（URL 末段不是任何课程名）不做干预，并清除记录。 */
(function () {
  "use strict";
  var KEY = "dhu-nav-top";
  /* 专业目录名 → 顶部/侧边导航使用的缩写（顶层分区 label 文本） */
  var DIR_SHORT = {
    "EnergyEnv": "能环", "EnvEngExcellent": "环卓", "EnvEngDual": "环管",
    "EnvScience": "环科", "BuildingEnv": "建环", "CivilGreen": "土木"
  };

  /* 把相对 href 解析为绝对路径（用于与 location.pathname 比对） */
  function absPath(href) {
    var a = document.createElement("a");
    a.href = href;
    return a.pathname;
  }

  /* 禁用侧边导航的展开/收起过渡动画，消除点击跳转后的视觉延迟与跳动 */
  (function () {
    var st = document.createElement("style");
    st.textContent = ".md-nav__toggle:checked ~ .md-nav, .md-nav__item--nested > .md-nav { transition: none !important; }";
    (document.head || document.documentElement).appendChild(st);
  })();

  /* 快照当前侧边导航的展开状态：每个顶层分区下已展开的子分区 label 列表 */
  function snapshotState() {
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    if (!root) return;
    var state = {};
    var topList = root.querySelector(":scope > .md-nav__list");
    if (!topList) return;
    var tops = topList.children;
    for (var k = 0; k < tops.length; k++) {
      var ti = tops[k];
      if (!ti.classList.contains("md-nav__item--nested")) continue;
      var lb = ti.querySelector(":scope > .md-nav__link");
      var topLabel = (lb && (lb.textContent || "").trim()) || "";
      if (!topLabel) continue;
      var openSubs = [];
      var subToggles = ti.querySelectorAll(".md-nav__item--nested > .md-nav__toggle");
      for (var q = 0; q < subToggles.length; q++) {
        if (subToggles[q].checked) {
          var sli = subToggles[q].closest(".md-nav__item");
          var slb = sli.querySelector(":scope > .md-nav__link");
          var s = (slb && (slb.textContent || "").trim()) || "";
          if (s && openSubs.indexOf(s) === -1) openSubs.push(s);
        }
      }
      state[topLabel] = openSubs;
    }
    try { sessionStorage.setItem("dhu-nav-state", JSON.stringify(state)); } catch (e) {}
  }

  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href === "#" || href.indexOf("#") === 0 || href.indexOf("http") === 0) return;
    if (href.indexOf("index.html") !== -1 || href.indexOf(".md") !== -1) return;
    /* 先快照当前展开状态（记住用户手动展开的分区），再记录目标顶层 */
    snapshotState();
    /* 按目标链接所属分区记录顶层：
       - 指向某专业课程/方向页（/courses/routes/<专业>/…）→ 该专业缩写
       - 指向公共基础课程（/courses/public/…，含课程页与列表页）→ 公共基础课程
       - 其他（主页等）→ 清除 */
    var tAbs = absPath(href);
    var m = tAbs.match(/\/courses\/routes\/([^\/]+)\//);
    if (m && DIR_SHORT[m[1]]) { sessionStorage.setItem(KEY, DIR_SHORT[m[1]]); return; }
    if (tAbs.indexOf("/courses/public/") !== -1) { sessionStorage.setItem(KEY, "公共基础课程"); return; }
    if (tAbs.indexOf("/courses/") !== -1) { sessionStorage.setItem(KEY, "公共基础课程"); return; }
    sessionStorage.removeItem(KEY);
  });

  /* 同层互斥：展开某个子分区（数理类/化学类/…）时，自动收起同一层的其他子分区。
     仅处理顶层之下的子分区；顶层 tab 由 Material 管理，不干预。
     程序化恢复展开状态不触发 change 事件，因此不影响"记住展开状态"逻辑。 */
  document.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains("md-nav__toggle")) return;
    if (!t.checked) return;
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    if (!root) return;
    var item = t.closest(".md-nav__item");
    if (!item) return;
    var topList = root.querySelector(":scope > .md-nav__list");
    if (!topList) return;
    var isTop = false;
    var it = item;
    while (it && topList && it.parentElement !== topList) it = it.parentElement;
    if (it === item) isTop = true; /* item 本身就是顶层分区 */
    if (isTop) return;
    var container = item.parentElement;
    if (!container) return;
    var siblings = container.querySelectorAll(":scope > .md-nav__item > .md-nav__toggle");
    for (var q = 0; q < siblings.length; q++) {
      if (siblings[q] !== t && siblings[q].checked) siblings[q].checked = false;
    }
  });

  /* 展开单个顶层分区路径上的所有折叠开关 */
  function expandTop(topItem, root) {
    if (!topItem) return;
    var node = topItem;
    while (node && node !== root) {
      var toggle = node.querySelector(":scope > .md-nav__toggle");
      if (toggle && !toggle.checked) toggle.checked = true;
      node = node.parentElement;
    }
  }

  /* 找到链接所属的顶层分区 */
  function topOf(link, root) {
    var topList = root.querySelector(":scope > .md-nav__list");
    var it = link.closest(".md-nav__item");
    while (it && topList && it.parentElement !== topList) it = it.parentElement;
    return it && topList ? it : null;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    if (!root) return;
    var curPath = location.pathname.replace(/\/+$/, "");
    var topList = root.querySelector(":scope > .md-nav__list");
    if (!topList) return;
    var links = root.querySelectorAll(".md-nav__link");
    var courseName = decodeURIComponent((curPath.split("/").pop() || "").replace(/\.html?$/, ""));
    /* 列表/导航页（URL 末段不是任何课程名）：由 Material 按当前页自动处理，
       同时清除残留的顶层上下文，避免直开列表页时侧边栏停留在旧专业 */
    var isListPage = true;
    for (i = 0; i < links.length; i++) {
      if ((links[i].textContent || "").trim() === courseName) { isListPage = false; break; }
    }
    if (isListPage) { sessionStorage.removeItem(KEY); return; }
    var ctx = sessionStorage.getItem(KEY);
    /* 课程标题带专业括号（如“工程热力学（能环）”“流体力学（建环）”等分设页面）：
       这些是专业课程（虽建在公共基础课程目录），一律按括号内专业展开对应分区，
       不随目标链接的物理目录跳到公共基础课程。 */
    var bracketShort = null;
    var bm = courseName.match(/（([^（）]+)）\s*$/);
    if (bm) bracketShort = bm[1];
    var shortSet = {};
    for (var sd in DIR_SHORT) shortSet[DIR_SHORT[sd]] = 1;
    if (bracketShort && shortSet[bracketShort]) ctx = bracketShort;
    var wantTops = [];
    var i, href, abs;
    if (ctx) {
      /* 有上下文：按顶层分区 label 文本（公共基础课程/专业缩写）直接定位并展开该分区。
         不依赖 href 匹配：方向页课程页内同分区链接为相对短路径，不含 "routes/<dir>/" 子串，
         旧 href 匹配会失败导致 Material 默认展开其他分区。 */
      var topChildren = topList.children;
      for (var p = 0; p < topChildren.length; p++) {
        var ti = topChildren[p];
        if (!ti || !ti.classList.contains("md-nav__item--nested")) continue;
        var lb = ti.querySelector(":scope > .md-nav__link");
        var txt = (lb && (lb.textContent || "") || "").trim();
        if (txt === ctx) { wantTops.push(ti); break; }
      }
    } else {
      /* 无上下文（直开/刷新）：课程页按课程名匹配展开所有归属顶层分区
         （Material 会把当前页条目 href 改写为 "./"，因此不能依赖 href 匹配当前页） */
      var seen = {};
      for (i = 0; i < links.length; i++) {
        if ((links[i].textContent || "").trim() !== courseName) continue;
        var t2 = topOf(links[i], root);
        if (t2) {
          /* 顶层分区唯一标识：分区 label 的 id（如 __nav_5_label），避免不同分区被折叠为同一 key */
          var lb2 = t2.querySelector(":scope > .md-nav__link");
          var key = (lb2 && lb2.id) || t2.id || "top";
          if (!seen[key]) { seen[key] = 1; wantTops.push(t2); }
        }
      }
      /* 兜底：课程名匹配不到时回退到 href 匹配（./ 目录回退链接） */
      if (!wantTops.length) {
        for (i = 0; i < links.length; i++) {
          href = links[i].getAttribute("href") || "";
          if (!href) continue;
          abs = absPath(href).replace(/\/+$/, "");
          if (abs !== curPath) continue;
          var t4 = topOf(links[i], root);
          if (t4 && wantTops.indexOf(t4) === -1) wantTops.push(t4);
        }
      }
    }
    if (!wantTops.length) return;
    /* 展开目标顶层分区；子分区按点击时快照的展开状态恢复（不强制全展开），
       避免把用户未展开的分区也一并展开 */
    wantTops.forEach(function (ti) { expandTop(ti, root); });
    var savedState = {};
    try { savedState = JSON.parse(sessionStorage.getItem("dhu-nav-state") || "{}"); } catch (e) {}
    var openSubs = savedState[ctx] || [];
    if (openSubs.length) {
      wantTops.forEach(function (ti) {
        var subToggles = ti.querySelectorAll(".md-nav__item--nested > .md-nav__toggle");
        for (var q = 0; q < subToggles.length; q++) {
          var sli = subToggles[q].closest(".md-nav__item");
          var slb = sli.querySelector(":scope > .md-nav__link");
          if ((slb && (slb.textContent || "").trim()) && openSubs.indexOf((slb.textContent || "").trim()) !== -1) {
            subToggles[q].checked = true;
          }
        }
      });
    }
    /* 高亮：各展开分区内课程名匹配当前课程的链接，清除其它高亮 */
    var keepItems = [];
    wantTops.forEach(function (ti) {
      var itemLinks = ti.querySelectorAll(".md-nav__link");
      for (var k = 0; k < itemLinks.length; k++) {
        if ((itemLinks[k].textContent || "").trim() !== courseName) continue;
        var cli = itemLinks[k].closest(".md-nav__item");
        if (cli && keepItems.indexOf(cli) === -1) {
          cli.classList.add("md-nav__item--active");
          keepItems.push(cli);
        }
      }
    });
    document.querySelectorAll(".md-nav__item--active").forEach(function (it) {
      if (keepItems.indexOf(it) === -1) it.classList.remove("md-nav__item--active");
    });
    wantTops.forEach(function (ti) { ti.classList.add("md-nav__item--active"); });
  });
})();
