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

  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href === "#" || href.indexOf("#") === 0) return;
    var dir = currentRouteDir();
    if (dir) {
      if (/\/courses\//.test(href) && href.indexOf("index.html") === -1 &&
          href.indexOf(".md") === -1 && href.indexOf("guideline") === -1) {
        sessionStorage.setItem(KEY, dir);
      }
    } else if (isPublicListPage()) {
      sessionStorage.removeItem(KEY);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var dir = sessionStorage.getItem(KEY);
    if (!dir) return;
    var needle = "routes/" + dir + "/";
    var root = document.querySelector('.md-nav[data-md-level="0"]');
    if (!root) return;
    var links = root.querySelectorAll(".md-nav__link");
    var found = null;
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute("href") || "";
      if (href.indexOf(needle) !== -1) { found = links[i]; break; }
    }
    if (!found) return;
    var foundItem = found.closest(".md-nav__item");
    if (!foundItem) return;
    var node = foundItem;
    while (node && node !== root) {
      var toggle = node.querySelector(":scope > .md-nav__toggle");
      if (toggle && !toggle.checked) toggle.checked = true;
      node = node.parentElement;
    }
    var topList = root.querySelector(":scope > .md-nav__list");
    if (topList) {
      var tops = topList.children;
      for (var j = 0; j < tops.length; j++) {
        var item = tops[j];
        if (item && item !== foundItem && item.classList.contains("md-nav__item--nested")) {
          var t = item.querySelector(":scope > .md-nav__toggle");
          if (t && t.checked) t.checked = false;
        }
      }
    }
    var curPath = location.pathname.replace(/\/+$/, "");
    var curLink = null;
    var itemLinks = foundItem.querySelectorAll(".md-nav__link");
    for (var k = 0; k < itemLinks.length; k++) {
      var h = (itemLinks[k].getAttribute("href") || "").replace(/\/+$/, "").split("#")[0].split("?")[0];
      if (h === curPath) { curLink = itemLinks[k]; break; }
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
