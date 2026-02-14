(function() {
    var COOKIE_NAME = 'sublingualism_review';
    var ADD_KEY = 'sublingualism_add';
    var REMOVE_KEY = 'sublingualism_remove';

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
        return match ? match[1] : null;
    }

    // ?review in URL sets the cookie (bootstrap from mobile)
    if (location.search.indexOf('review') !== -1 && getCookie(COOKIE_NAME) === null) {
        document.cookie = COOKIE_NAME + '=0;path=/;max-age=31536000';
    }

    var hasAccess = getCookie(COOKIE_NAME) !== null;
    var isActive = getCookie(COOKIE_NAME) === '1';

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

    function removeBar() {
        if (bar) {
            bar.remove();
            bar = null;
            countEl = null;
            document.body.style.paddingBottom = '';
        }
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

    // Click-to-fullscreen for all clips
    document.querySelectorAll('.clip').forEach(function(clip) {
        var video = clip.querySelector('video');

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
    });

    // Add/remove review overlay buttons
    function enableReview() {
        document.querySelectorAll('.clip').forEach(function(clip) {
            var videoId = clip.getAttribute('data-id');
            if (!videoId || clip.querySelector('.review-btn')) return;

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
        });
        createBar();
    }

    function disableReview() {
        document.querySelectorAll('.review-btn').forEach(function(btn) {
            btn.remove();
        });
        document.querySelectorAll('.clip').forEach(function(clip) {
            clip.style.outline = 'none';
            clip.style.opacity = '1';
        });
        removeBar();
    }

    // Nav controls
    if (hasAccess) {
        var nav = document.querySelector('.nav');
        if (nav) {
            var controls = document.createElement('div');
            controls.style.cssText = 'display:flex;gap:12px;align-items:center;';

            if (isCuratedPage) {
                var archiveLink = document.createElement('a');
                archiveLink.href = '/clips-all.html';
                archiveLink.textContent = 'archive';
                archiveLink.style.cssText = 'color:#fff;text-decoration:none;opacity:0.7;font-size:0.85rem;';
                archiveLink.onmouseover = function() { this.style.opacity = '1'; };
                archiveLink.onmouseout = function() { this.style.opacity = '0.7'; };
                controls.appendChild(archiveLink);
            }

            var toggleBtn = document.createElement('button');
            toggleBtn.textContent = isActive ? 'review on' : 'review';
            toggleBtn.style.cssText = 'background:none;border:1px solid rgba(255,255,255,0.3);color:#fff;padding:4px 10px;cursor:pointer;font-size:0.8rem;border-radius:3px;opacity:0.7;';
            if (isActive) {
                toggleBtn.style.borderColor = 'rgba(0,180,80,0.6)';
                toggleBtn.style.opacity = '1';
            }
            toggleBtn.addEventListener('click', function() {
                if (isActive) {
                    document.cookie = COOKIE_NAME + '=0;path=/;max-age=31536000';
                    isActive = false;
                    toggleBtn.textContent = 'review';
                    toggleBtn.style.borderColor = 'rgba(255,255,255,0.3)';
                    toggleBtn.style.opacity = '0.7';
                    disableReview();
                } else {
                    document.cookie = COOKIE_NAME + '=1;path=/;max-age=31536000';
                    isActive = true;
                    toggleBtn.textContent = 'review on';
                    toggleBtn.style.borderColor = 'rgba(0,180,80,0.6)';
                    toggleBtn.style.opacity = '1';
                    enableReview();
                }
            });
            controls.appendChild(toggleBtn);
            nav.appendChild(controls);
        }
    }

    // Activate on load if cookie is set
    if (isActive) {
        enableReview();
    }
})();
