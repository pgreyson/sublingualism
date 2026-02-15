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
                        clip.style.opacity = '1';
                        btn.style.opacity = '0.5';
                        btn.style.color = '#fff';
                    } else {
                        btn.textContent = '+';
                        btn.style.opacity = '0.5';
                        btn.style.color = '#fff';
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

    // Fullscreen playback with swipe-to-slide navigation
    var allClips = Array.prototype.slice.call(document.querySelectorAll('.clip'));
    var overlay = null;
    var track = null;        // sliding track with 3 panels
    var panels = [];         // [prev, current, next] panel elements
    var panelVideos = [];    // video element in each panel
    var currentIndex = -1;
    var savedScrollY = 0;
    var viewW = 0;

    function getClipSrc(index) {
        return allClips[index].querySelector('video').getAttribute('src');
    }

    function createOverlay() {
        var style = document.createElement('style');
        style.textContent = '.overlay-open{position:fixed!important;width:100%!important;overflow:hidden!important;}';
        document.head.appendChild(style);

        overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:9999;display:none;touch-action:none;overflow:hidden;';

        // Track holds 3 panels side by side; we translate it to slide
        track = document.createElement('div');
        track.style.cssText = 'display:flex;height:100%;will-change:transform;';

        for (var i = 0; i < 3; i++) {
            var panel = document.createElement('div');
            panel.style.cssText = 'height:100%;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:#000;';
            var vid = document.createElement('video');
            vid.style.cssText = 'width:100%;height:100%;object-fit:contain;';
            vid.setAttribute('loop', '');
            vid.setAttribute('playsinline', '');
            vid.setAttribute('preload', 'auto');
            panel.appendChild(vid);
            track.appendChild(panel);
            panels.push(panel);
            panelVideos.push(vid);
        }

        overlay.appendChild(track);

        // Close button
        var closeBtn = document.createElement('div');
        closeBtn.style.cssText = 'position:absolute;top:12px;right:16px;z-index:10;color:#fff;font-size:28px;opacity:0.6;cursor:pointer;padding:8px;line-height:1;';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            closeOverlay();
        });
        overlay.appendChild(closeBtn);

        // Add button — single centered button at bottom
        var overlayAddBtn = document.createElement('button');
        overlayAddBtn.className = 'overlay-add-btn';
        overlayAddBtn.style.cssText = 'position:absolute;bottom:16px;left:50%;transform:translateX(-50%);z-index:10;width:44px;height:44px;border-radius:50%;border:2px solid rgba(255,255,255,0.7);color:#fff;font-size:24px;line-height:1;cursor:pointer;display:none;align-items:center;justify-content:center;padding:0;';

        overlayAddBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (currentIndex === -1) return;
            var videoId = allClips[currentIndex].getAttribute('data-id');
            var nowAdded = toggleInList(ADD_KEY, videoId);
            updateOverlayAddBtns();
            // Also sync the page-level review button if it exists
            var pageClip = allClips[currentIndex];
            var pageBtn = pageClip.querySelector('.review-btn');
            if (pageBtn) {
                if (nowAdded) {
                    pageBtn.textContent = '\u2713';
                    pageBtn.style.background = 'rgba(0,180,80,0.8)';
                    pageClip.style.outline = '2px solid rgba(0,180,80,0.6)';
                } else {
                    pageBtn.textContent = '+';
                    pageBtn.style.background = 'rgba(0,0,0,0.6)';
                    pageClip.style.outline = 'none';
                }
            }
        });
        overlay.appendChild(overlayAddBtn);

        // Touch handling — drag the track with finger
        var touchStartX = 0;
        var touchStartY = 0;
        var touchStartTime = 0;
        var dragging = false;
        var dragOffset = 0;
        var directionLocked = false;

        overlay.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            dragging = false;
            directionLocked = false;
            dragOffset = 0;
            track.style.transition = 'none';
        }, {passive: true});

        overlay.addEventListener('touchmove', function(e) {
            var dx = e.touches[0].clientX - touchStartX;
            var dy = e.touches[0].clientY - touchStartY;

            if (!directionLocked) {
                if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                    directionLocked = true;
                    dragging = Math.abs(dx) > Math.abs(dy);
                }
            }

            if (dragging) {
                e.preventDefault();
                dragOffset = dx;
                // Clamp: don't drag past edges
                if (currentIndex === 0 && dx > 0) dx = dx * 0.3;
                if (currentIndex === allClips.length - 1 && dx < 0) dx = dx * 0.3;
                var baseOffset = -viewW;  // center panel
                track.style.transform = 'translateX(' + (baseOffset + dx) + 'px)';
            }
        }, {passive: false});

        overlay.addEventListener('touchend', function(e) {
            var dx = e.changedTouches[0].clientX - touchStartX;
            var dt = Date.now() - touchStartTime;
            var velocity = Math.abs(dx) / dt;

            if (dragging) {
                var threshold = viewW * 0.25;
                var swipedFast = velocity > 0.3 && Math.abs(dx) > 30;

                if ((Math.abs(dx) > threshold || swipedFast) && dx < 0 && currentIndex < allClips.length - 1) {
                    // Swipe left — go to next
                    animateToPanel(2, function() {
                        setCurrentClip(currentIndex + 1, 1);
                    });
                } else if ((Math.abs(dx) > threshold || swipedFast) && dx > 0 && currentIndex > 0) {
                    // Swipe right — go to prev
                    animateToPanel(0, function() {
                        setCurrentClip(currentIndex - 1, -1);
                    });
                } else {
                    // Snap back to center
                    animateToPanel(1);
                }
            }

            dragging = false;
        });

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (currentIndex === -1) return;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                if (currentIndex < allClips.length - 1) {
                    animateToPanel(2, function() {
                        setCurrentClip(currentIndex + 1, 1);
                    });
                }
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                if (currentIndex > 0) {
                    animateToPanel(0, function() {
                        setCurrentClip(currentIndex - 1, -1);
                    });
                }
            } else if (e.key === 'Escape') {
                closeOverlay();
            }
        });

        document.body.appendChild(overlay);
    }

    function updateOverlayAddBtns() {
        var btn = overlay ? overlay.querySelector('.overlay-add-btn') : null;
        if (!btn || currentIndex === -1) return;
        var videoId = allClips[currentIndex].getAttribute('data-id');
        var isAdded = getList(ADD_KEY).indexOf(videoId) !== -1;
        btn.style.display = isActive ? 'flex' : 'none';
        if (isAdded) {
            btn.textContent = '\u2713';
            btn.style.background = 'rgba(0,180,80,0.8)';
        } else {
            btn.textContent = '+';
            btn.style.background = 'rgba(0,0,0,0.6)';
        }
    }

    function animateToPanel(panelIndex, callback) {
        var targetX = -panelIndex * viewW;
        track.style.transition = 'transform 0.25s ease-out';
        track.style.transform = 'translateX(' + targetX + 'px)';
        if (callback) {
            var done = false;
            var finish = function() {
                if (done) return;
                done = true;
                track.removeEventListener('transitionend', finish);
                callback();
            };
            track.addEventListener('transitionend', finish);
            // Fallback in case transitionend doesn't fire
            setTimeout(finish, 300);
        }
    }

    function loadPanel(panelIndex, clipIndex, skipIfLoaded) {
        var vid = panelVideos[panelIndex];
        if (clipIndex < 0 || clipIndex >= allClips.length) {
            vid.removeAttribute('src');
            vid.load();
            return;
        }
        var src = getClipSrc(clipIndex);
        if (vid.getAttribute('src') === src && skipIfLoaded) return;
        if (vid.getAttribute('src') !== src) {
            vid.src = src;
            vid.preload = 'auto';
        }
        vid.muted = true;
        vid.currentTime = 0;
        // Force mobile Safari to fetch and decode the first frame
        var playPromise = vid.play();
        if (playPromise) {
            playPromise.then(function() {
                vid.pause();
                vid.currentTime = 0;
            }).catch(function() {});
        }
    }

    // direction: 0 = initial load, 1 = swiped to next, -1 = swiped to prev
    function setCurrentClip(index, direction) {
        currentIndex = index;

        if (direction === 1) {
            // Swiped to next: panel 2 has the clip we want, swap it to center
            var tmpVid = panelVideos[0];
            panelVideos[0] = panelVideos[1];
            panelVideos[1] = panelVideos[2];
            panelVideos[2] = tmpVid;
            // Physically reorder DOM elements in the track
            track.appendChild(panelVideos[0].parentNode);
            track.appendChild(panelVideos[1].parentNode);
            track.appendChild(panelVideos[2].parentNode);
            // Snap to center instantly
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
            // Panel 1 (center) already has the right video playing — don't touch it
            // Just load the new next panel
            loadPanel(0, index - 1, true);
            loadPanel(2, index + 1);
        } else if (direction === -1) {
            // Swiped to prev: panel 0 has the clip we want, swap it to center
            var tmpVid2 = panelVideos[2];
            panelVideos[2] = panelVideos[1];
            panelVideos[1] = panelVideos[0];
            panelVideos[0] = tmpVid2;
            track.appendChild(panelVideos[0].parentNode);
            track.appendChild(panelVideos[1].parentNode);
            track.appendChild(panelVideos[2].parentNode);
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
            loadPanel(0, index - 1);
            loadPanel(2, index + 1, true);
        } else {
            // Initial load
            loadPanel(0, index - 1);
            loadPanel(1, index);
            loadPanel(2, index + 1);
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
        }

        // Play center video
        var vid = panelVideos[1];
        vid.muted = false;
        vid.play();

        // Update overlay add buttons for current clip
        updateOverlayAddBtns();
    }

    function updateViewW() {
        viewW = overlay.clientWidth;
        track.style.width = (viewW * 3) + 'px';
        for (var i = 0; i < panelVideos.length; i++) {
            panelVideos[i].parentNode.style.width = viewW + 'px';
        }
    }

    function openOverlay(index) {
        if (!overlay) createOverlay();
        savedScrollY = window.scrollY;
        document.body.classList.add('overlay-open');
        document.body.style.top = -savedScrollY + 'px';
        overlay.style.display = 'block';
        updateViewW();

        setCurrentClip(index, 0);
    }

    function closeOverlay() {
        if (!overlay || currentIndex === -1) return;
        panelVideos.forEach(function(v) { v.pause(); v.removeAttribute('src'); v.load(); });
        overlay.style.display = 'none';
        document.body.classList.remove('overlay-open');
        document.body.style.top = '';
        window.scrollTo(0, savedScrollY);
        currentIndex = -1;
    }

    // Handle orientation/resize changes while overlay is open
    window.addEventListener('resize', function() {
        if (currentIndex !== -1) {
            updateViewW();
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
        }
    });

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

            var btn = document.createElement('button');
            btn.className = 'review-btn';

            if (isCuratedPage) {
                // Curated page: remove button beside the clip
                clip.style.position = 'relative';
                clip.style.paddingRight = '44px';
                btn.style.cssText = 'position:absolute;right:0;top:50%;transform:translateY(-50%);width:44px;height:44px;border:none;color:#fff;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;background:none;opacity:0.5;';
                var isRemoved = getList(REMOVE_KEY).indexOf(videoId) !== -1;
                btn.innerHTML = '&times;';
                if (isRemoved) {
                    clip.style.opacity = '0.3';
                    btn.style.opacity = '1';
                    btn.style.color = 'rgba(200,0,0,1)';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowRemoved = toggleInList(REMOVE_KEY, videoId);
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
            } else {
                // Archive pages: button beside the clip, outside the image
                clip.style.position = 'relative';
                clip.style.paddingRight = '44px';
                btn.style.cssText = 'position:absolute;right:0;top:50%;transform:translateY(-50%);width:44px;height:44px;border:none;color:#fff;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;background:none;opacity:0.5;';
                var isAdded = getList(ADD_KEY).indexOf(videoId) !== -1;
                if (isAdded) {
                    btn.textContent = '\u2713';
                    btn.style.opacity = '1';
                    btn.style.color = 'rgba(0,180,80,1)';
                } else {
                    btn.textContent = '+';
                }
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var nowAdded = toggleInList(ADD_KEY, videoId);
                    if (nowAdded) {
                        btn.textContent = '\u2713';
                        btn.style.opacity = '1';
                        btn.style.color = 'rgba(0,180,80,1)';
                    } else {
                        btn.textContent = '+';
                        btn.style.opacity = '0.5';
                        btn.style.color = '#fff';
                    }
                });
                clip.appendChild(btn);
            }
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
            clip.style.position = '';
            clip.style.paddingRight = '';
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
