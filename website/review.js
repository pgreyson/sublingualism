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

    function toggleInList(key, id) {
        var list = getList(key);
        var idx = list.indexOf(id);
        if (idx === -1) { list.push(id); } else { list.splice(idx, 1); }
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
                    var clip = btn.closest('.clip');
                    if (isCuratedPage) {
                        clip.style.outline = 'none';
                        clip.style.opacity = '1';
                    } else {
                        btn.textContent = '+';
                        btn.style.background = 'rgba(0,0,0,0.6)';
                        clip.style.outline = 'none';
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
            adds.forEach(function(id) { output.push({id: id, action: 'add'}); });
            removes.forEach(function(id) { output.push({id: id, action: 'remove'}); });
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

    // Click-to-fullscreen and review buttons for all clips
    document.querySelectorAll('.clip').forEach(function(clip) {
        var video = clip.querySelector('video');
        var videoId = clip.getAttribute('data-id');

        clip.addEventListener('click', function(e) {
            if (e.target.classList.contains('review-btn')) return;
            if (video.requestFullscreen) { video.requestFullscreen(); }
            else if (video.webkitEnterFullscreen) { video.webkitEnterFullscreen(); }
            video.muted = false;
            video.play();
        });
        video.addEventListener('fullscreenchange', function() {
            if (!document.fullscreenElement) { video.pause(); video.currentTime = 0; video.muted = true; }
        });
        video.addEventListener('webkitendfullscreen', function() {
            video.pause(); video.currentTime = 0; video.muted = true;
        });

        // Review mode buttons
        if (isReview && videoId) {
            clip.style.position = 'relative';
            var btn = document.createElement('button');
            btn.className = 'review-btn';
            btn.style.cssText = 'position:absolute;top:8px;right:8px;z-index:5;width:36px;height:36px;border-radius:50%;border:2px solid rgba(255,255,255,0.7);color:#fff;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;';

            if (isCuratedPage) {
                var isRemoved = getList(REMOVE_KEY).indexOf(videoId) !== -1;
                btn.innerHTML = '&times;';
                btn.style.background = 'rgba(200,0,0,0.7)';
                if (isRemoved) {
                    clip.style.opacity = '0.3';
                    clip.style.outline = '2px solid rgba(200,0,0,0.6)';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowRemoved = toggleInList(REMOVE_KEY, videoId);
                    if (nowRemoved) {
                        clip.style.opacity = '0.3';
                        clip.style.outline = '2px solid rgba(200,0,0,0.6)';
                    } else {
                        clip.style.opacity = '1';
                        clip.style.outline = 'none';
                    }
                });
            } else {
                var isAdded = getList(ADD_KEY).indexOf(videoId) !== -1;
                if (isAdded) {
                    btn.textContent = '\u2713';
                    btn.style.background = 'rgba(0,180,80,0.8)';
                    clip.style.outline = '2px solid rgba(0,180,80,0.6)';
                } else {
                    btn.textContent = '+';
                    btn.style.background = 'rgba(0,0,0,0.6)';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowAdded = toggleInList(ADD_KEY, videoId);
                    if (nowAdded) {
                        btn.textContent = '\u2713';
                        btn.style.background = 'rgba(0,180,80,0.8)';
                        clip.style.outline = '2px solid rgba(0,180,80,0.6)';
                    } else {
                        btn.textContent = '+';
                        btn.style.background = 'rgba(0,0,0,0.6)';
                        clip.style.outline = 'none';
                    }
                });
            }
            clip.appendChild(btn);
        }
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
