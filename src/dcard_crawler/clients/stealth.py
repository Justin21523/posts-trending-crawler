"""Advanced stealth patches for Playwright browsers."""

STEALTH_SCRIPTS = """
// Patch 1: Disable webdriver flag
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined,
  configurable: true
});

// Patch 2: Spoof plugins and mimetypes
const fakePlugins = [
  { name: 'PDF Viewer', filename: 'internal-pdf-viewer' },
  { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
  { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' },
  { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer' },
  { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer' }
];

Object.defineProperty(navigator, 'plugins', {
  get: () => Object.assign(fakePlugins, {
    item: i => fakePlugins[i],
    namedItem: n => fakePlugins.find(p => p.name === n),
    refresh: () => {},
    length: fakePlugins.length
  }),
  configurable: true
});

Object.defineProperty(navigator, 'mimeTypes', {
  get: () => ({ length: 2, item: i => null, namedItem: n => null }),
  configurable: true
});

// Patch 3: Spoof window.chrome
if (!window.chrome) window.chrome = {};

window.chrome.app = {
  isInstalled: false,
  InstallState: {
    DISABLED: 'disabled',
    INSTALLED: 'installed',
    NOT_INSTALLED: 'not_installed'
  },
  RunningState: {
    CANNOT_RUN: 'cannot_run',
    READY_TO_RUN: 'ready_to_run',
    RUNNING: 'running'
  }
};

window.chrome.runtime = {
  OnInstalledReason: {
    CHROME_UPDATE: 'chrome_update',
    INSTALL: 'install',
    SHARED_MODULE_UPDATE: 'shared_module_update',
    UPDATE: 'update'
  },
  OnRestartRequiredReason: {
    APP_UPDATE: 'app_update',
    OS_UPDATE: 'os_update',
    PERIODIC: 'periodic'
  },
  PlatformArch: {
    ARM: 'arm',
    ARM64: 'arm64',
    MIPS: 'mips',
    MIPS64: 'mips64',
    X86_32: 'x86-32',
    X86_64: 'x86-64'
  },
  PlatformOs: {
    ANDROID: 'android',
    CROS: 'cros',
    LINUX: 'linux',
    MAC: 'mac',
    OPENBSD: 'openbsd',
    WIN: 'win'
  },
  RequestUpdateCheckStatus: {
    NO_UPDATE: 'no_update',
    THROTTLED: 'throttled',
    UPDATE_AVAILABLE: 'update_available'
  },
  id: undefined,
  connect: () => {},
  sendMessage: () => {}
};

window.chrome.loadTimes = function() {
  return {
    requestTime: Date.now() / 1000,
    startLoadTime: Date.now() / 1000,
    commitLoadTime: Date.now() / 1000,
    finishDocumentLoadTime: Math.random() * 2,
    finishLoadTime: Math.random() * 3 + 2,
    firstPaintTime: Math.random() * 1.5 + 0.5,
    firstPaintAfterLoadTime: 0,
    navigationType: 'Other',
    wasFetchedViaSpdy: true,
    wasNpnNegotiated: true,
    npnNegotiatedProtocol: 'h2',
    wasAlternateProtocolAvailable: false,
    connectionInfo: 'h2'
  };
};

window.chrome.csi = function() {
  return {
    startE: Date.now(),
    onloadT: Date.now(),
    pageT: 3000 + Math.random() * 1000,
    tran: 15
  };
};

// Patch 4: Fix navigator.permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
  parameters.name === 'notifications'
    ? Promise.resolve({ state: Notification.permission })
    : originalQuery(parameters)
);

// Patch 5: Spoof WebGL vendor/renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
  if (parameter === 37445) return 'Intel Inc.';
  if (parameter === 37446) return 'Intel Iris OpenGL Engine';
  return getParameter.call(this, parameter);
};

// Patch 6: Fix languages
Object.defineProperty(navigator, 'language', {
  get: () => 'zh-TW',
  configurable: true
});
Object.defineProperty(navigator, 'languages', {
  get: () => ['zh-TW', 'zh', 'en-US', 'en'],
  configurable: true
});

// Patch 7: iframe contentWindow isolation
const origCreateElement = document.createElement.bind(document);
document.createElement = function(...args) {
  const element = origCreateElement(...args);
  if (args[0] && args[0].toLowerCase() === 'iframe') {
    Object.defineProperty(element, 'contentWindow', {
      get: function() {
        const win = this._contentWindow;
        if (win) {
          Object.defineProperty(win.navigator, 'webdriver', {
            get: () => undefined
          });
        }
        return win;
      }
    });
  }
  return element;
};

// Patch 8: Remove automation-related properties
delete navigator.__proto__.webdriver;

// Patch 9: Spoof connection effective type
if (!navigator.connection) {
  Object.defineProperty(navigator, 'connection', {
    get: () => ({
      effectiveType: '4g',
      rtt: 50,
      downlink: 10,
      saveData: false
    }),
    configurable: true
  });
}

// Patch 10: Hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
  get: () => 8,
  configurable: true
});

// Patch 11: Device memory
Object.defineProperty(navigator, 'deviceMemory', {
  get: () => 8,
  configurable: true
});

// Patch 12: Canvas fingerprint noise
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
  const ctx = this.getContext('2d');
  if (ctx) {
    const imageData = ctx.getImageData(0, 0, this.width, this.height);
    for (let i = 0; i < imageData.data.length; i += 4) {
      imageData.data[i] += Math.floor(Math.random() * 3) - 1;
    }
    ctx.putImageData(imageData, 0, 0);
  }
  return originalToDataURL.call(this, type);
};
"""


async def apply_stealth_to_context(context):
    """Apply stealth scripts to all pages in a browser context.

    Args:
        context: Playwright BrowserContext object
    """
    await context.add_init_script(STEALTH_SCRIPTS)
