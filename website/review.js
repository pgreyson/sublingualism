(function() {
    var isReview = location.search.indexOf('review') !== -1;
    var ADD_KEY = 'sublingualism_add';
    var REMOVE_KEY = 'sublingualism_remove';

    var path = location.pathname;
    var isCuratedPage = /\/clips\.html/.test(path) || path === '/clips';

    function getList(key) {
        try { return JSON.parse(localStorage.getItem(key)) || []; }
        catch(e) { return []; }
    }
    function saveList(key, arr) {
        localStorage.setItem(key, JSON.stringify(arr));
    }

    function toggleInList(key, src) {
        var list = getList(key);
        var idx = list.indexOf(src);
        if (idx === -1) { list.push(src); } else { list.splice(idx, 1); }
        saveList(key, list);
        updateCount();
        return idx === -1;
    }

    // Floating bar
    var bar, countEl;
    function createBar() {
        bar = document.createElement('div');
        bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:rgba(40,40,40,0.95);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;z-index:1000;backdrop-filter:blur(8px);border-top:1px solid rgba(255,255,255,0.15);';

        countEl = document.createElement('span');
        countEl.style.cssText = 'color:#fff;font-size:14px;opacity:0.8;';
        bar.appendChild(countEl);

        var btns = document.createElement('div');
        btns.style.cssText = 'display:flex;gap:10px;';

        var clearBtn = document.createElement('button');
        clearBtn.textContent = 'clear all';
        clearBtn.style.cssText = 'background:none;border:1px solid rgba(255,255,255,0.3);color:#fff;padding:6px 14px;cursor:pointer;font-size:13px;border-radius:4px;';
        clearBtn.addEventListener('click', function() {
            if (confirm('Clear all selections?')) {
                saveList(ADD_KEY, []);
                saveList(REMOVE_KEY, []);
                updateCount();
                document.querySelectorAll('.review-btn').forEach(function(btn) {
                    if (isCuratedPage) {
                        btn.style.display = 'flex';
                        btn.parentElement.style.outline = 'none';
                        btn.parentElement.style.opacity = '1';
                    } else {
                        btn.textContent = '+';
                        btn.style.background = 'rgba(0,0,0,0.6)';
                        btn.parentElement.style.outline = 'none';
                    }
                });
            }
        });

        var exportBtn = document.createElement('button');
        exportBtn.textContent = 'copy selections';
        exportBtn.style.cssText = 'background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#fff;padding:6px 14px;cursor:pointer;font-size:13px;border-radius:4px;';
        exportBtn.addEventListener('click', function() {
            var adds = getList(ADD_KEY);
            var removes = getList(REMOVE_KEY);
            if (adds.length === 0 && removes.length === 0) { alert('No changes'); return; }
            var output = [];
            adds.forEach(function(src) { output.push({src: src, action: 'add'}); });
            removes.forEach(function(src) { output.push({src: src, action: 'remove'}); });
            var text = JSON.stringify(output, null, 2);
            navigator.clipboard.writeText(text).then(function() {
                exportBtn.textContent = 'copied!';
                setTimeout(function() { exportBtn.textContent = 'copy selections'; }, 1500);
            });
        });

        btns.appendChild(clearBtn);
        btns.appendChild(exportBtn);
        bar.appendChild(btns);
        document.body.appendChild(bar);
        document.body.style.paddingBottom = '60px';
        updateCount();
    }

    function updateCount() {
        if (!countEl) return;
        var a = getList(ADD_KEY).length;
        var r = getList(REMOVE_KEY).length;
        var parts = [];
        if (a > 0) parts.push(a + ' to add');
        if (r > 0) parts.push(r + ' to remove');
        countEl.textContent = parts.length > 0 ? parts.join(', ') : 'no changes';
    }

    // Lazy-load iframes: store src in data-src, load when scrolled into view
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                var iframe = entry.target.querySelector('iframe');
                if (iframe && iframe.dataset.src) {
                    iframe.src = iframe.dataset.src;
                    delete iframe.dataset.src;
                }
                observer.unobserve(entry.target);
            }
        });
    }, { rootMargin: '200px' });

    // Set up each video wrap
    document.querySelectorAll('.video-wrap').forEach(function(wrap) {
        var iframe = wrap.querySelector('iframe');
        var overlay = wrap.querySelector('.tap-overlay');
        var src = iframe.getAttribute('src');

        // Defer loading: move src to data-src
        iframe.dataset.src = src;
        iframe.removeAttribute('src');
        observer.observe(wrap);

        var player = null;
        var isFullscreen = false;

        function getPlayer() {
            if (!player) player = new Vimeo.Player(iframe);
            return player;
        }

        // Review mode buttons
        if (isReview) {
            var btn = document.createElement('button');
            btn.className = 'review-btn';
            btn.style.cssText = 'position:absolute;top:8px;right:8px;z-index:5;width:36px;height:36px;border-radius:50%;border:2px solid rgba(255,255,255,0.7);color:#fff;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;';

            if (isCuratedPage) {
                var isRemoved = getList(REMOVE_KEY).indexOf(src) !== -1;
                btn.innerHTML = '&times;';
                btn.style.background = 'rgba(200,0,0,0.7)';
                if (isRemoved) {
                    wrap.style.opacity = '0.3';
                    wrap.style.outline = '2px solid rgba(200,0,0,0.6)';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowRemoved = toggleInList(REMOVE_KEY, src);
                    if (nowRemoved) {
                        wrap.style.opacity = '0.3';
                        wrap.style.outline = '2px solid rgba(200,0,0,0.6)';
                    } else {
                        wrap.style.opacity = '1';
                        wrap.style.outline = 'none';
                    }
                });
            } else {
                var isAdded = getList(ADD_KEY).indexOf(src) !== -1;
                if (isAdded) {
                    btn.textContent = '\u2713';
                    btn.style.background = 'rgba(0,180,80,0.8)';
                    wrap.style.outline = '2px solid rgba(0,180,80,0.6)';
                } else {
                    btn.textContent = '+';
                    btn.style.background = 'rgba(0,0,0,0.6)';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowAdded = toggleInList(ADD_KEY, src);
                    if (nowAdded) {
                        btn.textContent = '\u2713';
                        btn.style.background = 'rgba(0,180,80,0.8)';
                        wrap.style.outline = '2px solid rgba(0,180,80,0.6)';
                    } else {
                        btn.textContent = '+';
                        btn.style.background = 'rgba(0,0,0,0.6)';
                        wrap.style.outline = 'none';
                    }
                });
            }
            wrap.appendChild(btn);
        }

        // Tap to play fullscreen
        overlay.addEventListener('click', function() {
            if (isFullscreen) return;
            // Make sure iframe is loaded
            if (iframe.dataset.src) {
                iframe.src = iframe.dataset.src;
                delete iframe.dataset.src;
            }
            var p = getPlayer();
            p.requestFullscreen().then(function() {
                isFullscreen = true;
                p.play();
            });
        });

        // Listen for fullscreen exit via Vimeo API
        function setupFsListener() {
            var p = getPlayer();
            p.on('fullscreenchange', function(data) {
                isFullscreen = data.fullscreen;
                if (!data.fullscreen) {
                    p.pause();
                    p.setCurrentTime(0);
                }
            });
        }

        // Set up fullscreen listener once iframe loads
        var origObserve = observer.observe.bind(observer);
        iframe.addEventListener('load', function() {
            if (iframe.src) setupFsListener();
        }, { once: true });
    });

    // Preserve ?review on pagination links
    if (isReview) {
        createBar();
        document.querySelectorAll('.page-nav a').forEach(function(a) {
            var href = a.getAttribute('href');
            if (href && href.indexOf('?') === -1) {
                a.setAttribute('href', href + '?review');
            }
        });
        document.querySelectorAll('.nav a').forEach(function(a) {
            var href = a.getAttribute('href');
            if (href && href.indexOf('clips') !== -1 && href.indexOf('?') === -1) {
                a.setAttribute('href', href + '?review');
            }
        });
    }
})();
