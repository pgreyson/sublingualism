(function() {
    var isReview = location.search.indexOf('review') !== -1;
    var STORAGE_KEY = 'sublingualism_selections';

    function getSelections() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
        catch(e) { return []; }
    }

    function saveSelections(arr) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
    }

    function getVideoSrc(wrap) {
        return wrap.querySelector('iframe').getAttribute('src');
    }

    function isSelected(src) {
        return getSelections().indexOf(src) !== -1;
    }

    function toggleSelection(src) {
        var sel = getSelections();
        var idx = sel.indexOf(src);
        if (idx === -1) { sel.push(src); } else { sel.splice(idx, 1); }
        saveSelections(sel);
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
                saveSelections([]);
                updateCount();
                document.querySelectorAll('.review-btn').forEach(function(btn) {
                    btn.textContent = '+';
                    btn.style.background = 'rgba(0,0,0,0.6)';
                    btn.parentElement.style.outline = 'none';
                });
            }
        });

        var exportBtn = document.createElement('button');
        exportBtn.textContent = 'copy selections';
        exportBtn.style.cssText = 'background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#fff;padding:6px 14px;cursor:pointer;font-size:13px;border-radius:4px;';
        exportBtn.addEventListener('click', function() {
            var sel = getSelections();
            if (sel.length === 0) { alert('No clips selected'); return; }
            var text = JSON.stringify(sel, null, 2);
            navigator.clipboard.writeText(text).then(function() {
                exportBtn.textContent = 'copied!';
                setTimeout(function() { exportBtn.textContent = 'copy selections'; }, 1500);
            });
        });

        btns.appendChild(clearBtn);
        btns.appendChild(exportBtn);
        bar.appendChild(btns);
        document.body.appendChild(bar);
        updateCount();
    }

    function updateCount() {
        if (countEl) {
            var n = getSelections().length;
            countEl.textContent = n + ' clip' + (n !== 1 ? 's' : '') + ' selected';
        }
    }

    // Set up each video wrap
    document.querySelectorAll('.video-wrap').forEach(function(wrap) {
        var iframe = wrap.querySelector('iframe');
        var overlay = wrap.querySelector('.tap-overlay');
        var player = new Vimeo.Player(iframe);
        var isFullscreen = false;
        var src = getVideoSrc(wrap);

        if (isReview) {
            // Add review button
            var btn = document.createElement('button');
            btn.className = 'review-btn';
            btn.style.cssText = 'position:absolute;top:8px;right:8px;z-index:5;width:36px;height:36px;border-radius:50%;border:2px solid rgba(255,255,255,0.7);color:#fff;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;';

            if (isSelected(src)) {
                btn.textContent = '\u2713';
                btn.style.background = 'rgba(0,180,80,0.8)';
                wrap.style.outline = '2px solid rgba(0,180,80,0.6)';
            } else {
                btn.textContent = '+';
                btn.style.background = 'rgba(0,0,0,0.6)';
            }

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                var nowSelected = toggleSelection(src);
                if (nowSelected) {
                    btn.textContent = '\u2713';
                    btn.style.background = 'rgba(0,180,80,0.8)';
                    wrap.style.outline = '2px solid rgba(0,180,80,0.6)';
                } else {
                    btn.textContent = '+';
                    btn.style.background = 'rgba(0,0,0,0.6)';
                    wrap.style.outline = 'none';
                }
            });

            wrap.appendChild(btn);
        }

        // Normal playback behavior
        overlay.addEventListener('click', function() {
            if (!isFullscreen) {
                player.requestFullscreen().then(function() {
                    isFullscreen = true;
                    player.play();
                });
            }
        });

        player.on('fullscreenchange', function(data) {
            isFullscreen = data.fullscreen;
            if (!data.fullscreen) {
                player.pause();
                player.setCurrentTime(0);
            }
        });
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
        // Also preserve on nav links
        document.querySelectorAll('.nav a').forEach(function(a) {
            var href = a.getAttribute('href');
            if (href && href.indexOf('works') !== -1 && href.indexOf('?') === -1) {
                a.setAttribute('href', href + '?review');
            }
        });
    }
})();
