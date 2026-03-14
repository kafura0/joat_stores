/**
 * Lighthouse CI configuration — Story 3.2
 *
 * Enforces < 1.5s interactive time on simulated 3G for the public menu page.
 * Blocks merges that regress below the threshold (FR94).
 *
 * Run via: lhci autorun
 */

module.exports = {
  ci: {
    collect: {
      url: ["http://localhost:3000/menu/"],
      numberOfRuns: 3,
      settings: {
        // Simulate 3G connection
        throttlingMethod: "simulate",
        throttling: {
          rttMs: 150,
          throughputKbps: 1.6 * 1024,
          cpuSlowdownMultiplier: 4,
        },
        // Simulate mobile device
        emulatedFormFactor: "mobile",
        screenEmulation: {
          mobile: true,
          width: 375,
          height: 812,
          deviceScaleFactor: 3,
        },
      },
    },
    assert: {
      assertions: {
        // < 1.5s interactive time (FR94)
        "interactive": ["error", { maxNumericValue: 1500 }],
        // Performance score >= 0.8
        "categories:performance": ["warn", { minScore: 0.8 }],
        // Accessibility score >= 0.9
        "categories:accessibility": ["warn", { minScore: 0.9 }],
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
