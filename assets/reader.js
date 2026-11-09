/* Общие функции сайта «Токио между нами».
   Подключается в <head> без defer: тема и размер шрифта ставятся до отрисовки,
   остальное — после загрузки страницы. Всё хранится только в браузере читателя. */
(function(){
  var KEY_THEME = 'tbn-theme', KEY_FS = 'tbn-fs', KEY_LAST = 'tbn-last';
  var FS_STEPS = [0.9, 1, 1.1, 1.2, 1.3];
  var root = document.documentElement;

  function get(k){ try { return localStorage.getItem(k); } catch(e){ return null; } }
  function set(k, v){ try { localStorage.setItem(k, v); } catch(e){} }

  // --- до отрисовки ---
  var theme = get(KEY_THEME);
  if (theme === 'dark' || theme === 'light') root.setAttribute('data-theme', theme);
  var fsIdx = parseInt(get(KEY_FS), 10);
  if (isNaN(fsIdx) || fsIdx < 0 || fsIdx >= FS_STEPS.length) fsIdx = 1;
  root.style.setProperty('--fs', FS_STEPS[fsIdx]);

  function isDark(){
    var t = root.getAttribute('data-theme');
    if (t) return t === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function onReady(fn){
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  onReady(function(){
    var m = location.pathname.match(/chapter-(\d+)\.html/);
    var chapterNum = m ? parseInt(m[1], 10) : null;
    var prose = document.querySelector('.prose');

    // --- панель с кнопками ---
    var tools = document.createElement('div');
    tools.className = 'tools';
    function btn(label, title, fn){
      var b = document.createElement('button');
      b.type = 'button'; b.textContent = label; b.title = title; b.setAttribute('aria-label', title);
      b.addEventListener('click', fn); tools.appendChild(b); return b;
    }
    var bMinus, bPlus;
    function syncFs(){
      if (bMinus) bMinus.disabled = fsIdx === 0;
      if (bPlus) bPlus.disabled = fsIdx === FS_STEPS.length - 1;
    }
    if (prose){
      bMinus = btn('А−', 'Уменьшить шрифт', function(){
        if (fsIdx > 0){ fsIdx--; root.style.setProperty('--fs', FS_STEPS[fsIdx]); set(KEY_FS, fsIdx); syncFs(); }
      });
      bPlus = btn('А+', 'Увеличить шрифт', function(){
        if (fsIdx < FS_STEPS.length - 1){ fsIdx++; root.style.setProperty('--fs', FS_STEPS[fsIdx]); set(KEY_FS, fsIdx); syncFs(); }
      });
      syncFs();
    }
    var bTheme = btn('', '', function(){
      var next = isDark() ? 'light' : 'dark';
      root.setAttribute('data-theme', next); set(KEY_THEME, next); syncTheme();
    });
    function syncTheme(){
      var d = isDark();
      bTheme.textContent = d ? '☀' : '☾';
      var t = d ? 'Светлая тема' : 'Тёмная тема';
      bTheme.title = t; bTheme.setAttribute('aria-label', t);
    }
    syncTheme();

    var back = document.querySelector('.page > .back');
    var bar = document.createElement('div');
    bar.className = 'topbar';
    if (back){
      back.parentNode.insertBefore(bar, back);
      bar.appendChild(back);
    } else {
      bar.className += ' only-tools';
      var page = document.querySelector('.page');
      if (page) page.insertBefore(bar, page.firstChild);
    }
    bar.appendChild(tools);

    // --- только на главах ---
    if (chapterNum && prose){
      var title = document.querySelector('h1.chapter-title');

      // время чтения (≈180 слов в минуту)
      var words = (prose.innerText || '').split(/\s+/).filter(Boolean).length;
      var mins = Math.max(1, Math.round(words / 180));
      if (title){
        var rt = document.createElement('p');
        rt.className = 'readtime';
        rt.textContent = '≈ ' + mins + ' мин чтения';
        title.parentNode.insertBefore(rt, title.nextSibling);
      }

      // полоса прогресса + сохранение места
      var bar2 = document.createElement('div');
      bar2.className = 'read-progress';
      document.body.appendChild(bar2);
      var name = title ? title.textContent.trim() : '';
      var saveTimer = null;
      function pct(){
        var top = prose.getBoundingClientRect().top + window.scrollY;
        var h = prose.offsetHeight - window.innerHeight * 0.6;
        if (h <= 0) return 1;
        return Math.min(1, Math.max(0, (window.scrollY - top + window.innerHeight * 0.4) / h));
      }
      function onScroll(){
        var p = pct();
        bar2.style.width = (p * 100).toFixed(1) + '%';
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(function(){
          set(KEY_LAST, JSON.stringify({ n: chapterNum, name: name, p: Math.round(p * 1000) / 1000, t: Date.now() }));
        }, 400);
      }
      window.addEventListener('scroll', onScroll, { passive: true });

      // вернуться к месту, если пришли по кнопке «Продолжить»
      if (location.hash === '#resume'){
        try {
          var last = JSON.parse(get(KEY_LAST) || 'null');
          if (last && last.n === chapterNum && last.p > 0.02){
            var top = prose.getBoundingClientRect().top + window.scrollY;
            var y = top + last.p * (prose.offsetHeight - window.innerHeight * 0.6) - window.innerHeight * 0.4;
            window.scrollTo(0, Math.max(0, y));
          }
        } catch(e){}
        if (history.replaceState) history.replaceState(null, '', location.pathname);
      }
      onScroll();
    }

    // --- главная: «Продолжить чтение» ---
    var toc = document.querySelector('ul.toc');
    if (toc && !chapterNum){
      var last;
      try { last = JSON.parse(get(KEY_LAST) || 'null'); } catch(e){ last = null; }
      if (last && last.n){
        function pad(n){ return (n < 10 ? '0' : '') + n; }
        var finished = last.p >= 0.97;
        var target = last.n, label = 'Продолжить чтение', href;
        if (finished){
          var next = toc.querySelector('a[href="chapter-' + pad(last.n + 1) + '.html"]');
          if (next){ target = last.n + 1; label = 'Следующая глава'; href = 'chapter-' + pad(target) + '.html'; }
          else { label = 'Вы дочитали главу ' + last.n; href = 'chapter-' + pad(last.n) + '.html'; }
        } else {
          href = 'chapter-' + pad(last.n) + '.html#resume';
        }
        var link = toc.querySelector('a[href="chapter-' + pad(target) + '.html"] .title');
        var a = document.createElement('a');
        a.className = 'resume';
        a.href = href;
        a.innerHTML = '<span class="resume-label"></span><span class="resume-title"></span>';
        a.querySelector('.resume-label').textContent = label;
        a.querySelector('.resume-title').textContent = 'Глава ' + target + (link ? ' · ' + link.textContent.trim() : '') + ' →';
        var anchor = document.querySelector('.byline') || document.querySelector('.toc-label');
        if (anchor && anchor.classList.contains('byline')) anchor.parentNode.insertBefore(a, anchor.nextSibling);
        else (anchor || toc).parentNode.insertBefore(a, anchor || toc);
      }
    }
  });
})();
