(function() {
    var COOKIE_NAME = 'sublingualism_review';
    var REMOVE_KEY = 'sublingualism_photo_remove';

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
        return match ? match[1] : null;
    }

    if (location.search.indexOf('review') !== -1 && getCookie(COOKIE_NAME) === null) {
        document.cookie = COOKIE_NAME + '=0;path=/;max-age=31536000';
    }

    var hasAccess = getCookie(COOKIE_NAME) !== null;
    var isActive = getCookie(COOKIE_NAME) === '1';

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
                saveList(REMOVE_KEY, []);
                updateCount();
                document.querySelectorAll('.photo-review-btn').forEach(function(btn) {
                    var clip = btn.closest('.clip');
                    clip.style.opacity = '1';
                    btn.style.opacity = '0.5';
                    btn.style.color = '#fff';
                });
            }
        });

        var exportBtn = document.createElement('button');
        exportBtn.textContent = 'copy selections';
        exportBtn.style.cssText = 'background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#fff;padding:6px 14px;cursor:pointer;font-size:13px;border-radius:4px;';
        exportBtn.addEventListener('click', function() {
            var removes = getList(REMOVE_KEY);
            if (removes.length === 0) { alert('No changes'); return; }
            var output = removes.map(function(id) { return {id: id, action: 'remove'}; });
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
        var r = getList(REMOVE_KEY).length;
        countEl.textContent = r > 0 ? r + ' to remove' : 'no changes';
    }

    // ---- PhotoSwipe gallery ----
    var allClips = Array.prototype.slice.call(document.querySelectorAll('.clip'));

    // Load PhotoSwipe CSS
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/photoswipe@5.4.4/dist/photoswipe.css';
    document.head.appendChild(link);

    // Override PhotoSwipe styles for pure black aesthetic
    var style = document.createElement('style');
    style.textContent = '.pswp{--pswp-bg:#000;} .pswp__counter{display:none;}';
    document.head.appendChild(style);

    // Load PhotoSwipe UMD and init gallery
    var script = document.createElement('script');
    script.src = 'https://unpkg.com/photoswipe@5.4.4/dist/umd/photoswipe.umd.min.js';
    script.onload = function() { initGallery(); };
    document.head.appendChild(script);

    function initGallery() {
        allClips.forEach(function(clip, index) {
            clip.addEventListener('click', function(e) {
                if (e.target.classList.contains('photo-review-btn')) return;

                var slides = allClips.map(function(c) {
                    var img = c.querySelector('img');
                    return {
                        src: c.getAttribute('data-src'),
                        width: img && img.naturalWidth ? img.naturalWidth : 1600,
                        height: img && img.naturalHeight ? img.naturalHeight : 1200
                    };
                });

                var options = {
                    dataSource: slides,
                    index: index,
                    bgOpacity: 1,
                    showHideAnimationType: 'fade',
                    closeOnVerticalDrag: true,
                    pinchToClose: true,
                    padding: { top: 0, bottom: 0, left: 0, right: 0 }
                };

                var pswp = new window.PhotoSwipe(options);

                // Caption support
                pswp.on('uiRegister', function() {
                    pswp.ui.registerElement({
                        name: 'custom-caption',
                        order: 9,
                        isButton: false,
                        appendTo: 'root',
                        onInit: function(el) {
                            el.style.cssText = 'position:absolute;bottom:0;left:0;right:0;z-index:10;padding:16px 20px;background:linear-gradient(transparent,rgba(0,0,0,0.8));color:#fff;font-size:0.9rem;font-weight:300;line-height:1.6;opacity:0.8;pointer-events:none;';
                            function updateCaption() {
                                var caption = allClips[pswp.currIndex] ? allClips[pswp.currIndex].getAttribute('data-caption') || '' : '';
                                if (caption) {
                                    el.textContent = caption;
                                    el.style.display = 'block';
                                } else {
                                    el.style.display = 'none';
                                }
                            }
                            pswp.on('change', updateCaption);
                            updateCaption();
                        }
                    });
                });

                pswp.init();
            });
        });
    }

    // ---- Review mode ----
    function enableReview() {
        document.querySelectorAll('.clip').forEach(function(clip) {
            var photoId = clip.getAttribute('data-id');
            if (!photoId || clip.querySelector('.photo-review-btn')) return;

            clip.style.position = 'relative';
            var idx = allClips.indexOf(clip);
            var badge = document.createElement('span');
            badge.className = 'photo-number-badge';
            badge.textContent = idx + 1;
            badge.style.cssText = 'position:absolute;top:8px;left:8px;background:rgba(0,0,0,0.7);color:#fff;font-size:11px;padding:2px 6px;border-radius:3px;z-index:5;font-variant-numeric:tabular-nums;';
            clip.appendChild(badge);
            var btn = document.createElement('button');
            btn.className = 'photo-review-btn';
            btn.style.cssText = 'position:absolute;top:8px;right:8px;width:36px;height:36px;border:none;color:#fff;font-size:18px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;background:rgba(0,0,0,0.5);border-radius:50%;opacity:0.5;z-index:5;';
            btn.innerHTML = '&times;';

            var isRemoved = getList(REMOVE_KEY).indexOf(photoId) !== -1;
            if (isRemoved) {
                clip.style.opacity = '0.3';
                btn.style.opacity = '1';
                btn.style.color = 'rgba(200,0,0,1)';
            }

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                var nowRemoved = toggleInList(REMOVE_KEY, photoId);
                if (nowRemoved) {
                    clip.style.opacity = '0.3';
                    btn.style.opacity = '1';
                    btn.style.color = 'rgba(200,0,0,1)';
                } else {
                    clip.style.opacity = '1';
                    btn.style.opacity = '0.5';
                    btn.style.color = '#fff';
                }
            });
            clip.appendChild(btn);
        });
        createBar();
    }

    function disableReview() {
        document.querySelectorAll('.photo-review-btn').forEach(function(btn) { btn.remove(); });
        document.querySelectorAll('.photo-number-badge').forEach(function(b) { b.remove(); });
        document.querySelectorAll('.clip').forEach(function(clip) {
            clip.style.opacity = '1';
            clip.style.position = '';
        });
        removeBar();
    }

    // Nav controls
    if (hasAccess) {
        var nav = document.querySelector('.nav');
        if (nav) {
            var controls = document.createElement('div');
            controls.style.cssText = 'display:flex;gap:12px;align-items:center;';

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

    if (isActive) {
        enableReview();
    }
})();
