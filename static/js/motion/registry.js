/**
 * Motion Registry Engine
 * Declarative data-anim observer, lifecycle manager, HTMX swap hooks,
 * and strict reduced-motion/low-power safety gates.
 */

(function () {
  'use strict';

  if (window.__ota_motion_init) return;
  window.__ota_motion_init = true;

  const TOKENS = window.MOTION_TOKENS || {
    durations: { base: 0.28 },
    easings: { css: { emphasize: 'cubic-bezier(0.05, 0.7, 0.1, 1)' } },
    stagger: { item: 0.04 }
  };

  // Map of GSAP / Motion Contexts -> Scope Elements
  const contextMap = new Map();
  let intersectionObserver = null;

  const MotionRegistry = {
    /**
     * Evaluates if motion is permitted based on OS setting, URL param, or localStorage.
     */
    isMotionEnabled: function () {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('motion') === 'off') return false;

      const userPreference = localStorage.getItem('reduce_motion');
      if (userPreference === 'true') return false;

      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      return !mediaQuery.matches;
    },

    /**
     * Initializes the IntersectionObserver for declarative [data-anim] elements.
     */
    initObserver: function () {
      if (intersectionObserver) {
        intersectionObserver.disconnect();
      }

      intersectionObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target;
            this.animateElement(el);
            observer.unobserve(el);
          }
        });
      }, {
        root: null,
        rootMargin: '0px 0px -40px 0px',
        threshold: 0.15
      });
    },

    /**
     * Triggers animation with transient will-change.
     * Cleans up will-change ONLY when the transition originated from el itself (not child bubbling).
     */
    animateElement: function (el) {
      if (!el) return;
      el.classList.add('anim-animating');
      el.classList.add('is-animated');

      const cleanupWillChange = (event) => {
        if (event && event.target !== el) return;
        el.classList.remove('anim-animating');
        el.removeEventListener('transitionend', cleanupWillChange);
      };

      el.addEventListener('transitionend', cleanupWillChange);
      // Safety timeout in case transitionend does not fire
      setTimeout(() => {
        el.classList.remove('anim-animating');
        el.removeEventListener('transitionend', cleanupWillChange);
      }, 650);
    },

    /**
     * Scans and prepares declarative animations within a given root container.
     */
    initAnimations: function (root = document) {
      const motionActive = this.isMotionEnabled();
      document.documentElement.setAttribute('data-reduce-motion', (!motionActive).toString());

      const animElements = root.querySelectorAll ? root.querySelectorAll('[data-anim]') : [];

      if (!motionActive) {
        animElements.forEach((el) => {
          el.classList.add('is-animated');
          el.classList.remove('anim-animating');
        });
        return;
      }

      if (!intersectionObserver) {
        this.initObserver();
      }

      animElements.forEach((el) => {
        if (!el.classList.contains('is-animated')) {
          intersectionObserver.observe(el);
        }
      });
    },

    /**
     * Registers a motion context with its scoped container DOM element.
     * @param {Object} ctx - GSAP Context or custom context with a revert() method.
     * @param {HTMLElement} scopeEl - The DOM container that owns this context.
     */
    registerContext: function (ctx, scopeEl) {
      if (ctx && typeof ctx.revert === 'function') {
        contextMap.set(ctx, scopeEl || document.body);
      }
    },

    /**
     * Reverts and cleans up all contexts scoped inside the given target element.
     * Called on htmx:beforeSwap to guarantee zero memory leaks or ghost animations.
     */
    cleanup: function (targetEl) {
      if (!targetEl) return;
      for (const [ctx, scopeEl] of contextMap.entries()) {
        if (scopeEl && (targetEl === scopeEl || targetEl.contains(scopeEl))) {
          try {
            ctx.revert();
          } catch (e) {
            console.warn('[MotionRegistry] Error reverting context:', e);
          }
          contextMap.delete(ctx);
        }
      }
    },

    /**
     * Complete teardown of all registered contexts.
     */
    cleanupAll: function () {
      for (const [ctx] of contextMap.entries()) {
        try { ctx.revert(); } catch (e) { /* ignore */ }
      }
      contextMap.clear();
    },

    /**
     * Console-testable self-test for verifying context registration and target cleanup.
     * Run in DevTools via: window.MotionRegistry._testContextCleanup()
     */
    _testContextCleanup: function () {
      const container = document.createElement('div');
      const inner = document.createElement('div');
      container.appendChild(inner);
      document.body.appendChild(container);

      let reverted = false;
      const testCtx = {
        revert: () => { reverted = true; }
      };

      MotionRegistry.registerContext(testCtx, inner);
      const registered = contextMap.has(testCtx);

      // Trigger cleanup on parent container
      MotionRegistry.cleanup(container);
      const isReverted = reverted;
      const removedFromMap = !contextMap.has(testCtx);

      container.remove();

      if (registered && isReverted && removedFromMap) {
        console.log('[MotionRegistry Test] Context Cleanup Passed: Registered -> Reverted -> Removed ✅');
        return true;
      } else {
        console.error('[MotionRegistry Test] FAILED:', { registered, isReverted, removedFromMap });
        return false;
      }
    }
  };

  // Lifecycle Initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MotionRegistry.initAnimations(document));
  } else {
    MotionRegistry.initAnimations(document);
  }

  // HTMX Integration Hooks (Strict Memory Leak Prevention)
  document.addEventListener('htmx:beforeSwap', (evt) => {
    const target = evt.detail.target;
    if (target) {
      MotionRegistry.cleanup(target);
    }
  });

  document.addEventListener('htmx:afterSwap', (evt) => {
    const target = evt.detail.target;
    if (target) {
      MotionRegistry.initAnimations(target);

      // Flash highlight on newly swapped row or card
      if (target.tagName === 'TR' || target.classList.contains('htmx-swapped-row')) {
        target.classList.add('htmx-swapped-row');
      }
    }
  });

  // Listen for system reduced-motion changes live
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (motionQuery.addEventListener) {
    motionQuery.addEventListener('change', () => {
      MotionRegistry.initAnimations(document);
    });
  }

  window.MotionRegistry = MotionRegistry;
})();
