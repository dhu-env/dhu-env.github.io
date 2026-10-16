/* 东华环院课程攻略 · 侧边导航"专业上下文保持"脚本
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
    if (href.indexOf("index.html") !== -1 || href.indexOf(".md") !== -1) return;
    /* 判断点击链接所属的顶层导航分区（仅侧边栏链接才有） */
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    var topItem = null;
    if (root) {
      var topList = root.querySelector(":scope > .md-nav__list");
      var it = a.closest(".md-nav__item");
      while (it && topList && it.parentElement !== topList) it = it.parentElement;
      if (it && topList) topItem = it;
    }
    if (topItem) {
      /* 点击侧边栏链接：按目标分区设置专业上下文；公共区等无专业分区则清除 */
      var topLink = topItem.querySelector(":scope > .md-nav__link");
      var th = topLink ? (topLink.getAttribute("href") || "") : "";
      var m = th.match(/routes\/([^\/]+)\//);
      if (m) sessionStorage.setItem(KEY, m[1]);
      else sessionStorage.removeItem(KEY);
      return;
    }
    /* 点击内容区链接（方向页表格、公共列表表格等）：按当前页面更新 */
    var dir = currentRouteDir();
    if (dir) {
      sessionStorage.setItem(KEY, dir);
    } else if (isPublicListPage()) {
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
      if (!href) continue; /* 跳过无链接的导航项（label） */
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
