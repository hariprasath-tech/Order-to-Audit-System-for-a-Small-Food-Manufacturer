/**
 * Main Application Runtime
 * Theme orchestration, low-power detection, offline banner,
 * HTMX globalViewTransitions, Alpine v3 keyboard handler, and PWA Service Worker lifecycle.
 */

(function () {
  'use strict';

  if (window.__ota_app_init) return;
  window.__ota_app_init = true;

  const App = {
    /**
     * Initializes Theme (Light, Dark, System) and detects Low-Power/Save-Data modes
     */
    initTheme: function () {
      const storedTheme = localStorage.getItem('theme') || 'system';
      this.applyTheme(storedTheme, false);

      // Low-Power & Save-Data Hardware Detection (Disables ambient grain overlay)
      const isSaveData = navigator.connection && navigator.connection.saveData;
      const isLowMemory = navigator.deviceMemory && navigator.deviceMemory < 4;
      const isLowConcurrency = navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2;

      if (isSaveData || isLowMemory || isLowConcurrency) {
        document.documentElement.setAttribute('data-low-power', 'true');
      }

      // Listen for OS theme shifts if in system mode
      const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
      darkQuery.addEventListener('change', () => {
        if ((localStorage.getItem('theme') || 'system') === 'system') {
          this.applyTheme('system', true);
        }
      });
    },

    /**
     * Applies theme classes and data attributes
     */
    applyTheme: function (theme, animate = true) {
      const root = document.documentElement;
      let effectiveTheme = theme;

      if (theme === 'system') {
        effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }

      if (animate && window.MotionRegistry && window.MotionRegistry.isMotionEnabled()) {
        root.classList.add('theme-transition');
        setTimeout(() => root.classList.remove('theme-transition'), 300);
      }

      if (effectiveTheme === 'dark') {
        root.classList.add('dark');
        root.setAttribute('data-theme', 'dark');
      } else {
        root.classList.remove('dark');
        root.setAttribute('data-theme', 'light');
      }

      localStorage.setItem('theme', theme);
      window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme, effectiveTheme } }));
    },

    /**
     * Network Status Monitoring for the Offline Banner
     */
    initNetworkMonitor: function () {
      const banner = document.getElementById('offline-banner');
      if (!banner) return;

      const updateStatus = () => {
        if (!navigator.onLine) {
          banner.classList.add('is-visible');
          banner.setAttribute('aria-hidden', 'false');
        } else {
          banner.classList.remove('is-visible');
          banner.setAttribute('aria-hidden', 'true');
        }
      };

      window.addEventListener('online', updateStatus);
      window.addEventListener('offline', updateStatus);
      updateStatus();
    },

    /**
     * Service Worker Registration for PWA Shell
     */
    initPWA: function () {
      if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).then((reg) => {
          console.debug('[PWA] Service Worker active with scope:', reg.scope);
        }).catch((err) => {
          console.debug('[PWA] Service Worker registration skipped:', err.message);
        });
      }
    },

    /**
     * Dispatches cache clearance to the Service Worker on user logout
     */
    clearCachesOnLogout: function () {
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ action: 'CLEAR_CACHES' });
      }
    },

    /**
     * Intercepts logout actions ([data-logout]) to flush client caches before request dispatch
     */
    initLogoutHandler: function () {
      document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-logout]');
        if (trigger) {
          this.clearCachesOnLogout();
        }
      }, true);

      document.addEventListener('submit', (e) => {
        if (e.target && e.target.matches('form[data-logout]')) {
          this.clearCachesOnLogout();
        }
      }, true);
    },

    /**
     * Configures HTMX global View Transitions and CSRF headers
     */
    initHTMX: function () {
      const setupHTMX = () => {
        if (typeof htmx === 'undefined') return;

        htmx.config.globalViewTransitions = true;

        function getCookie(name) {
          let cookieValue = null;
          if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
              const cookie = cookies[i].trim();
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
              }
            }
          }
          return cookieValue;
        }

        document.addEventListener('htmx:configRequest', (event) => {
          const csrfToken = getCookie('csrftoken') ||
            (document.querySelector('meta[name="csrf-token"]') ? document.querySelector('meta[name="csrf-token"]').content : '');
          if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken;
          }
        });
      };

      if (typeof htmx !== 'undefined') {
        setupHTMX();
      } else {
        document.addEventListener('DOMContentLoaded', setupHTMX);
      }
    },

    /**
     * Global Keyboard Operability using Alpine v3 API
     * Dismisses top-most dialog with [data-dialog-open="true"] via Alpine.$data(el).open = false
     */
    initKeyboard: function () {
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          const openDialog = document.querySelector('[data-dialog-open="true"]');
          if (openDialog && typeof window.Alpine !== 'undefined' && typeof window.Alpine.$data === 'function') {
            const alpineData = window.Alpine.$data(openDialog);
            if (alpineData && 'open' in alpineData) {
              alpineData.open = false;
            }
          }
        }
      });
    }
  };

  // Bootstrap
  App.initTheme();
  App.initHTMX();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      App.initNetworkMonitor();
      App.initPWA();
      App.initLogoutHandler();
      App.initKeyboard();
    });
  } else {
    App.initNetworkMonitor();
    App.initPWA();
    App.initLogoutHandler();
    App.initKeyboard();
  }

  window.App = App;
})();
