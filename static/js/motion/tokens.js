/**
 * JavaScript Motion Tokens & Physics
 * Single source of truth for duration, easing, distances, and staggers across all animations.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MOTION_TOKENS = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  return {
    durations: {
      instant: 0.10,   // seconds for GSAP
      fast: 0.18,
      base: 0.28,
      slow: 0.48,
      hero: 0.90,
      ms: {
        instant: 100,  // ms for CSS/JS timeouts
        fast: 180,
        base: 280,
        slow: 480,
        hero: 900
      }
    },

    easings: {
      // CSS cubic-bezier definitions
      css: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        emphasize: 'cubic-bezier(0.05, 0.7, 0.1, 1)',
        exit: 'cubic-bezier(0.3, 0, 0.8, 0.15)',
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)'
      },
      // GSAP equivalents
      gsap: {
        standard: 'power2.out',
        emphasize: 'power3.out',
        exit: 'power2.in',
        spring: 'back.out(1.4)'
      }
    },

    stagger: {
      item: 0.04,   // 40ms
      card: 0.07,   // 70ms
      hero: 0.06    // 60ms
    },

    distances: {
      micro: 4,
      small: 12,
      medium: 24,
      large: 48
    }
  };
}));
