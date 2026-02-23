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

    // Fullscreen image overlay with swipe navigation
    var allClips = Array.prototype.slice.call(document.querySelectorAll('.clip'));
    var overlay = null;
    var track = null;
    var panels = [];
    var panelImgs = [];
    var currentIndex = -1;
    var savedScrollY = 0;
    var viewW = 0;

    function getClipSrc(index) {
        return allClips[index].getAttribute('data-src');
    }

    function getClipCaption(index) {
        if (index < 0 || index >= allClips.length) return '';
        return allClips[index].getAttribute('data-caption') || '';
    }

    var captionEl = null;
    // Zoom state
    var zoomScale = 1;
    var zoomX = 0;
    var zoomY = 0;
    var isZoomed = false;

    function resetZoom() {
        zoomScale = 1;
        zoomX = 0;
        zoomY = 0;
        isZoomed = false;
        if (panelImgs[1]) {
            panelImgs[1].style.transform = '';
            panelImgs[1].style.transformOrigin = '';
        }
    }

    function applyZoom(img) {
        if (zoomScale <= 1) {
            img.style.transform = '';
            img.style.transformOrigin = '';
            isZoomed = false;
        } else {
            img.style.transformOrigin = '0 0';
            img.style.transform = 'translate(' + zoomX + 'px,' + zoomY + 'px) scale(' + zoomScale + ')';
            isZoomed = true;
        }
    }

    function createOverlay() {
        var style = document.createElement('style');
        style.textContent = '.overlay-open{position:fixed!important;width:100%!important;overflow:hidden!important;}';
        document.head.appendChild(style);

        overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:9999;display:none;touch-action:none;overflow:hidden;';

        track = document.createElement('div');
        track.style.cssText = 'display:flex;height:100%;will-change:transform;';

        for (var i = 0; i < 3; i++) {
            var panel = document.createElement('div');
            panel.style.cssText = 'height:100%;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:#000;overflow:hidden;';
            var img = document.createElement('img');
            img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;will-change:transform;';
            panel.appendChild(img);
            track.appendChild(panel);
            panels.push(panel);
            panelImgs.push(img);
        }

        overlay.appendChild(track);

        // Caption bar
        captionEl = document.createElement('div');
        captionEl.style.cssText = 'position:absolute;bottom:0;left:0;right:0;z-index:10;padding:16px 20px;background:linear-gradient(transparent,rgba(0,0,0,0.8));color:#fff;font-size:0.9rem;font-weight:300;line-height:1.6;opacity:0.8;pointer-events:none;display:none;';
        overlay.appendChild(captionEl);

        var closeBtn = document.createElement('div');
        closeBtn.style.cssText = 'position:absolute;top:12px;right:16px;z-index:10;color:#fff;font-size:28px;opacity:0.6;cursor:pointer;padding:8px;line-height:1;';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            closeOverlay();
        });
        overlay.appendChild(closeBtn);

        // Touch handling
        var touchStartX = 0;
        var touchStartY = 0;
        var touchStartTime = 0;
        var dragging = false;
        var dragOffset = 0;
        var directionLocked = false;
        // Pinch state
        var pinching = false;
        var pinchStartDist = 0;
        var pinchStartScale = 1;
        var pinchStartZoomX = 0;
        var pinchStartZoomY = 0;
        var pinchMidX = 0;
        var pinchMidY = 0;
        var panStartX = 0;
        var panStartY = 0;
        var panStartZoomX = 0;
        var panStartZoomY = 0;

        function getTouchDist(e) {
            var dx = e.touches[0].clientX - e.touches[1].clientX;
            var dy = e.touches[0].clientY - e.touches[1].clientY;
            return Math.sqrt(dx * dx + dy * dy);
        }

        overlay.addEventListener('touchstart', function(e) {
            if (e.touches.length === 2) {
                pinching = true;
                dragging = false;
                pinchStartDist = getTouchDist(e);
                pinchStartScale = zoomScale;
                pinchStartZoomX = zoomX;
                pinchStartZoomY = zoomY;
                pinchMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                pinchMidY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
                return;
            }
            if (isZoomed && e.touches.length === 1) {
                panStartX = e.touches[0].clientX;
                panStartY = e.touches[0].clientY;
                panStartZoomX = zoomX;
                panStartZoomY = zoomY;
                dragging = false;
                directionLocked = false;
                return;
            }
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            dragging = false;
            directionLocked = false;
            dragOffset = 0;
            track.style.transition = 'none';
        }, {passive: true});

        overlay.addEventListener('touchmove', function(e) {
            if (pinching && e.touches.length === 2) {
                e.preventDefault();
                var dist = getTouchDist(e);
                var newScale = Math.max(1, Math.min(5, pinchStartScale * (dist / pinchStartDist)));
                var midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                var midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
                // Keep the point under the original pinch center stationary
                var imgX = (pinchMidX - pinchStartZoomX) / pinchStartScale;
                var imgY = (pinchMidY - pinchStartZoomY) / pinchStartScale;
                zoomScale = newScale;
                zoomX = midX - imgX * newScale;
                zoomY = midY - imgY * newScale;
                if (zoomScale <= 1) { zoomX = 0; zoomY = 0; }
                applyZoom(panelImgs[1]);
                return;
            }
            if (isZoomed && e.touches.length === 1) {
                e.preventDefault();
                var dx = e.touches[0].clientX - panStartX;
                var dy = e.touches[0].clientY - panStartY;
                zoomX = panStartZoomX + dx;
                zoomY = panStartZoomY + dy;
                applyZoom(panelImgs[1]);
                return;
            }

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
                if (currentIndex === 0 && dx > 0) dx = dx * 0.3;
                if (currentIndex === allClips.length - 1 && dx < 0) dx = dx * 0.3;
                var baseOffset = -viewW;
                track.style.transform = 'translateX(' + (baseOffset + dx) + 'px)';
            }
        }, {passive: false});

        overlay.addEventListener('touchend', function(e) {
            if (pinching) {
                if (e.touches.length === 0) {
                    pinching = false;
                    if (zoomScale <= 1.05) resetZoom();
                }
                return;
            }
            if (isZoomed) return;

            var dx = e.changedTouches[0].clientX - touchStartX;
            var dt = Date.now() - touchStartTime;
            var velocity = Math.abs(dx) / dt;

            if (dragging) {
                var threshold = viewW * 0.25;
                var swipedFast = velocity > 0.3 && Math.abs(dx) > 30;

                if ((Math.abs(dx) > threshold || swipedFast) && dx < 0 && currentIndex < allClips.length - 1) {
                    animateToPanel(2, function() { setCurrentClip(currentIndex + 1, 1); });
                } else if ((Math.abs(dx) > threshold || swipedFast) && dx > 0 && currentIndex > 0) {
                    animateToPanel(0, function() { setCurrentClip(currentIndex - 1, -1); });
                } else {
                    animateToPanel(1);
                }
            }

            dragging = false;
        });

        // Double-tap to zoom
        var lastTap = 0;
        overlay.addEventListener('touchend', function(e) {
            if (e.touches.length > 0 || pinching) return;
            var now = Date.now();
            if (now - lastTap < 300) {
                if (isZoomed) {
                    resetZoom();
                } else {
                    zoomScale = 2.5;
                    var rect = panelImgs[1].getBoundingClientRect();
                    var tapX = e.changedTouches[0].clientX;
                    var tapY = e.changedTouches[0].clientY;
                    zoomX = -(tapX - rect.left) * (zoomScale - 1);
                    zoomY = -(tapY - rect.top) * (zoomScale - 1);
                    applyZoom(panelImgs[1]);
                }
            }
            lastTap = now;
        });

        document.addEventListener('keydown', function(e) {
            if (currentIndex === -1) return;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                if (currentIndex < allClips.length - 1) {
                    animateToPanel(2, function() { setCurrentClip(currentIndex + 1, 1); });
                }
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                if (currentIndex > 0) {
                    animateToPanel(0, function() { setCurrentClip(currentIndex - 1, -1); });
                }
            } else if (e.key === 'Escape') {
                closeOverlay();
            }
        });

        document.body.appendChild(overlay);
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
            setTimeout(finish, 300);
        }
    }

    function loadPanel(panelIndex, clipIndex) {
        var img = panelImgs[panelIndex];
        if (clipIndex < 0 || clipIndex >= allClips.length) {
            img.removeAttribute('src');
            return;
        }
        var src = getClipSrc(clipIndex);
        if (img.getAttribute('src') === src) return;
        img.src = src;
    }

    function updateCaption(index) {
        if (!captionEl) return;
        var text = getClipCaption(index);
        if (text) {
            captionEl.textContent = text;
            captionEl.style.display = 'block';
        } else {
            captionEl.style.display = 'none';
        }
    }

    function setCurrentClip(index, direction) {
        currentIndex = index;
        resetZoom();
        updateCaption(index);

        if (direction === 1) {
            var tmpImg = panelImgs[0];
            panelImgs[0] = panelImgs[1];
            panelImgs[1] = panelImgs[2];
            panelImgs[2] = tmpImg;
            track.appendChild(panelImgs[0].parentNode);
            track.appendChild(panelImgs[1].parentNode);
            track.appendChild(panelImgs[2].parentNode);
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
            loadPanel(0, index - 1);
            loadPanel(2, index + 1);
        } else if (direction === -1) {
            var tmpImg2 = panelImgs[2];
            panelImgs[2] = panelImgs[1];
            panelImgs[1] = panelImgs[0];
            panelImgs[0] = tmpImg2;
            track.appendChild(panelImgs[0].parentNode);
            track.appendChild(panelImgs[1].parentNode);
            track.appendChild(panelImgs[2].parentNode);
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
            loadPanel(0, index - 1);
            loadPanel(2, index + 1);
        } else {
            loadPanel(0, index - 1);
            loadPanel(1, index);
            loadPanel(2, index + 1);
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
        }
    }

    function updateViewW() {
        viewW = overlay.clientWidth;
        track.style.width = (viewW * 3) + 'px';
        for (var i = 0; i < panelImgs.length; i++) {
            panelImgs[i].parentNode.style.width = viewW + 'px';
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
        panelImgs.forEach(function(img) { img.removeAttribute('src'); });
        overlay.style.display = 'none';
        document.body.classList.remove('overlay-open');
        document.body.style.top = '';
        window.scrollTo(0, savedScrollY);
        currentIndex = -1;
    }

    window.addEventListener('resize', function() {
        if (currentIndex !== -1) {
            updateViewW();
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + (-viewW) + 'px)';
        }
    });

    // Click-to-fullscreen for all clips
    allClips.forEach(function(clip, index) {
        clip.addEventListener('click', function(e) {
            if (e.target.classList.contains('photo-review-btn')) return;
            openOverlay(index);
        });
    });

    // Review mode
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
