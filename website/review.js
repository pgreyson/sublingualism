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

    // Fullscreen playback with swipe navigation
    var allClips = Array.prototype.slice.call(document.querySelectorAll('.clip'));
    var overlay = null;
    var videoA = null;
    var videoB = null;
    var activeVideo = null;
    var currentIndex = -1;
    var savedScrollY = 0;

    function getClipSrc(index) {
        return allClips[index].querySelector('video').getAttribute('src');
    }

    function getClipPoster(index) {
        return allClips[index].querySelector('video').getAttribute('poster') || '';
    }

    function createOverlay() {
        // Inject style tag for overlay
        var style = document.createElement('style');
        style.textContent = '.overlay-open{position:fixed!important;width:100%!important;overflow:hidden!important;}';
        document.head.appendChild(style);

        overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:9999;display:none;align-items:center;justify-content:center;touch-action:none;overflow:hidden;';

        var vidStyle = 'position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain;';
        videoA = document.createElement('video');
        videoA.style.cssText = vidStyle;
        videoA.setAttribute('loop', '');
        videoA.setAttribute('playsinline', '');
        videoA.setAttribute('preload', 'auto');

        videoB = document.createElement('video');
        videoB.style.cssText = vidStyle + 'opacity:0;';
        videoB.setAttribute('loop', '');
        videoB.setAttribute('playsinline', '');
        videoB.setAttribute('preload', 'auto');

        overlay.appendChild(videoA);
        overlay.appendChild(videoB);
        activeVideo = videoA;

        // Close button
        var closeBtn = document.createElement('div');
        closeBtn.style.cssText = 'position:absolute;top:12px;right:16px;z-index:10;color:#fff;font-size:28px;opacity:0.6;cursor:pointer;padding:8px;line-height:1;';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            closeOverlay();
        });
        overlay.appendChild(closeBtn);

        // Touch swipe handling
        var touchStartX = 0;
        var touchStartY = 0;
        var touchStartTime = 0;
        var swiping = false;

        overlay.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            swiping = false;
        }, {passive: true});

        overlay.addEventListener('touchmove', function(e) {
            var dx = e.touches[0].clientX - touchStartX;
            var dy = e.touches[0].clientY - touchStartY;
            if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 20) {
                swiping = true;
                e.preventDefault();
            }
        }, {passive: false});

        overlay.addEventListener('touchend', function(e) {
            var dx = e.changedTouches[0].clientX - touchStartX;
            var dy = e.changedTouches[0].clientY - touchStartY;
            var dt = Date.now() - touchStartTime;

            if (swiping && Math.abs(dx) > 50 && dt < 500) {
                if (dx < 0 && currentIndex < allClips.length - 1) {
                    showClip(currentIndex + 1);
                } else if (dx > 0 && currentIndex > 0) {
                    showClip(currentIndex - 1);
                }
                return;
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (currentIndex === -1) return;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                if (currentIndex < allClips.length - 1) showClip(currentIndex + 1);
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                if (currentIndex > 0) showClip(currentIndex - 1);
            } else if (e.key === 'Escape') {
                closeOverlay();
            }
        });

        document.body.appendChild(overlay);
    }

    function showClip(index) {
        currentIndex = index;
        var src = getClipSrc(index);
        var poster = getClipPoster(index);
        var nextVideo = (activeVideo === videoA) ? videoB : videoA;

        // Set poster on next video so there's an image immediately
        nextVideo.poster = poster;
        nextVideo.src = src;
        nextVideo.muted = false;

        var playWhenReady = function() {
            // Swap: show next, hide current
            nextVideo.style.opacity = '1';
            activeVideo.style.opacity = '0';
            activeVideo.pause();
            activeVideo = nextVideo;
            nextVideo.removeEventListener('canplay', playWhenReady);
        };

        // If it can play immediately, swap now; otherwise wait
        if (nextVideo.readyState >= 3) {
            nextVideo.play();
            playWhenReady();
        } else {
            // Show poster immediately via opacity swap, start playing when ready
            nextVideo.style.opacity = '1';
            activeVideo.style.opacity = '0';
            activeVideo.pause();
            activeVideo = nextVideo;
            nextVideo.addEventListener('canplay', function onCanPlay() {
                nextVideo.play();
                nextVideo.removeEventListener('canplay', onCanPlay);
            });
            nextVideo.load();
        }

        // Preload adjacent clips
        preloadClip(index - 1);
        preloadClip(index + 1);
    }

    var preloadCache = {};
    function preloadClip(index) {
        if (index < 0 || index >= allClips.length || preloadCache[index]) return;
        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = getClipSrc(index).replace('#t=0.001', '');
        document.head.appendChild(link);
        preloadCache[index] = true;
    }

    function openOverlay(index) {
        if (!overlay) createOverlay();
        savedScrollY = window.scrollY;
        document.body.classList.add('overlay-open');
        document.body.style.top = -savedScrollY + 'px';
        overlay.style.display = 'flex';

        // Reset both videos
        videoA.style.opacity = '1';
        videoB.style.opacity = '0';
        activeVideo = videoA;

        var src = getClipSrc(index);
        var poster = getClipPoster(index);
        currentIndex = index;
        videoA.poster = poster;
        videoA.src = src;
        videoA.muted = false;
        videoA.play();

        preloadClip(index - 1);
        preloadClip(index + 1);
    }

    function closeOverlay() {
        if (!overlay || currentIndex === -1) return;
        videoA.pause();
        videoB.pause();
        videoA.removeAttribute('src');
        videoB.removeAttribute('src');
        videoA.load();
        videoB.load();
        overlay.style.display = 'none';
        document.body.classList.remove('overlay-open');
        document.body.style.top = '';
        window.scrollTo(0, savedScrollY);
        currentIndex = -1;
    }

    // Click-to-play for all clips
    allClips.forEach(function(clip, index) {
        clip.addEventListener('click', function(e) {
            if (e.target.classList.contains('review-btn')) return;
            openOverlay(index);
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
